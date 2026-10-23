#!/usr/bin/env bash
set -euo pipefail
chmod +x /work/source/debian/scripts/sign-module
make -C /work/source O=/work/build -j24 \
    KBUILD_BUILD_USER=xyzbox KBUILD_BUILD_HOST=xyzbox-builder \
    KDEB_PKGVERSION=7.0.14-xyzbox2 bindeb-pkg
cp /work/build/.config /work/config-7.0.14-xyzbox-rt
cd /work
sha256sum linux-image-7.0.14-xyzbox-rt_7.0.14-xyzbox2_amd64.deb \
    linux-headers-7.0.14-xyzbox-rt_7.0.14-xyzbox2_amd64.deb \
    config-7.0.14-xyzbox-rt > SHA256SUMS.build
date --iso-8601=seconds > BUILD-COMPLETE
