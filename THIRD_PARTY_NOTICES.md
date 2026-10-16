# 第三方组件

第三方源码/二进制分发保留各自版权及许可证，具体条款以归档内部原文为准。

| 组件 | 版本/快照 | 许可证材料 |
|---|---|---|
| USB CAN Linux driver | 1.4.2 | `vendor/kcan-driver-1.4.2.tar.gz` 内许可证及源码头；`licenses/can-driver-*.txt` |
| pyAgxArm | 官方归档 1ae40ad | 原始 LGPL-3.0，完整源码归档；`licenses/pyAgxArm-LGPL-3.0.txt` |
| python-can | 4.6.1 | wheel 原许可证、对应源码发行包；`licenses/python-can-LICENSE.txt` |
| typing_extensions | 4.15.0 | wheel 原许可证及 `licenses/wheels/typing_extensions/` |
| packaging | 25.0 | wheel 原许可证及 `licenses/wheels/packaging/` |
| wrapt | 1.17.3 | wheel 原许可证及 `licenses/wheels/wrapt/` |
| setuptools | 80.10.2 | wheel 原许可证及 `licenses/wheels/setuptools/` |
| wheel | 0.48.0 | wheel 原许可证及 `licenses/wheels/wheel/` |
| Linux / Ubuntu 内核构建配方 | 源包 7.0.0-38.38~24.04.4 / Linux 7.0.14 | `licenses/linux-COPYING.txt`、`licenses/linux-GPL-2.0.txt`；完整源包及其他组件许可保存在交付机实时内核目录 |

来源、固定哈希和提取范围见 [`vendor/manifest.json`](vendor/manifest.json)。
LGPL-3.0 所引用的 GPL-3.0 完整原文见 [`licenses/GPL-3.0.txt`](licenses/GPL-3.0.txt)。
这些名称仅用于识别组件，不代表第三方为 XYZBox 的集成或示例作额外认证。

实时内核的源包校验、配置与构建步骤见 `system/realtime/` 和 `docs/07-realtime-kernel.md`。
向客户复制自编译内核包时，一并交付三个原始源包、配置和构建脚本；保留源码中的所有许可文件。
