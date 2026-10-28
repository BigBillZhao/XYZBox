# Yikai 交付链路与系统镜像工作站 · Agent handoff

本交接只覆盖 **Piper 产测准备、客户系统/RT、系统镜像工作站、已完成的内存验证**。不接管本仓其他 topic（例如新出现的 `cad/`），也不是整个 personal workspace 的总交接。

- 日期：2026-10-28，Asia/Shanghai。
- harness：codex；model：unknown；native session：`01a1678d-3bfb-75b0-964e-4b2dc0a3a6a9`。
- operator host：`Yuntians-MacBook-Pro.local`；canonical repo：`/Users/zyt/codex_ws/XYZBox`；GitHub：`BigBillZhao/XYZBox`，分支 `main`。
- 实现来源 revision：`4bbf6b7cc733bf110d4d07bd705098f1fc21e72e`。包含本交接的后续提交仅补文档/现场证据，不表示重做了硬件试验。
- 事实类别：用户已确认的决定单独列出；工程结果由版本绑定文件和现场只读快照支撑。无独立 native reviewer receipt，不将作者记录自我提升为共享知识的“已复核”声明。
- 本轮只要求详细 handoff。下列历史命令/成功动作不是新一轮刷盘、重启或机械臂运动许可。

## Topic 入口：按当前任务选择

四份交接分别可交给不同 agent；每份先链接本文的共同机器身份/凭据/Git边界，再承接各自的 goal、closed/open、wake、first-action 和证据。未指定下一任务时只读接手，不自动派工。

| Topic | 独立交接 | 当前边界 |
|---|---|---|
| Piper 通讯与产测 | [HANDOFF-PIPER-FACTORY.md](HANDOFF-PIPER-FACTORY.md) | 通讯/双臂动作已验；自动产测WebUI与清理包待做 |
| RT 与客户系统 | [HANDOFF-RT-CUSTOMER.md](HANDOFF-RT-CUSTOMER.md) | RT/SDK基础交付闭合；区分两块HP验收 |
| 系统镜像工作站 | [HANDOFF-IMAGE-STATION.md](HANDOFF-IMAGE-STATION.md) | 首个配置闭环；后续项目需新增适配和实机验收 |
| 内存与风扇验证 | [HANDOFF-HARDWARE-VALIDATION.md](HANDOFF-HARDWARE-VALIDATION.md) | 内存PASS闭合；风扇全速，自动曲线未部署 |

## 1. Goal 与接手后的第一步

原目标是批量出货：制作可复制的客户系统，把 SSD 装进信步 box 后可使用 CAN/SDK；接两条已知正常的 Piper 工装，开机显示本机测试页，测试员点击后完成使能、抬升、回垫、禁能，人工通过后移除产测包。首版只做初步检测，优先尽快可用，不做精密标定或寿命测试。

另一个已明确的目标：**系统镜像工作站是跨项目公共工具，Yikai 只是第一个已验证配置。**

接手先做只读核对：

1. 确认 repo/branch/diff；读本文和下方与当前用户任务有关的专题。不要全仓扫描或接管别的 session 的改动。
2. 若继续“产测 MVP”，第一项具体工作是静态核对已成功动作脚本的依赖，设计独立产测包和最小状态机。当前 `.110.12` 没有 CAN 枚举，不能以它作为立即跑双臂动作的工装。历史动作验证已完成，不重新开始一轮盲目 CAN/SDK 研究。
3. 若继续“镜像平台”，先读 `imaging_station/README.md`、`CONTRACT.md`、`core.py` 的配置限制，核验 `/api/state`；不要因换品牌名就向未适配系统开放恢复。
4. 内存长测已经结束且 PASS。普通接手无需重跑。若用户没有指定下一项，只汇报可接手的工作包，不自行启动新测试、移动机械臂或覆盖磁盘。

## 2. 用户决定：closed-stays-closed

- 客户软件范围：Ubuntu + 已验收内核 + CAN 驱动/SDK + 最小文档/示例。完整遥操、PICO、相机软件不在本次交付范围。
- 当前工装固定：**左臂物理 CAN1 → can0；右臂物理 CAN2 → can1；CAN3/4 空置、DOWN**。这与旧 Nero 示例的左右映射相反。
- M.2 SSD 先在刷盘工作站还原系统，再装进 box。一个 USB-C 硬盘盒即可按“源盘→NAS→换目标盘→恢复”顺序工作。
- 产测使用标准 Piper（无 X/L 后缀）、剪刀式示教手柄；双臂底座约 70cm，同向朝工作区。工装 home 不是厂家零位或通用客户坐标。
- 当前内存选型继续采用；依据是本台配置的 10 小时在线验证，不是全批次/全物理地址认证。厂家、料号、频率以采购 BOM 为准，本轮没采集到就不要猜。
- 后加的稳定性测试明确收窄为 **只测内存，不测试硬盘**。没有后台磁盘压测待续跑。
- 不动 review-board 事发现场：不修/重启 board，不改 `docs/08-factory-mvp-prd.md` 正文或其 comments/replies sidecar，不读取其中未提交/私有笔记。PRD 正文可只读；其过时字段以下文后续实测为准。
- 用户偏好直接推进、复用已验证结果，避免重复问同一授权。后继仍须依据其当前任务范围和现场条件决定动作，不能继承旧会话的 blanket 运动许可。

