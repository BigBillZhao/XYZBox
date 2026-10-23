#!/usr/bin/env bash
# This session's new SanDisk USB only. This destroys its current filesystem.
set -euo pipefail
[[ $EUID == 0 ]]
usb=/dev/disk/by-id/usb-USB_SanDisk_3.2Gen1_00023309012526182146-0:0
dev=$(readlink -f "$usb")
[[ -b "$dev" ]]
[[ $(lsblk -dnro SERIAL "$dev" | xargs) == 00023309012526182146 ]]
[[ $(lsblk -bdnro SIZE "$dev") == 250305576960 ]]
[[ $(lsblk -dnro TRAN "$dev" | xargs) == usb ]]
[[ -z $(lsblk -nro MOUNTPOINTS "$dev" | tr -d '[:space:]') ]]
sgdisk --zap-all "$dev"
sgdisk -n 1:1MiB:+2GiB -t 1:ef00 -c 1:XYZBOX_LIVE \
    -n 2:0:0 -t 2:8300 -c 2:XYZBOX_IMAGES "$dev"
blockdev --rereadpt "$dev"
udevadm settle
mkfs.vfat -F 32 -n XYZBOX_LIVE "${usb}-part1"
mkfs.ext4 -F -L XYZBOX_IMAGES "${usb}-part2"
mkdir -p /mnt/xyzbox-live /mnt/xyzbox-images
mount "${usb}-part1" /mnt/xyzbox-live
mount "${usb}-part2" /mnt/xyzbox-images
lsblk -o NAME,SIZE,MODEL,SERIAL,FSTYPE,LABEL,MOUNTPOINTS "$dev"
