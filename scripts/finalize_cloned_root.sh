#!/usr/bin/env bash
# Personalize an OFFLINE clone already mounted by the operator. Never partitions a disk.
set -euo pipefail
if [[ $EUID != 0 || $# != 2 ]]; then
    echo "Usage: sudo $0 MOUNTED_CLONE_ROOT EXPECTED_ROOT_PARTITION" >&2
    exit 2
fi
root=$(realpath -e -- "$1")
expected=$(readlink -f -- "$2")
[[ "$root" != / && -b "$expected" ]] || { echo 'Invalid offline target.' >&2; exit 2; }
actual=$(findmnt -nro SOURCE --mountpoint "$root")
actual=$(readlink -f -- "$actual")
[[ "$actual" == "$expected" ]] || { echo 'Mounted partition differs from explicit target.' >&2; exit 2; }
running=$(findmnt -nro SOURCE /)
running=$(readlink -f -- "$running")
[[ "$actual" != "$running" ]] || { echo 'Refusing to personalize the running system.' >&2; exit 2; }
[[ $(findmnt -nro FSTYPE --mountpoint "$root") == ext4 ]] || exit 2
[[ -f "$root/etc/os-release" && -d "$root/etc/ssh" ]] || exit 2
[[ ! -L "$root/etc" && ! -L "$root/etc/ssh" ]] || exit 2
grep -qx 'ID=ubuntu' "$root/etc/os-release"
grep -qx 'VERSION_ID="24.04"' "$root/etc/os-release"
parent=$(lsblk -nro PKNAME "$expected" | head -n 1)
serial=$(lsblk -dnro SERIAL "/dev/$parent" | xargs)
[[ "$serial" != 26030958613001465 ]] || { echo 'Refusing the known source SSD.' >&2; exit 2; }

new_id=$(tr -d '-' < /proc/sys/kernel/random/uuid)
new_name="yikai-${new_id:0:8}"
# Do not follow a stale symlink from a cloned image.
rm -f -- "$root/etc/machine-id" "$root/var/lib/dbus/machine-id"
printf '%s\n' "$new_id" > "$root/etc/machine-id"
chmod 444 "$root/etc/machine-id"
mkdir -p "$root/var/lib/dbus"
ln -s /etc/machine-id "$root/var/lib/dbus/machine-id"
printf '%s\n' "$new_name" > "$root/etc/hostname"
if grep -q '^127\.0\.1\.1[[:space:]]' "$root/etc/hosts"; then
    sed -i "s/^127\.0\.1\.1[[:space:]].*/127.0.1.1 $new_name/" "$root/etc/hosts"
else
    printf '127.0.1.1 %s\n' "$new_name" >> "$root/etc/hosts"
fi
find "$root/etc/ssh" -maxdepth 1 -type f -name 'ssh_host_*_key*' -delete
ssh-keygen -A -f "$root"
mkdir -p "$root/var/lib/xyzbox"
printf 'hostname=%s\nprepared_at=%s\n' "$new_name" "$(date --iso-8601=seconds)" > "$root/var/lib/xyzbox/clone-identity.txt"
sync
printf 'Clone identity prepared: %s (%s)\n' "$new_name" "$expected"
