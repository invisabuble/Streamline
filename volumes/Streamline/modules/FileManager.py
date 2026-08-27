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
        self.valid_icons = (".png", ".jpg")
        self.media_dir = os.path.abspath(media_dir)

        # List to store all files, directories within the media directory.
        self.hierarchy = []
        self.fix_blacklist = []

    async def SL_Task (self) :
        # Scan through the list of files in the media directory tree.
        # If any files are in the wrong format to be played correct them and add them to the playable list.
        self.hierarchy = self.list_files()

        # Setup a list to hold tasks for fixing the media files.
        fix_tasks = []

        # Iterate through the hierarchy and check all the files are playable.
        def collect_non_playables (entry) :

            for item in entry:

                # If the item is a file and its not playable then attempt to fix it.
                if (item["Info"]["Type"] == "File" and not item["Info"]["Playable"]) :

                    # Construct the file path. If its in the blacklist then dont attempt to fix it.
                    file_path = os.path.join(self.media_dir, item["Path"])
                    if (file_path in self.fix_blacklist) :
                        continue

                    # Create the fix task.
                    fix_tasks.append(self._fix_non_playable(file_path))

                    continue

                if (item["Info"]["Type"] == "Directory") :
                    collect_non_playables(item["Info"]["Children"])

        collect_non_playables(self.hierarchy)

        # Start the fix tasks.
        if (fix_tasks) :
            # Dont return control back to SL_Task until the fixes are done.
            # This prevents files being added to the fix list multiple times.
            await asyncio.gather(*fix_tasks, return_exceptions=True)

    def natural_sort_key(self, s):
        # Sort the items in the dictionary.
        return [int(text) if text.isdigit() else text.lower()
                for text in re.split(r'(\d+)', s)]

    def list_files (self, directory_path = "") :
        # List all files within a passed directory path.

        # Turn a relative path into a safe absolute path. 
        # Refuses any path that tries to escape the media directory.
        target_dir = os.path.abspath(
            os.path.join(self.media_dir, directory_path)
            )
        if not (
            target_dir == self.media_dir or 
            target_dir.startswith(self.media_dir + os.sep)
            ) :
            raise ValueError (f"Passed path escapes media directory: {directory_path}")
        
        entries = []
        directory_listing = sorted(os.listdir(target_dir), key=self.natural_sort_key)
        icon_file = self._find_file_icon(directory_listing, directory_path)

        for entry in directory_listing:

            # Skip over any hidden files.
            if entry.startswith(".") :
                continue

            full_path  = os.path.join(target_dir, entry)
            entry_path = os.path.join(directory_path, entry)

            Info = None

            if (os.path.isdir(full_path)) :
                Info = {
                    "Type"     : "Directory",
                    "Children" : self.list_files(entry_path)
                }
                
            elif (entry.lower().endswith(self.valid_files)) :
                Info = {
                    "Type"     : "File",
                    "Playable" : self.is_file_playable(full_path),
                    "Icon"     : icon_file
                }

            if (Info) : 
                entries.append(
                    {
                        "Name"     : entry,
                        "Info"     : Info,
                        "Path"     : entry_path
                    }
                )

        return entries
    
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