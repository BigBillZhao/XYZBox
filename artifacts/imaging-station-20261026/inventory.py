"""Read-only workstation inventory; contains no credential access."""
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import platform
import socket
import subprocess

def cmd(args):
    p = subprocess.run(args, text=True, capture_output=True)
    return {"returncode": p.returncode, "stdout": p.stdout.strip(), "stderr": p.stderr.strip()}

r = {"observed_at": datetime.now(timezone.utc).isoformat(), "hostname": socket.gethostname(),
     "kernel": platform.release(), "architecture": platform.machine(),
     "python": platform.python_version(), "filesystems": {}}
r["cpu_model"] = next(line.split(':', 1)[1].strip() for line in Path('/proc/cpuinfo').read_text().splitlines() if line.startswith('model name'))
r["memory_total_kib"] = int(next(line.split()[1] for line in Path('/proc/meminfo').read_text().splitlines() if line.startswith('MemTotal:')))
for path in ("/", "/home"):
    s = os.statvfs(path)
    r["filesystems"][path] = {"total_bytes": s.f_blocks*s.f_frsize, "available_bytes": s.f_bavail*s.f_frsize}
r["disks"] = json.loads(cmd(["lsblk", "-b", "-J", "-o", "NAME,SIZE,MODEL,SERIAL,TRAN,TYPE,FSTYPE,MOUNTPOINTS"])["stdout"])
r["ethernet_driver"] = cmd(["ethtool", "-i", "enp3s0"])
r["ethernet_link"] = cmd(["ethtool", "enp3s0"])
r["wifi_mac"] = Path("/sys/class/net/wlp5s0/address").read_text().strip()
r["ethernet_mac"] = Path("/sys/class/net/enp3s0/address").read_text().strip()
r["wifi_radio"] = cmd(["nmcli", "radio", "wifi"])
r["host_timezone"] = cmd(["timedatectl", "show", "-p", "Timezone", "--value"])
r["source_system"] = {"mountpoint": "/media/zenbot-alg/9a77295f-c637-43ce-95a5-38a845f5c878",
                       "hostname": "ubuntu", "customer_root_present": False,
                       "it87_autoload_present": False, "rt_kernel_present": True}
print(json.dumps(r, indent=2))
