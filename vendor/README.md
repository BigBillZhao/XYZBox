# Pinned Versions and Sources

English | [简体中文](README.zh-CN.md) · [Home](../README.md)

Sizes and SHA-256 checksums for every archive and wheel are recorded in [`manifest.json`](manifest.json).
Run `sha256sum --check vendor/SHA256SUMS` from the repository root to verify them together.

## kcan 1.4.2

- The original release URL is retained as `upstream_url` in `manifest.json` for traceability.
- The downloaded release was **1.4.2 / July 21, 2026**. Original ZIP SHA-256:
  `0859afc67dc63f232d64a8815a4c2a7bcf7129298c48748a70174647a4a6508c`
- Bundled file: `kcan-driver-1.4.2.tar.gz`.
- Extraction scope: the original release's `driver/` directory, original licenses, README, and release notes.
  Driver sources are unchanged. Installation only regenerates `dkms.conf` using functionality already provided by the original Makefile.
- Firmware images and automatic firmware upgrade tools are not bundled. Restoring the host CAN driver does not require flashing device firmware.
- Licenses: upstream `LICENSE.gpl` / `LICENSE.lgpl`; source copyright headers are preserved.

A `latest` URL may change later, so the installer uses only the bundled source archive with its pinned hash.

## pyAgxArm

- The SDK's original release source is recorded in `manifest.json`.
- Bundled file: `pyAgxArm-1ae40ad.tar.gz`, the unmodified official archive.
- The pinned source snapshot is `1ae40ad`. Full archive hash for exact reproduction:
  `ea8a38af9e6e44255a53c351c4cf788592a21abe694e0f2ce683f2b9be177711`
- License: LGPL-3.0. Complete sources, tests, build files, and license are included in the archive.
- This snapshot includes Nero v112 support. The displayed package version `1.0.0` alone does not establish that support.

## Offline Python dependencies

`python-wheels/` contains packages from PyPI; pinned versions are in the root `requirements-nero.txt`.
The target is Linux x86_64 / CPython 3.12. Obtain matching wheels online and validate separately for other platforms.
Runtime dependencies are python-can, typing_extensions, packaging, and wrapt. setuptools and wheel support offline SDK builds.

`python-sources/` also contains the upstream source distribution of python-can 4.6.1.
Original licenses/notices remain inside each wheel, with extracted copies in [`licenses/wheels/`](../licenses/wheels/).

Installation does not depend on a live upstream main branch and does not automatically upgrade the driver, SDK, or device firmware.