## 3. 机器与磁盘：必须按本体身份区分

| 对象 | 身份与角色 | 验证范围 |
|---|---|---|
| MBP | 本仓、操作入口；不是刷盘执行主机 | 本机 `127.0.0.1:8830` 是 SSH 转发，掉线会失效 |
| 刷盘机 | `zenbot-alg@192.168.106.3`，ThinkBook 16 G8 AHP，Ubuntu 24.04，32GB RAM | NAS 镜像捕获/恢复执行于本机 systemd 服务 |
| 刷盘机内置盘 | UMIS 1TB，`SS1Q23148Z1CD6340C7N`，同时含 Windows/BitLocker、Ubuntu `/` 和 `/home` | **整盘禁止作为刷盘目标**，不能只保护 root 分区 |
| 梵想源 SSD | Fanxiang S500Pro 256GB，`26030958613001465` | 原样备份后离线补齐客户系统并制作 v2，后由用户取走；当前物理位置未知 |
| 10/23 已验收 HP | EX900 Plus 256GB，`HASI26340100227`，hostname `yikai-21c5e86e` | 同机换盘冷启动、RT、真实双臂动作、客户 SDK 回传均通过；当时已关机交用户打包，实际发货状态未追踪 |
| 10/26 新 HP | EX900 Plus 256GB，`HASI26340100088`，hostname `yikai-f98ac0a5`，当前会话地址 `.110.12` | v2 恢复、冷启动、RT、SDK 环境、内存长测通过；不能套用另一块 HP 的运动验收 |
| ASMedia 硬盘盒 | ASM246X，USB bridge serial `AAAABBBB0010` | 换盘后此序列号不变，必须用 SMART passthrough 读取 SSD 本体序列号 |
| 5090D | SSH alias `5090d` | RT 构建包与旧 v1 镜像归档；不是当前 WebUI 执行主机 |

当前这些 256GB SSD 的实际容量为 **256060514304 bytes**，512-byte logical sector。标称同为 256GB 不表示每种型号都能容纳此布局。

### 2026-10-28 15:00–15:02 只读现场刷新

- `.106.3` 可达，`xyzbox-imager` active，NAS online，busy=false；仅内置系统盘可见，不能选择，未发现外接目标盘。两版镜像及四条历史任务记录可见。
- `/opt/xyzbox-imager/VERSION` 为 `4bbf6b7...`；core/server/finalizer/app.js/index.html 的 SHA256 与该本地实现一致。
- `.110.12` 仍为 `yikai-f98ac0a5`、HP `HASI26340100088`，RT `7.0.14-xyzbox-rt`、realtime=1；USB 仅 root hub，CAN 接口列表为空。用户在 10/26 已确认尚未装 CAN 卡；今天没有新的实体装配检查，不把“无枚举”当驱动回归。
- 内存结果文件仍是同一轮 PASS，测试服务 inactive，退出码 0；本轮没有重跑。
- 快照：[`artifacts/handoff-20261028/box-readonly.json`](../artifacts/handoff-20261028/box-readonly.json)、[`station-readonly.json`](../artifacts/handoff-20261028/station-readonly.json)。这些是带日期快照，接手时仍要刷新易变状态。

## 8. 后续工作包、wake 与完成条件

| 工作包 | wake / 第一项工作 | 完成条件 |
|---|---|---|
| **A 产测MVP，建议优先** | 用户继续原量产目标；先静态整理上述动作依赖与 `factory_test/` 独立边界，再做状态机/页面；装卡后才做只读接口与反馈核对 | 本机弹窗→点击开始→双臂初检/动作→回垫/禁能→人工判定→结构化留档→可重试地移除产测包；失败/重启不自动续跑；现场验收 |
| **B 多项目镜像平台** | 出现第二个实际项目/系统配置；确认其分区、启动、身份与软件需求，再写相应适配 | 项目归属、适配、镜像校验/恢复及真实冷启动分别验证；不得把Yikai/Ubuntu适配泛化成所有OS |
| C 当前新box通讯验收 | 用户装好CAN卡与测试工装；先确认USB枚举和两路参数/新鲜反馈 | 最新 `...00088` 有自己的通讯/动作记录，不挪用旧 `...00227` 记录 |
| D 风扇曲线 | 用户需要降噪时再开；先确认物理对应与fan2测速 | 验证后再部署持续策略；当前全速决定保持 |

