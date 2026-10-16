# XYZBox · USB CAN 与 Nero 关节控制

本仓库用于客户重装工控机后恢复 **USB CAN / M.2 USB CAN → Nero** 链路。
包含固定版本驱动源码、离线 Python 依赖、安装配置、排障手册及一个独立关节控制示例。
示例不依赖 LeRobot、ROS、GPU、PICO 或摄像头。

## 已验证的硬件与软件

| 项目 | 2026-10-16 现场结果 |
|---|---|
| 主机 | x86_64，Ubuntu 24.04.4 LTS，Python 3.12 |
| 内核 / 驱动 | `7.0.14-xyzbox-rt`（PREEMPT_RT）/ `kcan 1.4.2`，DKMS；保留原 generic 内核 |
| 新卡 | M.2 经 USB 枚举，`395e:0020 KCAN-USB X4`，四路 `can0`～`can3` |
| Nero 外部总线 | **经典 CAN，1 Mbps，采样点 0.75** |
| 机械臂固件 | 两臂均为 1.12，对应 SDK `v112` |
| 本次接线 | 物理 CAN1 → can0 → 右臂；物理 CAN2 → can1 → 左臂；其余两路未接 |

**上表的左右关系只属于本次接线，客户现场必须重新确认。** 卡有四路，不代表四路都要启用。
型号铭牌与引脚定义以客户实际产品为准；USB ID 是识别依据之一。
RT 切换后已检查系统启动、驱动和离线软件；本轮机械臂断电，未重复执行运动测试。

## 重装后最短路径

先完成 Ubuntu 安装并联网。机械臂控制程序全部退出，在机械臂断电时安装驱动和重启主机。

```bash
sudo apt update
sudo apt install -y git python3-venv
git clone ssh://git@gitea.zenbotx.com:19035/zenbot/XYZBox.git
cd XYZBox

# 固定的驱动与源码在仓库内，不依赖“latest”下载链接。
sudo bash scripts/install_kcan.sh

# 只填真正接线的系统接口名；默认 can0、can1。
sudo nano /etc/xyzbox-can.json
sudo reboot
```

重新登录，回到仓库目录：

```bash
lsusb -t                             # 对应 USB 接口应为 Driver=kcan
dkms status                          # CAN 驱动应显示 1.4.2 installed
ip -details link show type can       # 接线通道应 UP / 1000000 / mtu 16

# Ubuntu x86_64 / Python 3.12 的 Python 安装包已随仓库提供。
bash scripts/setup_nero_env.sh

# 机械臂上电，等待初始化完成。以下两步不使能、不移动机械臂。
.venv/bin/python tools/can_probe.py can0 can1
.venv/bin/python examples/nero_joint_control.py --channels can0 can1 --read
```

确认反馈正常、接线明确、运动空间允许后，**操作者主动执行**以下动作命令：

```bash
# 单臂先验证；--home 是本套工装的准备姿态，并非厂家零位。
.venv/bin/python examples/nero_joint_control.py --channels can0 --home --speed 10

# 自定七关节绝对目标，单位 rad：
.venv/bin/python examples/nero_joint_control.py --channels can0 \
  --joints 0 0.35 0 1.75 0 0 -0.6 --speed 10
```

默认运行示例只有读取；只有 `--home` / `--joints` 才会使能并发运动命令。
示例采用官方 SDK 的 **`move_j` 关节位置模式**。它不包含上位机持续 MIT/重力补偿循环。
退出不主动发送 `disable()`；退出也不是急停或经过验证的安全保持功能。

## 资料导航

| 文档 | 内容 |
|---|---|
| [重装与恢复](docs/01-reinstall.md) | 依赖、DKMS、Secure Boot、离线条件、已有安装、恢复和升级 |
| [硬件与接线](docs/02-hardware-and-can.md) | 两代现场卡、通道、速率、左右确认、验收判据 |
| [排障](docs/03-troubleshooting.md) | 无回复、ACK、假回显、接口 DOWN、错误计数、USB 热解绑陷阱 |
| [Nero 示例](docs/04-nero-example.md) | 无运动读取、单/双臂控制、参数、版本与退出行为 |
| [验证范围](docs/05-validation.md) | 现场证据与本仓库测试边界；避免把枚举成功当成机械臂已通 |
| [交付机软件清单](docs/06-delivery-software.md) | IK、XRoboToolkit、原录制流程、验收样例与维护归档 |
| [实时内核](docs/07-realtime-kernel.md) | PREEMPT_RT 的来源、构建、安装、DKMS、试启动与回退 |
| [第三方来源](vendor/README.md) | 固定版本、下载源、源码及 SHA-256 |

仓库不包含客户密码、SSH 私钥、原系统用户目录、数据集或机械臂固件升级程序。
本机接口配置不会刷写 CAN 卡或机械臂固件。PICO、相机与以太网管理页可独立配置；关节示例不需要它们。

## 离线恢复的边界

仓库包含驱动/SDK 源码以及 Linux x86_64、CPython 3.12 的 Python 轮子。
Ubuntu 的 `dkms`、编译器、**与正在运行内核完全匹配的 headers** 等 apt 包仍需预先准备。
详见 [离线准备](docs/01-reinstall.md#离线准备)。不要把旧系统编出的 `.ko` 直接拷到新内核使用。

## 验证仓库本身

```bash
sha256sum --check vendor/SHA256SUMS
.venv/bin/python -m unittest discover -s tests -v
```

测试不会访问实体 CAN 或驱动机械臂。
