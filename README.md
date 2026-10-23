# XYZBox · USB CAN and Nero Joint Control

English | [简体中文](README.zh-CN.md)

This repository provides the files and instructions needed to restore the **USB CAN / M.2 USB CAN → Nero** connection after reinstalling the industrial PC.
It includes pinned driver sources, offline Python dependencies, installation configuration, troubleshooting guides, and a standalone joint control example.
The example does not require LeRobot, ROS, a GPU, PICO, or cameras.

The replacement-box Piper factory work is recorded in the [October 23 commissioning checkpoint](docs/checkpoints/2026-10-23-piper.md), including the verified two-arm lift/return/disable sequence. Its wiring is **left CAN1/can0, right CAN2/can1**; the older Nero installation below has a different mapping.
The shipped HP-disk box has a [Piper customer quick start](customer/PIPER-QUICKSTART.zh-CN.md) and a [delivery checkpoint](docs/checkpoints/2026-10-23-shipping.md). Its customer entry is `~/yikai-box`, with an independently verified SDK environment.

## Verified hardware and software

| Item | On-site result, October 16, 2026 |
|---|---|
| Host | x86_64, Ubuntu 24.04.4 LTS, Python 3.12 |
| Kernel / driver | `7.0.14-xyzbox-rt` (PREEMPT_RT) / `kcan 1.4.2`, managed by DKMS; original generic kernel retained |
| Current adapter | M.2 connected over USB, `395e:0020 KCAN-USB X4`, four interfaces: `can0`–`can3` |
| Nero external bus | **Classic CAN, 1 Mbps, sample point 0.75** |
| Arm firmware | Both arms: 1.12, using SDK profile `v112` |
| Wiring on this machine | Physical CAN1 → can0 → right arm; physical CAN2 → can1 → left arm; other ports unused |

**The left/right mapping above applies only to this installation. Verify it again at the customer site.** A four-channel adapter does not require all four channels to be enabled.
Use the actual product label and pinout for the customer's hardware; the USB ID is only one identification aid.
System startup, the driver, and offline software were checked after switching to RT. The arms were powered off during that work, so motion tests were not repeated.

## Quick start after reinstalling

Install Ubuntu and establish network access first. Exit all arm control programs, and keep the arms powered off while installing the driver and rebooting the PC.

```bash
sudo apt update
sudo apt install -y git python3-venv
git clone https://github.com/BigBillZhao/XYZBox.git
cd XYZBox

# Pinned driver sources are included; no "latest" download is needed.
sudo bash scripts/install_kcan.sh

# List only the interfaces that are physically connected; defaults: can0, can1.
sudo nano /etc/xyzbox-can.json
sudo reboot
```

For Gitea, use `ssh://git@gitea.zenbotx.com:19035/zenbot/XYZBox.git` as the clone URL. The remaining steps are the same.

Log in again and return to the repository directory:

```bash
lsusb -t                             # The adapter should show Driver=kcan.
dkms status                          # Driver 1.4.2 should be installed for this kernel.
ip -details link show type can       # Connected channels: UP / 1000000 / mtu 16.

# Packages for Ubuntu x86_64 / Python 3.12 are included.
bash scripts/setup_nero_env.sh

# Power on the arms and wait for initialization. These checks do not enable or move them.
.venv/bin/python tools/can_probe.py can0 can1
.venv/bin/python examples/nero_joint_control.py --channels can0 can1 --read
```

After checking feedback, wiring, and clearance, the **on-site operator explicitly starts motion**:

```bash
# Verify one arm first. --home is this fixture's ready pose, not the factory zero.
.venv/bin/python examples/nero_joint_control.py --channels can0 --home --speed 10

# Seven absolute joint targets, in radians:
.venv/bin/python examples/nero_joint_control.py --channels can0 \
  --joints 0 0.35 0 1.75 0 0 -0.6 --speed 10
```

The example reads by default. Only `--home` / `--joints` enable the arm and send motion commands.
It uses the official SDK's **`move_j` joint position mode** and does not run a continuous host-side MIT/gravity compensation loop.
Exiting does not explicitly call `disable()`. Exiting is neither an emergency stop nor a verified safe hold function.

## Documentation

| Guide | Contents |
|---|---|
| [Reinstallation and recovery](docs/en/01-reinstall.md) | Dependencies, DKMS, Secure Boot, offline preparation, existing installations, recovery, and upgrades |
| [Hardware and wiring](docs/en/02-hardware-and-can.md) | Two observed adapters, channels, bitrate, arm identification, and acceptance checks |
| [Troubleshooting](docs/en/03-troubleshooting.md) | Missing feedback, ACK errors, local echo, DOWN interfaces, error counters, and USB unbind pitfalls |
| [Nero joint example](docs/en/04-nero-example.md) | Reading without motion, single/dual-arm commands, parameters, firmware profiles, and exit behavior |
| [Validation scope](docs/en/05-validation.md) | Recorded evidence and test boundaries; enumeration alone does not establish arm communication |
| [Delivered software inventory](docs/en/06-delivery-software.md) | IK, XRoboToolkit, original recording workflow, acceptance sample, and maintenance archive |
| [Real-time kernel](docs/en/07-realtime-kernel.md) | PREEMPT_RT source, build, installation, DKMS, trial boot, and rollback |
| [Disk cloning](docs/09-disk-cloning.md) | Offline used-block images, source/target identification, and unique clone identities (Chinese) |
| [Fan monitoring](docs/10-fan-monitoring.md) | IT8786E discovery, RPM readings, tested PWM response, and preserved defaults (Chinese) |
| [Third-party sources](vendor/README.md) | Pinned versions, sources, archives, and SHA-256 checksums |
| [Third-party notices](THIRD_PARTY_NOTICES.md) | Component licenses and source distribution information |

The repository does not contain customer passwords, SSH private keys, the original system's home directory, datasets, or arm firmware update tools.
Host interface configuration does not flash the adapter or arm firmware. PICO, cameras, and the Ethernet management page can be configured independently; the joint example does not require them.

## Offline recovery scope

Driver/SDK sources and Linux x86_64 / CPython 3.12 wheels are included.
Ubuntu packages such as `dkms`, the compiler, and **headers matching the running kernel exactly** must be prepared separately.
See [offline preparation](docs/en/01-reinstall.md#offline-preparation). Do not reuse a `.ko` compiled for a different kernel.

## Verify the repository

```bash
sha256sum --check vendor/SHA256SUMS
.venv/bin/python -m unittest discover -s tests -v
```

These tests do not access physical CAN devices or move the arms.
