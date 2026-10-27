# RAM-only overnight result — verified 2026-10-27

Target: `ubuntu@192.168.110.12`, hostname `yikai-f98ac0a5`.
Run: `20261026T134923Z`; `stressapptest 1.0.11`, 5120MiB, 4 warm-copy threads.
Started 2026-10-26 21:49:23; finished 2026-10-27 07:49:25 Asia/Shanghai.

Result: PASS, exit 0, 36002 elapsed seconds, 0 hardware incidents, 0 errors.
CPU package temperature sampled once per minute: peak 62°C, median 59°C.
600 samples, maximum sampling gap 61 seconds. Minimum available system RAM about 1.69GiB.

The current boot ID at retrieval matched the run's initial boot ID; no reboot was observed.
The systemd service was inactive/dead after normal exit. No new test was started during retrieval.
File Copy and Disk statistics are both zero. This does not certify RAM occupied by the OS or assess real-time scheduling latency.

- `summary.json` / `state.json`: unmodified target-side records.
- `memory.log` / `stdout.log`: stressapptest output.
- `telemetry.jsonl`: minute samples.
- `kernel.log`: records after the start cursor, including perf sampling-rate reductions and AppArmor status events. The configured MCE/OOM/hardware-error filter found no matches.

Provenance: harness=codex; model=unknown; native thread `01a1678d-3bfb-75b0-964e-4b2dc0a3a6a9`; operator host `Yuntians-MacBook-Pro.local`; code baseline `5af24003f512a0babbd3d3ad25170e609678e9c2`.
