# 交付机的软件与目录

整理日期：2026-10-16。客户机上的总入口为 `~/nero-delivery/README.md`，桌面为 `XYZBox-使用说明.md`。

## 已有功能

| 内容 | 实际位置 | 说明 |
|---|---|---|
| IK、手柄位姿映射与状态机 | `~/nero-workspace/repos/lerobot/src/lerobot/teleoperators/pico_nero_teleop/` | `placo_kinematics.py`、`pose_mapper.py`、`teleop_state_machine.py`、平滑与 XR 接口 |
| 双臂遥操 | 同仓库 `teleoperators/bi_pico_nero_teleop/` | 左右手、左右臂配置与共享 XR 客户端 |
| 机械臂执行与补偿 | 同仓库 `robots/nero_follower/`、`robots/bi_nero_follower/` | CAN SDK 适配、共享目标、执行循环、Pinocchio 重力补偿 |
| 原录制流程 | 同仓库 `scripts/lerobot_raw_record.py` | 原生键盘操作、状态/动作与多相机采集 |
| 模型资源 | 同仓库 `assets/nero/` | URDF、网格、夹爪和末端坐标 |
| 当前 SDK | `~/nero-workspace/vendor/pyAgxArm-1ae40ad/` | 支持 Nero 1.12 / v112 的固定源码 |
| XRoboToolkit 已安装程序 | `/opt/apps/roboticsservice` | PC Service、桌面界面；已装包版本 1.0.0.0 |
| XR Python 绑定和参考源码 | `~/nero-workspace/XRoboToolkit-Teleop-Sample-Python/dependencies/` | 绑定源码、头文件及相关运行库；当前 Python 模块版本 1.0.2 |
| Python 运行环境 | `~/nero-control/.venv-teleop` | Placo 0.9.16、Pinocchio 3.4.0、CPU PyTorch 2.10.0 等 |
| 相机支持 | LeRobot 相机模块与当前 Python 环境 | 三相机配置和设备规则；保留相关 ROS 源码供参考 |

项目定制的是位姿映射、IK 接入、状态机、驱动适配与录制链路等代码；
Placo、Pinocchio、XRoboToolkit 等计算库/工具保留第三方身份和许可原文。
本机并没有部署完整 ROS 运行环境，保留 ROS 源码不代表 ROS 链路已经验收。

## 客户入口

- 桌面「关节回位（会运动）」：不需要相机和头显，回到准备姿态后持续 PD。
- XRoboToolkit：连接 PICO。
- 桌面「双臂遥操与录制」：原录制流程，需头显和显式配置的三台相机。
- 桌面「交付资料」：软件清单、验收样例、数据包与维护归档入口。

不设置开机自动运动。home 与录制程序互斥；退出控制进程会结束其 PD 指令循环。

## 整理原则与实际处理

- 保留 `~/nero-workspace` 及原运行依赖路径，避免改坏已有模型和动态库引用。
- `nero-workspace` 的真实位置仍是 `~/nero-control/migration-20261014/import/workspace`，不能删除。
- 退役会话实验、旧测试、临时构建/测试环境、迁移快照和旧说明移入 `~/nero-control/maintenance-archive/20261016/`。
- 部分历史路径保留兼容符号链接，便于读取原诊断记录；它们不是新增后台服务。
- 保留 846 帧、三路各 846 张图像、约 28.8 秒的完整验收样例。样例压缩包哈希仍为
  `4afe0c5b8febbf405f67b60b02d5eee62bf3a2b6e34d63e654ec99fbdd8c6c37`。
- 初期仅状态/动作、无图像的片段归档，不与完整样例混在一起。
- 新录制默认使用 `~/nero-data/raw/nero_capture_YYYYMMDD`，不继续追加到验收样例。
- 既有 SSH 公钥按交付方明确选择保留，用于售后维护；不在仓库保存密码或私钥。

## 交付清单与复验

`~/nero-delivery/manifests/` 保存软件实际路径/版本、Python 包列表、离线验证和样例校验。
整理后已复验 11 个关键模块、628 个 Python 文件、42 处模型资源、FK 与重力补偿，未连接硬件。

完整遥操环境与本仓库的最小 USB CAN 示例是两个安装范围。
本仓库能恢复 USB CAN 和独立关节示例；完整遥操还需要本机工作区、模型、XR 桌面程序/绑定及相机依赖。
不要只复制 venv 到不同 Python/架构的系统，就认为完整遥操环境已恢复。
