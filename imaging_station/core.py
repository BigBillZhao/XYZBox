#!/usr/bin/env python3
"""Small, fail-closed USB disk imager. No shell commands or request-supplied hooks.

Image format: xyzbox-partclone-v1. A ready directory contains manifest.json,
gpt.bin, partition-table.json and part-N.pcl.zst. SHA256 covers every data file;
partclone_sha256 also permits an exact used-block read-back before finalization.
"""
from __future__ import annotations

import argparse
import contextlib
import datetime as dt
import fcntl
import hashlib
import json
import os
from pathlib import Path
import re
import stat
import subprocess
import sys
import threading
import time
import uuid


FORMAT = "xyzbox-partclone-v1"
FINALIZER = "/opt/xyzbox-imager/finalize_target.py"
FILESYSTEMS = {"ext4": "partclone.ext4", "vfat": "partclone.fat"}
SLUG = re.compile(r"^[a-zA-Z0-9][a-zA-Z0-9_.-]{0,95}$")
ACTIVE = {"queued", "running"}


class ImagingError(RuntimeError):
    pass


class BusyError(ImagingError):
    pass


def now():
    return dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds")


def run(argv, *, ok=(0,), timeout=30):
    result = subprocess.run(argv, capture_output=True, text=True, timeout=timeout,
                            env={**os.environ, "LC_ALL": "C"})
    if result.returncode not in ok:
        raise ImagingError(f"{Path(argv[0]).name} failed ({result.returncode}): "
                           + (result.stdout.strip() + "\n" + result.stderr.strip()).strip()[-1600:])
    return result.stdout


def atomic_json(path, value):
    path = Path(path)
    temp = path.with_name(path.name + ".tmp-" + uuid.uuid4().hex)
    with temp.open("x", encoding="utf-8") as handle:
        json.dump(value, handle, indent=2, ensure_ascii=False)
        handle.write("\n")
        handle.flush()
        os.fsync(handle.fileno())
    os.replace(temp, path)


