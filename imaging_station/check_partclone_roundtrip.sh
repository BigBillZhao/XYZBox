#!/usr/bin/env bash
# Disposable regular files only: no /dev paths, loop devices, mounts or SSH.
set -euo pipefail

if [[ $# -ne 1 ]]; then
    echo "Usage: $0 SCRATCH_DIRECTORY" >&2
    exit 2
fi

scratch=$(realpath -m -- "$1")
case "$scratch" in
    /|/dev|/dev/*|/proc|/proc/*|/sys|/sys/*)
        echo "Scratch directory must be a normal filesystem directory" >&2
        exit 2 ;;
esac
mkdir -p -- "$scratch"
work=$(mktemp -d -- "$scratch/partclone-roundtrip.XXXXXXXX")
log="$work/commands.log"
passed=0

finish() {
    result=$?
    if [[ $passed -eq 1 ]]; then
        rm -rf -- "$work"
    else
        echo "Partclone roundtrip FAILED; files and command output retained at $work" >&2
        if [[ -f "$log" ]]; then
            tail -n 100 -- "$log" >&2
        fi
    fi
    exit "$result"
}
trap finish EXIT

step() {
    local description=$1
    shift
    echo "$description" >&2
    printf '\nSTEP: %s\nCOMMAND:' "$description" >> "$log"
    printf ' %q' "$@" >> "$log"
    printf '\n' >> "$log"
    # Both stdout and stderr are retained, including unsupported-file errors.
    # No --force, --ignore_crc, --rescue or ignored return codes are used.
    if "$@" >> "$log" 2>&1; then
        return 0
    else
        local result=$?
        echo "Command failed with exit $result: $description" >&2
        return "$result"
    fi
}

step_stdout() {
    local output_file=$1 description=$2
    shift 2
    echo "$description" >&2
    printf '\nSTEP: %s\nCOMMAND:' "$description" >> "$log"
    printf ' %q' "$@" >> "$log"
    printf ' > %q\n' "$output_file" >> "$log"
    if "$@" > "$output_file" 2>> "$log"; then
        return 0
    else
        local result=$?
        echo "Command failed with exit $result: $description" >&2
        return "$result"
    fi
}

for command in truncate mkfs.ext4 mkfs.fat partclone.ext4 partclone.restore partclone.chkimg \
               e2fsck fsck.fat sha256sum python3; do
    if ! command -v "$command" >/dev/null 2>&1; then
        echo "Required tool missing: $command" >&2
        exit 2
    fi
done
if command -v partclone.fat >/dev/null 2>&1; then
    fat_partclone=partclone.fat
elif command -v partclone.vfat >/dev/null 2>&1; then
    fat_partclone=partclone.vfat
else
    echo "Required tool missing: partclone.fat / partclone.vfat" >&2
    exit 2
fi

for filesystem in ext4 vfat; do
    source_file="$work/$filesystem.source.fs"
    target_file="$work/$filesystem.target.fs"
    image_a="$work/$filesystem.a.pcl"
    image_b="$work/$filesystem.b.pcl"
    image_c="$work/$filesystem.c.pcl"
    step "$filesystem: create 128MiB source regular file" truncate -s 134217728 -- "$source_file"
    step "$filesystem: create 128MiB target regular file" truncate -s 134217728 -- "$target_file"
    [[ -f "$source_file" && ! -b "$source_file" && -f "$target_file" && ! -b "$target_file" ]]
    if [[ "$filesystem" == ext4 ]]; then
        binary=partclone.ext4
        step "$filesystem: make filesystem" mkfs.ext4 -q -F "$source_file"
    else
        binary=$fat_partclone
        step "$filesystem: make filesystem" mkfs.fat -F 32 "$source_file"
    fi
    step "$filesystem: clone source (A)" "$binary" --clone --source "$source_file" \
        --output "$image_a" --logfile "$work/$filesystem.clone-a.log"
    # Engine capture uses --output -; prove stdout contains only image bytes and
    # progress/diagnostics stay on stderr by comparing it with a direct-file clone.
    step_stdout "$image_b" "$filesystem: clone source through stdout (B)" \
        "$binary" --clone --source "$source_file" --output - --logfile "$work/$filesystem.clone-b.log"
    hash_a=$(sha256sum -- "$image_a")
    hash_a=${hash_a%% *}
    hash_b=$(sha256sum -- "$image_b")
    hash_b=${hash_b%% *}
    if [[ "$hash_a" != "$hash_b" ]]; then
        echo "$filesystem: repeated Partclone image streams differ (A=$hash_a B=$hash_b)" >&2
        exit 1
    fi
    step "$filesystem: check Partclone image CRC" partclone.chkimg --source "$image_a" \
        --logfile "$work/$filesystem.check.log"
    step "$filesystem: restore into second regular file" partclone.restore --source "$image_a" \
        --overwrite "$target_file" --logfile "$work/$filesystem.restore.log"
    step "$filesystem: recapture restored filesystem (C)" "$binary" --clone --source "$target_file" \
        --output "$image_c" --logfile "$work/$filesystem.clone-c.log"
    hash_c=$(sha256sum -- "$image_c")
    hash_c=${hash_c%% *}
    if [[ "$hash_a" != "$hash_c" ]]; then
        echo "$filesystem: restored read-back differs (A=$hash_a C=$hash_c)" >&2
        exit 1
    fi
    if [[ "$filesystem" == ext4 ]]; then
        step "$filesystem: readonly filesystem check" e2fsck -f -n "$target_file"
    else
        step "$filesystem: readonly filesystem check" fsck.fat -n "$target_file"
    fi
    python3 - "$filesystem" "$hash_a" >> "$work/results.jsonl" <<'PY'
import json,sys
print(json.dumps({"filesystem":sys.argv[1],"filesystem_bytes":134217728,
                  "partclone_sha256":sys.argv[2],"repeated_capture_equal":True,
                  "stdout_image_matches_file_image":True,
                  "restored_readback_equal":True,"partclone_crc_passed":True,
                  "readonly_fscheck_passed":True}))
PY
done

python3 - "$work/results.jsonl" <<'PY'
import json,sys
from pathlib import Path
print(json.dumps({"test":"partclone-regular-file-roundtrip", "passed":True,
                  "uses_physical_devices":False,
                  "results":[json.loads(line) for line in Path(sys.argv[1]).read_text().splitlines()]}))
PY
passed=1
