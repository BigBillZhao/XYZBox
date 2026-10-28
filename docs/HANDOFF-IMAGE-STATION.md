# 跨项目系统镜像工作站 · topic handoff

本 topic 属于 XYZBox 交付链路，接手先读[共同入口](HANDOFF-DELIVERY-IMAGING.md)中的机器/磁盘身份、凭据入口、冻结决定和 Git 现场。本文件只交接下述范围，不启动新硬件动作或其他 topic。

- harness：codex；model：unknown；native session：`01a1678d-3bfb-75b0-964e-4b2dc0a3a6a9`。
- host：`Yuntians-MacBook-Pro.local`；日期：2026-10-28，Asia/Shanghai。
- 来源实现：`4bbf6b7cc733bf110d4d07bd705098f1fc21e72e`。无 native reviewer receipt；工程结果按原始文件/快照的版本与条件使用，不自我提升为共享知识已复核。

## Goal / closed / open

系统镜像工作站是多个项目共用的系统制作/分发工具，Yikai 是首个已验证配置。现有代码暂寄 XYZBox，不因为更名先拆空仓。

单硬盘盒“源盘→NAS→换目标盘→恢复→box冷启动”已经闭环；当前客户版为 20261026-v2。已完成的是此硬件/系统配置的链路和通用界面，不表示任意OS/分区均已适配。项目名称、技术 ready/verified、人工 customer_ready 含义不同。

## Wake / first-action

用户继续平台或新增第二项目时，先只读确认 repo/branch/diff，读 `imaging_station/README.md`、`CONTRACT.md`、profile列表和finalizer假设，再通过工作站GET `/api/state` 刷新状态。新增设备先实际适配并完成试刷/冷启动，之后才注册配置和开放恢复；不只添一个profile名字。

2026-10-28只读快照为 [`station-readonly.json`](../artifacts/handoff-20261028/station-readonly.json)：服务在线、NAS在线、无进行中的任务、只见受保护内置盘；快照不能代替刷盘时重新核对SSD本体序列号。

## 6. 镜像与工作站：位置、代码和边界

### 三种镜像不要混用

| 镜像 | 存储与内容 |
|---|---|
| 10/23 旧 v1 `yikai-box-noble-piper-rt-20261023-v1` | Clonezilla 格式，4,622,365,169 bytes；归档 `5090d:/data/xyzbox-images/` 与当时闪迪 U 盘。制作早于最后客户目录/风扇整理，不是当前完整客户版；格式不能直接放进新站列表当 ready |
| `fanxiang-original-20261026` | NAS 原样保底备份，4,654,665,436 bytes；在修改源盘前完成校验，缺补齐后的客户入口 |
| **`20261026T124736Z-cdaaebd4`** | NAS 客户版 **20261026-v2**，3,907,322,618 bytes；含 RT、kcan、客户独立 SDK、文档、it87/lm-sensors，已清理旧调试/安装资料 |

NAS 为 `//192.168.100.100/home`，专用 `AlgoLaptop`；库目录 `/mnt/xyzbox-nas/XYZBoxImages`。`manifest.json` 记录来源、最低容量、分区/数据摘要和 profile；`.records/20261026/` 保存本轮验收副本。NAS 名称仍是兼容路径，跨项目定位不要求立即搬库。

v2 的恢复任务 `209f8d6cec0d42849fff1a6efa4ca041` 成功，耗时3m44s。早期两个失败记录保留，不删除/改成成功；修复后的完整链路重新运行通过。原始记录见 `artifacts/imaging-station-20261026/`，冷启动见 `hp-coldboot.json`。

### 部署

- 刷盘机 `.106.3`：`/opt/xyzbox-imager` 代码，`/var/lib/xyzbox-imager` 任务 JSON/日志；`xyzbox-imager.service` 系统服务。
- CIFS 单元 `mnt-xyzbox\x2dnas.mount`；凭据路径 `/etc/xyzbox-imager/nas.credentials`（root-only）。只读位置/权限即可，不 cat 值，不带进客户镜像。
- 本机 WebUI `http://127.0.0.1:8830/`；桌面/应用名「系统镜像工作站」，图形登录后自动打开。MBP 远程看同一地址需显式 SSH-L：`ssh -N -L 127.0.0.1:8830:127.0.0.1:8830 zenbot-alg@192.168.106.3`。先查端口占用，只处理自己旧转发，不杀别人的进程。
- 只监听 loopback，不是公司 LAN 无认证共享网站。Host/Origin/请求头有检查；本轮不扩公网或弱化访问边界。
- ThinkBook 曾因充电/休眠、双网卡同 IP 的 ARP 现象掉线；用户要求先不继续改网络/全局电源策略。任务期间有 sleep inhibitor，空闲仍可能休眠。失联先判断其是否醒着/接电，不重装驱动或复制凭据去补通路。
- 现场网卡实协商1Gbps；USB UAS10Gbps，不能把连接到2.5G交换机等同于链路已到2.5G。

