# USB CAN 排障

## 按层排查

| 现象 | 先查什么 | 下一步 |
|---|---|---|
| `lsusb` 没有设备 | M.2 插槽 USB 信号、转接板、供电、连接 | 先解决枚举，不安装一堆 Python 包 |
| 有 USB，但没有 can 接口 | `lsusb -t`、`dkms status`、内核日志 | 确认绑定 kcan，模块匹配当前内核 |
| 四路卡只出现两路 | 实物型号、USB ID、两个 USB interface 是否都被接管 | 参考旧卡案例；不能把软件 can0/can1 当成物理 CAN3/CAN4 |
| can 存在但 DOWN | `/etc/xyzbox-can.json`、udev USB ID 匹配、服务日志 | 启动对应 `xyzbox-can@canN.service` |
| 固件查询超时 | 真实 RX、ACK、接线端口、波特率、机械臂初始化 | 不要先绕过固件检测或强发使能 |
| TX 有计数、RX 为 0 | 发送回显与实际总线反馈 | 仅 TX 成功/本机回显不算机械臂在线 |
| 大量 ACK 错误 / TX error 128 | 对端是否在这条线、H/L、端接、供电和速率 | 停止探测，查物理链路，不继续刷命令 |
| SDK 有关节但控制异常 | 实际固件与 SDK profile | Nero 1.12 要能解析为 `v112` |

## 常用只读检查

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

`ERROR-ACTIVE` 是正常 CAN 状态名。关注错误计数是否增长、是否进入 ERROR-PASSIVE/BUS-OFF。
RX 统计中的错误事件也不是机械臂关节帧；本仓库探测工具会分开计数。

```bash
# 默认完全被动接收，不发应用帧：
.venv/bin/python tools/can_probe.py can0 can1

# 控制程序已退出、确认接线后，显式请求 Nero 固件：
.venv/bin/python tools/can_probe.py can0 can1 --query-firmware
```

固件请求为标准帧 `0x4AF`、数据 `01`；不发送使能、关节目标或失能。
本工具只有先看到真实 RX 才发送查询；没有反馈时不在总线上排队发包。
刚打开接口时首帧可能丢失，工具重试三次。
完整固件载荷保留用于辅助排查，不能无条件把它视为所有版本通用的唯一序列号。

## 已遇到的问题

### 1. 1.4.1 在 Linux 7.0 编译失败

典型报错是 `can_change_mtu undeclared`。该内核接口已发生变化。
现场先定位到这一点，随后改用官方 **1.4.2** 原版，它通过特性检测适配 Linux 7.0。
本仓库提供 1.4.2，不需要客户再手改这处代码。

### 2. DKMS 版本标签不对

官方 1.4.2 包中的静态 `driver/dkms.conf` 曾保留旧 `1.4.0` 标签，
而 Makefile 的 `DKMS_VER` 已是 1.4.2。安装脚本只在新解压的源码目录删除并重新生成这个文件。
检查结果应为 `<驱动包名>/1.4.2, <当前内核>, x86_64: installed`。

### 3. 手工 insmod 报 Unknown symbol

`insmod kcan.ko` 不会自动加载 `can-dev` 等依赖。
正式安装后使用 `modprobe kcan`；临时编译测试也应先准备依赖。
不要仅凭 `Unknown symbol` 就认定固件坏了或刷固件。

### 4. 接到了驱动没有暴露的端口

10 月 14 日的 PCAN 兼容四口卡只出现 can0/can1，而线接在实物 CAN3/CAN4。
最初表现为 Nero 固件查询超时。移到 CAN1/CAN2 后两臂立即持续反馈。
10 月 16 日换成 `395e:0020` 的 M.2 USB X4，四个通道均正常枚举；这次是旧初始化规则没匹配新 USB ID。

### 5. 不要热做 USB sysfs unbind/rebind

g1wh 的 KCAN X4-G2 台架记录过：对 USB 设备做强制解绑/重绑后，MCU 不再应答，
出现 `-110/-71` 超时，最终需要断开 USB 供电才能恢复。
本仓库安装脚本不使用这些操作，也不把 xHCI remove/rescan 当成常规恢复方法。
先使机械臂处于可断开控制的状态，再按硬件手册断电重插/冷启动。

### 6. 未接线通道的错误风暴

只给已接线、确认速率的通道发查询。错误重发会占用 USB 和 CPU。
停止探测后，在允许停止该通道控制的前提下把无用接口 down，再检查线束。
不要通过无限重试“等它自己恢复”。

## 现场事实与适用范围

本页案例来自本次工控机和 5090D 上 g1wh 的 CAN 台架资料。
其中 g1wh 使用达妙裸电机协议，Nero 使用整机协议；可复用驱动经验，不能直接复用运动报文或所有总线参数。
