#!/usr/bin/env bash
set -euo pipefail
[[ $EUID == 0 ]]
dest=/home/ubuntu/xyzbox-rt-20261023
mkdir -p "$dest"
cp -a /etc/default/grub "$dest/grub.before"
cp -a /etc/default/grub.d "$dest/grub.d.before"
uname -a > "$dest/generic-uname.txt"
dkms status > "$dest/dkms.before.txt"
ip -details link show type can > "$dest/can.before.txt"
lsblk -b -o NAME,SIZE,MODEL,SERIAL,TRAN,TYPE,FSTYPE,MOUNTPOINTS > "$dest/disks.before.txt"
apt-mark manual linux-image-7.0.0-38-generic linux-headers-7.0.0-38-generic linux-modules-7.0.0-38-generic
printf '%s\n' 'GRUB_DEFAULT="Advanced options for Ubuntu>Ubuntu, with Linux 7.0.0-38-generic"' > /etc/default/grub.d/90-xyzbox-kernel.cfg
update-grub
cyclictest -a 2 -t1 -p80 -i1000 -D30s -m -q > "$dest/generic-cyclictest.txt" 2>&1
cat "$dest/generic-cyclictest.txt"
