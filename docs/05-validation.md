# 验证记录与边界

[English](en/05-validation.md) | 简体中文 · [首页](../README.zh-CN.md)

## 2026-10-16 RT 切换前的现场链路

环境：Ubuntu 24.04.4 LTS / x86_64，内核 `7.0.0-38-generic`，kcan `Release_1.4.2_20260721_n`，
Python 3.12，pyAgxArm 固定归档 `1ae40ad`，python-can 4.6.1。

| 检查 | 结果 |
|---|---|
| 新卡 USB 枚举 | `395e:0020 KCAN-USB X4`，USB driver=kcan |
| 通道 | can0～can3；本次 can0/can1 接臂，can2/can3 未接并保持 DOWN |
| 实际速率 | 经典 CAN 1 Mbps，采样点 0.75 |
| 固件 | 两臂均 1.12，匹配 v112；反馈载荷与之前同一对机械臂一致 |
| 被动接收 | 两路两秒各约 4,200 个真实数据帧 |
| CAN 错误 | 两个接线通道 TX/RX error counter 均为 0 |
| 原程序 home 后 | 两臂 NORMAL / CAN_CTRL，14 个关节均显示使能 |
| 稳定后最大关节偏差 | 左 0.2285°，右 0.1700° |
| PICO / 相机 | 本次关节 home 未使用 |

原有 home 程序使用 LeRobot 的关节插值与 MIT+重力补偿，保持到位后持续 PD。
它是这次硬件/驱动/SDK链路的现场证据，不等同于本仓库新 `move_j` 示例的实物运动验收。

## 本仓库交付检查

以下结果由仓库对应提交的交付过程记录：

- 驱动、SDK、离线轮子：SHA-256 完整性核对。
- kcan 源码包：在对应内核 headers 下重新编译，不安装、不重载运行驱动。
- Python：新建独立 venv，使用仓库离线包安装，检查依赖和 v112 profile。
- 示例：参数、无运动读取分支和运动分支调用顺序的离线测试。
- CAN 启用 helper：未选通道不操作、不同配置的 UP 接口拒绝重配、正常配置的行为测试。
- 真实硬件验证限于明确记录的只读测试；没有为编写仓库资料而额外移动机械臂。

原始 USB CAN 资料包结果见 [`validation/RESULTS.json`](../validation/RESULTS.json)，对应提交 `1ed8aef`。
若某项写着未执行，不应视为通过。

## 交付整理与 RT 切换后的复验

`7.0.14-xyzbox-rt` 已实际启动，PREEMPT_RT 生效，已设置为默认，原 generic 内核保留。
USB CAN 驱动匹配新内核并已加载；四路接口、两路经典 CAN 1 Mbps、原网络配置、显示服务与 HDMI 输出检查通过。
11 个模块导入、628 个 Python 文件、42 处模型资源、FK/重力补偿和 13 项离线测试通过。
原录制程序源码哈希不变，完整三相机验收样例压缩包哈希不变。
本轮没有连接机械臂执行运动，未测试 PICO/相机硬件。2026-10-16 用户已现场确认实时内核重启后的显示、登录和鼠标键盘操作正常。
详细结果见 [`validation/DELIVERY-20261016.json`](../validation/DELIVERY-20261016.json)；
调度观测及恢复步骤见 [实时内核说明](07-realtime-kernel.md)。

## 客户恢复后仍须验证

重装产生的内核、USB 拓扑、卡型号、线束和对端固件可能不同。
请重新完成 README 的分层检查；不要只根据 Git 里的历史“通过”结论跳过实机确认。