### 代码图

| 文件 | 责任 |
|---|---|
| `imaging_station/core.py` | `Engine`：原生 SSD 识别、系统盘排除、单任务锁、Partclone捕获/恢复/验证、持久任务；`RESTORE_PROFILES` 是已验证恢复配置列表 |
| `server.py`、`static/` | 本机HTTP API、通用界面、项目筛选；`--preview-state` 仅展示历史快照，不创建 Engine，POST 全拒绝 |
| `finalize_target.py` | **当前适配仅 Ubuntu24.04 + 两分区 EFI/FAT 与 Ext4**；新 GPT/FS UUID、machine-id、SSH host keys、hostname，更新 fstab/GRUB 与 UEFI fallback。hostname仍带 yikai前缀，不能直接当任意系统通用适配 |
| `install_station.sh`、`xyzbox-imager.service`、`nas.mount.in` | 安装与持久服务；legacy xyzbox 名称保留兼容；安装器不获取凭据或下载依赖 |
| `prepare_customer_source.sh` | 本轮特定离线母盘整理配方，含固定路径/kit哈希/原备份前提；不是通用 OS 安装器 |
| `test_core.py`、`test_server.py` | 33项无物理盘测试，覆盖错盘/热插拔、完整性、任务锁、未适配profile拒绝、HTTP边界、预览禁写 |
| `check_partclone_roundtrip.sh`、`check_gpt_restore.sh` | Linux 临时普通文件回归，分别验证FAT/Ext4往返与空MBR→GPT；不操作真实磁盘 |

完整 API 与格式见 [`imaging_station/CONTRACT.md`](../imaging_station/CONTRACT.md)。GET `/api/state`；POST `/api/jobs` 仅 capture/restore，无任意 shell。project/project_name/profile/version 是归属元数据，技术 ready/verified 与人工 `customer_ready` 分开。捕获仍主要按 profile 记录，旧项目归属可从注册表推导；没有项目管理/发布审批后台。

已验证 profile 只有 `seavo-sv3-piper-rt`。新增项目需要实际适配身份/启动/系统，再注册和开放 UI；不能只向 `RESTORE_PROFILES` 添个名字就称为已适配。多系统、任意分区、Windows/加密/LVM 等不在现有保证内。

### 刷盘约束与已解决陷阱

- 格式 `xyzbox-partclone-v1`：GPT backup + partition table + `part-N.pcl.zst`，按已用块复制，不是256GB全扇区拷贝。源分区须卸载，捕获时块只读。
- CIFS真实在线检查防止 NAS 掉载后静默写本地目录；先完整验证镜像，再写目标。恢复后使用同版本 Partclone 流摘要读回比对、fsck，再做身份初始化/检查。
- 自动排除根/home/boot/EFI/swap 所在整盘；目标须外接USB、能取到本体型号/序列号、重新输入序列号；每次关键操作重验，不能缓存 `/dev/sda` 当身份。普通U盘若没有可验证原生SMART身份，不是已支持目标。
- 源SSD不允许被它自己生成的镜像覆盖；`.partial-*`不发布为ready。服务中断标 interrupted，不续跑半个恢复。百分比是阶段进度。
- 最小目标实际容量保持256060514304 bytes；**没有缩分区**。更大盘可恢复但不自动扩容，更小的“256GB”盘可能不行。
- 新盘有空MBR时 `sgdisk --load-backup` 仍需显式 `--mbrtogpt`；错误要保留stdout和stderr。
- `lsblk -J` 只有包含 NAME 或显式 tree 才有 children。`swapon` 在 Ubuntu24.04无 `--json`，当前实现用兼容 raw 输出。
- 修改 Ext4 UUID 前需要记录一次 `e2fsck -f -p`，只读 fsck 不更新时间。UUID变化须同步 fstab 和 GRUB配置；fallback补齐 shim/grub文件，不写刷盘机NVRAM。
- NAS 输出文件打开失败也必须清理已启动 Partclone；不能让失败任务释放锁后残留复制进程。源码已有回归。
- 不直接复用旧 `scripts/finalize_cloned_root.sh` 的硬编码临时盘/会话假设；生产站使用当前 `finalize_target.py`。

## 完成条件与关闭范围

当前第一项目已完成捕获/恢复/读回校验/身份初始化/冷启动。第二项目在用户提供实际目标时再开，需有自己的配置限制、试刷和启动收据。

当前没有待自动启动的捕获、恢复、盘清理或网络/电源策略修改。UMIS内置盘整盘禁止作目标；不能以USB桥序列号认盘；标称256GB不足以判断容量可恢复。访问入口和凭据真源见共同入口第9节，不把密码复制到本文件或目标镜像。
