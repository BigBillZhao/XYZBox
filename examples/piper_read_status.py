#!/usr/bin/env python3
"""Read standard Piper SDK feedback. Does not enable, move, reset or query firmware."""
import argparse
import json
import math
import re
import time
from pyAgxArm import AgxArmFactory, ArmModel, create_agx_arm_config


def read_arm(channel, profile, timeout):
    config = create_agx_arm_config(robot=ArmModel.PIPER, firmeware_version=profile,
                                   interface="socketcan", channel=channel)
    arm = AgxArmFactory.create_arm(config)
    try:
        arm.connect()
        start = time.monotonic()
        stamp, updates = None, 0
        while time.monotonic() - start < timeout:
            q, status = arm.get_joint_angles(), arm.get_arm_status()
            if q is not None and status is not None and len(q.msg) == 6:
                if q.timestamp != stamp:
                    stamp, updates = q.timestamp, updates + 1
                if updates >= 3 and time.monotonic() - start >= .3:
                    values = list(q.msg)
                    if all(math.isfinite(v) for v in values):
                        return {"channel": channel, "model": "piper", "profile": profile,
                                "joints_rad": values,
                                "joints_deg": [math.degrees(v) for v in values],
                                "enabled": arm.get_joints_enable_status_list(),
                                "status": str(status.msg)}
            time.sleep(.02)
        raise RuntimeError(f"{channel}: no updating six-joint SDK feedback; check power, wiring, bitrate and leader/follower mode")
    finally:
        arm.disconnect()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--channels", nargs="+", default=["can0", "can1"])
    parser.add_argument("--profile", choices=["default", "v183", "v188", "v189"], default="default")
    parser.add_argument("--timeout", type=float, default=3)
    args = parser.parse_args()
    if not 0 < args.timeout <= 30 or len(set(args.channels)) != len(args.channels) or any(not re.fullmatch(r"can[0-9]+", c) for c in args.channels):
        parser.error("Use distinct canN channels and timeout in (0,30].")
    print(json.dumps({"read_only": True, "arms": [read_arm(c, args.profile, args.timeout) for c in args.channels]}, indent=2))


if __name__ == "__main__":
    main()
