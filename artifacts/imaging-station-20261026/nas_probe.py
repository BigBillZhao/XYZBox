"""Read SMB auth from stdin; verify a disposable 64 MiB NAS round trip."""
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import time

auth = sys.stdin.read()
cache = Path.home() / '.cache/xyzbox-imager'
cache.mkdir(parents=True, exist_ok=True)
source, restored = cache/'nas-probe.bin', cache/'nas-probe-readback.bin'
remote = 'XYZBoxImages/.probe-20261026.bin'
size = 64 * 1024 * 1024

def run(command):
    begin = time.monotonic()
    result = subprocess.run(['smbclient', '//192.168.100.100/home', '-A', '/dev/stdin',
                             '-d', '0', '-c', command], input=auth, text=True,
                            capture_output=True, timeout=90)
    if result.returncode:
        raise RuntimeError(result.stderr[:500])
    return time.monotonic() - begin

try:
    source.write_bytes(os.urandom(size))
    expected = hashlib.sha256(source.read_bytes()).hexdigest()
    write_s = run(f'put {source} {remote}')
    read_s = run(f'get {remote} {restored}')
    actual = hashlib.sha256(restored.read_bytes()).hexdigest()
    assert expected == actual
    print(json.dumps({'bytes': size, 'write_seconds': write_s, 'read_seconds': read_s,
                      'write_MiB_s': size / 2**20 / write_s, 'read_MiB_s': size / 2**20 / read_s,
                      'sha256_match': True, 'sha256': actual}))
finally:
    try:
        run(f'del {remote}')
    finally:
        source.unlink(missing_ok=True)
        restored.unlink(missing_ok=True)
