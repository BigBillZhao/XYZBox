# Yikai 刷盘工作站 MVP

部署主机：`zenbot-alg@192.168.106.3`，ThinkBook 16 G8 AHP，Ubuntu 24.04。
本机入口：**http://127.0.0.1:8830/**。桌面「Yikai 刷盘工作台」和应用菜单可打开；图形登录后自动打开。
服务随系统启动，任务由后台服务执行，关闭浏览器不会中止任务。

NAS 使用专用账号的 `//192.168.100.100/home/XYZBoxImages`，镜像不占工作站根分区。
root-only 凭据在 `/etc/xyzbox-imager/nas.credentials`，不进入代码、日志或客户镜像。
当前局域网协商为 **1Gbps**；硬盘盒 USB UAS 为 10Gbps。

## 日常操作

1. 将源盘或目标盘装入 USB 硬盘盒并插上；工作站会阻止 USB 磁盘被桌面自动挂载。
2. 在 WebUI 核对 SSD 本体型号、序列号和容量。内置系统盘整盘锁定，硬盘盒序列号不作 SSD 身份。
3. 制作镜像：选择母盘，填写名称、硬件配置和原生序列号，开始备份。
4. 刷盘：选择已校验镜像和另一块目标盘，输入目标 SSD 序列号后开始。**写入覆盖整个目标盘**。
5. 等待任务「已完成」；失败或中断不能作为发货验收。更换硬盘前确认任务结束、分区均已卸载。
6. 将刷好的盘装入信步 box，实际冷启动，核对 RT、CAN 和客户只读示例，再做该台设备的验收。

系统不允许用某镜像覆盖其源 SSD，防止误刷母盘。技术校验通过与 `customer_ready` 放行标记分别记录。
本轮客户版 **20261026-v2** 已恢复至惠普 `HASI26340100088` 并通过读回和离线 SDK/启动配置检查；新主机名 `yikai-f98ac0a5`。
已在信步 box `192.168.110.12` 实际冷启动，确认目标 SSD、RT 内核、SDK 环境及风扇读取正常。
当前 USB 列表无 CAN 硬件，双臂通信验收仍待其接入；不复用 10 月 23 日另一块惠普盘的旧验收结论。

当前仅支持 GPT + FAT/Ext4、Ubuntu 24.04、x86_64、上述信步硬件配置。
源盘必须卸载；目标容量须不小于镜像记录的**实际字节数**，目前为 `256060514304`。
大盘可恢复，分区暂不自动扩容；小于母盘的同标称 256GB 盘不支持直接恢复。此版未做收缩流程。
百分比表示阶段进度，不是精确剩余时间；镜像读写的详细 Partclone 日志保存在工作站。
无停止/继续按钮；中断恢复后应重新完整刷盘。

## 数据与校验

- `/opt/xyzbox-imager`：部署代码、静态页面、固定身份初始化程序。
- `/var/lib/xyzbox-imager/jobs/*.json`：持久任务记录；重启服务后未完成记录标为 interrupted。
- `/var/lib/xyzbox-imager/*.log`：Partclone、压缩、校验和任务日志。
- `/mnt/xyzbox-nas/XYZBoxImages/<id>/manifest.json`：镜像版本、来源、软件、最小目标容量和校验和。
- `.partial-*`：未完成镜像；不会登记为可恢复版本。
- `gpt.bin`、`partition-table.json`、`part-N.pcl.zst`：GPT 和按已用块压缩的分区镜像。

捕获：源盘置块只读 → GPT/已用块流式保存至 NAS → SHA256 → 解压流 SHA256 + Partclone CRC → 原子登记 ready。
恢复：先核对整个镜像 → 再核对目标 SSD → 写 GPT 和分区 → 读回已用块 SHA256 + 只读文件系统检查 → 初始化身份 → 再检查文件系统。
每台目标生成新的 GPT GUID、Ext4/FAT UUID、machine-id、主机名和 SSH 主机密钥，更新 fstab/GRUB，并补齐 UEFI fallback。
不会修改刷盘机的启动项或内置 Windows/Ubuntu 分区。任务运行时阻止休眠；未改全局电源/路由器策略。

## 维护

```bash
sudo systemctl status xyzbox-imager 'mnt-xyzbox\x2dnas.mount'
sudo journalctl -u xyzbox-imager --utc -n 100 --no-pager
sudo systemctl restart 'mnt-xyzbox\x2dnas.mount'  # NAS 恢复后重新挂载
```

不要在任务执行时重启服务或拔盘。若服务必须停止，任务会中断，目标盘应重刷；源盘可能保留块只读状态，可在确认任务已停后重新插拔。
API 只监听本机回环地址，不修改防火墙。远程查看可用显式 SSH 转发：

```bash
ssh -N -L 127.0.0.1:8830:127.0.0.1:8830 zenbot-alg@192.168.106.3
```

开发检查：`python3 -m unittest imaging_station.test_core imaging_station.test_server`；Linux 上运行 `check_partclone_roundtrip.sh` 和 `check_gpt_restore.sh` 验证普通文件往返，不使用物理盘。
安装前需已有 NAS 挂载单元和凭据，并安装 python3、partclone、zstd、smartmontools、cifs-utils、fdisk、gdisk、parted、dosfstools、e2fsprogs。
然后执行 `sudo bash imaging_station/install_station.sh`。安装器不下载软件、不收集凭据。
