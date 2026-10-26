# .110.12 内存过夜校验

用户于 2026-10-26 明确收窄为：**只测内存，不测试硬盘**。CAN 卡尚未安装是已确认的装配状态。
这不是刷盘工作站的定时任务；测试运行在已冷启动的 box `ubuntu@192.168.110.12` / `yikai-f98ac0a5` 本机。

程序：发行版 `stressapptest 1.0.11`，`-M 5120 -m 4 -W -s 36000 --stop_on_errors`。
测试约 5GiB RAM，4 个内存复制线程，10 小时；保留约 2GiB 给操作系统。
仅内存负载与校验，没有 `-f/-d/--findfiles`，不运行 fio、SMART 长测或盘面写入测试。硬盘仅保存少量日志。
在线测试不能覆盖操作系统正在占用的全部物理 RAM，不替代离线全内存测试。

## 本机运行与记录

- 程序：`/opt/xyzbox-memory-test/run.py`
- systemd：`xyzbox-memory-test.service`（系统级；SSH/MBP 离线后仍继续；任务期间阻止休眠）
- 当前记录：`/var/lib/xyzbox-memory-test/latest/`
- `memory.log`：测试器的详细校验与 PASS/FAIL。
- `stdout.log`：程序原始输出；`telemetry.jsonl`：每分钟温度、RAM、swap 和负载。
- `state.json`：运行状态；`summary.json`：结束后的结果、退出码、峰值温度和内核异常。
- `kernel.log`：测试时间内的内核记录，辅助判断 MCE、OOM 等。

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
