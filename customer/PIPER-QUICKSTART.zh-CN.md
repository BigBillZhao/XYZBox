# Yikai Box · Piper SDK 使用说明

本机已配置 Ubuntu 24.04、实时内核、昆宏四路 CAN 驱动和固定版本 pyAgxArm SDK。
客户入口：`/home/ubuntu/yikai-box`。登录用户：`ubuntu`；登录凭据单独交付。

## 接线与开机

- 物理 CAN1 对应 Linux `can0`，本次测试接左臂。
- 物理 CAN2 对应 Linux `can1`，本次测试接右臂。
- CAN3/4 保留，默认不启用。CAN1/2 开机自动启用，Classic CAN 1 Mbps。
- 核对机械臂与盒子的 CAN-H/CAN-L、供电及总线终端。标签决定接线，不按线色猜测。
- 本机使用 DHCP；当前主机名为 `yikai-21c5e86e`，客户网络中的 IP 会重新分配。

## 第一次运行：只读取状态

打开终端：

```bash
cd ~/yikai-box
source .venv/bin/activate
python examples/piper_read_status.py --channels can0 can1
```

只接一条臂时，把通道改为 `--channels can0` 或 `--channels can1`。
示例只读取 SDK 回传，不使能、不运动、不切换主从角色。
本次使用标准 Piper、固件 `S-V1.7-3`，对应 `--profile default`。
本机已完成「惠普盘冷启动 → RT 内核 → 双臂抬升 → 回位 → 禁能」测试。

## 编写自己的程序

```python
from pyAgxArm import AgxArmFactory, ArmModel, PiperFW, create_agx_arm_config

cfg = create_agx_arm_config(
    robot=ArmModel.PIPER,
    firmeware_version=PiperFW.DEFAULT,
    interface="socketcan",
    channel="can0",
)
arm = AgxArmFactory.create_arm(cfg)
arm.connect()
# 等待新鲜反馈后，按 SDK 文档读取状态、使能并执行自己的轨迹。
# 结束前由应用明确处理机械臂保持/支撑/禁能，再断开连接。
arm.disconnect()
```

完整离线 API：`~/yikai-box/docs/sdk/piper_api.md`；固件对应表：`firmware_reference.md`。
SDK 公开方法包括 `enable()`、`move_j()`、`move_mit()`、`disable()`。
六关节角度单位为 rad。断开连接不等于禁能，也不等于机械臂被安全保持。
本次夹具 home 和抬升坐标不作为客户场地的默认坐标；请使用客户自己的安装位置、负载和工作空间。

不同型号（Piper X/L/H、Nero）或固件版本应选匹配的 `ArmModel` 和固件 profile。
本次验收覆盖上述标准 Piper；不代表每个型号、固件和 API 都已逐项实测。

## 排查与恢复

```bash
uname -r                        # 本次交付：7.0.14-xyzbox-rt
cat /sys/kernel/realtime         # 应为 1
ip -details link show type can   # can0/can1：UP、1000000、mtu 16
dkms status                     # 当前内核下应有 kunhong-linux-driver/1.4.2
```

没有回传时先核对通道、接线、上电状态和机械臂主从/示教状态。
开启终端的另一个程序不会自动停止原控制程序；一条臂由一个控制程序负责。

SDK 环境需要重建时，可离线执行：

```bash
cd ~/yikai-box
bash scripts/setup_piper_env.sh
```

普通内核 `7.0.0-38-generic` 保留作回退。更换内核后需重新编译 CAN DKMS 并复验。
SDK 固定为 pyAgxArm `1ae40ad`（Python 包版本显示 1.0.0），不要仅按包版本号判断源码是否相同。
厂商原始源码与依赖校验位于 `vendor/`；不必联网下载最新版才能使用。

## 风扇

```bash
sensors it8786-isa-0a40
```

已配置开机加载 `it87` 读取风扇。当前保持原始全速策略。
第二路低占空比测速有波动，本次未部署自动调速服务。

本机没有配置开机自动运动。售前调试记录留在维护目录，客户日常从 `~/yikai-box` 开始。
