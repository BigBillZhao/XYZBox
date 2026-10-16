#!/usr/bin/env bash
# Install files only. Do not unload a live driver, rebind USB, or reboot automatically.
set -euo pipefail
repo=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)
skip_apt=false
if [[ ${1:-} == --skip-apt ]]; then skip_apt=true; shift; fi
if [[ $# != 0 ]]; then echo "Usage: sudo $0 [--skip-apt]" >&2; exit 2; fi
if [[ $EUID != 0 ]]; then echo 'Run this installer with sudo.' >&2; exit 2; fi
if [[ $(uname -s) != Linux ]]; then echo 'Linux is required.' >&2; exit 2; fi
(
    cd "$repo"
    sha256sum --check vendor/SHA256SUMS
)
if [[ $skip_apt == false ]]; then
    apt-get update
    apt-get install -y build-essential dkms "linux-headers-$(uname -r)" \
        can-utils iproute2 usbutils python3 python3-venv mokutil
fi
if mokutil --sb-state 2>/dev/null | grep -q '^SecureBoot enabled'; then
    echo 'Secure Boot is enabled. Complete the module-signing/MOK procedure in docs/01-reinstall.md first.' >&2
    exit 2
fi
test -d "/lib/modules/$(uname -r)/build" || { echo 'Matching kernel headers are missing.' >&2; exit 2; }
source_dir=/usr/src/kunhong-linux-driver-1.4.2
archive="$repo/vendor/kcan-driver-1.4.2.tar.gz"
source_hash=$(sha256sum "$archive" | awk '{print $1}')
if [[ -e $source_dir ]]; then
    if [[ ! -f $source_dir/.xyzbox-source-sha256 ]] || [[ $(cat "$source_dir/.xyzbox-source-sha256") != "$source_hash" ]]; then
        echo "$source_dir already exists and is not this kit's source. Preserve it; see reinstall instructions." >&2
        exit 2
    fi
else
    install -d "$source_dir"
    tar -xzf "$archive" --strip-components=1 -C "$source_dir"
    # The vendor release contains stale generated 1.4.0 metadata. Regenerate it.
    rm "$source_dir/dkms.conf"
    make -C "$source_dir" dkms.conf
    printf '%s\n' "$source_hash" > "$source_dir/.xyzbox-source-sha256"
fi
if ! dkms status -m kunhong-linux-driver -v 1.4.2 | grep -q .; then
    dkms add -m kunhong-linux-driver -v 1.4.2
fi
dkms install -m kunhong-linux-driver -v 1.4.2 -k "$(uname -r)"
install -m 755 "$repo/tools/can_up.py" /usr/local/sbin/xyzbox-can-up
install -m 644 "$repo/system/xyzbox-can@.service" /etc/systemd/system/xyzbox-can@.service
install -m 644 "$repo/system/80-xyzbox-can.rules" /etc/udev/rules.d/80-xyzbox-can.rules
if [[ ! -e /etc/xyzbox-can.json ]]; then
    install -m 644 "$repo/system/can-config.json" /etc/xyzbox-can.json
fi
printf '%s\n' '# XYZBox USB CAN SocketCAN driver' 'blacklist peak_usb' > /etc/modprobe.d/xyzbox-kcan.conf
printf '%s\n' kcan > /etc/modules-load.d/xyzbox-kcan.conf
systemctl daemon-reload
udevadm control --reload-rules
if command -v update-initramfs >/dev/null; then update-initramfs -u -k "$(uname -r)"; fi
dkms status -m kunhong-linux-driver -v 1.4.2
echo 'Installed. No USB rebind, motor command, or reboot was performed.'
echo 'Review /etc/xyzbox-can.json. With robot power off, reboot the PC; then run the checks in README.md.'
