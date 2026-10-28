# 实时内核与客户系统交付 · topic handoff

本 topic 属于 XYZBox 交付链路，接手先读[共同入口](HANDOFF-DELIVERY-IMAGING.md)中的机器/磁盘身份、凭据入口、冻结决定和 Git 现场。本文件只交接下述范围，不启动新硬件动作或其他 topic。

- harness：codex；model：unknown；native session：`01a1678d-3bfb-75b0-964e-4b2dc0a3a6a9`。
- host：`Yuntians-MacBook-Pro.local`；日期：2026-10-28，Asia/Shanghai。
- 来源实现：`4bbf6b7cc733bf110d4d07bd705098f1fc21e72e`。无 native reviewer receipt；工程结果按原始文件/快照的版本与条件使用，不自我提升为共享知识已复核。

## Goal / closed / open

交付可在信步 box 冷启动使用的 Ubuntu + RT + CAN 驱动/SDK + 最小文档/示例；完整遥操、PICO、相机不在本次客户软件范围。

该基础交付已完成。旧 HP `...00227` 有 RT 下真实双臂复验；新 HP `...00088` 有客户 v2 冷启动、RT 和 SDK 环境检查，目前未装 CAN，不能借用旧盘运动收据。本 topic 没有等待自动执行的内核安装、重启或升级。

## Wake / first-action

若用户需要客户交付支持，先只读核对实际 SSD/hostname、当前内核与 provisioning，再读下列客户说明/安装入口；确认是旧盘还是新盘，避免使用旧验收措辞。只有用户要求新内核/硬件适配时才开启新的构建、DKMS 和回退验收。镜像制作/身份初始化由[镜像工作站 topic](HANDOFF-IMAGE-STATION.md)负责。

## 5. RT 与客户交付包：已闭合

- Ubuntu 24.04.4 / Python 3.12；RT `7.0.14-xyzbox-rt`，package `7.0.14-xyzbox2`；保留 `7.0.0-38-generic` 回退。
- 实际启用 CONFIG_PREEMPT_RT，realtime=1，CAN DKMS 1.4.2 为当前内核重编译并验证。不是只加 preempt=full 或 lowlatency。
- 10/23 先做 RT 通讯/禁能检查，随后 HP `...00227` 冷启动后的真实双臂动作也通过。早期“RT 尚未运动”段落是中间状态，以后续追加验收和 shipping checkpoint 为准。
- 30秒空闲 cyclictest：generic max39µs、RT max52µs；这没有证明时延变小，也不是最坏延迟保证。未做长时间受控 RT 调度认证。
- 构建、安装/回退：[`docs/07-realtime-kernel.md`](07-realtime-kernel.md)、`scripts/build_rt_kernel.sh`、`artifacts/rt-kernel-20261023/`；实际 deb 等大文件归档在 `5090d:/data/xyzbox-rt-20261023`，此位置未在本轮重新 SSH 校验。自编内核的更新维护由交付方负责，不是 Ubuntu Pro 官方 RT 包；私有签名密钥不复制。

客户入口为 `~/yikai-box`：固定 pyAgxArm 源码 **1ae40ad**（包版本显示1.0.0）、独立 `.venv`、离线 wheels、API 文档、只读例子。
SDK archive 在 `vendor/pyAgxArm-1ae40ad.tar.gz`，SHA256 `ea8a38af9e6e44255a53c351c4cf788592a21abe694e0f2ce683f2b9be177711`；源码/依赖校验见 `vendor/SHA256SUMS`。不要下载 latest 替代，也不要因文件名 `requirements-nero.txt` 就套用旧 Nero 型号/映射。

- SDK 离线重建：`scripts/setup_piper_env.sh`；只读例子：`examples/piper_read_status.py`；客户模板：`customer/PIPER-IMAGE-QUICKSTART.zh-CN.md`。
- 构造母盘时 venv 必须在目标 chroot 内以 `/home/ubuntu/yikai-box/.venv` 建立，不能在宿主 `/media/...` 下建完搬过去，否则 shebang 会错。
- `customer/PIPER-QUICKSTART.zh-CN.md` 和 10/23 shipping checkpoint 是特定旧 HP 的已验收记录，含旧主机名/验收措辞；新镜像用 IMAGE-QUICKSTART 模板，不能复制旧验收当新收据。

## 证据与限制入口

首读 `docs/checkpoints/2026-10-23-shipping.md`、`artifacts/hp-rt-acceptance-20261023/`；最新新盘只读快照为 [`box-readonly.json`](../artifacts/handoff-20261028/box-readonly.json)。构建归档的5090D路径本轮未重新核验，不把存在于历史文字中当作当前可下载保证。

30秒空闲 cyclictest 只支持记录的样本，未证明RT降低延迟或确定最坏界限；不要对客户作额外性能承诺。签名私钥、NAS凭据和调试SSH公钥不应打入客户镜像。
