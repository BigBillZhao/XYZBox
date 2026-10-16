# 固定版本与来源

所有归档和轮子的大小与 SHA-256 都在 [`manifest.json`](manifest.json)；
可用 `sha256sum --check vendor/SHA256SUMS` 一次核对。

## kcan 1.4.2

- 上游：[KH-UCANFD Linux SDK](https://gitee.com/ChengDu-KunHong/KH-UCANFD_Linux_SDK)
- 原发行包来源：`https://gitee.com/ChengDu-KunHong/KH-UCANFD_Linux_SDK/releases/download/latest/KH-UCANFD_Linux_SDK.zip`
- 获取时内容为 **1.4.2 / 2026-07-21**；原 ZIP SHA-256：
  `0859afc67dc63f232d64a8815a4c2a7bcf7129298c48748a70174647a4a6508c`
- 仓库文件：`kcan-driver-1.4.2.tar.gz`。
- 提取范围：原发行包 `driver/`，加原始许可证、README、release notes。
  驱动源码未修改；安装时只重新生成原 Makefile 已支持的 dkms.conf。
- 没有打包固件镜像或自动升级工具。恢复主机 CAN 驱动无需刷新设备固件。
- 许可证：上游 `LICENSE.gpl` / `LICENSE.lgpl`；源码头部版权保留。

`latest` URL 将来可能变化，所以安装脚本只使用已经放入本仓库、哈希固定的源码包。

## pyAgxArm

- 上游：[agilexrobotics/pyAgxArm](https://github.com/agilexrobotics/pyAgxArm)
- 仓库文件：`pyAgxArm-1ae40ad.tar.gz`，原官方归档未修改。
- 归档顶层为 `agilexrobotics-pyAgxArm-1ae40ad`，完整归档哈希用于精确复现：
  `ea8a38af9e6e44255a53c351c4cf788592a21abe694e0f2ce683f2b9be177711`
- 许可证：LGPL-3.0；完整源码、测试、构建文件和许可证随归档提供。
- 该源码包含 Nero v112；不能仅凭安装包显示的 `1.0.0` 确认这一点。

## Python 离线依赖

`python-wheels/` 来自 PyPI，固定版本见根目录 `requirements-nero.txt`。
目标为 Linux x86_64 / CPython 3.12；其他平台请在线取得相应轮子后单独验收。
运行依赖为 python-can、typing_extensions、packaging、wrapt；setuptools 和 wheel 用于离线构建 SDK。

`python-sources/` 同时提供 python-can 4.6.1 的上游源码发行包。
各 wheel 内原有 license/notice 均保留，并提取副本至 [`licenses/wheels/`](../licenses/wheels/)。

本仓库的安装过程不需要上游主分支实时可用，也不会自动升级到新驱动、SDK 或设备固件。
