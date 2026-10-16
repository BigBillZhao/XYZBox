#!/usr/bin/env python3
"""Configure one allowed interface. Never send an application CAN frame."""
import argparse
import json
from pathlib import Path
import re
import subprocess


def validate_config(config):
    channels = config.get("channels")
    if not isinstance(channels, list) or not channels or len(channels) != len(set(channels)):
        raise ValueError("channels must be a nonempty list of distinct interface names")
    if any(not isinstance(c, str) or not re.fullmatch(r"(?:can|kcan)[0-9]+", c) for c in channels):
        raise ValueError("channels must look like can0 or kcan0")
    if config.get("bitrate") != 1_000_000:
        raise ValueError("This Nero configuration requires classic CAN at 1000000 bit/s")
    sample = config.get("sample_point")
    if not isinstance(sample, (int, float)) or not 0.5 <= sample < 1:
        raise ValueError("sample_point must be in [0.5, 1)")
    return config


def configure(channel, config, run=subprocess.run, output=subprocess.check_output):
    validate_config(config)
    if channel not in config["channels"]:
        print(f"{channel}: not selected in configuration; unchanged")
        return
    link = json.loads(output(["ip", "-j", "-details", "link", "show", "dev", channel], text=True))[0]
    if link.get("linkinfo", {}).get("info_kind") != "can":
        raise ValueError(f"{channel} is not a CAN interface")
    if "UP" in link.get("flags", []):
        info = link["linkinfo"]["info_data"]
        if info.get("bittiming", {}).get("bitrate") != config["bitrate"] or link.get("mtu") != 16:
            raise RuntimeError(f"{channel} is active with different settings; refusing live reconfiguration")
        print(f"{channel}: already up at classic CAN 1 Mbps")
        return
    run(["ip", "link", "set", "dev", channel, "type", "can", "bitrate", str(config["bitrate"]),
         "sample-point", str(config["sample_point"]), "fd", "off"], check=True)
    run(["ip", "link", "set", "dev", channel, "up"], check=True)
    print(f"{channel}: classic CAN 1 Mbps configured; no application frame sent")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("channel")
    parser.add_argument("--config", type=Path, default=Path("/etc/xyzbox-can.json"))
    args = parser.parse_args()
    configure(args.channel, json.loads(args.config.read_text()))


if __name__ == "__main__":
    main()
