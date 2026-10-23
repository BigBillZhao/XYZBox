#!/usr/bin/env bash
set -euo pipefail
repo=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)
venv=${1:-"$repo/.venv"}
python3 -c 'import platform,sys; assert platform.system() == "Linux" and sys.version_info[:2] == (3,12) and platform.machine() == "x86_64", "Offline wheels require Linux x86_64 / Python 3.12"'
(cd "$repo" && sha256sum --check vendor/SHA256SUMS)
python3 -m venv "$venv"
"$venv/bin/python" -m pip install --no-index --find-links "$repo/vendor/python-wheels" -r "$repo/requirements-nero.txt"
PIP_NO_INDEX=1 PIP_DISABLE_PIP_VERSION_CHECK=1 "$venv/bin/python" -m pip install --no-deps --no-build-isolation "$repo/vendor/pyAgxArm-1ae40ad.tar.gz"
"$venv/bin/python" -m pip check
"$venv/bin/python" -c 'from pyAgxArm import ArmModel,resolve_firmware_profile; assert resolve_firmware_profile(ArmModel.PIPER,"S-V1.7-3") == "default"; print("Piper SDK environment ready")'
