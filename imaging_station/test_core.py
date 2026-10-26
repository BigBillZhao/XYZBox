"""No real disks, credentials, network, mounts, or privileged writes are used."""
import contextlib
import copy
import hashlib
import json
import os
from pathlib import Path
import stat
import sys
import tempfile
import unittest
from unittest.mock import Mock, patch

try:
    from . import core
except ImportError:
    import core


class CoreTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.repository = self.root / "repository"
        self.repository.mkdir()
        self.engine = core.Engine(str(self.repository), str(self.root / "state"))
        self.drive = {"device": "/dev/sdz", "model": "Native SSD", "serial": "SSD-123",
                      "size_bytes": 1024 * 1024 * 1024, "transport": "usb", "mountpoints": [],
                      "eligible": True, "reason": "", "read_only": False, "sector_size": 512}
        self.payload = {"operation": "capture", "device": "/dev/sdz", "serial": "SSD-123",
                        "confirm_serial": "SSD-123", "label": "Original", "profile": "seavo-piper"}

    def inventory(self, mountpoints=None, children=None, transport="usb"):
        return [{"name": "/dev/sdz", "path": "/dev/sdz", "type": "disk", "size": 1024**3,
                 "model": "USB Bridge", "serial": "BRIDGE-123", "tran": transport,
                 "mountpoints": mountpoints or [], "children": children or [],
                 "log-sec": 512, "ro": False}]

    def enumerate(self, inventory, swaps=None):
        with patch.object(self.engine, "_inventory", return_value=inventory), \
                patch.object(self.engine, "_native_identity", return_value=("Native SSD", "SSD-123")), \
                patch.object(core, "run", return_value='\n'.join(s['name'] for s in (swaps or []))):
            return self.engine.drives()[0]

    def test_system_disk_exclusion_follows_lvm_descendants(self):
        nested = [{"name": "/dev/sdz2", "type": "part", "mountpoints": [], "children": [
            {"name": "/dev/mapper/root", "type": "lvm", "mountpoints": ["/"]}]}]
        drive = self.enumerate(self.inventory(children=nested))
        self.assertFalse(drive["eligible"])
        self.assertIn("system", drive["reason"])

    def test_home_boot_and_efi_are_system_disks(self):
        for mountpoint in ("/home", "/home/shared", "/boot", "/boot/efi", "/efi"):
            with self.subTest(mountpoint=mountpoint):
                self.assertFalse(self.enumerate(self.inventory(mountpoints=[mountpoint]))["eligible"])

    def test_swap_partition_protects_whole_usb_disk(self):
        children = [{"name": "/dev/sdz3", "type": "part", "mountpoints": []}]
        self.assertIn("system", self.enumerate(self.inventory(children=children),
                                               [{"name": "/dev/sdz3"}])["reason"])

    def test_mounted_external_disk_is_not_eligible(self):
        drive = self.enumerate(self.inventory(children=[
            {"name": "/dev/sdz1", "type": "part", "mountpoints": ["/media/user/disk"]}]))
        self.assertFalse(drive["eligible"])
        self.assertIn("Unmount", drive["reason"])

    def test_internal_disk_is_never_eligible(self):
        self.assertFalse(self.enumerate(self.inventory(transport="nvme"))["eligible"])

    def test_native_serial_replaces_enclosure_serial(self):
        drive = self.enumerate(self.inventory())
        self.assertTrue(drive["eligible"])
        self.assertEqual(drive["serial"], "SSD-123")

    def test_native_serial_required_even_for_unmounted_usb(self):
        with patch.object(self.engine, "_inventory", return_value=self.inventory()), \
                patch.object(self.engine, "_native_identity", return_value=None), \
                patch.object(core, "run", return_value=''):
            self.assertFalse(self.engine.drives()[0]["eligible"])

    def test_cifs_is_required_not_local_fallback(self):
        result = {"filesystems": [{"target": str(self.root), "fstype": "ext4", "options": "rw"}]}
        with patch.object(core, "run", side_effect=lambda *_args, **_kwargs: json.dumps(result)):
            self.assertFalse(self.engine.repository_online())
            result["filesystems"][0]["fstype"] = "cifs"
            self.assertTrue(self.engine.repository_online())
            result["filesystems"][0]["options"] = "ro"
            self.assertFalse(self.engine.repository_online())

    def test_missing_repository_does_not_create_local_directory(self):
        missing = self.root / "offline" / "images"
        engine = core.Engine(str(missing), str(self.root / "other-state"))
        self.assertFalse(engine.repository_online())
        self.assertFalse(missing.exists())

    def test_disk_hot_swap_identity_mismatch_aborts(self):
        with patch.object(self.engine, "drives", return_value=[dict(self.drive, serial="SSD-456")]):
            with self.assertRaisesRegex(core.ImagingError, "serial changed"):
                self.engine._drive("/dev/sdz", "SSD-123", self.drive)

    def test_geometry_change_aborts(self):
        with patch.object(self.engine, "drives", return_value=[dict(self.drive, size_bytes=2**30 + 512)]):
            with self.assertRaisesRegex(core.ImagingError, "geometry changed"):
                self.engine._drive("/dev/sdz", "SSD-123", self.drive)

    def test_regular_file_cannot_be_device(self):
        with patch.object(self.engine, "drives", return_value=[self.drive]), \
                patch.object(core.os, "stat", return_value=type("Stat", (), {"st_mode": stat.S_IFREG})()):
            with self.assertRaisesRegex(core.ImagingError, "block device"):
                self.engine._drive("/dev/sdz", "SSD-123")

    def test_explicit_serial_confirmation_required(self):
        with patch.object(core.os, "geteuid", return_value=0):
            payload = dict(self.payload, confirm_serial="BRIDGE-123")
            with self.assertRaisesRegex(core.ImagingError, "native SSD serial"):
                self.engine.submit(payload)
        self.assertEqual(self.engine.jobs(), [])

    def test_process_lock_rejects_concurrent_submission(self):
        fd = self.engine._lock()
        try:
            with patch.object(core.os, "geteuid", return_value=0):
                with self.assertRaises(core.BusyError):
                    self.engine.submit(self.payload)
        finally:
            os.close(fd)

    def test_restart_marks_stale_job_interrupted(self):
        job = {"id": "stale", "status": "running", "started_at": core.now()}
        self.engine._save(job)
        restarted = core.Engine(str(self.repository), str(self.root / "state"))
        self.assertEqual(restarted.jobs()[0]["status"], "interrupted")

    def test_restart_does_not_interrupt_job_owned_by_live_process(self):
        job = {"id": "live", "status": "running", "started_at": core.now()}
        self.engine._save(job)
        fd = self.engine._lock()
        try:
            restarted = core.Engine(str(self.repository), str(self.root / "state"))
            self.assertEqual(restarted.jobs()[0]["status"], "running")
        finally:
            os.close(fd)

    def test_smaller_nominal_capacity_rejected(self):
        manifest = {"status": "ready", "verified": True, "minimum_disk_bytes": 256060514304,
                    "sector_size": 512}
        with self.assertRaisesRegex(core.ImagingError, "smaller"):
            self.engine._validate_restore(manifest, dict(self.drive, size_bytes=256000000000))

    def test_ready_flag_and_sector_size_checked(self):
        manifest = {"status": "building", "verified": True, "minimum_disk_bytes": 1024,
                    "sector_size": 512}
        with self.assertRaisesRegex(core.ImagingError, "ready"):
            self.engine._validate_restore(manifest, self.drive)
        manifest.update(status="ready", sector_size=4096)
        with self.assertRaisesRegex(core.ImagingError, "sector sizes"):
            self.engine._validate_restore(manifest, self.drive)

    def test_image_source_ssd_cannot_be_overwritten(self):
        manifest = {"status": "ready", "verified": True, "minimum_disk_bytes": 1024,
                    "sector_size": 512, "source": {"serial": self.drive["serial"]}}
        with self.assertRaisesRegex(core.ImagingError, "source SSD"):
            self.engine._validate_restore(manifest, self.drive)

    def test_unsafe_image_paths_and_symlinks_rejected(self):
        for image_id in ("../foo", "/tmp/foo", ".hidden", "a/b"):
            with self.assertRaises(core.ImagingError):
                self.engine._image_path(image_id)
        (self.repository / "linked").symlink_to(self.root, target_is_directory=True)
        with self.assertRaises(core.ImagingError):
            self.engine._image_path("linked")
        with self.assertRaises(core.ImagingError):
            self.engine._data_file(self.repository, "../outside")

    def image_fixture(self):
        directory = self.repository / "image1"
        directory.mkdir()
        for filename in ("gpt.bin", "partition-table.json", "part-1.pcl.zst"):
            (directory / filename).write_bytes(b"test-" + filename.encode())
        manifest = {"format": core.FORMAT, "id": "image1", "status": "ready", "verified": True,
                    "minimum_disk_bytes": 1024**3, "sector_size": 512,
                    "files": {f: core.sha256(directory / f) for f in ("gpt.bin", "partition-table.json")},
                    "partitions": [{"number": 1, "start": 2048, "sectors": 8192,
                                    "fstype": "ext4", "file": "part-1.pcl.zst",
                                    "sha256": core.sha256(directory / "part-1.pcl.zst"),
                                    "partclone_sha256": "a" * 64}]}
        core.atomic_json(directory / "manifest.json", manifest)
        return directory, manifest

    def test_corrupt_image_stops_before_any_decompression_or_disk_write(self):
        directory, manifest = self.image_fixture()
        (directory / "part-1.pcl.zst").write_bytes(b"damaged")
        with patch.object(self.engine, "_require_repository"), \
                patch.object(self.engine, "_pipe") as pipe:
            with self.assertRaisesRegex(core.ImagingError, "SHA256 mismatch"):
                self.engine._verify(directory, manifest, {"id": "job"})
            pipe.assert_not_called()

    def test_invalid_geometry_and_missing_readback_hash_stop_before_commands(self):
        directory, manifest = self.image_fixture()
        for changed in ({"sectors": 1024**4}, {"partclone_sha256": "bad"}):
            modified = copy.deepcopy(manifest)
            modified["partitions"][0].update(changed)
            with patch.object(self.engine, "_pipe") as pipe:
                with self.assertRaises(core.ImagingError):
                    self.engine._verify(directory, modified, {"id": "job"})
                pipe.assert_not_called()

    def test_restore_verification_failure_precedes_all_device_mutations(self):
        self.image_fixture()
        job = {"id": "job", "image_id": "image1", "device": "/dev/sdz", "serial": "SSD-123", "log": []}
        with patch.object(self.engine, "_require_repository"), \
                patch.object(self.engine, "_verify", side_effect=core.ImagingError("corrupt image")), \
                patch.object(self.engine, "_drive") as drive, patch.object(core, "run") as command:
            with self.assertRaisesRegex(core.ImagingError, "corrupt"):
                self.engine._restore(job, self.drive)
            command.assert_not_called()
            drive.assert_not_called()

    def test_worker_failure_is_persisted_and_releases_lock(self):
        job = {"id": "failure", "operation": "capture", "status": "queued", "device": "/dev/sdz",
               "serial": "SSD-123", "started_at": core.now(), "log": []}
        fd = self.engine._lock()
        with patch.object(self.engine, "_inhibit", return_value=contextlib.nullcontext()), \
                patch.object(self.engine, "_drive", return_value=self.drive), \
                patch.object(self.engine, "_capture", side_effect=core.ImagingError("CIFS disconnected")):
            self.engine._worker(job, self.payload, self.drive, fd)
        saved = self.engine.jobs()[0]
        self.assertEqual(saved["status"], "failed")
        self.assertIn("CIFS disconnected", saved["error"])
        os.close(self.engine._lock())

    def test_stream_integrity_hash_and_subprocess_exit_codes(self):
        data = b"partclone-stream" * 1000
        source = [sys.executable, "-c", "import sys;sys.stdout.buffer.write(b'partclone-stream'*1000)"]
        sink = [sys.executable, "-c", "import sys;sys.stdin.buffer.read()"]
        self.engine._pipe(source, sink, {"id": "pipe"}, expected_sha256=hashlib.sha256(data).hexdigest())
        with self.assertRaisesRegex(core.ImagingError, "SHA256 mismatch"):
            self.engine._pipe(source, sink, {"id": "pipe"}, expected_sha256="0" * 64)
        bad_source = [sys.executable, "-c", "raise SystemExit(7)"]
        with self.assertRaisesRegex(core.ImagingError, "7/0"):
            self.engine._pipe(bad_source, sink, {"id": "pipe"})

    def test_nas_output_open_failure_reaps_started_partclone(self):
        child = Mock()
        child.poll.return_value = None
        destination = Mock()
        destination.open.side_effect = OSError('NAS disconnected')
        with patch.object(core.subprocess, 'Popen', return_value=child):
            with self.assertRaisesRegex(OSError, 'NAS disconnected'):
                self.engine._clone('/dev/fake', 'ext4', destination, {'id': 'nas-open-failure'})
        child.kill.assert_called_once()
        child.wait.assert_called_once()
        child.stdout.close.assert_called_once()


if __name__ == "__main__":
    unittest.main()
