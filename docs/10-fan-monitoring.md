# 风扇监控与调速：IT8786E

2026-10-23 在惠普克隆盘启动的同一台 box 上，检测到 **ITE IT8786E**，ISA 地址 `0xa40`。
正常加载内核自带 `it87` 后，出现两路风扇转速和三路 PWM 属性。
没有使用 `force_id`、ACPI 资源冲突绕过或 PWM 极性覆盖。

此前只有 coretemp、NVMe 等温度节点，是未加载监控驱动，不代表主板没有风扇传感器。
芯片与驱动支持见 [Linux it87 文档](https://docs.kernel.org/hwmon/it87.html)。

## 已部署的监控入口

当前惠普盘已安装 `lm-sensors`，并将 [`system/xyzbox-hwmon.conf`](../system/xyzbox-hwmon.conf)
安装到 `/etc/modules-load.d/xyzbox-hwmon.conf`，用于开机加载 `it87`。发货收尾时再次重启，已验证驱动自动加载及转速节点出现。

```bash
sudo modprobe it87
sensors it8786-isa-0a40
```

`hwmonN` 编号可能随开机变化，应按 `name=it8786` 定位，不能固定使用 `hwmon4`。
用户提供的信步 `SV3-12P26-1235U Series Motherboard User Guide (Ver0.0) E4R20260817` 第 22 页
（PDF 第 23 页）明确：33 号为 `CPU_FAN1`，34 号为 `SYS_FAN1`，均为 4×1、1.25 mm 插座。
二者针序均为 1 GND、2 供电、3 测速、4 调速；供电默认 12V，5V 是电阻选配而非软件开关。
用户确认使用这两个四针接口。
`fan1/fan2` 与 33/34 插座的软件编号对应尚未独立确认；驱动编号本身不能证明用途。
参见 [hwmon 接口说明](https://docs.kernel.org/hwmon/sysfs-interface.html)。

## 本次实测

| 操作 | fan1 读数 | fan2 读数 |
|---|---:|---:|
| 原始全速模式 | 约 4500 RPM | 约 4350 RPM |
| 仅 PWM1 设为 80%，12 秒 | 3792–3813 RPM | 保持原速度范围 |
| PWM1 恢复 | 约 4530 RPM | 保持原速度范围 |
| 仅 PWM2 设为 80%，12 秒 | 保持原速度范围 | 3924–4383 RPM，有跳动 |
| 仅 PWM2 设为 60%，12 秒 | 保持原速度范围 | 2376–4383 RPM，明显跳动 |

PWM1 的调速效果稳定。PWM2 有调速响应，但读数不稳定；已知为四针接口，仍未定位测速跳变原因，不能当作精确 RPM 控制接口。
测试期间 CPU 为 34–37°C；每轮均恢复原始设置：`pwm1_enable=pwm2_enable=0`，占空比寄存器恢复为 `0`。

对本芯片，`pwmN_enable=0` 是全速/不调速模式，不是风扇停转；`1` 是手动模式。
手动占空比取值为 0–255；`204` 对应 80%，`153` 对应 60%。
若以后调整，应先写目标占空比，再切到手动模式；恢复时先切回原来的全速模式。
当前自动模式温度点未配置，不能直接把 `pwmN_enable` 改为 `2` 当作可用的温控曲线。

原始采样与两轮可复现短测脚本保存在
[`artifacts/hp-rt-acceptance-20261023`](../artifacts/hp-rt-acceptance-20261023/)。
本次未部署持续降速或自动调速服务。

## 镜像范围

这些监控配置安装在当前 **HP EX900 Plus** 系统上，晚于 `yikai-box-noble-piper-rt-20261023-v1` 镜像制作。
v1 镜像已有内核 `it87` 模块，但没有这次新增的 `lm-sensors` 和自动加载配置；后续制作新母盘版本时再纳入。
