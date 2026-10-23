"""Five-second CAN receive-only snapshot after changing the kernel."""
from collections import Counter
from datetime import datetime, timezone
import json
import selectors
import socket
import struct
import time

selector = selectors.DefaultSelector()
counts = {ch: Counter() for ch in ("can0", "can1")}
latest = {ch: {} for ch in counts}
errors = {ch: 0 for ch in counts}
for channel in counts:
    sock = socket.socket(socket.PF_CAN, socket.SOCK_RAW, socket.CAN_RAW)
    sock.setsockopt(socket.SOL_CAN_RAW, 2, struct.pack("=I", 0x1FFFFFFF))
    sock.bind((channel,))
    sock.setblocking(False)
    selector.register(sock, selectors.EVENT_READ, channel)
until = time.monotonic() + 5
while time.monotonic() < until:
    for key, _ in selector.select(max(0, until - time.monotonic())):
        raw = key.fileobj.recv(16)
        frame_id, length, payload = struct.unpack("=IB3x8s", raw)
        channel = key.data
        if frame_id & 0x20000000:
            errors[channel] += 1
        frame_id &= 0x1FFFFFFF
        counts[channel][hex(frame_id)] += 1
        if frame_id == 0x2A1 or 0x261 <= frame_id <= 0x266 or 0x2A5 <= frame_id <= 0x2A7:
            latest[channel][hex(frame_id)] = payload[:length].hex()
for key in list(selector.get_map().values()):
    key.fileobj.close()
result = {
    "observed_at": datetime.now(timezone.utc).isoformat(),
    "application_send_calls": 0,
    "counts": counts,
    "error_frames": errors,
    "latest": latest,
    "all_six_disabled": {
        channel: all(
            hex(i) in data and not (bytes.fromhex(data[hex(i)])[5] & 0x40)
            for i in range(0x261, 0x267)
        ) for channel, data in latest.items()
    },
}
print(json.dumps(result, indent=2))
