#!/usr/bin/env bash
set -euo pipefail
[[ $EUID == 0 ]]
test -f /home/ubuntu/xyzbox-rt-20261023/RT-VERIFIED
usb=/dev/disk/by-id/usb-USB_SanDisk_3.2Gen1_00023309012526182146-0:0
[[ $(lsblk -dnro SERIAL "$usb" | xargs) == 00023309012526182146 ]]
mkdir -p /mnt/xyzbox-images
mount "${usb}-part2" /mnt/xyzbox-images
install -m 755 /home/ubuntu/clone-session.sh /mnt/xyzbox-images/xyzbox/clone-session.sh
mkdir -p /mnt/xyzbox-images/xyzbox/rt-evidence
cp /home/ubuntu/xyzbox-rt-20261023/{RT-VERIFIED,rt-uname.txt,dkms.rt.txt,can-rt.json,rt-cyclictest.txt,generic-cyclictest.txt,SHA256SUMS.build} /mnt/xyzbox-images/xyzbox/rt-evidence/
sync
umount /mnt/xyzbox-images
efibootmgr --create-only --disk "$usb" --part 1 --label 'XYZBox Clonezilla 20261023' --loader '\EFI\boot\bootx64.efi'
entry=$(efibootmgr | awk '/^Boot[0-9A-Fa-f]+\*? XYZBox Clonezilla 20261023/ {print substr($1, 5, 4)}')
[[ "$entry" =~ ^[0-9A-Fa-f]{4}$ ]]
efibootmgr --bootnext "$entry"
efibootmgr
