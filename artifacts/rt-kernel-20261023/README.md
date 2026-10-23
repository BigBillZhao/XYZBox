# Piper box: RT kernel and disk clone, 2026-10-23

This is the new box at the session address `192.168.110.12`, not the retired Nero controller.
Native Codex thread and build provenance are recorded in `build-manifest.json`.

## Real-time kernel

- Installed `7.0.14-xyzbox-rt`, package `7.0.14-xyzbox2`, retaining `7.0.0-38-generic`.
- Booted RT, confirmed `/sys/kernel/realtime=1`, rebuilt and loaded kcan 1.4.2 through DKMS.
- Network and display manager active; each 1 Mbps CAN channel delivered about 15,200 frames in five seconds with no error frames. All twelve driver enable bits were off.
- Made RT the default only after verification. No robot motion was executed in this kernel-validation phase.
- Idle cyclictest, 30 seconds: generic 1/5/39 µs min/average/max; RT 1/11/52 µs. These samples do not establish a latency improvement or a worst-case bound.

See `runtime-validation.json` and `evidence/`. The exact binaries remain at
`5090d:/data/xyzbox-rt-20261023/`; their hashes are in `SHA256SUMS.build`.
Do not copy the builder's private signing key. Only image, headers and matching config were transferred to the box.

## Reproduction fixes

`build.sh` used the prior source and configuration with a new package revision. The minimal Ubuntu container needed Python 3 for kernel configuration helpers.
The source-package diff created `debian/scripts/sign-module` with mode 0644. `repackage.sh` restored 0755 and rebuilt the packages; a packaged i915 module's signer was verified.
The canonical build script and both language guides now include these requirements.

## Clone

The SanDisk USB has a 2 GiB FAT32 live partition and an ext4 image partition.
`clone-session.sh` was run from Clonezilla Live, after identifying all three disks again.
It made the Fanxiang source read-only, saved and checked a Partclone image, restored it to the HP SSD through the ASM246X bridge, and personalized the offline target.

Image: `yikai-box-noble-piper-rt-20261023-v1`, 4,622,365,169 bytes in its saved directory.
Target hostname: `yikai-21c5e86e`; machine-id and SSH host keys are independent of the source.
The target was unmounted at `2026-10-23T14:18:21+00:00`.

`evidence/B3SUMS` identifies the image files; `Info-img-id.txt` is Clonezilla's image identifier.
Final archive verification and any cold-boot result are recorded separately in `clone-validation.json`.
The clone contains the existing functioning Piper software; this work does not implement the future factory WebUI.

See [disk-cloning procedure](../../docs/09-disk-cloning.md).
