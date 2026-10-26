# Imaging workstation resource audit — 2026-10-26

Initial audit scope: document requirements, add the operator public key, inspect the workstation and external source, verify NAS access, and diagnose the reported network interruption.
The initial audit files precede the subsequently authorized deployment. Execution evidence below records the later image capture, customer cleanup, WebUI and HP restore; do not interpret the original inventory as the current disk state.

- Workstation: `zenbot-alg@192.168.106.3`, ThinkBook 16 G8 AHP, Ubuntu 24.04.4.
- Public-key login independently verified after adding the existing operator public key.
- External source identity was read with `smartctl -i -d sntasmedia /dev/sda`: Fanxiang S500Pro 256GB, serial `26030958613001465`, firmware SN17027, 512-byte logical sectors.
- NAS: `192.168.100.100`, dedicated `AlgoLaptop` identity, `home/XYZBoxImages`.
- The credential was consumed through stdin by the SMB client; no credential value is stored in these artifacts.
- A 64 MiB workstation→NAS→workstation round trip verified SHA-256; temporary probe files were removed.
- `network-events.txt` is in UTC. The host itself was configured to America/New_York, so its default displayed times differed from Shanghai by twelve hours.
- The conflict MAC in the NetworkManager event matches the workstation's Wi-Fi MAC. Wi-Fi was already disabled by the time of successful inspection. No network configuration or router settings were changed by this audit.

See [requirements and feasibility assessment](../../docs/11-imaging-station-plan-20261026.md).

## Execution evidence

- Harness: Codex; model: unknown; native thread `01a1678d-3bfb-75b0-964e-4b2dc0a3a6a9`; operator host `Yuntians-MacBook-Pro.local`.
- Baseline source revision: `c7923116c4887c257d9d187438b1e2c625b1e37e`; final code and artifact revision is the Git commit containing this directory.
- NAS mount and imaging API are root-owned; no credential content is present here.
- Original source: Fanxiang S500Pro 256GB, `26030958613001465`; new target: HP EX900 Plus 256GB, `HASI26340100088`. USB bridge serial `AAAABBBB0010` stays constant across both.
- Original image `fanxiang-original-20261026`: 4,654,665,436 bytes, preserved before customer cleanup.
- Customer image `20261026T124736Z-cdaaebd4`: 3,907,322,618 bytes; capture job `35a7a500c94049f6ac021009a715d4e8` completed 2026-10-26 12:50:29 UTC.
- Both images use Partclone allocated blocks plus zstd, compressed/uncompressed SHA256 and Partclone CRC. The minimum actual target capacity remains 256060514304 bytes; this is not a shrunken image.
- First HP restore correctly failed at partition-table restore on the target's empty MBR label, before filesystem data writes; the `--mbrtogpt` compatibility fix was reproduced using sparse regular files. The failed record is retained.
- FAT32 and Ext4 128MiB regular-file capture/restore/recapture checks passed, including clean stdout image streams, exact read-back digests, CRC and read-only fsck. A separate empty-MBR→GPT test passed. No physical disks are used by those regression tests.
- Thirty-one disk-free Python tests cover device exclusion, native serial/hot-swap, locking, interrupted jobs, integrity failures before writes, capacity, NAS output failure cleanup, and HTTP Host/origin/request boundaries.
- Final automatic restore job `209f8d6cec0d42849fff1a6efa4ca041` succeeded 13:05:01–13:08:45 UTC (3m44s), including used-block read-back, filesystem checks and identity/boot finalization. New hostname: `yikai-f98ac0a5`.
- `hp-offline-inspection.json` verifies the new UUID references in fstab/GRUB, UEFI fallback file contents, RT/generic kernels, kcan module and the customer SDK/pip environment. The target is unmounted and safe to remove.
- `hp-coldboot.json` records actual cold boot at `192.168.110.12`: correct target SSD, hostname, RT kernel/realtime=1, SDK dependencies and synchronized clock. kcan/it87 loaded. The customer-facing non-secret provisioning receipt was made readable to ubuntu.
- CAN feedback remains unverified: USB inventory contains only root hubs, no CAN device/interface. User clarification about CAN/internal USB assembly is pending; no arm movement occurred. The previous `HASI26340100227` shipping test is not evidence for this different HP SSD.

Runtime procedures and limitations: [imaging_station/README.md](../../imaging_station/README.md).
