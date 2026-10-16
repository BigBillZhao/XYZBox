#!/usr/bin/env bash
set -euo pipefail
repo=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)
online=false
if [[ ${1:-} == --online ]]; then online=true; shift; fi
if [[ $# -gt 1 ]]; then echo "Usage: $0 [--online] [venv-directory]" >&2; exit 2; fi
venv=${1:-"$repo/.venv"}
if [[ $online == false ]]; then
    python3 -c 'import platform,sys; assert platform.system() == "Linux" and sys.version_info[:2] == (3,12) and platform.machine() == "x86_64", "Bundled wheels target Linux x86_64 / CPython 3.12; use --online for another Linux platform."'
fi
(cd "$repo" && sha256sum --check vendor/SHA256SUMS)
python3 -m venv "$venv"
if [[ $online == true ]]; then
    "$venv/bin/python" -m pip install -r "$repo/requirements-nero.txt"
else
    "$venv/bin/python" -m pip install --no-index --find-links "$repo/vendor/python-wheels" -r "$repo/requirements-nero.txt"
fi
PIP_NO_INDEX=1 PIP_DISABLE_PIP_VERSION_CHECK=1 "$venv/bin/python" -m pip install --no-deps --no-build-isolation "$repo/vendor/pyAgxArm-1ae40ad.tar.gz"
"$venv/bin/python" -m pip check
"$venv/bin/python" -c 'from pyAgxArm import resolve_firmware_profile; assert resolve_firmware_profile("nero", "1.12") == "v112"; print("Nero 1.12 profile: v112")'
echo "Environment ready: $venv"
echo 'Start with examples/nero_joint_control.py --read; no LeRobot, PICO, camera, or GPU dependency.'
