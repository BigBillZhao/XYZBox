#!/usr/bin/env bash
set -euo pipefail
[[ $EUID == 0 ]]
usb=/dev/disk/by-id/usb-USB_SanDisk_3.2Gen1_00023309012526182146-0:0
live=/mnt/xyzbox-live
images=/mnt/xyzbox-images
[[ $(readlink -f "${usb}-part1") == $(readlink -f "$(findmnt -nro SOURCE --mountpoint "$live")") ]]
[[ $(readlink -f "${usb}-part2") == $(readlink -f "$(findmnt -nro SOURCE --mountpoint "$images")") ]]
iso=/home/ubuntu/clonezilla-live-3.3.3-37-amd64.iso
echo "3079458d926a37d3533e5d5caeb61b6e49c2dc69e2c97e0332ef37986bb3414f  $iso" | sha256sum -c -
mkdir -p /mnt/xyzbox-clonezilla-iso
mount -o loop,ro "$iso" /mnt/xyzbox-clonezilla-iso
trap 'umount /mnt/xyzbox-clonezilla-iso' EXIT
rsync -rtL --modify-window=1 /mnt/xyzbox-clonezilla-iso/ "$live/"
mkdir -p "$images/xyzbox"
install -m 755 /home/ubuntu/setup-live.sh /home/ubuntu/finalize_cloned_root.sh "$images/xyzbox/"
install -m 644 /home/ubuntu/xyzbox-live-operator.pub "$images/xyzbox/authorized_keys"
cp "$live/boot/grub/grub.cfg" "$images/xyzbox/grub.original.cfg"
cat >> "$live/boot/grub/grub.cfg" <<'EOF'

# Added for the 2026-10-23 XYZBox commissioning session.
menuentry "XYZBox offline clone (SSH key only)" --id xyzbox-clone {
  search --set --label XYZBOX_LIVE
  linux /live/vmlinuz boot=live union=overlay username=user config components loglevel=3 hostname=xyzbox-clone-live noswap edd=on nomodeset enforcing=0 locales=en_US.UTF-8 keyboard-layouts=NONE ocs_live_run="bash" ocs_live_extra_param="" ocs_live_batch="no" ocs_prerun="mount /dev/disk/by-label/XYZBOX_IMAGES /home/partimag" ocs_prerun1="bash /home/partimag/xyzbox/setup-live.sh" vga=788 net.ifnames=0 quiet nosplash i915.blacklist=yes video=eDP-1:d
  initrd /live/initrd.img
}
set default=xyzbox-clone
set timeout=3
EOF
grub-script-check "$live/boot/grub/grub.cfg"
test -f "$live/EFI/boot/bootx64.efi"
test -f "$live/EFI/boot/grubx64.efi"
sync
echo 'Live USB populated; boot order unchanged.'
