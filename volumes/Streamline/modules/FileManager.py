from modules.SL_CM import SL_CM

import re
import os
import struct
import asyncio
import subprocess

class FileManager (SL_CM) :
    def __init__ (self, media_dir = "/mnt/", update_interval = 15, max_fix_threads = 1) :
        super().__init__(update_interval)

        self._fix_semaphore = asyncio.Semaphore(max_fix_threads)

        self.valid_files = (".mkv", ".mp4", ".avi", ".mov")
        self.valid_icons = (".png", ".jpg", ".webp", ".jpeg")
        self.media_dir = os.path.abspath(media_dir)

        # self.hierarchy is the classified media library - see _build_library().
        # It's what gets served to the frontend directly, no separate transform step.
        self.hierarchy = []
        self.fix_blacklist = []

    async def SL_Task (self) :
        # Scan through the media directory tree and build the classified library.
        # If any files are in the wrong format to be played correct them and add them to the playable list.
        self.hierarchy = self.list_files()

        # Setup a list to hold tasks for fixing the media files.
        fix_tasks = []

        # Iterate through the hierarchy and check all the files are playable.
        # An Item's Media is either a single path (a movie - the Item itself
        # carries "Playable"), or a list of episodes (a season - each episode
        # carries its own "Playable").
        def queue_fix (path, playable) :
            if (playable) :
                return

            # Construct the file path. If its in the blacklist then dont attempt to fix it.
            file_path = os.path.join(self.media_dir, path)
            if (file_path in self.fix_blacklist) :
                return

            # Create the fix task.
            fix_tasks.append(self._fix_non_playable(file_path))

        for title in self.hierarchy :
            for item in title["Items"] :
                if isinstance(item["Media"], list) :
                    for episode in item["Media"] :
                        queue_fix(episode["Path"], episode["Playable"])
                else :
                    queue_fix(item["Media"], item["Playable"])

        # Start the fix tasks.
        if (fix_tasks) :
            # Dont return control back to SL_Task until the fixes are done.
            # This prevents files being added to the fix list multiple times.
            await asyncio.gather(*fix_tasks, return_exceptions=True)

    def natural_sort_key(self, s):
        # Sort the items in the dictionary.
        return [int(text) if text.isdigit() else text.lower()
                for text in re.split(r'(\d+)', s)]

    def list_files (self, directory_path = "", _depth = 0) :
        # Build the classified media library directly while walking the disk.
        #
        # depth 0 (the media root): each sub-folder is a category (e.g. "Movies") -
        #                           its titles are flattened straight into the result.
        # depth 1 (a category)    : each sub-folder is a title, classified as
        #                           "Movie" or "Series" purely by how many Items
        #                           it resolves to. A single file, or a set of
        #                           sub-folders that resolve to exactly one Item,
        #                           is a "Movie". Everything else is a "Series" -
        #                           its Items are either standalone films (Media
        #                           is a path) or seasons (Media is an episode list).

        # Turn a relative path into a safe absolute path.
        # Refuses any path that tries to escape the media directory.
        target_dir = os.path.abspath(os.path.join(self.media_dir, directory_path))
        if not (target_dir == self.media_dir or target_dir.startswith(self.media_dir + os.sep)) :
            raise ValueError (f"Passed path escapes media directory: {directory_path}")

        listing = sorted((e for e in os.listdir(target_dir) if not e.startswith(".")), key = self.natural_sort_key)
        dirs    = [e for e in listing if os.path.isdir(os.path.join(target_dir, e))]

        if (_depth == 0) :
            titles = []
            for category in dirs :
                titles += self.list_files(os.path.join(directory_path, category), 1)
            return titles

        strip = lambda name : re.sub(r'^\d+\s+', '', name)
        titles = []

        for title in dirs :
            title_path, title_dir = os.path.join(directory_path, title), os.path.join(target_dir, title)
            title_listing = sorted((e for e in os.listdir(title_dir) if not e.startswith(".")), key = self.natural_sort_key)
            title_dirs    = [e for e in title_listing if os.path.isdir(os.path.join(title_dir, e))]
            title_files   = [e for e in title_listing if e.lower().endswith(self.valid_files)]

            # A file directly inside the title folder, no sub-folders: a standalone movie.
            if (title_files and not title_dirs) :
                icon = self._find_file_icon(title_listing, title_path)
                items = [self._movie_item(title, icon, title_path, title_dir, title_files[0])]
                titles.append({"Type" : "Movie", "Name" : strip(title), "Items" : items})
                continue

            # Sub-folders: each is either a single film (-> one Item with a
            # path in Media) or a season of episode files (-> one Item whose
            # Media is the list of episodes).
            items = []
            for season_num, sub in enumerate(title_dirs, start = 1) :
                sub_path, sub_dir = os.path.join(title_path, sub), os.path.join(title_dir, sub)
                sub_listing = sorted((e for e in os.listdir(sub_dir) if not e.startswith(".")), key = self.natural_sort_key)
                sub_files   = [e for e in sub_listing if e.lower().endswith(self.valid_files)]
                if not sub_files :
                    continue

                icon = self._find_file_icon(sub_listing, sub_path)

                if (len(sub_files) == 1) :
                    items.append(self._movie_item(sub, icon, sub_path, sub_dir, sub_files[0]))
                else :
                    items.append({
                        "Name" : strip(sub),
                        "Icon" : icon,
                        "Media" : [
                            {
                                "Name"     : f"S{season_num:02d}E{ep_num:02d}",
                                "Path"     : os.path.join(sub_path, f),
                                "Playable" : self.is_file_playable(os.path.join(sub_dir, f))
                            }
                            for ep_num, f in enumerate(sub_files, start = 1)
                        ]
                    })

            # A title of exactly one item is a movie, whatever produced it -
            # a lone sub-folder, or a franchise/series that only ever had one entry.
            kind = "Movie" if len(items) == 1 else "Series"
            titles.append({"Type" : kind, "Name" : strip(title), "Items" : items})

        return titles

    def _movie_item (self, name, icon, entry_path, entry_dir, filename) :
        return {
            "Name"     : re.sub(r'^\d+\s+', '', name),
            "Icon"     : icon,
            "Media"    : os.path.join(entry_path, filename),
            "Playable" : self.is_file_playable(os.path.join(entry_dir, filename))
        }
    
    def _find_file_icon (self, directory_listing, directory_path) :
        # Attempt to find a file named "icon" alongside the media file.

        for candidate in directory_listing :
            candidate_base, candidate_ext = os.path.splitext(candidate)
            if candidate_base == "icon" and candidate_ext.lower() in self.valid_icons :
                return os.path.join(directory_path, candidate)

        return "UNKNOWN"
    
    def is_file_playable (self, file_path) : 
        if not file_path.lower().endswith((".mp4", ".mov")) :
            return True

        boxes = []
        with open(file_path, "rb") as file :
            file.seek(0, 2)
            file_size = file.tell()
            file.seek(0)

            pos = 0
            while pos + 8 <= file_size and len(boxes) < 50 :  # safety cap against malformed files
                file.seek(pos)
                header = file.read(8)
                if len(header) < 8 :
                    break

                size, box_type = struct.unpack(">I4s", header)
                box_type = box_type.decode(errors = "replace")
                boxes.append(box_type)

                if size == 1 :
                    # 64-bit extended size follows immediately after the 8-byte header.
                    ext = file.read(8)
                    if len(ext) < 8 :
                        break
                    size = struct.unpack(">Q", ext)[0]
                elif size == 0 :
                    break  # box extends to EOF

                if size < 8 :
                    break  # malformed box, avoid an infinite loop

                pos += size

        if ("moov" in boxes and "mdat" in boxes) :
            return boxes.index("moov") < boxes.index("mdat")

        return False

    async def _fix_non_playable (self, file_path) :
        async with self._fix_semaphore :
            base, extension = os.path.splitext(file_path)
            tmp_file_path = f"{base}.tmp{extension}"

            self.log(f"Fixing {file_path}")

            try :
                await asyncio.to_thread(
                    subprocess.run,
                    ["ffmpeg", "-y", "-loglevel", "error", "-i", file_path, "-c", "copy", "-movflags", "+faststart", tmp_file_path],
                    check=True,
                    capture_output=True
                    )
            except subprocess.CalledProcessError as e :
                self.log(f"Error fixing {file_path} : {e.stderr.decode(errors='ignore')}")
                self.fix_blacklist.append(file_path)
                return
            
            try :
                os.replace(tmp_file_path, file_path)
            except OSError as e :
                self.log(f"Error replacing {file_path} with fixed version : {e}")
                self.fix_blacklist.append(file_path)
                return

            self.log(f"{file_path} fixed.")