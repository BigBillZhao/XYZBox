#!/usr/bin/env bash
set -euo pipefail
[[ $EUID == 0 ]]
cd /home/ubuntu/xyzbox-rt-20261023
[[ $(uname -r) == 7.0.14-xyzbox-rt ]]
[[ $(cat /sys/kernel/realtime) == 1 ]]
grep -qx 'CONFIG_PREEMPT_RT=y' /boot/config-7.0.14-xyzbox-rt
uname -a | tee rt-uname.txt
dkms status | tee dkms.rt.txt
modinfo -F vermagic kcan | grep '^7.0.14-xyzbox-rt '
systemctl is-active ssh NetworkManager display-manager
ip -details link show type can | tee can.rt.txt
lsusb -t | tee usb.rt.txt
python3 passive-can-check.py > can-rt.json
python3 - <<'PY'
import json
p = json.load(open('can-rt.json'))
assert all(p['all_six_disabled'].values()), p
assert not any(p['error_frames'].values()), p
assert all(sum(c.values()) > 0 for c in p['counts'].values()), p
print('Both Piper CAN channels receive feedback; all twelve drivers are disabled.')
PY
cyclictest -a 2 -t1 -p80 -i1000 -D30s -m -q > rt-cyclictest.txt 2>&1
cat rt-cyclictest.txt
printf '%s\n' 'GRUB_DEFAULT="Advanced options for Ubuntu>Ubuntu, with Linux 7.0.14-xyzbox-rt"' > /etc/default/grub.d/90-xyzbox-kernel.cfg
update-grub
grub-script-check /boot/grub/grub.cfg
date --iso-8601=seconds > RT-VERIFIED
echo 'RT verified and made the default; generic kernel retained.'
