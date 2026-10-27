#!/bin/bash
set -euo pipefail
[[ $EUID == 0 ]] || { echo 'Run with sudo'; exit 2; }
source_dir=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)
[[ -f /etc/xyzbox-imager/nas.credentials && ! -L /etc/xyzbox-imager/nas.credentials ]]
[[ $(stat -c '%u:%a' /etc/xyzbox-imager/nas.credentials) == 0:600 ]]
install -d -m 755 /opt/xyzbox-imager /opt/xyzbox-imager/static
install -d -m 700 /var/lib/xyzbox-imager /etc/xyzbox-imager
install -m 644 "$source_dir"/{core.py,server.py,finalize_target.py} /opt/xyzbox-imager/
install -m 644 "$source_dir"/static/{index.html,styles.css,app.js} /opt/xyzbox-imager/static/
install -m 755 "$source_dir/open_ui.sh" /opt/xyzbox-imager/open_ui.sh
install -m 644 "$source_dir/xyzbox-imager.service" /etc/systemd/system/
install -d /mnt/xyzbox-nas
install -m 644 "$source_dir/nas.mount.in" '/etc/systemd/system/mnt-xyzbox\x2dnas.mount'
cat > /etc/udev/rules.d/99-xyzbox-imager.rules <<'RULE'
# Dedicated imaging station: avoid desktop automount during GPT/FS restore.
SUBSYSTEM=="block", ENV{ID_BUS}=="usb", ENV{UDISKS_IGNORE}="1"
RULE
udevadm control --reload-rules
udevadm trigger --subsystem-match=block --action=change
udevadm settle
systemctl daemon-reload
systemctl enable --now 'mnt-xyzbox\x2dnas.mount'
systemctl enable --now xyzbox-imager.service
desktop_user=${1:-${SUDO_USER:-}}
if [[ -n "$desktop_user" && "$desktop_user" != root ]]; then
    operator_home=$(getent passwd "$desktop_user" | cut -d: -f6)
    [[ -d "$operator_home" && $(id -u "$desktop_user") -ge 1000 ]]
    desktop=$(runuser -u "$desktop_user" -- xdg-user-dir DESKTOP)
    install -d -o "$desktop_user" -g "$(id -gn "$desktop_user")" \
        "$operator_home/.local/share/applications" "$operator_home/.config/autostart" "$desktop"
    cat > /var/lib/xyzbox-imager/xyzbox-imager.desktop <<'ENTRY'
[Desktop Entry]
Type=Application
Name=系统镜像工作站
Comment=按项目管理、制作和部署系统镜像
Exec=/opt/xyzbox-imager/open_ui.sh
Icon=drive-harddisk
Terminal=false
Categories=System;
ENTRY
    for dest in "$operator_home/.local/share/applications" "$operator_home/.config/autostart" "$desktop"; do
        install -m 755 -o "$desktop_user" -g "$(id -gn "$desktop_user")" \
            /var/lib/xyzbox-imager/xyzbox-imager.desktop "$dest/xyzbox-imager.desktop"
    done
fi
