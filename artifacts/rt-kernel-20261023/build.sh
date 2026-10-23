#!/usr/bin/env bash
set -euo pipefail
cd /work/downloads
apt-get source --download-only linux-hwe-7.0=7.0.0-38.38~24.04.4
sha256sum --check /work/repo/system/realtime/SHA256SUMS.sources
if [[ ! -f /work/source/Makefile ]]; then
    dpkg-source -x linux-hwe-7.0_7.0.0-38.38~24.04.4.dsc /work/source
fi
bash /work/repo/scripts/build_rt_kernel.sh --prepare-only /work/source /work/build
make -C /work/source O=/work/build -j24 \
    KBUILD_BUILD_USER=xyzbox KBUILD_BUILD_HOST=xyzbox-builder \
    KDEB_PKGVERSION=7.0.14-xyzbox2 bindeb-pkg
cp /work/build/.config /work/config-7.0.14-xyzbox-rt
cd /work
sha256sum linux-image-7.0.14-xyzbox-rt_7.0.14-xyzbox2_amd64.deb \
    linux-headers-7.0.14-xyzbox-rt_7.0.14-xyzbox2_amd64.deb \
    config-7.0.14-xyzbox-rt > SHA256SUMS.build
date --iso-8601=seconds > BUILD-COMPLETE
