# 重装与恢复

## 1. 安装目标系统

已验证目标为 Ubuntu 24.04.4 LTS / x86_64 / Python 3.12。
现场内核为 `7.0.0-38-generic`。其他内核、ARM 主机与其他发行版尚未在本仓库重新验收。
保存客户数据后，按整机常规流程安装 Ubuntu；本仓库不执行磁盘分区或清盘。

准备软件源、网络和 Gitea 访问权限。仓库 URL 中的端口 `19035` 是 Git SSH 端口，
不是工控机 SSH 端口。仓库不附带访问密钥；也可以由交付方提供完整仓库压缩包。

## 2. 安装 kcan 1.4.2

```bash
cd XYZBox
sudo bash scripts/install_kcan.sh
```

安装器会：

1. 检查 `vendor/SHA256SUMS`，安装编译器、DKMS、匹配内核头文件和 CAN 工具。
2. 从仓库里的源码包创建 `/usr/src/kunhong-linux-driver-1.4.2`。
3. 修复发行包中旧的 **生成文件** `dkms.conf`：由原版 1.4.2 Makefile 重新生成版本信息。
4. 通过 DKMS 构建、安装内核模块；Linux 7.0 兼容性由官方 1.4.2 源码提供，没有现场补丁。
5. 安装 `/etc/xyzbox-can.json`、systemd 模板及 udev 规则。
6. 写入开机加载 `kcan`、禁止 `peak_usb` 自动抢占的配置，并更新 initramfs。

安装器不主动卸载正在运行的驱动、不解绑 USB、不升级固件、不重启、不发机械臂命令。
模块安装到磁盘后，按 README 的顺序在机械臂断电时重启工控机。

### Secure Boot

本次现场 Secure Boot 为 disabled。脚本遇到 enabled 会在模块安装前停下。
客户若要求启用 Secure Boot，应按客户的安全策略完成 DKMS 模块签名和 MOK 注册，再安装/加载模块；
不要把签名私钥放进本仓库。仅编译成功并不表示内核允许加载。
`dmesg` 中的 `Required key not available` 等错误应先处理签名信任。

### 已有安装

同一套脚本可重复运行；已存在 `/etc/xyzbox-can.json` 时保留它。
如果 `/usr/src/kunhong-linux-driver-1.4.2` 不是这套资料创建的，脚本不会覆盖。
先检查 `dkms status`、已有源码和当前用途；保存必要文件后，在维护窗口使用原安装方式卸载或迁移，
不要套用厂商脚本里删除整个 `/var/lib/dkms/kunhong-linux-driver` 的旧示例。

在已有现场电脑上，不要为了验证安装器而重新装驱动；可使用只读验收步骤。

## 3. 启用已接线的接口

`/etc/xyzbox-can.json` 的默认值：

```json
{"channels":["can0","can1"],"bitrate":1000000,"sample_point":0.75}
```

只填写已接机械臂的通道。若已有厂商命名规则把接口改成 `kcan0`，这里也要用真实名称。
本资料不新增接口重命名规则。

```bash
sudo systemctl start xyzbox-can@can0.service xyzbox-can@can1.service
systemctl status xyzbox-can@can0.service xyzbox-can@can1.service
ip -details -statistics link show can0
ip -details -statistics link show can1
```

预期为 UP、MTU 16、bitrate 1000000。`ERROR-ACTIVE` 是 CAN 正常工作的状态名，
应结合 `berr-counter tx/rx` 是否为 0 判断，不能只看这个名字中的 ERROR。

helper 遇到已经 UP 且速率/MTU 匹配的接口会保持现状；遇到不同配置会拒绝在线重配。
如果需要更改正在用的速率，先结束所有控制并做好机械臂支撑，再在维护窗口操作。

## 4. 恢复最小 Python 环境

```bash
bash scripts/setup_nero_env.sh
```

默认 `.venv` 全部安装来自仓库，适用于 Linux x86_64 / CPython 3.12。
Python 版本由 `python3 --version` 确认；需要 `python3-venv`。

```bash
# 指定环境目录：
bash scripts/setup_nero_env.sh /path/to/nero-venv

# 其他 Linux 架构/Python 版本需在线取得匹配依赖；尚需自行验收：
bash scripts/setup_nero_env.sh --online /path/to/nero-venv
```

SDK 源码固定为官方归档 `1ae40ad`，完整归档 SHA-256 见 manifest。
不要按 `pip` 显示的 `pyAgxArm 1.0.0` 判断是否支持 1.12：不同源码快照可能使用同一包版本号。
脚本会实际检查 `resolve_firmware_profile('nero', '1.12') == 'v112'`。

## 5. 重启验收

按顺序确认：

1. USB 枚举正确，`lsusb -t` 显示 `kcan`。
2. 已接通道按配置启用；无关通道保持 DOWN。
3. 被动监听有外部反馈；若只见本机发送回显，不算通过。
4. 无运动示例读到固件、七关节角和状态。
5. 操作者确认接线和空间后，才执行显式关节移动示例。

重启后出现 `can0` 但 DOWN，常见原因是 udev 只匹配旧卡 USB ID，或配置里的名字与实际接口不一致。
2026-10-16 的更换卡案例就是如此：驱动已经加载，缺的是新 `395e:0020` 的初始化规则。

## 离线准备

已随仓库提供：kcan 源码、pyAgxArm 源码、Python 3.12/x86_64 运行及构建轮子。

另外准备以下 Ubuntu 包及其依赖，版本应来自目标系统的软件源：

```text
build-essential dkms linux-headers-<目标正在运行的内核版本>
can-utils iproute2 usbutils python3 python3-venv mokutil
```

建议在与客户**相同 Ubuntu 版本和目标内核**的联网机器上准备离线 apt 仓库/安装介质，
并在断网环境实际试装。单纯复制本机 apt 缓存不能保证依赖齐全。
依赖已离线安装后：

```bash
sudo bash scripts/install_kcan.sh --skip-apt
bash scripts/setup_nero_env.sh
```

## 内核更新与恢复

DKMS 会为新内核重编，但不代表所有未来内核都已兼容。升级前保留一个验证过的可启动内核，
升级后先检查 DKMS 构建日志和 CAN 枚举，再允许控制程序运行。

恢复到旧内核优先使用 GRUB 中已保留的内核；不要热拔驱动来掩盖安装问题。
确需撤销本套安装时，先关闭机械臂控制并安排重启维护：

```bash
sudo dkms remove -m kunhong-linux-driver -v 1.4.2 --all
sudo rm /etc/modprobe.d/xyzbox-kcan.conf /etc/modules-load.d/xyzbox-kcan.conf
sudo rm /etc/udev/rules.d/80-xyzbox-can.rules /etc/systemd/system/xyzbox-can@.service
sudo systemctl daemon-reload
sudo update-initramfs -u
```

以上只撤销本套命名的配置。保留 `/etc/xyzbox-can.json` 和源码用于追溯；恢复后的驱动是否支持实际卡仍需核验。
