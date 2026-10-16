#!/usr/bin/env bash
# Build packages only; never install, change GRUB, or reboot.
set -euo pipefail
prepare_only=false
if [[ ${1:-} == --prepare-only ]]; then prepare_only=true; shift; fi
if [[ $# != 2 ]]; then
    echo "Usage: $0 [--prepare-only] EXTRACTED_UBUNTU_SOURCE EMPTY_OUTPUT_DIRECTORY" >&2
    exit 2
fi
if [[ $EUID == 0 ]]; then echo 'Build as an ordinary user, not root.' >&2; exit 2; fi
repo=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)
src=$(realpath -- "$1")
mkdir -p -- "$2"
out=$(realpath -- "$2")
if [[ -n $(find "$out" -mindepth 1 -maxdepth 1 -print -quit) ]]; then
    echo 'Output directory must be empty. To resume, use the make command in docs/07-realtime-kernel.md.' >&2
    exit 2
fi
[[ $(make -s -C "$src" kernelversion) == 7.0.14 ]] || { echo 'Expected the documented 7.0.14 source.' >&2; exit 2; }
test -f "$src/debian/canonical-certs.pem"
test -f "$src/debian/canonical-revoked-certs.pem"
cp "$repo/system/realtime/config-generic-7.0.0-38" "$out/.config"
"$src/scripts/config" --file "$out/.config" \
    --enable EXPERT --enable PREEMPT_RT --enable PREEMPT \
    --disable PREEMPT_LAZY --disable PREEMPT_DYNAMIC \
    --disable RUST --disable DEBUG_INFO_DWARF5 \
    --disable DEBUG_INFO_DWARF4 --disable DEBUG_INFO_DWARF_TOOLCHAIN_DEFAULT \
    --enable DEBUG_INFO_NONE --disable DEBUG_INFO_BTF --disable DEBUG_INFO_BTF_MODULES \
    --disable LOCALVERSION_AUTO --set-str LOCALVERSION '-xyzbox-rt' \
    --set-str SYSTEM_TRUSTED_KEYS "$src/debian/canonical-certs.pem" \
    --set-str SYSTEM_REVOCATION_KEYS "$src/debian/canonical-revoked-certs.pem"
make -C "$src" O="$out" olddefconfig
grep -qx 'CONFIG_PREEMPT_RT=y' "$out/.config"
for name in BLK_DEV_NVME EXT4_FS EFI EFI_STUB USB_XHCI_HCD DRM_I915 E1000E IGC CAN CAN_RAW USB_VIDEO_CLASS; do
    grep -Eq "^CONFIG_${name}=(y|m)$" "$out/.config" || { echo "Missing required CONFIG_$name" >&2; exit 1; }
done
"$src/scripts/diffconfig" "$repo/system/realtime/config-generic-7.0.0-38" "$out/.config" > "$out/config-diff.txt"
make -s -C "$src" O="$out" kernelrelease
if [[ $prepare_only == true ]]; then exit 0; fi
jobs=${BUILD_JOBS:-6}
[[ $jobs =~ ^[1-9][0-9]*$ ]] || { echo 'BUILD_JOBS must be a positive integer.' >&2; exit 2; }
make -C "$src" O="$out" -j"$jobs" \
    KBUILD_BUILD_USER=xyzbox KBUILD_BUILD_HOST=nero-control \
    KDEB_PKGVERSION=7.0.14-xyzbox1 bindeb-pkg
echo 'Packages are in the parent of the output directory. Install only the image and matching headers.'
