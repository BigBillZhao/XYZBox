# Imaging workstation resource audit — 2026-10-26

Scope: document requirements, add the operator public key, inspect the workstation and external source, verify NAS access, and diagnose the reported network interruption.
No source disk cleanup, repartitioning, image capture, target restore or WebUI deployment was performed.

- Workstation: `zenbot-alg@192.168.106.3`, ThinkBook 16 G8 AHP, Ubuntu 24.04.4.
- Public-key login independently verified after adding the existing operator public key.
- External source identity was read with `smartctl -i -d sntasmedia /dev/sda`: Fanxiang S500Pro 256GB, serial `26030958613001465`, firmware SN17027, 512-byte logical sectors.
- NAS: `192.168.100.100`, dedicated `AlgoLaptop` identity, `home/XYZBoxImages`.
- The credential was consumed through stdin by the SMB client; no credential value is stored in these artifacts.
- A 64 MiB workstation→NAS→workstation round trip verified SHA-256; temporary probe files were removed.
- `network-events.txt` is in UTC. The host itself was configured to America/New_York, so its default displayed times differed from Shanghai by twelve hours.
- The conflict MAC in the NetworkManager event matches the workstation's Wi-Fi MAC. Wi-Fi was already disabled by the time of successful inspection. No network configuration or router settings were changed by this audit.

See [requirements and feasibility assessment](../../docs/11-imaging-station-plan-20261026.md).
