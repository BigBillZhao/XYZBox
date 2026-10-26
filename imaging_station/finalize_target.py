#!/usr/bin/env python3
"""Give an offline Ubuntu target unique identity and portable UEFI boot files."""
import argparse
from contextlib import ExitStack
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import uuid


def run(*args, ok=(0,)):
    result = subprocess.run(args, text=True, capture_output=True, timeout=300)
    if result.returncode not in ok:
        raise RuntimeError(f'{args[0]} exited {result.returncode}: '
                           + (result.stdout + '\n' + result.stderr).strip()[-1800:])
    return result.stdout.strip()


def main():
    p = argparse.ArgumentParser()
    p.add_argument('--device', required=True)
    p.add_argument('--job-id', required=True)
    p.add_argument('--image-id', required=True)
    a = p.parse_args()
    assert os.geteuid() == 0
    assert re.fullmatch(r'[a-zA-Z0-9_-]+', a.job_id)
    assert re.fullmatch(r'[a-zA-Z0-9][a-zA-Z0-9_.-]{0,95}', a.image_id)
    # lsblk emits children in JSON only with NAME or --tree. Without NAME it
    # flattens partitions into sibling top-level records, even for one device.
    disk = json.loads(run('lsblk', '-J', '-p', '-o', 'NAME,PATH,TYPE,TRAN,FSTYPE,MOUNTPOINTS', a.device))['blockdevices'][0]
    assert disk['type'] == 'disk' and disk['tran'] == 'usb'
    parts = disk.get('children', [])
    assert len(parts) == 2 and all(not any(p.get('mountpoints') or []) for p in parts)
    rootpart = next(p['path'] for p in parts if p['fstype'] == 'ext4')
    efipart = next(p['path'] for p in parts if p['fstype'] == 'vfat')
    replacements = {}
    for part in parts:
        old = run('blkid', '-s', 'PARTUUID', '-o', 'value', part['path'])
        replacements[part['path']] = old
    oldroot = run('blkid', '-s', 'UUID', '-o', 'value', rootpart)
    oldefi = run('blkid', '-s', 'UUID', '-o', 'value', efipart)
    # No other disk may be mounted through a second path to this USB device.
    assert not any(p.get('mountpoints') and any(p['mountpoints']) for p in parts)
    run('sgdisk', '-G', a.device)
    run('partprobe', a.device)
    run('udevadm', 'settle')
    mapping = {old: run('blkid', '-c', '/dev/null', '-s', 'PARTUUID', '-o', 'value', path)
               for path, old in replacements.items()}
    # tune2fs requires a freshly recorded check before changing UUID on this
    # filesystem. The preceding read-only check does not update that timestamp.
    run('e2fsck', '-f', '-p', rootpart, ok=(0, 1))
    run('tune2fs', '-U', 'random', rootpart)
    run('fatlabel', '-i', efipart, uuid.uuid4().hex[:8])
    mapping[oldroot] = run('blkid', '-c', '/dev/null', '-s', 'UUID', '-o', 'value', rootpart)
    mapping[oldefi] = run('blkid', '-c', '/dev/null', '-s', 'UUID', '-o', 'value', efipart)
    root = Path('/run/xyzbox-imager') / ('target-' + a.job_id)
    root.mkdir(parents=True, exist_ok=False)
    try:
        with ExitStack() as stack:
            run('mount', '-t', 'ext4', '-o', 'nosuid,nodev', rootpart, str(root))
            stack.callback(subprocess.run, ['umount', str(root)], check=True)
            for rel in ('etc', 'etc/ssh', 'var', 'var/lib', 'boot', 'boot/efi'):
                assert (root / rel).is_dir() and not (root / rel).is_symlink(), rel
            assert 'VERSION_ID="24.04"' in (root / 'etc/os-release').read_text()
            run('mount', '-t', 'vfat', '-o', 'nosuid,nodev', efipart, str(root / 'boot/efi'))
            stack.callback(subprocess.run, ['umount', str(root / 'boot/efi')], check=True)
            # GRUB's generated config and EFI search stub refer to filesystem UUIDs.
            paths = [root / 'etc/fstab', root / 'etc/initramfs-tools/conf.d/resume', root / 'boot/grub/grub.cfg']
            paths.extend((root / 'boot/efi/EFI').glob('*/grub.cfg'))
            for path in paths:
                if path.is_file():
                    assert not path.is_symlink()
                    text = path.read_text()
                    for old, new in mapping.items():
                        text = text.replace(old, new)
                    path.write_text(text)
            mid = uuid.uuid4().hex
            hostname = 'yikai-' + mid[:8]
            for rel in ('etc/machine-id', 'var/lib/dbus/machine-id'):
                (root / rel).unlink(missing_ok=True)
            (root / 'etc/machine-id').write_text(mid + '\n')
            (root / 'etc/machine-id').chmod(0o444)
            (root / 'var/lib/dbus').mkdir(exist_ok=True)
            (root / 'var/lib/dbus/machine-id').symlink_to('/etc/machine-id')
            (root / 'etc/hostname').write_text(hostname + '\n')
            hosts = root / 'etc/hosts'
            text = hosts.read_text()
            line = '127.0.1.1\t' + hostname
            text = re.sub(r'^127\.0\.1\.1\s.*$', line, text, flags=re.M) if re.search(r'^127\.0\.1\.1\s', text, re.M) else text.rstrip() + '\n' + line + '\n'
            hosts.write_text(text)
            for key in (root / 'etc/ssh').glob('ssh_host_*_key*'):
                key.unlink()
            run('ssh-keygen', '-A', '-f', str(root))
            ubuntu = root / 'boot/efi/EFI/ubuntu'
            fallback = root / 'boot/efi/EFI/BOOT'
            fallback.mkdir(exist_ok=True)
            assert (ubuntu / 'grubx64.efi').is_file()
            boot = ubuntu / 'shimx64.efi'
            shutil.copy2(boot if boot.exists() else ubuntu / 'grubx64.efi', fallback / 'BOOTX64.EFI')
            for name in ('grubx64.efi', 'mmx64.efi', 'grub.cfg'):
                if (ubuntu / name).exists():
                    shutil.copy2(ubuntu / name, fallback / name)
            info = {'hostname': hostname, 'machine_id': mid, 'image_id': a.image_id,
                    'job_id': a.job_id, 'prepared_at': datetime.now(timezone.utc).isoformat(),
                    'boot_tested': False, 'filesystem_uuid': mapping[oldroot]}
            dest = root / 'var/lib/xyzbox'
            dest.mkdir(exist_ok=True)
            dest.chmod(0o755)
            receipt = dest / 'provisioning.json'
            receipt.write_text(json.dumps(info, ensure_ascii=False, indent=2) + '\n')
            receipt.chmod(0o644)  # Non-secret receipt is a customer-facing diagnostic.
            os.sync()
            print(json.dumps(info))
    finally:
        root.rmdir()


if __name__ == '__main__':
    main()
