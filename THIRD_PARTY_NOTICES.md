# Third-Party Components

English | [简体中文](THIRD_PARTY_NOTICES.zh-CN.md)

Distributed third-party sources and binaries retain their respective copyrights and licenses. The original license text inside each archive governs that component.

| Component | Version / snapshot | License materials |
|---|---|---|
| USB CAN Linux driver | 1.4.2 | Licenses and source headers inside `vendor/kcan-driver-1.4.2.tar.gz`; `licenses/can-driver-*.txt` |
| pyAgxArm | Official archive 1ae40ad | Original LGPL-3.0, complete source archive; `licenses/pyAgxArm-LGPL-3.0.txt` |
| python-can | 4.6.1 | Original wheel license, corresponding source distribution; `licenses/python-can-LICENSE.txt` |
| typing_extensions | 4.15.0 | Original wheel license and `licenses/wheels/typing_extensions/` |
| packaging | 25.0 | Original wheel license and `licenses/wheels/packaging/` |
| wrapt | 1.17.3 | Original wheel license and `licenses/wheels/wrapt/` |
| setuptools | 80.10.2 | Original wheel license and `licenses/wheels/setuptools/` |
| wheel | 0.48.0 | Original wheel license and `licenses/wheels/wheel/` |
| Linux / Ubuntu kernel build recipe | Source package 7.0.0-38.38~24.04.4 / Linux 7.0.14 | `licenses/linux-COPYING.txt`, `licenses/linux-GPL-2.0.txt`; complete source packages and other component licenses retained in the delivery machine's real-time kernel directory |

Sources, pinned hashes, and extraction scope are recorded in [`vendor/manifest.json`](vendor/manifest.json).
The complete GPL-3.0 text referenced by LGPL-3.0 is in [`licenses/GPL-3.0.txt`](licenses/GPL-3.0.txt).
Component names identify the software; they do not imply additional third-party certification of XYZBox's integration or examples.

RT kernel source checksums, configuration, and build steps are in `system/realtime/` and [the real-time kernel guide](docs/en/07-realtime-kernel.md).
When delivering custom kernel binaries to a customer, also deliver the three original source archives, configuration, and build script. Preserve all license files in the sources.