产测 A 的最低记录：机器/磁盘身份、镜像/软件版本、两路通道、步骤结果、时间、人工判定和失败原始信息。首版不先建大数据库。
运行包（内核/驱动/SDK/客户文档）与产测包（网页/流程/工装轨迹/弹窗）隔离。**人工通过后的自删只删产测包**，先保存结果；不删除客户 SDK、驱动、镜像平台或本轮验收凭据。清理失败表示“测试通过，待清理”，可重试；返工保留历史。
待拍的新输入仅在对应工作包需要时问：批量并发/第二项目配置/现场工装。当前不为这些问题阻塞文档交接，也不自动派发上述开发任务。

## 9. 访问与凭据边界

- `.106.3` 已加入 MBP 现有公钥，SSH key 登录可用；未关闭其密码认证。sudo 使用用户此前给的刷盘机账户凭据，**值不在仓库/本文中**。原用户指令在本交接署名线程的 turn_index=26、native turn `01a17823-d36d-7591-877d-19e633018031`（2026-10-26，开头“这些内容请先document”）；需要时用现有历史读取器定点由程序消费，不输出或另存值。
- `.110.12` 客户 v2 清掉了调试 `~/.ssh`，密钥拒绝是预期；可用原安装凭据。确切真源是 Codex 安装线程 `01a16823-f27a-7c93-89df-8489c618368b`（“修复GUI并重装系统”）的原用户指令/preview。可通过现有 `codex_tui.read_thread` 定点由程序消费，禁止把密码/哈希打印进模型或复制到交接、代码、临时口令文件。**不是 fleet 通用 sudo askpass 凭据**，该凭据曾单次尝试不匹配，别再猜。
- SSH host keys 在每次恢复后重新生成；相同IP可能是不同盘/机器。先核对当前SSD/hostname/provisioning，不能只看IP继承控制权。旧 `/private/tmp/xyzbox-hp-00088-known-hosts` 是本机曾用于核对的临时记录，可能不存在，不当作跨机资源。
- NAS本机服务凭据现成位于root-only路径，由 mount.cifs 消费；不要复制整份 `secrets.md`。首次设备准备时用户指定过 `NAS_AlgoLaptop_PASSWD`，若必须重新配置，仅沿现有凭据消费边界处理，值不进入模型文本。
- 状态、代码和日志可只读核验；本文不要求继任者自动给新主机加公钥、放宽sudo/网络边界或修改电源策略。

## 10. 可复现检查、Git现场与资料读取顺序

本地代码检查（不访问实体盘/机械臂）：

```bash
cd /Users/zyt/codex_ws/XYZBox
git status --short
python3 -m unittest imaging_station.test_core imaging_station.test_server
python3 -m py_compile memory_test/run.py
node --check imaging_station/static/app.js
```

33项镜像站测试最后在实现revision通过；本文仅文档修改，不为交接重复跑全部硬件测试。普通回环HTTP测试在MBP沙箱可能需正常网络权限，不要将 sandbox bind denied 当产品失败。

只读远端起点：`.106.3` 的 `systemctl is-active xyzbox-imager` / GET API；`.110.12` 的 hostname、uname、lsblk、ip/lsusb、`cat /var/lib/xyzbox/provisioning.json` 和 `memory_test/run.py status`。当前仅handoff，不触发任何 POST、SDK模式切换、运动、刷盘、重启或重跑压力测试。

资料顺序：本文 → 对应 topic handoff → 当前工作包 README/源码 → 原始证据。`docs/08`、`docs/09`、早期checkpoint包含历史“待确认/未实现”，以10/26、10/27追加结果为准；别编辑冻结PRD来消除年代差异。

仓库跟踪文件在本轮开始无未提交改动，但已有大量未跟踪原始CAN/照片/研究目录与新 `cad/`；这些未被本交接接管。**不得 git add -A、清理这些目录或修改board sidecar**。关键成功脚本/姿态/精简验收已入Git，其他大原始抓包有的仅在本机/旧现场；`git ls-files -- PATH` 判定，不把本地存在等同别人clone后可得。

若需生产部署，先确认任务busy=false，版本与代码差异可解释，再按当前用户任务操作。重写本交接的稳定结论应回所属README/checkpoint/代码文档，消费完成后修复入口并在Git中删除临时交接；原文历史由Git保留。

## 11. 独立读者试读记录

已实际完成3轮原生独立读者试读（`fork_turns=none`，禁工具/写入/委派，无模型覆盖）。第1轮为入口摘要，第2轮为拆分前原文入口，第3轮为拆分后原文入口；三轮均返回 `NO-BLOCKING-QUESTIONS`，主会话核对没有误读，最后连续两轮满足停止条件。

实际范围、文档哈希、读者来源和剩余限制见[试读记录](../artifacts/handoff-20261028/reader-interviews.md)及[拆分版文档哈希](../artifacts/handoff-20261028/interview-document-versions.json)。最终文件比被读版本仅追加本记录与链接；topic正文未改变。试读只验证可接手性，不是硬件复测或独立知识可信度晋升。
