#!/usr/bin/env python3
"""Observe real bus RX; optionally request Nero firmware without enabling motors."""
import argparse
from collections import Counter
import json
import time
import can


def probe(channel, seconds=2.0, query=False):
    ids, errors, firmware, echoes = Counter(), Counter(), set(), 0
    with can.Bus(channel=channel, interface="socketcan", fd=True) as bus:
        deadline = time.monotonic() + seconds
        next_query = 0.0
        sent = 0
        while time.monotonic() < deadline:
            now = time.monotonic()
            if query and ids and sent < 3 and now >= next_query:
                bus.send(can.Message(arbitration_id=0x4AF, is_extended_id=False, data=[1]), timeout=.5)
                sent += 1
                next_query = now + .4
            msg = bus.recv(timeout=min(.05, max(0, deadline-time.monotonic())))
            if msg is None:
                continue
            if msg.is_error_frame:
                errors[f"{msg.arbitration_id:x}:{msg.data.hex()}"] += 1
            elif not msg.is_rx:
                echoes += 1
            else:
                ids[f"0x{msg.arbitration_id:03x}"] += 1
                if msg.arbitration_id == 0x4AF:
                    firmware.add(msg.data.hex())
        return {"channel": channel, "real_rx_frames": sum(ids.values()), "ids": dict(ids),
                "error_frames": sum(errors.values()), "error_samples": dict(list(errors.items())[:8]),
                "local_tx_echoes_excluded": echoes, "firmware_requests_sent": sent,
                "firmware_payloads": sorted(firmware)}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("channels", nargs="+")
    parser.add_argument("--seconds", type=float, default=2)
    parser.add_argument("--query-firmware", action="store_true")
    args = parser.parse_args()
    if not 1.5 <= args.seconds <= 30:
        parser.error("--seconds must be between 1.5 and 30")
    results = [probe(ch, args.seconds, args.query_firmware) for ch in args.channels]
    print(json.dumps(results, indent=2))
    return 0 if all(r["real_rx_frames"] > 0 and r["error_frames"] == 0 for r in results) else 2


if __name__ == "__main__":
    raise SystemExit(main())
