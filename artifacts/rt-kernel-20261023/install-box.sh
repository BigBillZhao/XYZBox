#!/usr/bin/env bash
set -euo pipefail
[[ $EUID == 0 ]]
cd /home/ubuntu/xyzbox-rt-20261023
sha256sum --check SHA256SUMS.build
grep -qx 'CONFIG_PREEMPT_RT=y' config-7.0.14-xyzbox-rt
grep -q 'Ubuntu, with Linux 7.0.0-38-generic' /boot/grub/grub.cfg
dpkg -i linux-headers-7.0.14-xyzbox-rt_7.0.14-xyzbox2_amd64.deb
install -m 644 config-7.0.14-xyzbox-rt /usr/src/linux-headers-7.0.14-xyzbox-rt/.config
dpkg -i linux-image-7.0.14-xyzbox-rt_7.0.14-xyzbox2_amd64.deb
dkms autoinstall -k 7.0.14-xyzbox-rt
dkms status | tee dkms.after-install.txt
dkms status | grep -F 'kunhong-linux-driver/1.4.2, 7.0.14-xyzbox-rt, x86_64: installed'
modinfo -k 7.0.14-xyzbox-rt kcan | tee kcan-modinfo.txt
modinfo -k 7.0.14-xyzbox-rt -F vermagic kcan | grep '^7.0.14-xyzbox-rt '
update-initramfs -u -k 7.0.14-xyzbox-rt
update-grub
grub-script-check /boot/grub/grub.cfg
grep -q 'Ubuntu, with Linux 7.0.14-xyzbox-rt' /boot/grub/grub.cfg
grub-reboot 'Advanced options for Ubuntu>Ubuntu, with Linux 7.0.14-xyzbox-rt'
grub-editenv list
echo 'RT installed. One-shot boot selected; generic remains the persistent fallback.'
