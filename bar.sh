#!/bin/bash

# Build the docker containers.
if [[ $1 = "build" ]]; then

	# Build the containers.
	echo -e "\033[01;36mBuilding container for Streamline...\033[0;0m\n"

	if [[ $2 = "-nc" ]]; then
		docker compose build --no-cache
	else
		docker compose build
	fi

	if [ $? -eq 0 ]; then
		echo -e "\n\033[01;102m BUILD COMPLETED \033[0;0m\n"
	else
		echo -e "\n\033[01;91m BUILD FAILED \033[0;0m\n"
		exit
	fi

fi

# mount_usb.sh - mount every attached USB drive under /mnt/usbN
# Run with sudo: sudo ./mount_usb.sh

MOUNT_BASE="/mnt/usb"
INDEX=1

# List top-level block devices and their transport type (usb, sata, mmc...).
# -n = no header, -r = raw (easy to parse with awk)
for DEVICE in $(lsblk -o NAME,TRAN -nr | awk '$2=="usb" {print $1}'); do

    # A USB stick usually has partitions (sda1, sda2...). Find them.
    PARTITIONS=(/dev/${DEVICE}*[0-9])

    # If no partitions exist (some drives have a filesystem directly on the
    # whole disk with no partition table), fall back to the raw device.
    if [ ! -e "${PARTITIONS[0]}" ]; then
        PARTITIONS=(/dev/${DEVICE})
    fi

    for PARTITION in "${PARTITIONS[@]}"; do
        [ -e "$PARTITION" ] || continue

        # Skip anything already mounted.
        if mount | grep -q "^$PARTITION "; then
            echo "$PARTITION is already mounted, skipping"
            continue
        fi

        MOUNT_POINT="${MOUNT_BASE}${INDEX}"
        mkdir -p "$MOUNT_POINT"

        if mount "$PARTITION" "$MOUNT_POINT"; then
            echo "Mounted $PARTITION at $MOUNT_POINT"
            INDEX=$((INDEX + 1))
        else
            echo "Failed to mount $PARTITION"
            rmdir "$MOUNT_POINT"
        fi
    done
done

# Run the docker containers in detached mode.
docker compose up Streamline -d