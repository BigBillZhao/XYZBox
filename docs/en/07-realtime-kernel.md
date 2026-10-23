# Real-Time Kernel: Installation, Verification, and Rollback

English | [简体中文](../07-realtime-kernel.md) · [Home](../../README.md)

## Delivery status

On October 23, 2026, the new dual-Piper box (session address `192.168.110.12`)
booted `7.0.14-xyzbox-rt`, package version `7.0.14-xyzbox2`, and made it the default while retaining generic.
PREEMPT_RT, CAN DKMS, networking and desktop services passed verification. Five-second passive captures received approximately
15,200 frames on each 1 Mbps CAN channel, with zero CAN error frames and all twelve drivers disabled.
No arm motion was run during this RT validation. A 30-second idle cyclictest observed a 52 µs maximum versus 39 µs on generic;
these samples do not demonstrate lower latency or establish a worst-case bound.
See [build and runtime evidence](../../artifacts/rt-kernel-20261023/).

The following records the earlier Nero delivery machine:

October 16, 2026: `7.0.14-xyzbox-rt` was installed, trial-booted, checked, and set as the default kernel.
`uname` reports `PREEMPT_RT`, and `/sys/kernel/realtime` is `1`.
The original `7.0.0-38-generic` image, headers, and modules are marked as manually installed and retained for rollback.
CAN driver 1.4.2 was rebuilt, signed, and loaded for RT. All four interfaces are visible; the two in use run classic CAN at 1 Mbps.
SSH, the display service, HDMI output, existing static network settings, and offline software checks passed.
The arms were powered off during this phase; arm motion and PICO/camera hardware were not tested. On October 16, 2026, the user confirmed normal display, login, mouse, and keyboard operation after rebooting into RT.
Results are in [`validation/DELIVERY-20261016.json`](../../validation/DELIVERY-20261016.json) and in `~/nero-delivery/manifests/` on the customer PC.

