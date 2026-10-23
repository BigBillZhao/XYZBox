#!/usr/bin/env bash
# Fixed devices for this session. Run only inside the prepared Clonezilla Live.
set -euo pipefail
[[ $EUID == 0 ]]
grep -qw 'boot=live' /proc/cmdline
base=/home/partimag
mountpoint -q "$base"
exec > >(tee -a "$base/xyzbox/clone-session.log") 2>&1
src=$(readlink -f /dev/disk/by-id/nvme-Fanxiang_S500Pro_256GB_26030958613001465)
dst=$(readlink -f /dev/disk/by-id/usb-ASMT_ASM246X_AAAABBBB0010-0:0)
usb=$(readlink -f /dev/disk/by-id/usb-USB_SanDisk_3.2Gen1_00023309012526182146-0:0)
[[ -b "$src" && -b "$dst" && -b "$usb" ]]
[[ "$src" != "$dst" && "$dst" != "$usb" && "$src" != "$usb" ]]
[[ $(blockdev --getsize64 "$src") == 256060514304 ]]
[[ $(blockdev --getsize64 "$dst") == 256060514304 ]]
[[ $(lsblk -dnro SERIAL "$src" | xargs) == 26030958613001465 ]]
[[ $(lsblk -dnro SERIAL "$dst" | xargs) == AAAABBBB0010 ]]
for dev in "$src" "$dst"; do
    [[ -z $(lsblk -nro MOUNTPOINTS "$dev" | tr -d '[:space:]') ]]
done
image=yikai-box-noble-piper-rt-20261023-v1
[[ ! -e "$base/$image" ]]
lsblk -b -o NAME,SIZE,MODEL,SERIAL,FSTYPE,MOUNTPOINTS
# Protect the source throughout this offline session.
blockdev --setro "$src"
while read -r part; do blockdev --setro "$part"; done < <(lsblk -lnpo NAME,TYPE "$src" | awk '$2 == "part" {print $1}')
ocs-sr -batch -nogui -q2 -j2 -z9p -i 4096 -sfsck -senc -gb3 -p true savedisk "$image" "${src##*/}"
date --iso-8601=seconds > "$base/xyzbox/IMAGE-SAVED"
ocs-sr -batch -nogui -iui -irhr -iefi -p true restoredisk "$image" "${dst##*/}"
udevadm settle
rootpart=/dev/disk/by-id/usb-ASMT_ASM246X_AAAABBBB0010-0:0-part2
efipart=/dev/disk/by-id/usb-ASMT_ASM246X_AAAABBBB0010-0:0-part1
mkdir -p /mnt/xyzbox-clone
mount "$rootpart" /mnt/xyzbox-clone
trap 'umount /mnt/xyzbox-clone/boot/efi 2>/dev/null || true; umount /mnt/xyzbox-clone 2>/dev/null || true' EXIT
mount "$efipart" /mnt/xyzbox-clone/boot/efi
bash "$base/xyzbox/finalize_cloned_root.sh" /mnt/xyzbox-clone "$rootpart"
grep -qx 'CONFIG_PREEMPT_RT=y' /mnt/xyzbox-clone/boot/config-7.0.14-xyzbox-rt
grep -q '7.0.14-xyzbox-rt' /mnt/xyzbox-clone/etc/default/grub.d/90-xyzbox-kernel.cfg
test -f /mnt/xyzbox-clone/boot/efi/EFI/BOOT/BOOTX64.EFI
test -f /mnt/xyzbox-clone/lib/modules/7.0.14-xyzbox-rt/updates/dkms/kcan.ko
cp /mnt/xyzbox-clone/var/lib/xyzbox/clone-identity.txt "$base/xyzbox/target-identity.txt"
sha256sum /mnt/xyzbox-clone/boot/vmlinuz-7.0.14-xyzbox-rt > "$base/xyzbox/target-kernel.sha256"
umount /mnt/xyzbox-clone/boot/efi
umount /mnt/xyzbox-clone
trap - EXIT
sync
date --iso-8601=seconds > "$base/xyzbox/CLONE-COMPLETE"
echo 'Image saved and target SSD restored, personalized, and unmounted.'
