# 内存稳定性与风扇监控 · topic handoff

本 topic 属于 XYZBox 交付链路，接手先读[共同入口](HANDOFF-DELIVERY-IMAGING.md)中的机器/磁盘身份、凭据入口、冻结决定和 Git 现场。本文件只交接下述范围，不启动新硬件动作或其他 topic。

- harness：codex；model：unknown；native session：`01a1678d-3bfb-75b0-964e-4b2dc0a3a6a9`。
- host：`Yuntians-MacBook-Pro.local`；日期：2026-10-28，Asia/Shanghai。
- 来源实现：`4bbf6b7cc733bf110d4d07bd705098f1fc21e72e`。无 native reviewer receipt；工程结果按原始文件/快照的版本与条件使用，不自我提升为共享知识已复核。

## Goal / closed / open

用户最终要求只测内存，不做硬盘压测；任务须独立运行于box，不依赖MBP或SSH在线。本台内存10小时验证已PASS，用户据此决定继续当前内存选型，该事项已闭合。

风扇已可读取并做过PWM响应探索，但未部署自动风扇曲线；两路保持全速。CPU/机箱风扇软件对应和fan2低占空比测速仍有未独立确认部分。

## Wake / first-action

普通接手只读取仓内归档结果和下方日志说明，不重跑内存、更不补硬盘压测。若用户询问当前机器状态，先核对HP `...00088`/hostname及同一run的结果文件，不把服务inactive误报为失败。

只有用户要求新内存配置验证，或需要风扇降噪时，才开启相应工作；风扇第一步是确认物理对应及fan2测速，不直接部署持续PWM策略。CAN装配和产测另见[Piper topic](HANDOFF-PIPER-FACTORY.md)。

## 7. 内存与风扇：已完成，不默认重跑

内存 run `20261026T134923Z`：5GiB、4线程、10小时，2026-10-27 07:49:25上海时间结束，elapsed36002秒，PASS/exit0、0 hardware incidents/0 errors；600条遥测，CPU封装采样峰值62°C、中位59°C；无重启。仅在线分配区域，不覆盖OS占用的全部8GB，也未做硬盘压测或RT延迟评测。

- 源码 `memory_test/run.py`、本机 `/opt/xyzbox-memory-test/run.py`；系统服务 `xyzbox-memory-test`，只手动单次启动，不开机重跑。
- 本机结果 `/var/lib/xyzbox-memory-test/latest/{summary.json,memory.log,telemetry.jsonl,kernel.log}`；完整已归档 `artifacts/memory-test-20261026/results/`，这才是本轮结果。
- MemorySwapMax=0，任务独立于MBP/SSH。日志按journal cursor截取，避免启动时校时引入旧事件。未来若结果文件缺失或boot/PID变更，报告中断，不补写PASS。
- 温度/转速读取通过it87 + lm-sensors；CPU_FAN1/SYS_FAN1物理接口33/34已确认。软件fan1/fan2对应未独立确认；PWM2低占空比测速有波动，两路已恢复全速，没有部署自动风扇曲线。细节 `docs/10-fan-monitoring.md`。

## 证据与完成条件

首读 `memory_test/README.md`、`artifacts/memory-test-20261026/results/summary.json`，原始memory.log、telemetry.jsonl、kernel.log与结果一同归档。最新只读快照 [`box-readonly.json`](../artifacts/handoff-20261028/box-readonly.json) 仍是同一run PASS、服务inactive，未重跑。

本次PASS只覆盖该台配置的在线分配区域，非全批次/全物理地址认证；没有硬盘压测或RT延迟评测。风扇详情见 `docs/10-fan-monitoring.md`。不因未实现曲线而自动唤醒此工作包。