PREEMPT_RT requires `CONFIG_PREEMPT_RT=y`. Adding only `preempt=full`, `threadirqs`, or a lowlatency kernel does not replace this check.
See the [Linux kernel configuration documentation](https://docs.kernel.org/core-api/real-time/kernel-configuration.html).

The RT kernel improves schedulability; it does not guarantee zero latency in Python, USB CAN, cameras, or the full teleoperation workflow.
The delivered configuration retains desktop, USB, and network drivers. It does not automatically assign high priority to every Python thread or disable RT throttling protections.

## Maintenance options

With an applicable Ubuntu Pro subscription, an officially maintained real-time kernel can be used. The account holder should attach the machine interactively:

```bash
sudo apt update
sudo apt install ubuntu-pro-client
sudo pro attach
sudo pro enable realtime-kernel --access-only
apt-cache policy linux-realtime-hwe-24.04
sudo apt install linux-realtime-hwe-24.04
```

Check matching headers, USB CAN DKMS, and the rollback boot option before rebooting. Do not put Pro credentials in the repository.
Available kernel versions depend on the actual subscription repositories and [official installation instructions](https://ubuntu.com/pro-client/docs/en/docs/howtoguides/enable_realtime_kernel/).

This machine is not attached to Pro. The delivery team chose to build from the **same source package** as the original Ubuntu kernel:
`linux-hwe-7.0 7.0.0-38.38~24.04.4`, with source version `7.0.14`.
The Ubuntu package ABI number differs from the underlying stable kernel version; this is expected.
The delivery maintainer must track updates, rebuild, and revalidate these custom packages. They are not officially maintained RT binary packages.
An older `6.8.1-1015-realtime` package was visible in public repositories on October 16, 2026, but was not used to replace the current kernel.

## Build from the matching source

Prepare at least 40 GB of space and build as a normal user. Keep the PC connected to power, exit control programs, and power off the arms.

```bash
sudo apt update
sudo apt install build-essential python3 bc bison flex gawk libssl-dev libelf-dev libdw-dev \
  libncurses-dev dwarves rsync cpio kmod fakeroot dpkg-dev debhelper zstd rt-tests stress-ng
```

Enable Ubuntu 24.04 `deb-src` repositories using a mirror with Ubuntu archive signatures.
This build used `https://mirrors.nju.edu.cn/ubuntu`, suites `noble-updates` / `noble-security`, component `main`,
with `Signed-By: /usr/share/keyrings/ubuntu-archive-keyring.gpg`.
Enable the source repository and update its index:

```bash
repo="$HOME/XYZBox"
rt="$HOME/xyzbox-rt-rebuild"
# Skip adding an identical deb-src entry if it already exists. Binary package sources are unchanged.
sudo install -m 644 "$repo/system/realtime/ubuntu-kernel-src.sources" \
  /etc/apt/sources.list.d/xyzbox-kernel-src.sources
sudo apt update
mkdir -p "$rt/downloads"
cd "$rt/downloads"
apt-get source --download-only linux-hwe-7.0=7.0.0-38.38~24.04.4
sha256sum --check "$repo/system/realtime/SHA256SUMS.sources"
dpkg-source -x linux-hwe-7.0_7.0.0-38.38~24.04.4.dsc "$rt/source"
BUILD_JOBS=6 bash "$repo/scripts/build_rt_kernel.sh" "$rt/source" "$rt/build"
```

If the mirror later removes this version, use the three original source archives and checksum list retained on the delivery machine.
The sources were checked against APT's signed index and SHA-256. The developer signature on the `.dsc` was not separately verified locally with its public key.
Do not substitute an arbitrary archive with the same filename.

The script retains broad hardware support, enables PREEMPT_RT, and disables dynamic preemption, Rust, and DWARF/BTF debug data.
The latter two choices match the available toolchain and limit build size. RT dependencies disable some incompatible options, such as legacy iptables;
this machine uses the nftables backend. Configuration differences are saved in `config-diff.txt` in the build directory.
Public certificates still come from the Ubuntu source package. Do not commit a module signing private key generated during the build.
The build script also restores executable permission on `debian/scripts/sign-module`.
Files added by the source-package diff may have mode 0644; without this fix, module installation reports `Permission denied` and skips signing.

After fixing a missing dependency, resume an interrupted build with the same source and build directories:

```bash
make -C "$rt/source" O="$rt/build" -j6 \
  KBUILD_BUILD_USER=xyzbox KBUILD_BUILD_HOST=nero-control \
  KDEB_PKGVERSION=7.0.14-xyzbox1 bindeb-pkg
cp "$rt/build/.config" "$rt/config-7.0.14-xyzbox-rt"
```

## Install and trial-boot

Retain the original generic kernel. Secure Boot is disabled on this industrial PC; the custom kernel does not have a trusted distribution boot signature.
If Secure Boot is enabled on another machine, complete the organization's own kernel/module signing and key enrollment procedure first.
Do not blindly disable the customer's existing boot security settings.

Inspect the actual menu entries in `/boot/grub/grub.cfg`. The following examples use Ubuntu's default English menu labels.
Versions and menu entries must match the target machine; `rt` points to the directory containing the built packages.

```bash
# Pin the old kernel before installation so package installation cannot change the next default boot.
sudo apt-mark manual linux-image-7.0.0-38-generic linux-headers-7.0.0-38-generic \
  linux-modules-7.0.0-38-generic
echo 'GRUB_DEFAULT="Advanced options for Ubuntu>Ubuntu, with Linux 7.0.0-38-generic"' \
  | sudo tee /etc/default/grub.d/90-xyzbox-kernel.cfg
sudo update-grub

# Install headers first, then supply the matching configuration for Ubuntu DKMS.
sudo dpkg -i "$rt/linux-headers-7.0.14-xyzbox-rt_7.0.14-xyzbox1_amd64.deb"
sudo install -m 644 "$rt/config-7.0.14-xyzbox-rt" \
  /usr/src/linux-headers-7.0.14-xyzbox-rt/.config
# Install the image next; its hooks build the CAN module for the new kernel.
# Do not install *.deb indiscriminately and overwrite linux-libc-dev.
sudo dpkg -i "$rt/linux-image-7.0.14-xyzbox-rt_7.0.14-xyzbox1_amd64.deb"
sudo dkms autoinstall -k 7.0.14-xyzbox-rt
dkms status
modinfo -k 7.0.14-xyzbox-rt kcan
sudo update-initramfs -u -k 7.0.14-xyzbox-rt
sudo update-grub

# Select the new kernel for one boot only. Exit control programs and power off the arms first.
sudo grub-reboot 'Advanced options for Ubuntu>Ubuntu, with Linux 7.0.14-xyzbox-rt'
sudo reboot
```

DKMS must report the module installed for the new kernel, and `modinfo` vermagic must match. Do not trial-boot after a failed check.
Upstream Linux 7.0 headers packages omit the top-level `.config`; adding it above provides compatibility with Ubuntu 24.04 DKMS.
If installation has already reported `Kernel config ... not found`, add the configuration and run `dkms build --force` and `dkms install --force`
for that module, then update initramfs, even if the earlier module build succeeded. Do not ignore the compatibility warning.
The driver's build option `RT=NO_RT` selects the ordinary Linux interface rather than Xenomai/RTDM.
For Linux PREEMPT_RT + SocketCAN, retain that ordinary Linux interface; the option name is not a reason to switch to a Xenomai build.
Preserve the existing `video=eDP-1:d` display fix, network settings, and CAN channel configuration.
A one-time boot entry does not detect system health. If boot hangs, an on-site restart is required; the following boot returns to the pinned old kernel.

## Checks after boot

```bash
uname -r
cat /sys/kernel/realtime                  # Expected: 1.
grep '^CONFIG_PREEMPT_RT=y' /boot/config-$(uname -r)
dkms status
lsusb -t                                # Adapter: Driver=kcan.
ip -details link show type can           # Connected channels: classic CAN, 1 Mbps, mtu 16.
systemctl is-active ssh NetworkManager display-manager
sudo cyclictest -a 2 -t1 -p80 -i1000 -D30s -m -q
```

Check the management network, device-network static addresses, display/login, and original Python environment.
Without cameras or arms connected, these are kernel, driver enumeration, and offline software checks, not full teleoperation acceptance.
Each measurement below ran for 30 seconds and 30,000 cycles. Values are in µs:

| Kernel / condition | Minimum | Average | Maximum observed |
|---|---:|---:|---:|
| generic / idle | 1 | 5 | 44 |
| generic / 6 CPU load workers | 1 | 1 | 9 |
| PREEMPT_RT / idle | 1 | 5 | 19 |
| PREEMPT_RT / 6 CPU load workers | 1 | 1 | 4 |

CPU load used `stress-ng --cpu 6 --cpu-method matrixprod --timeout 55s --quiet`, with the same cyclictest command started after three seconds.
Authenticate with sudo before timing so the password prompt does not consume the load window. Confirm the load is still running when measurement ends.
cyclictest requested CPU latency QoS of 0 µs.
These are single short observations, not worst-case guarantees or upper bounds on real control application latency.
Application qualification still requires camera, graphics, and control workloads.

Set RT as the default only after the basic checks pass:

```bash
echo 'GRUB_DEFAULT="Advanced options for Ubuntu>Ubuntu, with Linux 7.0.14-xyzbox-rt"' \
  | sudo tee /etc/default/grub.d/90-xyzbox-kernel.cfg
sudo update-grub
```

## Rollback and future upgrades

If display, network, or CAN problems occur, choose the retained generic kernel under GRUB's “Advanced options for Ubuntu”,
or change `GRUB_DEFAULT` above back to `7.0.0-38-generic` while the system is reachable and reboot.
Confirm the old kernel works before considering removal of RT packages. Never uninstall the running kernel.

Every kernel change requires matching headers, a USB CAN DKMS rebuild, a trial boot, and rechecks.
A pinned default kernel does not automatically switch to newer security releases. The maintainer must schedule updates rather than leaving this snapshot in place indefinitely.
If source or build configuration changes, use a new kernel suffix and package version. Different builds must not share the same `uname -r`,
or DKMS may incorrectly treat an old module as already installed for the new build.
