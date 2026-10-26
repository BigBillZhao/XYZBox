#!/bin/bash
# Offline preparation only; the source has a verified original backup on NAS.
set -euo pipefail
[[ $EUID == 0 && $# == 5 ]] || { echo 'root required: ROOT NATIVE_SERIAL VERIFIED_MARKER SDK_KIT LM_SENSORS_DEB'; exit 2; }
root=$(realpath -e -- "$1")
serial=$2
verified=$3
kit=$(realpath -e -- "$4")
deb=$(realpath -e -- "$5")
[[ "$root" == /mnt/xyzbox-source && -f "$verified" ]]
grep -q '^ORIGINAL_BACKUP_VERIFIED ' "$verified"
[[ $(findmnt -nro FSTYPE --mountpoint /mnt/xyzbox-nas) == cifs ]]
source=$(findmnt -nro SOURCE --mountpoint "$root")
[[ -b "$source" && $(findmnt -nro FSTYPE --mountpoint "$root") == ext4 ]]
disk="/dev/$(lsblk -dnro PKNAME "$source")"
[[ $(lsblk -dnro TRAN "$disk") == usb ]]
python3 - "$disk" "$serial" <<'PY'
import json,subprocess,sys
r=json.loads(subprocess.check_output(['smartctl','-j','-i','-d','sntasmedia',sys.argv[1]]))
assert r['serial_number']==sys.argv[2]
PY
[[ $(sha256sum "$kit" | cut -d' ' -f1) == de355cf3a42b06dde72030b14e63f40988960e35ffb5c091a0a9b708a2b7b39b ]]
[[ ! -L "$root/home/ubuntu" && ! -e "$root/home/ubuntu/yikai-box" ]]
install -d "$root/home/ubuntu/yikai-box"
tar --no-same-owner -xf "$kit" -C "$root/home/ubuntu/yikai-box"
install -m 644 /home/zenbot-alg/PIPER-IMAGE-QUICKSTART.zh-CN.md "$root/home/ubuntu/yikai-box/README.md"
install -m 644 /home/zenbot-alg/PIPER-IMAGE-QUICKSTART.zh-CN.md "$root/home/ubuntu/Desktop/YikaiBox-使用说明.md"
install -m 644 /home/zenbot-alg/xyzbox-hwmon.conf "$root/etc/modules-load.d/xyzbox-hwmon.conf"
install -m 644 "$deb" "$root/tmp/xyzbox-lm-sensors.deb"
# lm-sensors is read-only monitoring; do not start services inside the chroot.
[[ ! -e "$root/usr/sbin/policy-rc.d" ]]
printf '#!/bin/sh\nexit 101\n' > "$root/usr/sbin/policy-rc.d"
chmod 755 "$root/usr/sbin/policy-rc.d"
trap 'rm -f "$root/usr/sbin/policy-rc.d" "$root/tmp/xyzbox-lm-sensors.deb"' EXIT
chroot "$root" dpkg -i /tmp/xyzbox-lm-sensors.deb
chroot "$root" bash /home/ubuntu/yikai-box/scripts/setup_piper_env.sh /home/ubuntu/yikai-box/.venv
chroot "$root" /home/ubuntu/yikai-box/.venv/bin/python /home/ubuntu/yikai-box/examples/piper_read_status.py --help
chown -R 1000:1000 "$root/home/ubuntu/yikai-box" "$root/home/ubuntu/Desktop/YikaiBox-使用说明.md"
# These commissioning/installer paths were inventoried and have no service refs.
for rel in \
  home/ubuntu/xyzbox-commissioning-20261023 \
  home/ubuntu/xyzbox-rt-20261023 \
  home/ubuntu/clonezilla-live-3.3.3-37-amd64.iso \
  home/ubuntu/xyzbox-can-install-20261023.tar.gz \
  home/ubuntu/clone-session.sh home/ubuntu/finalize_cloned_root.sh \
  home/ubuntu/install-rt-box.sh home/ubuntu/populate-live-usb.sh \
  home/ubuntu/prepare-clone-boot.sh home/ubuntu/prepare-live-usb.sh \
  home/ubuntu/prepare-rt-box.sh home/ubuntu/setup-live.sh \
  home/ubuntu/verify-rt-box.sh home/ubuntu/xyzbox-live-operator.pub; do
  rm -rf -- "$root/$rel"
done
# Do not distribute commissioning access, interactive history or installer logs.
rm -rf -- "$root/home/ubuntu/.ssh" "$root/root/.ssh" "$root/home/ubuntu/.cache" "$root/var/log/installer"
rm -f -- "$root/home/ubuntu/.bash_history" "$root/root/.bash_history"
find "$root/var/cache/apt/archives" -maxdepth 1 -type f -name '*.deb' -delete
find "$root/var/log" -xdev -type f -exec truncate -s 0 '{}' +
mkdir -p "$root/var/lib/xyzbox"
cat > "$root/etc/xyzbox-image.json" <<'JSON'
{"profile":"seavo-sv3-piper-rt","version":"20261026-v2","ubuntu":"24.04.4","kernel":"7.0.14-xyzbox-rt","sdk":"pyAgxArm 1ae40ad","can_driver":"1.4.2","customer_ready":false,"note":"Offline preparation; restored target needs boot acceptance"}
JSON
sync
echo CUSTOMER_SOURCE_PREPARED
