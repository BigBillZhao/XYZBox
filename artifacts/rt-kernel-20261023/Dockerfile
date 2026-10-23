FROM ubuntu:24.04
ARG DEBIAN_FRONTEND=noninteractive
RUN sed -i -e 's|http://archive.ubuntu.com/ubuntu/|http://mirrors.nju.edu.cn/ubuntu/|g' \
    -e 's|http://security.ubuntu.com/ubuntu/|http://mirrors.nju.edu.cn/ubuntu/|g' \
    /etc/apt/sources.list.d/ubuntu.sources
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential bc bison flex gawk libssl-dev libelf-dev libdw-dev \
    libncurses-dev dwarves rsync cpio kmod fakeroot dpkg-dev debhelper zstd \
    ca-certificates curl xz-utils && rm -rf /var/lib/apt/lists/*
COPY ubuntu-kernel-src.sources /etc/apt/sources.list.d/xyzbox-kernel-src.sources
RUN apt-get update
RUN apt-get install -y --no-install-recommends python3
RUN useradd -u 1100 -m builder
WORKDIR /work
