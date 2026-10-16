# Validation Records and Scope

English | [简体中文](../05-validation.md) · [Home](../../README.md)

## On-site link before the RT switch, October 16, 2026

Environment: Ubuntu 24.04.4 LTS / x86_64, kernel `7.0.0-38-generic`, kcan `Release_1.4.2_20260721_n`,
Python 3.12, pinned pyAgxArm archive `1ae40ad`, python-can 4.6.1.

| Check | Result |
|---|---|
| New adapter enumeration | `395e:0020 KCAN-USB X4`, USB driver=kcan |
| Channels | can0–can3; can0/can1 connected to arms, can2/can3 unused and DOWN |
| Actual bus settings | Classic CAN, 1 Mbps, sample point 0.75 |
| Firmware | Both arms 1.12, matching v112; response payloads consistent with earlier records for the same pair of arms |
| Passive reception | Approximately 4,200 real data frames per channel over two seconds |
| CAN errors | TX/RX error counters zero on both connected channels |
| After home with the original program | Both arms NORMAL / CAN_CTRL, all 14 joints reported enabled |
| Maximum joint error after settling | Left 0.2285°, right 0.1700° |
| PICO / cameras | Not used for this joint home test |

The original home program uses LeRobot joint interpolation and MIT + gravity compensation, with continuous PD after reaching the target.
This is on-site evidence for the hardware/driver/SDK connection, not physical motion acceptance of this repository's new `move_j` example.

## Repository delivery checks

These checks were recorded during delivery for the corresponding repository revision:

- Driver, SDK, and offline wheels: SHA-256 integrity checks.
- kcan source archive: rebuilt against the corresponding kernel headers, without installing or reloading the running driver for that check.
- Python: a fresh isolated venv installed from bundled packages, with dependency and v112 profile checks.
- Example: offline tests of arguments, non-motion reading, and the motion branch's call sequence.
- CAN setup helper: tests for leaving unselected channels untouched, refusing to reconfigure UP interfaces with different settings, and handling matching configurations.
- Physical hardware checks for preparing the repository were limited to explicitly recorded read-only checks; no additional arm movement was performed for documentation.

The original USB CAN package results are in [`validation/RESULTS.json`](../../validation/RESULTS.json), associated with commit `1ed8aef`.
A check marked as not run must not be treated as passed.

## Checks after delivery organization and the RT switch

The machine booted `7.0.14-xyzbox-rt`, PREEMPT_RT was confirmed active, and this kernel was set as the default. The original generic kernel was retained.
The matching USB CAN driver loaded successfully. Checks passed for four interfaces, two connected classic CAN 1 Mbps channels, the original network configuration, the display service, and HDMI output.
Checks passed for 11 module imports, 628 Python files, 42 model resource references, FK/gravity compensation, and 13 offline tests.
The original recording program's source hash and the complete three-camera acceptance archive's hash were unchanged.
No arm motion or PICO/camera hardware tests were performed during this phase. On October 16, 2026, the user confirmed normal display, login, mouse, and keyboard operation after the RT reboot.
See [`validation/DELIVERY-20261016.json`](../../validation/DELIVERY-20261016.json) for detailed results,
and the [real-time kernel guide](07-realtime-kernel.md) for scheduling observations and recovery steps.

## Checks still required after a customer reinstall

Reinstallation may change the kernel, USB topology, adapter, cables, or peer firmware.
Repeat the layered checks in the README. Historical “passed” results in Git do not replace checks on the restored machine.
