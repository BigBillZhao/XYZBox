#!/usr/bin/env bash
# Session-specific Clonezilla environment. No source/target disk writes here.
set -euo pipefail
repo=/home/partimag
install -d -m 700 -o user -g user /home/user/.ssh
install -m 600 -o user -g user "$repo/xyzbox/authorized_keys" /home/user/.ssh/authorized_keys
mkdir -p /etc/ssh/sshd_config.d
cat > /etc/ssh/sshd_config.d/00-xyzbox-live.conf <<'EOF'
PasswordAuthentication no
KbdInteractiveAuthentication no
PermitRootLogin no
AllowUsers user
EOF
ssh-keygen -A
/usr/sbin/sshd -t
systemctl restart ssh
hostname xyzbox-clone-live
# Keep the currently assigned source-box LAN address during the offline boot.
# Bind this only to the physically verified NIC; other PCs keep normal DHCP.
for path in /sys/class/net/*; do
    if [[ $(cat "$path/address") == 68:ed:a4:b1:c8:33 ]]; then
        iface=${path##*/}
        ip link set "$iface" up
        ip address replace 192.168.110.12/20 dev "$iface"
        break
    fi
done
date --iso-8601=seconds > "$repo/xyzbox/LIVE-READY"
ip -br address | tee "$repo/xyzbox/live-addresses.txt"
