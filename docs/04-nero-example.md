# Nero 关节控制示例

入口：[`examples/nero_joint_control.py`](../examples/nero_joint_control.py)。
它直接使用随仓库固定的官方 pyAgxArm，默认只读取。

## 读取，不使能

```bash
.venv/bin/python examples/nero_joint_control.py --channels can0 --read
.venv/bin/python examples/nero_joint_control.py --channels can0 can1 --read
```

实际流程：

1. 先被动等待关节/状态反馈；没有反馈时直接退出，不发送固件请求，避免未接通总线持续重发。
2. 对每个通道最多请求三次固件版本，不在探测过程中使能或切换运动模式。
3. 用 SDK 的 `resolve_firmware_profile` 选择协议；1.12 对应 v112。
4. 等待七关节角和机械臂状态，再打印结果。

这里的“只读”允许发送固件查询，但不会使能、发目标、回零或失能。
对旧版 ≤1.11，可能需按厂家说明先打开 CAN 推送；不应为了通过检测盲目使能。

## 显式关节移动

确认机械臂周围空间、支撑和接线后，由现场操作者执行：

```bash
# 单臂：
.venv/bin/python examples/nero_joint_control.py --channels can0 --home --speed 10

# 双臂同一个关节目标：
.venv/bin/python examples/nero_joint_control.py --channels can0 can1 --home --speed 10

# 任意七关节绝对角度（rad），不是相对增量：
.venv/bin/python examples/nero_joint_control.py --channels can0 \
  --joints 0 0.35 0 1.75 0 0 -0.6 --speed 10 --timeout 30
```

`--home` 的目标为：

```text
[0, 0.35, 0, 1.75, 0, 0, -0.6] rad
```

这是本次工装的准备姿态，**不是厂家机械零位，也不进行编码器标定/置零**。
客户装配、坐标系或工作空间不同，应先重新确认目标。

示例验证七个有限角度、SDK 关节限制、机械臂 NORMAL 状态，再使能并调用 `move_j`。
`--speed` 范围为 1～20，含义是控制器百分比，不是 rad/s。
到位判据是所有关节误差小于 0.03 rad，连续三次采样满足；超过时间或反馈停止更新会返回错误。

## 退出与保持

这个示例使用控制器的 `move_j` 关节位置模式；它没有额外的 90 Hz MIT/重力补偿线程。
完成、异常或 Ctrl+C 时关闭 SDK 通信，不自动调用 `disable()`，防止举起且无支撑的臂因失能下落。
异常、超时或 Ctrl+C 也不会自动取消控制器已经收到的目标。
不能把关闭通信当作急停，也不能据此承诺控制器看门狗/断线后一定保持。
需要连续上位机 PD 的应用，应另行验证控制回路和停止策略。

本仓库新示例的运动分支只做离线测试；现场已有系统验证过双臂 home，但使用的是原 LeRobot MIT+重力补偿路径。
因此新示例首次上机仍要按客户现场流程验收，不将两者的验证范围混在一起。

## 单控制源

示例使用同用户的 `/run/user/<uid>/nero-teleop-<uid>.lock`，与原现场启动器互斥。
它不能阻止不使用该锁的其他 CAN 程序、其他用户或设备。运行前仍要确认没有其他控制源。

示例不会碰夹爪、相机、PICO、机械臂网络地址或设备固件。
