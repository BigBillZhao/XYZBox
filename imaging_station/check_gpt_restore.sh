#!/bin/bash
# Disk-free regression for new SSDs with a valid but empty DOS/MBR label.
set -euo pipefail
base=${1:?scratch-directory-required}
mkdir -p "$base"
work=$(mktemp -d "$base/gpt-roundtrip.XXXXXX")
trap 'rm -rf -- "$work"' EXIT
truncate -s 128M "$work/source.img"
truncate -s 128M "$work/target.img"
sgdisk --clear --new=1:2048:+16M --typecode=1:ef00 --new=2:0:0 --typecode=2:8300 "$work/source.img" >"$work/commands.log" 2>&1
sgdisk --backup="$work/gpt.bin" "$work/source.img" >>"$work/commands.log" 2>&1
python3 - "$work/target.img" <<'PY'
import sys
with open(sys.argv[1],'r+b') as f:
    f.seek(510); f.write(b'\x55\xaa')
PY
sgdisk --mbrtogpt --load-backup="$work/gpt.bin" "$work/target.img" >>"$work/commands.log" 2>&1
sfdisk -J "$work/source.img" > "$work/source.json"
sfdisk -J "$work/target.img" > "$work/target.json"
python3 - "$work" <<'PY'
import json,sys
from pathlib import Path
p=Path(sys.argv[1]); source=json.loads((p/'source.json').read_text())['partitiontable']; target=json.loads((p/'target.json').read_text())['partitiontable']
assert target['label']=='gpt'
assert [(x['start'],x['size'],x['type']) for x in source['partitions']] == [(x['start'],x['size'],x['type']) for x in target['partitions']]
print(json.dumps({'test':'empty-mbr-to-gpt-restore','passed':True,'uses_physical_devices':False}))
PY
