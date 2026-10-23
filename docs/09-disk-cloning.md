# Yikai box 母盘与整盘复制

当前流程：先完成源机 RT 内核与 CAN 验收，再从独立 U 盘启动 Clonezilla，保存整盘镜像，恢复到目标 SSD，最后单独初始化目标机身份。

## 2026-10-23 本轮设备

| 用途 | 设备识别 | 容量（字节） |
|---|---|---:|
| 源系统盘 | Fanxiang S500Pro，NVMe，序列号 `26030958613001465` | 256060514304 |
| 目标 SSD | 用户确认的惠普 SSD；USB 桥 `ASMT ASM246X / AAAABBBB0010` | 256060514304 |
| 维护 U 盘 | SanDisk 3.2Gen1，序列号 `00023309012526182146` | 250305576960 |

设备名如 `/dev/sda` 会在重启后变化，必须重新核对序列号、容量和挂载状态。
目标桥的序列号不是 SSD 本体序列号；本轮识别还依据插入顺序和用户对实物的确认。

闪迪 U 盘分为 `XYZBOX_LIVE`（2 GiB、FAT32、EFI）和 `XYZBOX_IMAGES`（剩余空间、ext4）。
前者存放 Clonezilla 3.3.3-37，后者存放版本化母盘镜像、操作记录及目标身份初始化脚本。
本轮额外配置了仅密钥登录的维护 SSH；它是这次操作的维护入口，不属于客户系统。

## 为什么采用这一流程

源盘保留在 box 内，避免反复拆装；目标 SSD 通过 USB 转接盒连接。
Clonezilla 对 ext4 使用 Partclone 复制已使用的数据块，而非把全部 256GB 空白空间逐扇区复制。
整盘镜像同时保留 GPT、EFI 分区与 Linux 根分区。镜像恢复必须离线执行，源分区不应挂载。
见 [Clonezilla 官方说明](https://clonezilla.org/) 与 [操作文档](https://clonezilla.org/clonezilla-live-doc.php)。

标称容量相同不代表实际扇区数相同。本轮两块 SSD 的字节数完全相同，符合直接恢复的容量条件。
以后若目标盘更小，应另行制作收缩过分区的母盘；不能仅凭已用空间很小而忽略分区尺寸。

## 恢复后的身份初始化

恢复后的目标根分区仍未启动时，显式按设备路径挂载，运行：

```bash
sudo bash finalize_cloned_root.sh /mnt/target-root /dev/明确核对的目标根分区
```

脚本重新生成 machine-id、SSH 主机密钥与 `yikai-xxxxxxxx` 主机名，处理 D-Bus machine-id 链接。
它拒绝当前运行系统，以及本轮已知的梵想源盘。它不分区、不格式化磁盘。
每次从同一个原始母盘恢复后都必须执行；母盘中的机器身份不能直接批量交付。

当前系统的两个有线网口使用 DHCP，没有绑定源机 MAC；cloud-init 已被安装器禁用。
CAN 配置依据适配器类型和通道顺序，物理 CAN1 对左臂、CAN2 对右臂，CAN3/4 保留。
新工控机应采用相同硬件和 UEFI 启动配置；本轮自编译 RT 内核使用的机器 Secure Boot 为关闭状态。

EFI 文件可随整盘镜像复制，主板 NVRAM 启动项不能随硬盘复制。
本轮源盘已有 `EFI/BOOT/BOOTX64.EFI`、fallback 程序及 Ubuntu 启动文件。
目标盘最终验收仍包括：单独装入新工控机、冷启动、网络连接、RT 内核与 CAN 枚举。

构建、安装及运行证据归档在 [`artifacts/rt-kernel-20261023`](../artifacts/rt-kernel-20261023/)。
本轮实际执行结果随验收补入该目录，不能把流程文档当成已经完成的冷启动验证。

## 本轮结果

已从梵想源盘生成并验证 `yikai-box-noble-piper-rt-20261023-v1`，镜像约 4.62 GB。
惠普目标 SSD 的恢复、独立 machine-id/SSH 主机密钥初始化和卸载均完成，新主机名为 `yikai-21c5e86e`。
镜像同时保存在闪迪 U 盘的 `XYZBOX_IMAGES` 分区与
`5090d:/data/xyzbox-images/yikai-box-noble-piper-rt-20261023-v1`；5090D 副本 28 项 BLAKE3 校验通过。
内核构建包另存于 `5090d:/data/xyzbox-rt-20261023`。

用户已取下目标 SSD，明确稍后测试新工控机。原 box 已重新从梵想盘启动进入 RT，
网络、桌面、两路 CAN 与十二个驱动禁能状态再次核验正常。新工控机冷启动仍未验证。
