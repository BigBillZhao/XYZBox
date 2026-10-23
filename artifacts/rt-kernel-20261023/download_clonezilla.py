"""Fetch fixed, official-mirror ISO in ranges; verify official SHA-256."""
from concurrent.futures import ThreadPoolExecutor, as_completed
import hashlib
from pathlib import Path
import subprocess

URL = "https://free.nchc.org.tw/clonezilla-live/stable/clonezilla-live-3.3.3-37-amd64.iso"
SIZE = 505413632
SHA256 = "3079458d926a37d3533e5d5caeb61b6e49c2dc69e2c97e0332ef37986bb3414f"
CHUNK = 8 * 1024 * 1024
WORK = Path("/private/tmp/xyzbox-cz-chunks")
OUT = Path("/private/tmp/clonezilla-live-3.3.3-37-amd64.verified.iso")
WORK.mkdir(exist_ok=True)


def fetch(index):
    start = index * CHUNK
    end = min(SIZE, start + CHUNK) - 1
    path = WORK / f"{index:04d}.part"
    if not path.exists() or path.stat().st_size != end - start + 1:
        subprocess.run([
            "curl", "-fsSL", "--connect-timeout", "10", "--max-time", "180",
            "--retry", "2", "--range", f"{start}-{end}", "-o", str(path), URL,
        ], check=True)
    if path.stat().st_size != end - start + 1:
        raise RuntimeError(f"Unexpected range size for {index}")
    return index


count = (SIZE + CHUNK - 1) // CHUNK
with ThreadPoolExecutor(max_workers=16) as pool:
    for n, future in enumerate(as_completed(pool.submit(fetch, i) for i in range(count)), 1):
        print(f"range {future.result()}: complete ({n}/{count})", flush=True)
digest = hashlib.sha256()
with OUT.open("wb") as dest:
    for i in range(count):
        data = (WORK / f"{i:04d}.part").read_bytes()
        digest.update(data)
        dest.write(data)
assert OUT.stat().st_size == SIZE
assert digest.hexdigest() == SHA256, digest.hexdigest()
print(f"SHA256 OK: {OUT}", flush=True)
