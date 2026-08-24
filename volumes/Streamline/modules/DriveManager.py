from modules.SL_CM import SL_CM

import os
import pyudev
import asyncio
import subprocess

class DriveManager (SL_CM) :
    def __init__ (self, mount_directory = "/mnt/", update_interval = 10) :
        super().__init__(update_interval)

        self.mount_dir       = mount_directory
        self._mounted_drives = {}

        # Setup the pyudev monitor in a way that wont block the SL_Task method
        self._context = pyudev.Context()
        self._monitor = pyudev.Monitor.from_netlink(self._context)
        self._monitor.filter_by(subsystem = "block")

    async def __aenter__ (self) :
        await super().__aenter__()

        # Mount drives that are already plugged in.
        for drive in self._context.list_devices(subsystem = "block") :
            if self._is_usb(drive) and drive.device_node not in self._mounted_drives :
                self.mount_drive(drive)
        return self

    async def SL_Task (self) :
        # Monitor the kernel for newly plugged in drives.
        # If any are found, mount them.
        
        # Run blocking call in a worker thread.
        drive = await asyncio.to_thread(self._monitor.poll, self.interval)
        if drive is None:
            return

        # If the drive isnt a usb device then return.
        if not self._is_usb(drive) :
            return

        if (drive.action == "add") :
            self.mount_drive(drive)
        
        if (drive.action == "remove") :
            self.unmount_drive(drive)

    def _is_usb (self, drive) :
        # Determine if a drive is a usb drive.
        
        # If the drive type is not partition or disk do not attempt to mount it.
        if drive.device_type not in ("partition", "disk") :
            return False
        
        # If there is no filesystem on the drive do not attempt to mount it.
        if not drive.get("ID_FS_TYPE") :
            return False
        
        return drive.find_parent("usb") is not None

    def mount_drive(self, drive) :
        # Mount a drive.
        label = drive.get("ID_FS_LABEL")

        # Create the mount name and mount point.
        mount_name  = label if label else os.path.basename(drive.device_node)
        mount_point = os.path.join(self.mount_dir, mount_name)

        self.log(f"Attempting to mount {mount_name}")

        # Create the directory of the mount point.
        os.makedirs(mount_point, exist_ok = True)

        try :
            # Attempt to mount the drive at the mount point.
            subprocess.run(
                [
                    "mount", drive.device_node, mount_point
                ], check = True
            )
            # Record the mounted drive in the _mounted_drives directory.
            self._mounted_drives[drive.device_node] = mount_point
            self.log(f"Mounted {mount_name}.")

        except subprocess.CalledProcessError as e :
            self.log(f"Failed to mount {mount_name} : {e}")

        pass

    def unmount_drive(self, drive) :
        # Unmount a drive.
        
        # Remove the mount point from the mounted drives directory.
        mount_point = self._mounted_drives.pop(drive.device_node, None)
        if mount_point is None:
            self.log(f"{drive.device_node} is unmounted.")
            return
        
        # Attempt to unmount the drive.
        try :
            subprocess.run(
                [
                    "umount", mount_point
                ], check = True
            )
            self.log(f"Unmounted {mount_point}.")
        except subprocess.CalledProcessError as e :
            self.log(f"Failed to unmount {mount_point} : {e}")

        
        # Attempt to cleanup any created directories.
        try :
            os.rmdir(mount_point)
        except OSError as e :
            self.log(f"Could not remove {mount_point} : {e}")