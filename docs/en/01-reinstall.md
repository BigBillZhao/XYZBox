# Reinstallation and Recovery

English | [简体中文](../01-reinstall.md) · [Home](../../README.md)

## 1. Install the target system

The verified platform is Ubuntu 24.04.4 LTS / x86_64 / Python 3.12.
Both the original `7.0.0-38-generic` and current `7.0.14-xyzbox-rt` kernels have been checked; see the [real-time kernel guide](07-realtime-kernel.md) for the RT validation scope. Other kernels, ARM hosts, and other distributions have not been validated by this repository.
Back up customer data and install Ubuntu using the normal system installation procedure. This repository does not partition or erase disks.

Prepare access to Ubuntu package sources, the network, and the chosen repository. Get the files from [GitHub](https://github.com/BigBillZhao/XYZBox),
or use the Gitea SSH URL `ssh://git@gitea.zenbotx.com:19035/zenbot/XYZBox.git`.
Port `19035` in that URL is the Gitea Git SSH port, not the industrial PC's SSH port.
Access keys are not included. The delivery team can also supply a complete repository archive.

## 2. Install kcan 1.4.2

```bash
cd XYZBox
sudo bash scripts/install_kcan.sh
```

The installer:

1. Checks `vendor/SHA256SUMS` and installs build tools, DKMS, matching kernel headers, and CAN tools.
2. Extracts the bundled source into a versioned directory under `/usr/src/`.
3. Regenerates the outdated **generated file** `dkms.conf` using the original 1.4.2 Makefile.
4. Builds and installs the module through DKMS. Linux 7.0 support comes from the original 1.4.2 sources, without a local compatibility patch.
5. Installs `/etc/xyzbox-can.json`, the systemd template, and udev rules.
6. Configures `kcan` to load at boot, prevents `peak_usb` from claiming the adapter automatically, and updates initramfs.

The installer does not unload the running driver, unbind USB, update firmware, reboot, or send arm commands.
After installing the module on disk, reboot with the arms powered off, following the README sequence.

### Secure Boot

Secure Boot was disabled on the verified machine. The script stops before module installation if it detects Secure Boot enabled.
If the customer requires Secure Boot, complete module signing and MOK enrollment according to their security policy before installation/loading.
Do not place signing private keys in this repository. A successful build does not establish that the kernel will trust the module.
Resolve signing/trust errors such as `Required key not available` in `dmesg` first.

### Existing installations

The script can be run again and preserves an existing `/etc/xyzbox-can.json`.
It refuses to overwrite a versioned source directory under `/usr/src/` that was not created by this installer.
Check `dkms status`, the existing sources, and their use first. Preserve needed files, then use the original installation method to remove or migrate that installation during maintenance.
Avoid old removal examples that delete every version of the driver.

On a working machine, use read-only checks rather than reinstalling the driver just to test the installer.

## 3. Enable connected interfaces

Default `/etc/xyzbox-can.json`:

```json
{"channels":["can0","can1"],"bitrate":1000000,"sample_point":0.75}
```

List only channels connected to arms. If existing naming rules use names such as `kcan0`, use those actual names here.
This package does not add interface renaming rules.

```bash
sudo systemctl start xyzbox-can@can0.service xyzbox-can@can1.service
systemctl status xyzbox-can@can0.service xyzbox-can@can1.service
ip -details -statistics link show can0
ip -details -statistics link show can1
```

Expect UP, MTU 16, and bitrate 1000000. `ERROR-ACTIVE` is the name of a normal CAN operating state;
check whether `berr-counter tx/rx` is zero rather than treating the word ERROR as a failure by itself.

The helper leaves an already-UP interface unchanged when bitrate/MTU match. It refuses to reconfigure an UP interface with different settings.
To change an active bitrate, stop control, support the arms, and make the change during maintenance.

## 4. Restore the minimal Python environment

```bash
bash scripts/setup_nero_env.sh
```

By default, `.venv` is installed entirely from the repository for Linux x86_64 / CPython 3.12.
Check `python3 --version`; `python3-venv` must be installed.

```bash
# Use a different environment directory:
bash scripts/setup_nero_env.sh /path/to/nero-venv

# Other Linux architectures/Python versions need matching online packages and separate validation:
bash scripts/setup_nero_env.sh --online /path/to/nero-venv
```

The SDK is pinned to the official archive `1ae40ad`; its full SHA-256 is in the manifest.
A `pip` version of `pyAgxArm 1.0.0` alone does not establish support for firmware 1.12, because different source snapshots may share that package version.
The script checks `resolve_firmware_profile('nero', '1.12') == 'v112'` directly.

## 5. Check the system after reboot

Verify in order:

1. USB enumeration is correct and `lsusb -t` reports `kcan`.
2. Connected channels are enabled with the configured settings; unused channels remain DOWN.
3. Passive reception shows external feedback. Local transmit echo alone does not pass this check.
4. The non-motion example reads firmware, seven joint angles, and arm status.
5. The operator confirms wiring and clearance before explicitly running joint motion.

If `can0` exists but remains DOWN after reboot, check whether udev matches only an old USB ID or the configured interface name differs from the actual name.
This happened during the October 16, 2026 adapter replacement: the driver was loaded, but initialization rules did not yet match the new `395e:0020` ID.

## Offline preparation

Included: kcan sources, pyAgxArm sources, and Python 3.12/x86_64 runtime and build wheels.

Prepare these Ubuntu packages and their dependencies separately, using versions from the target system's package sources:

```text
build-essential dkms linux-headers-<target-running-kernel-version>
can-utils iproute2 usbutils python3 python3-venv mokutil
```

Prepare an offline APT repository or installation medium on a networked machine with the **same Ubuntu release and target kernel**, and test the installation with networking disconnected.
Copying an APT cache alone does not guarantee a complete dependency set.
Once the system dependencies are installed offline:

```bash
sudo bash scripts/install_kcan.sh --skip-apt
bash scripts/setup_nero_env.sh
```

## Kernel updates and recovery

DKMS rebuilds for new kernels, but this does not establish compatibility with every future kernel. Retain a verified bootable kernel before upgrading.
Check DKMS build logs and CAN enumeration after the update before running control software.

Prefer booting the retained kernel from GRUB for recovery. Do not unload a live driver to mask installation problems.
If this installation must be removed, stop arm control and schedule reboot maintenance first:

```bash
# Confirm the package name with dkms status, then enter it at the prompt:
read -r -p 'DKMS package name: ' driver_package
test -n "$driver_package" && sudo dkms remove -m "$driver_package" -v 1.4.2 --all
sudo rm /etc/modprobe.d/xyzbox-kcan.conf /etc/modules-load.d/xyzbox-kcan.conf
sudo rm /etc/udev/rules.d/80-xyzbox-can.rules /etc/systemd/system/xyzbox-can@.service
sudo systemctl daemon-reload
sudo update-initramfs -u
```

This removes only the configuration files named by this package. Retain `/etc/xyzbox-can.json` and the sources for traceability.
Verify that the driver used after recovery supports the actual adapter.