def sha256(path):
    digest = hashlib.sha256()
    with Path(path).open("rb") as source:
        for block in iter(lambda: source.read(4 * 1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def descendants(node):
    yield node
    for child in node.get("children", []):
        yield from descendants(child)


def mounts(node):
    return [p for p in (node.get("mountpoints") or []) if p]


def is_system_mount(path):
    # A separately mounted descendant of /home or /boot also belongs to the host.
    return path == "/" or any(path == p or path.startswith(p + "/")
                              for p in ("/home", "/boot", "/efi", "/usr", "/var"))


class Engine:
    def __init__(self, repository: str, state_dir: str):
        self.repository = Path(repository).absolute()
        self.state_dir = Path(state_dir).absolute()
        self.job_dir = self.state_dir / "jobs"
        self.job_dir.mkdir(parents=True, exist_ok=True)
        self.lock_path = self.state_dir / "active.lock"
        self._mutex = threading.RLock()
        # A held process lock means another live Engine owns an imaging job.
        try:
            fd = self._lock()
        except BusyError:
            pass
        else:
            try:
                for job in self.jobs():
                    if job["status"] in ACTIVE:
                        job.update(status="interrupted", phase="interrupted",
                                   finished_at=now(), error="Station process stopped before completion")
                        self._save(job)
            finally:
                os.close(fd)

    def _lock(self):
        fd = os.open(self.lock_path, os.O_CREAT | os.O_RDWR, 0o600)
        try:
            fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            os.close(fd)
            raise BusyError("Another imaging job is already active") from None
        return fd

    def repository_online(self):
        try:
            if not self.repository.is_dir():
                return False
            data = json.loads(run(["findmnt", "--json", "--target", str(self.repository),
                                   "--output", "TARGET,SOURCE,FSTYPE,OPTIONS"]))
            mount = data["filesystems"][0]
            target = Path(mount["target"]).resolve()
            return (mount["fstype"] == "cifs" and
                    self.repository.resolve().is_relative_to(target) and
                    "rw" in mount.get("options", "").split(","))
        except (OSError, ValueError, KeyError, IndexError, ImagingError, subprocess.SubprocessError):
            return False

    def _require_repository(self):
        if not self.repository_online():
            raise ImagingError("Image repository is not an online writable CIFS mount")

    def _inventory(self):
        return json.loads(run(["lsblk", "--json", "--bytes", "--paths", "--output",
                               "NAME,PATH,TYPE,PKNAME,MODEL,SERIAL,SIZE,TRAN,MOUNTPOINTS,FSTYPE,RO,LOG-SEC,PTTYPE"]))["blockdevices"]

    def _native_identity(self, device):
        # A USB bridge's SERIAL is not the SSD serial. Only SMART passthrough
        # responses with a real ATA/NVMe model and serial can make a USB eligible.
        for mode in ("sntasmedia", "sat", "sntjmicron", "sntrealtek", None):
            args = ["smartctl", "--json", "--info"]
            if mode:
                args += ["--device", mode]
            try:
                result = subprocess.run(args + [device], capture_output=True, text=True,
                                        timeout=12, env={**os.environ, "LC_ALL": "C"})
                data = json.loads(result.stdout)
                if result.returncode & 3:
                    continue
                serial = str(data.get("serial_number", "")).strip()
                model = str(data.get("model_name", "")).strip()
                if (serial and model and serial not in ("AAAABBBB0010", "000000000000")
                        and not re.search(r"ASM\d|ASMedia|USB.*Bridge", model, re.I)):
                    return model, serial
            except (OSError, ValueError, subprocess.SubprocessError):
                continue
        return None

    def drives(self):
        try:
            inventory = self._inventory()
            swap_paths = run(["swapon", "--show=NAME", "--raw", "--noheadings"])
            # util-linux swapon has no JSON mode on Ubuntu 24.04. Raw output
            # escapes whitespace as \xNN; decode before resolving device paths.
            swap_nodes = {os.path.realpath(re.sub(r"\\x([0-9a-fA-F]{2})",
                          lambda m: chr(int(m[1], 16)), line.strip()))
                          for line in swap_paths.splitlines() if line.strip()}
        except (OSError, ValueError, ImagingError, subprocess.SubprocessError) as exc:
            raise ImagingError("Cannot safely enumerate system disks: " + str(exc)) from exc
        found = []
        for disk in inventory:
            if disk.get("type") != "disk":
                continue
            nodes = list(descendants(disk))
            device = disk.get("path") or disk["name"]
            mountpoints = sorted({m for n in nodes for m in mounts(n)})
            protected = any(is_system_mount(m) for m in mountpoints)
            protected |= any(os.path.realpath(n.get("path") or n["name"]) in swap_nodes for n in nodes)
            native = self._native_identity(device) if disk.get("tran") == "usb" else None
            reason = ""
            if protected:
                reason = "Host system disk (root/home/boot/EFI/swap ancestor)"
            elif disk.get("tran") != "usb":
                reason = "Only external USB disks are supported"
            elif mountpoints:
                reason = "Unmount every partition before imaging"
            elif any(n.get("type") not in ("disk", "part") for n in nodes):
                reason = "Mapped, encrypted, RAID or LVM child devices are unsupported"
            elif not native:
                reason = "Cannot read native SSD model/serial through USB bridge"
            found.append({"device": device,
                          "model": native[0] if native else str(disk.get("model") or "").strip(),
                          "serial": native[1] if native else str(disk.get("serial") or "").strip(),
                          "size_bytes": int(disk["size"]), "transport": disk.get("tran") or "",
                          "mountpoints": mountpoints, "eligible": not reason, "reason": reason,
                          "read_only": bool(disk.get("ro")),
                          "sector_size": int(disk.get("log-sec") or 512)})
        return found

    def _drive(self, device, serial, expected=None):
        # Require the exact top-level /dev path, not a partition, alias or file.
        drive = next((d for d in self.drives() if d["device"] == device), None)
        if not drive or not drive["eligible"]:
            raise ImagingError(drive["reason"] if drive else "Device is not an eligible whole USB disk")
        if not serial or drive["serial"] != serial:
            raise ImagingError("Native disk serial changed or does not match confirmation")
        if expected and any(drive[k] != expected[k] for k in ("model", "serial", "size_bytes", "sector_size")):
            raise ImagingError("Disk identity or geometry changed during the job")
        if not stat.S_ISBLK(os.stat(device).st_mode):
            raise ImagingError("Imaging device must be a block device")
        return drive

    def jobs(self):
        jobs = []
        for path in self.job_dir.glob("*.json"):
            try:
                item = json.loads(path.read_text())
                if isinstance(item, dict) and item.get("id") == path.stem:
                    jobs.append(item)
            except (OSError, ValueError):
                continue
        return sorted(jobs, key=lambda j: j.get("started_at", ""), reverse=True)[:100]

    def _image_path(self, image_id):
        if not isinstance(image_id, str) or not SLUG.fullmatch(image_id):
            raise ImagingError("Invalid image ID")
        path = self.repository / image_id
        if path.is_symlink() or path.resolve().parent != self.repository.resolve():
            raise ImagingError("Image directory must be directly inside the repository")
        return path

    def _manifest(self, image_id):
        path = self._image_path(image_id)
        try:
            if (path / "manifest.json").is_symlink():
                raise ImagingError("Manifest symlinks are not permitted")
            value = json.loads((path / "manifest.json").read_text())
        except (OSError, ValueError) as exc:
            raise ImagingError("Cannot read image manifest") from exc
        if value.get("format") != FORMAT or value.get("id") != image_id:
            raise ImagingError("Unsupported or mismatched image manifest")
        return value

    def images(self):
        if not self.repository_online():
            return []
        images = []
        for path in self.repository.iterdir():
            if not path.is_dir() or path.name.startswith("."):
                continue
            try:
                manifest = self._manifest(path.name)
                images.append({k: manifest.get(k) for k in (
                    "id", "label", "profile", "created_at", "status", "minimum_disk_bytes",
                    "size_bytes", "source", "software", "verified", "customer_ready")})
            except ImagingError:
                continue
        return sorted(images, key=lambda i: i.get("created_at", ""), reverse=True)

    def _save(self, job):
        with self._mutex:
            atomic_json(self.job_dir / (job["id"] + ".json"), job)

    def _phase(self, job, phase, progress=None, message=None):
        job.update(phase=phase, progress=progress)
        if message:
            job["log"].append({"at": now(), "message": str(message)[:2000]})
            job["log"] = job["log"][-200:]
        self._save(job)

    def submit(self, payload):
        if os.geteuid() != 0:
            raise ImagingError("Disk imaging requires the root-owned station service")
        if not isinstance(payload, dict):
            raise ImagingError("Job request must be an object")
        operation = payload.get("operation")
        if operation not in ("capture", "restore"):
            raise ImagingError("Operation must be capture or restore")
        device, serial = payload.get("device"), payload.get("serial")
        if not isinstance(device, str) or not device.startswith("/dev/"):
            raise ImagingError("A whole USB disk device is required")
        if not isinstance(serial, str) or payload.get("confirm_serial") != serial:
            raise ImagingError("Type the native SSD serial to confirm this job")
        fd = self._lock()
        try:
            self._require_repository()
            expected = self._drive(device, serial)
            if operation == "restore":
                image_id = payload.get("image_id")
                manifest = self._manifest(image_id)
                self._validate_restore(manifest, expected)
                if not Path(FINALIZER).is_file():
                    raise ImagingError("Target finalizer is not installed")
            else:
                label = payload.get("label", "")
                profile = payload.get("profile", "")
                if not isinstance(label, str) or not label.strip() or len(label) > 128:
                    raise ImagingError("Capture label must contain 1–128 characters")
                if not isinstance(profile, str) or not SLUG.fullmatch(profile):
                    raise ImagingError("A hardware profile slug is required")
                image_id = dt.datetime.now(dt.timezone.utc).strftime("%Y%m%dT%H%M%SZ-") + uuid.uuid4().hex[:8]
            job = {"id": uuid.uuid4().hex, "operation": operation, "status": "queued",
                   "phase": "queued", "progress": None, "device": device, "serial": serial,
                   "image_id": image_id, "started_at": now(), "finished_at": None,
                   "error": None, "log": []}
            self._save(job)
            thread = threading.Thread(target=self._worker, args=(job, dict(payload), expected, fd),
                                      daemon=True, name="imaging-" + job["id"][:8])
            thread.start()
            fd = None  # The worker owns the process lock until every cleanup completes.
            return dict(job)
        finally:
            if fd is not None:
                os.close(fd)

    @contextlib.contextmanager
    def _inhibit(self):
        command = ["systemd-inhibit", "--what=sleep:idle", "--mode=block", "--who=XYZBoxImager",
                   "--why=USB disk imaging in progress", sys.executable, "-c",
                   "import sys; sys.stdin.buffer.read()"]
        with tempfile_log(self.state_dir / "inhibitor.log") as log:
            proc = subprocess.Popen(command, stdin=subprocess.PIPE, stdout=log, stderr=log)
            try:
                time.sleep(0.2)
                if proc.poll() is not None:
                    raise ImagingError("Could not acquire the system sleep inhibitor")
                yield
            finally:
                if proc.stdin:
                    proc.stdin.close()
                try:
                    proc.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    proc.kill()
                    proc.wait()

    def _worker(self, job, payload, expected, fd):
        try:
            with self._inhibit():
                job["status"] = "running"
                self._phase(job, "preflight", 0)
                self._drive(job["device"], job["serial"], expected)
                if job["operation"] == "capture":
                    self._capture(job, payload, expected)
                else:
                    self._restore(job, expected)
                job.update(status="succeeded", phase="complete", progress=100,
                           finished_at=now())
        except BaseException as exc:
            job.update(status="failed", phase="failed", error=str(exc)[:2000], finished_at=now())
            job["log"].append({"at": now(), "message": "Failed: " + str(exc)[:2000]})
        finally:
            try:
                self._save(job)
            finally:
                os.close(fd)

    def _table(self, device):
        table = json.loads(run(["sfdisk", "--json", device]))["partitiontable"]
        if table.get("label") != "gpt" or table.get("unit") != "sectors":
            raise ImagingError("MVP supports GPT partition tables only")
        return table

    def _partition_plan(self, device):
        table = self._table(device)
        disk = next((d for d in self._inventory() if (d.get("path") or d["name"]) == device), None)
        lookup = {n.get("path") or n["name"]: n for n in descendants(disk or {}) if n.get("name")}
        plan = []
        for part in table.get("partitions", []):
            node = part["node"]
            fstype = lookup.get(node, {}).get("fstype")
            if fstype not in FILESYSTEMS:
                raise ImagingError(f"Unsupported partition filesystem: {node} ({fstype or 'unknown'})")
            match = re.fullmatch(re.escape(device) + (r"p(\d+)" if device[-1].isdigit() else r"(\d+)"), node)
            if not match:
                raise ImagingError("Cannot identify partition number")
            number = int(match.group(1))
            plan.append({"number": number, "start": int(part["start"]), "sectors": int(part["size"]),
                         "type": part["type"], "fstype": fstype, "file": f"part-{number}.pcl.zst"})
        if not plan:
            raise ImagingError("No supported partitions found")
        return table, plan

    @staticmethod
    def _partition_node(device, number):
        return device + ("p" if device[-1].isdigit() else "") + str(number)

    def _capture(self, job, payload, expected):
        device = job["device"]
        self._require_repository()
        partial = self.repository / (".partial-" + job["image_id"])
        partial.mkdir(mode=0o700)
        prior_ro = int(run(["blockdev", "--getro", device]).strip())
        changed_ro = False
        try:
            self._drive(device, job["serial"], expected)
            if not prior_ro:
                run(["blockdev", "--setro", device])
                changed_ro = True
            if run(["blockdev", "--getro", device]).strip() != "1":
                raise ImagingError("Source could not be made block read-only")
            table, plan = self._partition_plan(device)
            self._phase(job, "capture-gpt", 3)
            self._drive(device, job["serial"], expected)
            run(["sgdisk", "--backup=" + str(partial / "gpt.bin"), device])
            atomic_json(partial / "partition-table.json", table)
            for index, part in enumerate(plan):
                self._require_repository()
                self._drive(device, job["serial"], expected)
                node = self._partition_node(device, part["number"])
                self._phase(job, "capture-partition-" + str(part["number"]), 5 + index * 55 / len(plan))
                part["partclone_sha256"] = self._clone(node, part["fstype"], partial / part["file"], job)
                part["sha256"] = sha256(partial / part["file"])
                part["compressed_bytes"] = (partial / part["file"]).stat().st_size
            manifest = {"format": FORMAT, "id": job["image_id"], "label": payload["label"].strip(),
                        "profile": payload["profile"], "created_at": now(), "status": "building",
                        "minimum_disk_bytes": expected["size_bytes"], "sector_size": expected["sector_size"],
                        "source": {k: expected[k] for k in ("model", "serial", "size_bytes")},
                        "software": {}, "customer_ready": False, "verified": False,
                        "partitions": plan, "files": {"gpt.bin": sha256(partial / "gpt.bin"),
                            "partition-table.json": sha256(partial / "partition-table.json")}}
            self._phase(job, "verify-image", 65)
            self._verify(partial, manifest, job)
        finally:
            if changed_ro:
                # Never make a different hot-swapped disk writable in cleanup.
                self._drive(device, job["serial"], expected)
                run(["blockdev", "--setrw", device])
        # Publication follows source cleanup too: a failed job never leaves a
        # ready image, even if restoring the source's original RO state failed.
        manifest.update(status="ready", verified=True, verified_at=now(),
                        size_bytes=sum(p.stat().st_size for p in partial.iterdir() if p.is_file()))
        atomic_json(partial / "manifest.json", manifest)
        self._require_repository()
        final = self._image_path(job["image_id"])
        if final.exists():
            raise ImagingError("Image ID already exists")
        os.rename(partial, final)
        self._phase(job, "published", 99, "Image checksums and Partclone CRC verified; original captured unchanged")

    def _clone(self, node, fstype, destination, job):
        log_path = self.state_dir / (job["id"] + ".commands.log")
        with tempfile_log(log_path) as log:
            clone = subprocess.Popen([FILESYSTEMS[fstype], "--clone", "--source", node,
                                      "--output", "-", "--logfile", str(log_path) + ".partclone"],
                                     stdout=subprocess.PIPE, stderr=log)
            compressor = None
            output = None
            digest = hashlib.sha256()
            try:
                # NAS can disconnect between preflight and open(). Keep the
                # already-started Partclone within cleanup on that path too.
                output = destination.open("xb") if destination else None
                if output:
                    compressor = subprocess.Popen(["zstd", "-T0", "-3", "--quiet", "--stdout"],
                                                  stdin=subprocess.PIPE, stdout=output, stderr=log)
                for block in iter(lambda: clone.stdout.read(1024 * 1024), b""):
                    digest.update(block)
                    if compressor:
                        compressor.stdin.write(block)
                clone.stdout.close()
                if compressor:
                    compressor.stdin.close()
                    if compressor.wait() != 0:
                        raise ImagingError("zstd capture failed; see job command log")
                if clone.wait() != 0:
                    raise ImagingError("Partclone capture failed; see job command log")
                if output:
                    output.flush()
                    os.fsync(output.fileno())
                return digest.hexdigest()
            finally:
                for proc in (clone, compressor):
                    if proc and proc.poll() is None:
                        proc.kill()
                        proc.wait()
                with contextlib.suppress(OSError):
                    clone.stdout.close()
                if compressor and compressor.stdin:
                    with contextlib.suppress(OSError):
                        compressor.stdin.close()
                if output:
                    output.close()

    @staticmethod
    def _data_file(directory, filename):
        if not isinstance(filename, str) or Path(filename).name != filename or filename in (".", ".."):
            raise ImagingError("Invalid image data filename")
        path = directory / filename
        if path.is_symlink() or not path.is_file():
            raise ImagingError("Missing or unsafe image data file: " + filename)
        return path

    def _verify(self, directory, manifest, job):
        if manifest.get("format") != FORMAT:
            raise ImagingError("Unsupported image format")
        files = dict(manifest.get("files", {}))
        if set(files) != {"gpt.bin", "partition-table.json"}:
            raise ImagingError("Missing GPT/partition metadata checksums")
        parts = manifest.get("partitions", [])
        if not parts:
            raise ImagingError("Image has no partitions")
        disk_bytes, sector_size = manifest.get("minimum_disk_bytes"), manifest.get("sector_size")
        if not isinstance(disk_bytes, int) or disk_bytes <= 0 or sector_size not in (512, 4096):
            raise ImagingError("Invalid image disk geometry")
        used_ranges = []
        for part in parts:
            if part.get("fstype") not in FILESYSTEMS or not isinstance(part.get("number"), int) or part["number"] < 1:
                raise ImagingError("Unsupported image partition")
            expected_file = f"part-{part['number']}.pcl.zst"
            if part.get("file") != expected_file or expected_file in files:
                raise ImagingError("Duplicate or unexpected partition file")
            start, sectors = part.get("start"), part.get("sectors")
            if (not isinstance(start, int) or not isinstance(sectors, int) or start < 34 or sectors < 1
                    or (start + sectors) * sector_size > disk_bytes):
                raise ImagingError("Invalid image partition geometry")
            if any(start < end and begin < start + sectors for begin, end in used_ranges):
                raise ImagingError("Overlapping image partitions")
            used_ranges.append((start, start + sectors))
            if not re.fullmatch(r"[a-f0-9]{64}", str(part.get("partclone_sha256", ""))):
                raise ImagingError("Missing used-block read-back checksum")
            files[expected_file] = part.get("sha256")
        for filename, expected in files.items():
            self._require_repository()
            path = self._data_file(directory, filename)
            if not isinstance(expected, str) or sha256(path) != expected:
                raise ImagingError("SHA256 mismatch: " + filename)
        for part in parts:
            path = self._data_file(directory, part["file"])
            self._pipe(["zstd", "--decompress", "--quiet", "--stdout", str(path)],
                       ["partclone.chkimg", "--source", "-", "--logfile",
                        str(self.state_dir / (job["id"] + ".check.log"))], job,
                       expected_sha256=part["partclone_sha256"])

    def _validate_restore(self, manifest, drive):
        if manifest.get("status") != "ready" or manifest.get("verified") is not True:
            raise ImagingError("Only verified ready images can be restored")
        minimum = manifest.get("minimum_disk_bytes")
        if not isinstance(minimum, int) or minimum <= 0 or drive["size_bytes"] < minimum:
            raise ImagingError("Target is smaller than the image's actual minimum disk size")
        if drive["sector_size"] != manifest.get("sector_size"):
            raise ImagingError("Target and image logical sector sizes differ")
        if drive.get("read_only"):
            raise ImagingError("Restore target is read-only")
        if drive.get("serial") == manifest.get("source", {}).get("serial"):
            raise ImagingError("Refusing to overwrite this image's source SSD; insert a different target")

    def _restore(self, job, expected):
        self._require_repository()
        manifest = self._manifest(job["image_id"])
        self._validate_restore(manifest, expected)
        directory = self._image_path(job["image_id"])
        self._phase(job, "verify-before-write", 0)
        self._verify(directory, manifest, job)
        device = job["device"]
        self._drive(device, job["serial"], expected)
        self._phase(job, "restore-gpt", 20)
        # Blank/new SSDs often arrive with an empty DOS/MBR label. sgdisk
        # refuses even --load-backup on these unless conversion is explicit.
        # The operator already confirmed whole-target replacement and serial.
        run(["sgdisk", "--mbrtogpt", "--load-backup=" + str(directory / "gpt.bin"), device])
        self._drive(device, job["serial"], expected)
        # Move backup GPT to the physical end on larger targets, without growing FS.
        run(["sgdisk", "--move-second-header", device])
        run(["partprobe", device])
        run(["udevadm", "settle", "--timeout=15"])
        restored_table = self._table(device)
        actual_parts = restored_table.get("partitions", [])
        for part in manifest["partitions"]:
            node = self._partition_node(device, part["number"])
            actual = next((p for p in actual_parts if p["node"] == node), None)
            if not actual or (int(actual["start"]), int(actual["size"])) != (part["start"], part["sectors"]):
                raise ImagingError("Restored GPT geometry does not match manifest")
        parts = manifest["partitions"]
        for index, part in enumerate(parts):
            self._require_repository()
            self._drive(device, job["serial"], expected)
            node = self._partition_node(device, part["number"])
            self._phase(job, "restore-partition-" + str(part["number"]), 25 + index * 35 / len(parts))
            self._pipe(["zstd", "--decompress", "--quiet", "--stdout", str(directory / part["file"])],
                       ["partclone.restore", "--source", "-", "--overwrite", node,
                        "--logfile", str(self.state_dir / (job["id"] + ".restore.log"))], job)
        run(["sync"], timeout=120)
        self._drive(device, job["serial"], expected)
        run(["blockdev", "--flushbufs", device])
        for index, part in enumerate(parts):
            self._drive(device, job["serial"], expected)
            node = self._partition_node(device, part["number"])
            self._phase(job, "read-back-partition-" + str(part["number"]), 65 + index * 20 / len(parts))
            actual = self._clone(node, part["fstype"], None, job)
            if actual != part.get("partclone_sha256"):
                raise ImagingError("Used-block read-back differs from image on " + node)
            self._fscheck(node, part["fstype"])
        self._drive(device, job["serial"], expected)
        self._phase(job, "finalize-identity-and-boot", 90)
        run([sys.executable, FINALIZER, "--device", device, "--job-id", job["id"],
             "--image-id", job["image_id"]], timeout=600)
        self._drive(device, job["serial"], expected)
        run(["sync"], timeout=120)
        for part in parts:
            self._fscheck(self._partition_node(device, part["number"]), part["fstype"])
        self._phase(job, "verified", 99, "Used-block read-back, filesystem checks and target finalization passed")

    @staticmethod
    def _fscheck(node, fstype):
        if fstype == "ext4":
            run(["e2fsck", "-f", "-n", node], timeout=1800)
        elif fstype == "vfat":
            run(["fsck.fat", "-n", node], timeout=600)

    def _pipe(self, first, second, job, expected_sha256=None):
        with tempfile_log(self.state_dir / (job["id"] + ".commands.log")) as log:
            producer = subprocess.Popen(first, stdout=subprocess.PIPE, stderr=log)
            consumer = None
            try:
                if expected_sha256 is None:
                    consumer = subprocess.Popen(second, stdin=producer.stdout, stdout=log, stderr=log)
                    producer.stdout.close()
                else:
                    consumer = subprocess.Popen(second, stdin=subprocess.PIPE, stdout=log, stderr=log)
                    digest = hashlib.sha256()
                    for block in iter(lambda: producer.stdout.read(1024 * 1024), b""):
                        digest.update(block)
                        consumer.stdin.write(block)
                    producer.stdout.close()
                    consumer.stdin.close()
                second_code = consumer.wait()
                first_code = producer.wait()
                if first_code or second_code:
                    raise ImagingError(f"{Path(first[0]).name} | {Path(second[0]).name} failed "
                                       f"({first_code}/{second_code}); see job command log")
                if expected_sha256 is not None and digest.hexdigest() != expected_sha256:
                    raise ImagingError("Uncompressed Partclone SHA256 mismatch")
            finally:
                for proc in (producer, consumer):
                    if proc and proc.poll() is None:
                        proc.kill()
                        proc.wait()


@contextlib.contextmanager
def tempfile_log(path):
    # Deliberately persistent command logs, not in-memory pipe buffers.
    with Path(path).open("ab", buffering=0) as handle:
        yield handle


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repository", default="/mnt/xyzbox-nas/XYZBoxImages")
    parser.add_argument("--state-dir", default="/var/lib/xyzbox-imager")
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("state")
    for operation in ("capture", "restore"):
        command = sub.add_parser(operation)
        command.add_argument("--device", required=True)
        command.add_argument("--serial", required=True)
        command.add_argument("--wait", action="store_true")
        if operation == "capture":
            command.add_argument("--label", required=True)
            command.add_argument("--profile", required=True)
        else:
            command.add_argument("--image-id", required=True)
    args = parser.parse_args()
    engine = Engine(args.repository, args.state_dir)
    if args.command == "state":
        print(json.dumps({"repository_online": engine.repository_online(), "drives": engine.drives(),
                          "images": engine.images(), "jobs": engine.jobs()}, ensure_ascii=False))
        return 0
    payload = {"operation": args.command, "device": args.device, "serial": args.serial,
               "confirm_serial": args.serial}
    for key in ("label", "profile", "image_id"):
        if hasattr(args, key):
            payload[key] = getattr(args, key)
    job = engine.submit(payload)
    print(json.dumps(job), flush=True)
    # CLI must retain its worker/inhibitor/lock until the job completes, even when
    # --wait is omitted; the HTTP daemon uses submit() directly instead.
    while True:
        current = next(j for j in engine.jobs() if j["id"] == job["id"])
        if current["status"] not in ACTIVE:
            print(json.dumps(current), flush=True)
            return 0 if current["status"] == "succeeded" else 1
        time.sleep(2)


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except ImagingError as exc:
        print(str(exc), file=sys.stderr)
        raise SystemExit(1)
