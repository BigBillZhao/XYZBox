"""Offline, read-only inspection of the explicitly named HP test SSD."""
from contextlib import ExitStack
from datetime import datetime, timezone
import json
from pathlib import Path
import subprocess
import sys


def run(*args):
    return subprocess.check_output(args, text=True).strip()


device, expected_serial, job_id = sys.argv[1:]
smart = json.loads(run('smartctl', '-j', '-i', '-d', 'sntasmedia', device))
assert smart['serial_number'] == expected_serial
tree = json.loads(run('lsblk', '-J', '-p', '-o', 'NAME,PATH,TYPE,TRAN,FSTYPE,MOUNTPOINTS', device))['blockdevices'][0]
assert tree['tran'] == 'usb' and len(tree['children']) == 2
assert not any(m for p in tree['children'] for m in (p['mountpoints'] or []))
rootpart = next(p['path'] for p in tree['children'] if p['fstype'] == 'ext4')
efipart = next(p['path'] for p in tree['children'] if p['fstype'] == 'vfat')
rootuuid = run('blkid', '-c', '/dev/null', '-s', 'UUID', '-o', 'value', rootpart)
efiuuid = run('blkid', '-c', '/dev/null', '-s', 'UUID', '-o', 'value', efipart)
root = Path('/run/xyzbox-imager/inspection-' + job_id)
root.mkdir(exist_ok=False)
try:
    with ExitStack() as stack:
        run('mount', '-t', 'ext4', '-o', 'ro,noload,nosuid,nodev', rootpart, str(root))
        stack.callback(subprocess.run, ['umount', str(root)], check=True)
        run('mount', '-t', 'vfat', '-o', 'ro,nosuid,nodev', efipart, str(root / 'boot/efi'))
        stack.callback(subprocess.run, ['umount', str(root / 'boot/efi')], check=True)
        provisioning = json.loads((root / 'var/lib/xyzbox/provisioning.json').read_text())
        assert provisioning['job_id'] == job_id
        assert provisioning['filesystem_uuid'] == rootuuid
        fstab = (root / 'etc/fstab').read_text()
        assert rootuuid in fstab and efiuuid in fstab
        cfgs = ['boot/grub/grub.cfg', 'boot/efi/EFI/ubuntu/grub.cfg', 'boot/efi/EFI/BOOT/grub.cfg']
        for cfg in cfgs:
            text = (root / cfg).read_text()
            assert rootuuid in text and '9a77295f-c637-43ce-95a5-38a845f5c878' not in text
        assert (root / 'boot/efi/EFI/BOOT/BOOTX64.EFI').read_bytes() == (root / 'boot/efi/EFI/ubuntu/shimx64.efi').read_bytes()
        assert (root / 'boot/efi/EFI/BOOT/grubx64.efi').read_bytes() == (root / 'boot/efi/EFI/ubuntu/grubx64.efi').read_bytes()
        for name in ('vmlinuz-7.0.14-xyzbox-rt', 'initrd.img-7.0.14-xyzbox-rt', 'vmlinuz-7.0.0-38-generic'):
            assert (root / 'boot' / name).is_file()
        modules = [line.split('#', 1)[0].strip() for line in (root / 'etc/modules-load.d/xyzbox-hwmon.conf').read_text().splitlines()]
        assert 'it87' in modules
        assert not (root / 'home/ubuntu/.ssh').exists()
        pip = run('chroot', str(root), 'env', 'PYTHONDONTWRITEBYTECODE=1', '/home/ubuntu/yikai-box/.venv/bin/python', '-m', 'pip', 'check')
        sdk = run('chroot', str(root), 'env', 'PYTHONDONTWRITEBYTECODE=1', '/home/ubuntu/yikai-box/.venv/bin/python', '-c', 'from pyAgxArm import ArmModel,resolve_firmware_profile; assert resolve_firmware_profile(ArmModel.PIPER,"S-V1.7-3")=="default"; print("Piper SDK import/profile passed")')
        mod = run('modinfo', '-b', str(root), '-k', '7.0.14-xyzbox-rt', '-F', 'version', 'kcan')
        result = dict(observed_at=datetime.now(timezone.utc).isoformat(), model=smart['model_name'], serial=expected_serial,
                      job_id=job_id, provisioning=provisioning, root_uuid=rootuuid, efi_uuid=efiuuid,
                      fstab_grub_uuid_checks_passed=True, uefi_fallback_checks_passed=True,
                      rt_and_generic_kernels_present=True, kcan_module_version=mod, sdk_check=sdk,
                      pip_check=pip, boot_tested=False,
                      note='Offline checks only; actual cold boot and CAN require Seavo box')
        print(json.dumps(result, ensure_ascii=False, indent=2))
finally:
    root.rmdir()
