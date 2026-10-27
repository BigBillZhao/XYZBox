# .110.12 内存过夜校验

用户于 2026-10-26 明确收窄为：**只测内存，不测试硬盘**。CAN 卡尚未安装是已确认的装配状态。
这不是刷盘工作站的定时任务；测试运行在已冷启动的 box `ubuntu@192.168.110.12` / `yikai-f98ac0a5` 本机。

程序：发行版 `stressapptest 1.0.11`，`-M 5120 -m 4 -W -s 36000 --stop_on_errors`。
测试约 5GiB RAM，4 个内存复制线程，10 小时；保留约 2GiB 给操作系统。
仅内存负载与校验，没有 `-f/-d/--findfiles`，不运行 fio、SMART 长测或盘面写入测试。硬盘仅保存少量日志。
在线测试不能覆盖操作系统正在占用的全部物理 RAM，不替代离线全内存测试。

## 本次运行

- run ID：`20261026T134923Z`
- 开始：2026-10-26 **21:49:23**，Asia/Shanghai。
- 预计结束：2026-10-27 **07:49:23**，Asia/Shanghai。
- 配置：5120MiB，4 线程，36000 秒；cgroup `MemorySwapMax=0`，防止把被测页换出到硬盘。
- 256MiB / 20 秒短测已通过，0 hardware incidents、0 errors；这是启动前验证，不是整夜测试结果。
- 正式任务由 systemd 管理，启动时确认 active/running，现已正常结束。没有配置测试结束后自动关机。
- 无显示器时原机的 `plymouth-quit-wait` 使 multi-user.target 未完成，测试服务因此仅依赖 journald，避免等待图形启动；未修改显示/启动目标配置。

## 2026-10-27 已核验结果

**PASS**。实际运行 36002 秒（10 小时 2 秒），2026-10-27 **07:49:25** 北京时间正常结束，退出码 0。
`stressapptest` 报告 **0 hardware incidents、0 errors**；没有记录到 MCE、OOM 等筛选的内核异常。
2026-10-27 10:32 SSH 复核时 boot ID 仍与开始一致，服务已正常退出，没有重启后重跑。

- 600 条每分钟遥测，最大采样间隔 61 秒。
- CPU 封装温度：采样峰值 **62°C**，中位数 **59°C**。
- 系统可用内存最低约 **1.69GiB**。
- File Copy、Disk 工作量均为 0；本轮没有硬盘压力测试。
- 内核原文含 perf 自动降低采样频率及 AppArmor 状态日志，保留供复核；未进行实时调度延迟评测。

证据已取回 [`artifacts/memory-test-20261026/results`](../artifacts/memory-test-20261026/results/summary.json)，包括完整结果、内存校验日志、温度遥测和内核日志。
结论限定于本次在线分配的 5GiB RAM 与此负载，不等于离线检测了全部物理内存。

## 本机运行与记录

- 程序：`/opt/xyzbox-memory-test/run.py`
- systemd：`xyzbox-memory-test.service`（系统级；SSH/MBP 离线后仍继续；任务期间阻止休眠）
- 当前记录：`/var/lib/xyzbox-memory-test/latest/`
- `memory.log`：测试器的详细校验与 PASS/FAIL。
- `stdout.log`：程序原始输出；`telemetry.jsonl`：每分钟温度、RAM、swap 和负载。
- `state.json`：运行状态；`summary.json`：结束后的结果、退出码、峰值温度和内核异常。
- `kernel.log`：测试时间内的内核记录，辅助判断 MCE、OOM 等。

内核日志按启动时记录的 journal cursor 截取，避免机器启动初期校时造成历史日志混入。

断开 SSH 不影响任务。若 box 重启、断电或进程异常结束，不能记为通过；状态查询会区分中断。
该服务不设开机自动重跑，避免重启后把失败的一晚覆盖成新的测试。

2026-10-27 查看结果：

```bash
python3 /opt/xyzbox-memory-test/run.py status
cat /var/lib/xyzbox-memory-test/latest/summary.json
tail -n 25 /var/lib/xyzbox-memory-test/latest/memory.log
systemctl status xyzbox-memory-test --no-pager
```

如需提前停止：`sudo systemctl stop xyzbox-memory-test`，会记录为中断，不冒充 PASS。
开始时间与预计结束时间以 `state.json` 为准，ISO 时间是 UTC；加 8 小时即北京时间。

原项目 checkpoint：[2026-10-26-imaging.md](../docs/checkpoints/2026-10-26-imaging.md)。
上游工具说明：[stressapptest](https://github.com/stressapptest/stressapptest)。
