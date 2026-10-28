# Piper 通讯、姿态与产测 MVP · topic handoff

本 topic 属于 XYZBox 交付链路，接手先读[共同入口](HANDOFF-DELIVERY-IMAGING.md)中的机器/磁盘身份、凭据入口、冻结决定和 Git 现场。本文件只交接下述范围，不启动新硬件动作或其他 topic。

- harness：codex；model：unknown；native session：`01a1678d-3bfb-75b0-964e-4b2dc0a3a6a9`。
- host：`Yuntians-MacBook-Pro.local`；日期：2026-10-28，Asia/Shanghai。
- 来源实现：`4bbf6b7cc733bf110d4d07bd705098f1fc21e72e`。无 native reviewer receipt；工程结果按原始文件/快照的版本与条件使用，不自我提升为共享知识已复核。

## Goal / closed / open

原目标是 box 连两条已知正常 Piper 工装，开机本机弹窗测试；点击后使能、抬升、回垫、禁能，人工通过后移除产测包。首版优先可用，只做基础检测。

已闭合的是 CAN 调通、home/目标姿态和多轮双臂动作，**尚未完成的是自动产测 WebUI、状态机与通过后清理包**。当前新 HP `...00088` 的 box 没有 CAN 枚举，旧 HP `...00227` 的运动收据不能代替它。

## Wake / first-action

用户继续原量产目标时，先只读确认 repo/branch/diff，静态核对下文动作脚本的完整依赖，设计 `factory_test/` 独立边界与最小状态机；无需先重做 CAN 研究或立即移动机械臂。实际通讯核验需用户装卡/接工装后，刷新本体身份、接口和真实反馈。

## 4. 通讯、姿态、动作：已完成与可复用入口

固定硬件：KCAN-USB X4，USB `395e:0020`，M.2 使用 USB 通路，驱动 kcan 1.4.2；两路 Classic CAN 1Mbps、sample point 0.75。只认真实接收/ACK，不能把本机 TX echo 算成机械臂反馈。

关键调试结论：

- 两根 CAN 线最终都交换 H/L 后正常；CAN3↔CAN4 外部对测也通过，卡与接口的诊断已有证据。
- 标准 Piper 固件 `H-V1.2-1 / S-V1.7-3`，SDK PIPER/DEFAULT。示教主臂静止时可能不持续发送；主臂输出 `0x155/156/157` 不等同普通实际状态反馈。转 follower 后按标准反馈 `0x2A5/2A6/2A7`、状态/驱动帧读状态。腕部示教按钮可能切走 CAN 控制。
- 成功控制在每个 100Hz 周期持续设置控制模式并发送六轴 MIT/PD 帧；模式速度字段恢复 SDK 默认 50。这两项一起改后成功，未单独隔离根因。
- 纯 PD 参数 Kp=20、Kd=1，v_des=0、输入 t_ff=0；20秒抬升、8秒停留、20秒回程，回支撑附近后确认禁能。命令输入零力矩不等于协议量化后的物理力矩严格为零。
- 用户先看过 Frame 可视化并认可，随后要求抬得更明显；最终目标相对原 home 法兰约上移 80mm。双臂实际完成多轮，用户确认并要求再跑供其录视频；本任务不声称保存了用户视频。

### 冻结的 home（degree）

```text
left  [ 1.216, -2.938, 1.732,  5.621, 14.296, -23.730]
right [-2.786, -2.310, 1.776, -1.117,  7.395,   3.187]
```

保持原始 home 不变；每轮实际起点需新鲜反馈。禁能后在垫上松弛会改变角度，不据禁能后的最后一帧反推回程是否失败。该测试不是精密定位验收，也不把此工装姿态用于客户场地。

### 已入 Git 的主要材料

- [`docs/checkpoints/2026-10-23-piper.md`](checkpoints/2026-10-23-piper.md)：协议、姿态、模式修正与动作证据，细节首读。
- `artifacts/piper-commissioning-20261023/bimanual-lift-8cm/`：`home-poses.json`、`targets.json`、`make_targets.py`、`sdk_constants.py`、`run_bimanual_8cm.py`。
- `artifacts/piper-commissioning-20261023/can-diagnostics/driver-review/bimanual_lift_arm.py`：已成功的六轴执行器源码；不是生产服务。
- `artifacts/piper-commissioning-20261023/can-diagnostics/live-checks/angle-limits-{left,right}-01/summary.json`：原工装读回的限位证据。
- `checkpoint-evidence/`：两轮压缩事件、最终禁能快照、源哈希；`artifacts/hp-rt-acceptance-20261023/`：HP + RT 下实际动作复验。

**运行依赖陷阱**：历史 wrapper 硬编码 `/home/ubuntu/xyzbox-commissioning-20261023`，依赖 `left/right-lift-8cm.json`、两侧限位报告、下层脚本及 SDK archive。运行用的左右 trajectory JSON 没有独立以该文件名入 Git；不能把 wrapper 单独复制后直接运行。可从已提交的 `targets.json`/home/限位资料构造任务输入，依下层脚本要求包含 `version=3`、`arm`、`home_rad`、`start_rad`、`target_rad`，其中 start 来自当前新鲜反馈，路径与哈希需在打包时核对。

客户 v2 母盘已清掉 commissioning 调试目录；最新 `.110.12` 不保证有旧绝对入口。以后做产测应单独封装这些依赖，不把整套研究目录重新堆回客户系统。异常停止/支撑释放逻辑也须保留并实机验收；退出进程或 SDK disconnect 不等于禁能。

## 完成条件与交接陷阱

本机弹窗→点击开始→双臂初检/动作→回垫/禁能→人工判定→结构化留档→可重试地移除产测包；失败可返工。

最低记录为机器/磁盘身份、镜像/软件版本、两路通道、步骤结果、时间、人工判定、失败原始信息；首版不先建大数据库。
运行包与产测包隔离，先保存结果，再只移除产测包；保留客户 SDK、驱动、内核和验收凭据。清理失败表示“测试通过，待清理”，可重试；返工保留历史。

左 CAN1/can0、右 CAN2/can1，其他两路 DOWN；与旧 Nero 左右相反。两臂底座约70cm，同向朝工作区。review-board 与冻结 PRD/sidecar 不动，引用历史时保留年代。禁能和异常释放行为必须在生产包中明确，不能用退出进程代替禁能。
