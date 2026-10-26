# Yikai Box · Piper 客户系统

系统预装 Ubuntu 24.04、实时内核 `7.0.14-xyzbox-rt`、昆宏 CAN 驱动 1.4.2 与固定版本 pyAgxArm。
账户为 `ubuntu`，登录凭据单独交付；网络使用 DHCP，主机名可在终端运行 `hostname` 查看。

物理 CAN1 对应 `can0`（左臂），CAN2 对应 `can1`（右臂），开机自动启用 Classic CAN 1Mbps。
CAN3/4 默认关闭。请核对两端 CAN-H/CAN-L、供电和终端电阻，按标签接线。
系统没有配置开机自动运动。

## 第一次运行

```bash
cd ~/yikai-box
source .venv/bin/activate
python examples/piper_read_status.py --channels can0 can1
```

示例只读取状态，不使能、不运动、不切换主从角色。只接一条臂时使用 `--channels can0` 或 `--channels can1`。
当前 SDK 配置适用标准 Piper、固件 S-V1.7-3（default profile）；其他型号或固件请选择对应配置。
完整 API 文档：`~/yikai-box/docs/sdk/piper_api.md`；固件表：`firmware_reference.md`。

`enable()`、`move_j()`、`move_mit()`、`disable()` 可供应用调用，六关节角度单位为 rad。
应用须根据自己的安装位置、负载和工作空间设置轨迹；`disconnect()` 不等于禁能。
镜像恢复记录不替代本台机器的启动和机械臂验收记录。

## 检查与维护

```bash
uname -r
cat /sys/kernel/realtime         # 应为 1
ip -details link show type can   # can0/can1 UP、1000000、mtu 16
dkms status                     # kunhong-linux-driver/1.4.2
sensors it8786-isa-0a40          # 风扇与温度读取
cat /var/lib/xyzbox/provisioning.json
```

风扇保持主板原始策略，已配置自动加载 `it87`；未部署自动调速。
无回传时先核对通道、接线、上电与主从/示教状态。一条臂由一个控制程序负责。
SDK 固定源码为 `1ae40ad`（包版本 1.0.0），不要仅凭包版本识别源码。
需要重建 Python 环境时，在 `~/yikai-box` 执行 `bash scripts/setup_piper_env.sh`，依赖已离线保存。
保留普通内核 `7.0.0-38-generic` 用于回退；更换内核后须重新编译 CAN DKMS 并复验。
