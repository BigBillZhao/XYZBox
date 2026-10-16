# 实时内核：安装、复验与回退

## 交付状态

2026-10-16：原内核为 `7.0.0-38-generic`，已保存基线配置与调度测试。
同源 `7.0.14-xyzbox-rt` 正在编译，**尚未安装、重启或完成 RT 验证**。
最终安装状态以本页更新和客户机 `~/nero-delivery/manifests/` 的记录为准。

PREEMPT_RT 必须实际启用 `CONFIG_PREEMPT_RT=y`；只增加 `preempt=full`、`threadirqs`
或安装 lowlatency 内核不能代替这项检查。[Linux 内核配置说明](https://docs.kernel.org/core-api/real-time/kernel-configuration.html)

实时内核改善可调度性，不保证 Python、USB CAN、相机或整个遥操流程零延迟。
交付配置保留桌面、USB 与网卡驱动；不自动把全部 Python 线程设为高优先级，也不关闭 RT 限流保护。

## 维护路线

有适用的 Ubuntu Pro 订阅时，可使用官方维护的实时内核。先由账号持有人在本机交互绑定：

```bash
sudo apt update
sudo apt install ubuntu-pro-client
sudo pro attach
sudo pro enable realtime-kernel --access-only
apt-cache policy linux-realtime-hwe-24.04
sudo apt install linux-realtime-hwe-24.04
```

此后仍需检查匹配 headers、USB CAN DKMS、启动回退，再重启；不要把 Pro 凭据写进仓库。
支持的内核版本以实际订阅源和[官方安装说明](https://ubuntu.com/pro-client/docs/en/docs/howtoguides/enable_realtime_kernel/)为准。

本机尚未绑定 Pro。下面提供从现用 Ubuntu 内核**同一源包**构建的路线：
源包 `linux-hwe-7.0 7.0.0-38.38~24.04.4`，源码版本 `7.0.14`。
Ubuntu 包的 ABI 编号与源码的 stable 版本号不同，这是正常的。
自编译包需要交付维护方持续跟进内核更新、重新构建并复验；它不属于官方维护的 RT 二进制包。
2026-10-16 公开仓库还可见较旧的 `6.8.1-1015-realtime`，本次没有用它替换现用内核。

## 同源构建

准备至少 40 GB 空间，在普通用户下构建。机器应接电，控制程序退出，机械臂断电。

```bash
sudo apt update
sudo apt install build-essential bc bison flex libssl-dev libelf-dev libdw-dev \
  libncurses-dev dwarves rsync cpio kmod fakeroot dpkg-dev debhelper zstd rt-tests
```

APT 需启用 Ubuntu 24.04 的 `deb-src`，使用带 Ubuntu 归档签名的镜像。
本次使用 `https://mirrors.nju.edu.cn/ubuntu` 的 `noble-updates` / `noble-security`、`main` 源；
`Signed-By` 为 `/usr/share/keyrings/ubuntu-archive-keyring.gpg`。
启用源码源并更新索引后：

```bash
repo="$HOME/XYZBox"
rt="$HOME/xyzbox-rt-rebuild"
# 已有相同 deb-src 时不必再添加；这里只增加源码索引，不替换二进制软件源。
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

镜像以后若不再保留该版本，使用交付机保存的三个原始源包和校验清单。
本次来源由 APT 已签名的索引及 SHA-256 核对；本地没有单独验证 `.dsc` 的开发者签名公钥。
不能只下载一个任意的同名压缩包继续执行。

脚本保留完整硬件配置，启用 PREEMPT_RT，关闭动态抢占、Rust 和 DWARF/BTF 调试数据。
后两项用于匹配本机工具链并控制构建体积。RT 依赖会关闭部分不兼容配置（例如 legacy iptables）；
本机使用 nftables 后端。配置差异保存在构建目录的 `config-diff.txt`。
公钥证书继续来自 Ubuntu 源包，构建产生的模块签名私钥不得提交到仓库。

若编译中断，修复依赖后在相同源码和构建目录继续：

```bash
make -C "$rt/source" O="$rt/build" -j6 \
  KBUILD_BUILD_USER=xyzbox KBUILD_BUILD_HOST=nero-control \
  KDEB_PKGVERSION=7.0.14-xyzbox1 bindeb-pkg
```

## 安装与首次试启动

保留原 generic 内核。当前工控机 Secure Boot 已关闭；自编译内核不具备受信任的发行版启动签名。
其他机器若启用了 Secure Boot，需先完成组织自己的内核/模块签名与密钥登记流程。
不要盲目关闭客户已有的启动安全设置。

先检查 `/boot/grub/grub.cfg` 中的实际菜单名称。下面是 Ubuntu 默认英文菜单的示例，
版本和菜单项必须与本机一致；`rt` 指向构建包所在目录。

```bash
# 安装前先固定旧内核，避免安装包改变下次默认启动项。
echo 'GRUB_DEFAULT="Advanced options for Ubuntu>Ubuntu, with Linux 7.0.0-38-generic"' \
  | sudo tee /etc/default/grub.d/90-xyzbox-kernel.cfg
sudo update-grub

# 只装内核 image 和对应 headers；不要用 *.deb 把 linux-libc-dev 一起覆盖。
sudo dpkg -i "$rt/linux-headers-7.0.14-xyzbox-rt_7.0.14-xyzbox1_amd64.deb" \
  "$rt/linux-image-7.0.14-xyzbox-rt_7.0.14-xyzbox1_amd64.deb"
sudo dkms autoinstall -k 7.0.14-xyzbox-rt
dkms status
modinfo -k 7.0.14-xyzbox-rt kcan
sudo update-initramfs -u -k 7.0.14-xyzbox-rt
sudo update-grub

# 新内核仅试启动一次；重启前确认程序退出、机械臂断电。
sudo grub-reboot 'Advanced options for Ubuntu>Ubuntu, with Linux 7.0.14-xyzbox-rt'
sudo reboot
```

DKMS 必须显示新内核下已安装，`modinfo` 的 vermagic 必须匹配新内核，失败时不要试启动。
保留原有 `video=eDP-1:d` 显示修复、网络配置和 CAN 通道配置。
一次性启动项不会自动检测机器是否健康；若启动挂住，需现场重新启动机器，下一次会回到固定的旧内核。

## 启动后验收

```bash
uname -r
cat /sys/kernel/realtime                  # 应为 1
grep '^CONFIG_PREEMPT_RT=y' /boot/config-$(uname -r)
dkms status
lsusb -t                                # USB CAN 对应 Driver=kcan
ip -details link show type can           # 接线通道经典 CAN、1 Mbps、mtu 16
systemctl is-active ssh NetworkManager display-manager
sudo cyclictest -a 2 -t1 -p80 -i1000 -D30s -m -q
```

核验管理网、设备网静态配置、显示/登录和原 Python 环境。未接相机或机械臂时，
只能完成内核、驱动枚举与离线软件检查，不能记为完整遥操验收。
本次 generic 空闲基线：30,000 周期，最小 1 µs、平均 5 µs、最大 44 µs；
它只是同条件对比值，不能当作最坏情况承诺。正式应用还需带相机、图形和控制负载测试。

全部基础验证通过后才设为默认：

```bash
echo 'GRUB_DEFAULT="Advanced options for Ubuntu>Ubuntu, with Linux 7.0.14-xyzbox-rt"' \
  | sudo tee /etc/default/grub.d/90-xyzbox-kernel.cfg
sudo update-grub
```

## 回退与后续升级

出现显示、网络或 CAN 问题时，在 GRUB「Advanced options for Ubuntu」选择保留的 generic 内核；
或在线将上面的 `GRUB_DEFAULT` 改回 `7.0.0-38-generic` 后重启。
先确认旧内核运行正常，再考虑移除 RT 包，绝不卸载当前正在运行的内核。

以后每次换内核均需匹配 headers、重编 USB CAN DKMS、试启动和复验。
固定默认内核不会自动切到新安全版本；维护方必须主动安排更新，不应长期停留在这个快照。
