import os

VIDEO_EXTENSIONS = (".mkv", ".mp4", ".avi", ".mov")


class MediaLibrary:
    """
    Lists video files under a root directory, including nested folders,
    and safely resolves paths coming from the frontend.
    """

    def __init__(self, root_dir):
        self.root_dir = os.path.abspath(root_dir)

    def list_files(self, relative_path=""):
        """
        Return the contents of one directory (relative to root_dir) as a
        list of {name, type, path} dicts - type is "file" or "directory".
        Does NOT recurse automatically; the frontend calls this again with
        a subdirectory's path when the user clicks into it.
        """
        target_dir = self._resolve(relative_path)

        entries = []
        for name in sorted(os.listdir(target_dir)):
            if name.startswith("."):
                continue  # skip hidden files - macOS AppleDouble junk (._Movie.mp4),
                          # .DS_Store, .Trashes, etc. commonly left on USB drives

            full_path = os.path.join(target_dir, name)
            entry_path = os.path.join(relative_path, name)

            if os.path.isdir(full_path):
                entries.append({"name": name, "type": "directory", "path": entry_path})
            elif name.lower().endswith(VIDEO_EXTENSIONS):
                entries.append({"name": name, "type": "file", "path": entry_path})

        return entries

    def resolve_file(self, relative_path):
        """
        Resolve a relative file path to a safe absolute path, for casting.
        Raises ValueError if the path escapes root_dir or isn't a real file.
        """
        absolute_path = self._resolve(relative_path)

        if not os.path.isfile(absolute_path):
            raise ValueError(f"Not a file: {relative_path!r}")

        return absolute_path

    def _resolve(self, relative_path):
        """
        Turn a relative path from the frontend into a safe absolute path.
        Refuses anything that tries to escape root_dir (e.g. "../../etc"),
        since relative_path ultimately comes from user-controlled input.
        """
        target = os.path.abspath(os.path.join(self.root_dir, relative_path))

        if not (target == self.root_dir or target.startswith(self.root_dir + os.sep)):
            raise ValueError(f"Path escapes media root: {relative_path!r}")

        return target