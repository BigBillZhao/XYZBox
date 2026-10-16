# USB CAN Troubleshooting

English | [简体中文](../03-troubleshooting.md) · [Home](../../README.md)

## Diagnose one layer at a time

| Symptom | Check first | Next step |
|---|---|---|
| Device absent from `lsusb` | M.2 slot USB signals, carrier, power, connections | Restore enumeration before investigating Python packages. |
| USB device present, no CAN interface | `lsusb -t`, `dkms status`, kernel logs | Confirm that kcan is bound and matches the running kernel. |
| Four-port adapter exposes only two channels | Actual model, USB ID, whether both USB interfaces are claimed | See the older adapter case; software can0/can1 must not be assumed to mean physical CAN3/CAN4. |
| CAN interface exists but is DOWN | `/etc/xyzbox-can.json`, udev USB ID match, service logs | Start the corresponding `xyzbox-can@canN.service`. |
| Firmware query times out | Real RX, ACKs, physical ports, bitrate, arm initialization | Diagnose communication before bypassing firmware detection or forcing enable commands. |
| TX increases, RX remains zero | Transmit echo versus actual bus feedback | Successful TX/local echo alone does not establish that the arm is online. |
| Repeated ACK errors / TX error 128 | Peer on that cable, H/L, termination, power, bitrate | Stop probing and inspect the physical link. |
| Joint feedback exists but control is abnormal | Actual firmware and SDK profile | Nero 1.12 must resolve to `v112`. |

## Common read-only checks

```bash
uname -r
lsusb
lsusb -t
lsmod | grep -E 'kcan|peak_usb|can_dev'
dkms status
modinfo kcan
ip -details -statistics link show type can
systemctl status xyzbox-can@can0.service
journalctl -u xyzbox-can@can0.service -b --no-pager
journalctl -k -b --no-pager | grep -Ei 'kcan|peak_usb|usb|can[0-9]'
```

`ERROR-ACTIVE` is a normal CAN state. Watch for increasing error counters or transitions to ERROR-PASSIVE/BUS-OFF.
Error events counted in RX statistics are not arm joint frames; the included probe counts them separately.

```bash
# Passive reception by default; no application frames are transmitted:
.venv/bin/python tools/can_probe.py can0 can1

# With control programs stopped and wiring confirmed, explicitly request Nero firmware:
.venv/bin/python tools/can_probe.py can0 can1 --query-firmware
```

The firmware request is standard frame `0x4AF` with data `01`. It does not enable, send joint targets, or disable the arm.
The tool sends a query only after observing real RX, so it does not queue transmissions on a bus with no feedback.
The first frame after opening an interface may be lost; the tool makes up to three query attempts.
The full firmware payload is retained for diagnosis. Do not assume it is a universally unique serial number across firmware versions.

## Problems observed during setup

### 1. Driver 1.4.1 fails to build on Linux 7.0

The typical error is `can_change_mtu undeclared`, caused by a changed kernel interface.
After identifying the issue, the installation switched to the original upstream **1.4.2** release, which adapts to Linux 7.0 using feature detection.
This repository includes 1.4.2; customers do not need to patch that code manually.

### 2. Incorrect DKMS version label

The static `driver/dkms.conf` in the upstream 1.4.2 package retained an old `1.4.0` label,
while the Makefile's `DKMS_VER` was already 1.4.2. The installer deletes and regenerates only that file in the newly extracted source directory.
The expected status is `<driver-package>/1.4.2, <running-kernel>, x86_64: installed`.

### 3. Manual insmod reports Unknown symbol

`insmod kcan.ko` does not automatically load dependencies such as `can-dev`.
Use `modprobe kcan` after installation; prepare dependencies first even for temporary build tests.
An `Unknown symbol` error alone is not evidence of damaged firmware and is not a reason to flash it.

### 4. Cables connected to ports not exposed by the driver

The PCAN-compatible four-port adapter used on October 14 exposed only can0/can1, while the cables were connected to physical CAN3/CAN4.
Nero firmware queries initially timed out. Moving the cables to CAN1/CAN2 immediately restored continuous feedback from both arms.
The October 16 replacement, an M.2 USB X4 with ID `395e:0020`, exposed all four channels. That replacement instead required updating initialization rules to match the new USB ID.

### 5. Avoid live USB sysfs unbind/rebind

On the g1wh KCAN X4-G2 bench, forced USB unbind/rebind left the MCU unresponsive,
with `-110/-71` timeouts. Removing USB power was required to recover it.
The installer does not use these operations or treat xHCI remove/rescan as routine recovery.
First put the arms in a condition where control can be disconnected, then follow the hardware manual for a power cycle or cold start.

### 6. Error storms on unconnected channels

Send queries only on connected channels with a confirmed bitrate. Error retransmission consumes USB and CPU resources.
Stop probing, bring unused interfaces down only when their control can safely stop, and inspect the wiring.
Do not rely on unlimited retries for recovery.

## Evidence and applicability

These cases come from this industrial PC and the g1wh CAN bench records on the 5090D machine.
The g1wh bench uses the bare Damiao motor protocol; Nero uses a complete-arm controller protocol. Driver experience transfers, but motion frames and all bus parameters do not.
