#!/usr/bin/env python3
"""Read Nero joints, or explicitly request a joint-space move using pyAgxArm."""
import argparse
from contextlib import contextmanager
import fcntl
import json
import math
import os
from pathlib import Path
import re
import sys
import time

from pyAgxArm import AgxArmFactory, ArmModel, create_agx_arm_config, resolve_firmware_profile

# This is the tested fixture's preparation pose, not a universal factory zero.
HOME = [0.0, 0.35, 0.0, 1.75, 0.0, 0.0, -0.6]


@contextmanager
def controller_lock():
    runtime = Path(f"/run/user/{os.getuid()}")
    if not runtime.is_dir():
        runtime = Path("/tmp")
    # Same lock name as the field LeRobot launcher. Other software must cooperate.
    fd = os.open(runtime / f"nero-teleop-{os.getuid()}.lock", os.O_CREAT | os.O_RDWR, 0o600)
    try:
        try:
            fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError as exc:
            raise RuntimeError("Another cooperating Nero controller is running; stop it before this example.") from exc
        yield
    finally:
        os.close(fd)


def validate_target(target, config):
    if len(target) != 7 or not all(math.isfinite(v) for v in target):
        raise ValueError("Exactly seven finite joint angles in radians are required.")
    for i, value in enumerate(target, 1):
        lo, hi = config["joint_limits"][f"joint{i}"]
        if not lo <= value <= hi:
            raise ValueError(f"Joint {i}: {value} is outside SDK limits [{lo}, {hi}].")


def discover_firmware(channel, interface="socketcan"):
    """Only request firmware. Never enable motors while identifying the device."""
    config = create_agx_arm_config(robot=ArmModel.NERO, channel=channel, interface=interface)
    probe = AgxArmFactory.create_arm(config)
    try:
        probe.connect()
        # Nero 1.12 broadcasts feedback at power-up. Do not queue CAN requests
        # on a disconnected bus: controllers may otherwise keep retrying them.
        wait_feedback(probe, timeout=1.5)
        for _ in range(3):
            value = probe.get_firmware(timeout=1.0, min_interval=0.0)
            if value and value.get("software_version"):
                return value["software_version"]
        raise TimeoutError(f"{channel}: no firmware reply after three queries; do not infer success from TX echo.")
    finally:
        probe.disconnect()


def wait_feedback(robot, timeout=3.0):
    end = time.monotonic() + timeout
    while time.monotonic() < end:
        joint = robot.get_joint_angles()
        status = robot.get_arm_status()
        if joint is not None and status is not None:
            q = list(joint.msg)
            if len(q) == 7 and all(math.isfinite(v) for v in q):
                return joint, status
        time.sleep(.02)
    raise TimeoutError("No complete joint/status feedback; no motion will be requested.")


def run(channels, target=None, speed=10, timeout=30.0, interface="socketcan"):
    """interface='virtual' is used by tests; the CLI only exposes SocketCAN."""
    if not 1 <= speed <= 20 or not math.isfinite(timeout) or not 0 < timeout <= 120:
        raise ValueError("speed must be 1..20 percent and timeout must be in (0, 120] seconds")
    robots = []
    report = {}
    try:
        # Identify and validate EVERY selected arm before enabling any of them.
        for channel in channels:
            version = discover_firmware(channel, interface)
            profile = resolve_firmware_profile(ArmModel.NERO, version)
            config = create_agx_arm_config(robot=ArmModel.NERO, firmeware_version=profile,
                                          channel=channel, interface=interface, enable_joint_limits=True)
            if target is not None:
                validate_target(target, config)
            robot = AgxArmFactory.create_arm(config)
            robots.append((channel, robot))
            robot.connect()
            joint, status = wait_feedback(robot)
            report[channel] = {"firmware": version, "profile": profile,
                               "joints_rad": list(joint.msg), "arm_status": str(status.msg.arm_status),
                               "control_mode": str(status.msg.ctrl_mode)}
        if target is None:
            print(json.dumps({"mode": "read_only", "arms": report}, ensure_ascii=False, indent=2))
            return report

        print("Explicit joint-space move requested:", target, "radians; speed", speed, "%", flush=True)
        for channel, robot in robots:
            # Normal status is enum value 0 in the pinned SDK.
            if int(robot.get_arm_status().msg.arm_status) != 0:
                raise RuntimeError(f"{channel}: arm status is not NORMAL; refusing motion")
        for channel, robot in robots:
            if not robot.enable():
                raise RuntimeError(f"{channel}: enable was not confirmed")
            robot.set_speed_percent(speed)
        for _, robot in robots:
            robot.move_j(list(target))

        deadline = time.monotonic() + timeout
        seen = {ch: (None, time.monotonic()) for ch, _ in robots}
        settled = 0
        while time.monotonic() < deadline:
            errors = {}
            for channel, robot in robots:
                joint = robot.get_joint_angles()
                if joint is None:
                    raise RuntimeError(f"{channel}: feedback disappeared")
                stamp, last_change = seen[channel]
                if joint.timestamp != stamp:
                    seen[channel] = (joint.timestamp, time.monotonic())
                elif time.monotonic() - last_change > .5:
                    raise RuntimeError(f"{channel}: joint feedback is stale")
                errors[channel] = max(abs(a-b) for a, b in zip(joint.msg, target))
            settled = settled + 1 if all(e < .03 for e in errors.values()) else 0
            if settled >= 3:
                print(json.dumps({"reached": True, "max_error_rad": errors}, indent=2))
                return errors
            time.sleep(.05)
        raise TimeoutError("Target was not confirmed within timeout; inspect the arm before another command.")
    finally:
        for _, robot in reversed(robots):
            robot.disconnect()
        # Deliberately no disable(): an unsupported raised arm can fall when disabled.
        # Ending this example is not an emergency stop or a certified holding function.


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--channels", nargs="+", default=["can0"])
    modes = parser.add_mutually_exclusive_group()
    modes.add_argument("--read", action="store_true", help="Read only (also the default)")
    modes.add_argument("--home", action="store_true", help="MOVE to this fixture's preset HOME")
    modes.add_argument("--joints", nargs=7, type=float, metavar="RAD", help="MOVE to seven absolute joint angles")
    parser.add_argument("--speed", type=int, default=10, help="1..20 percent; only used for motion")
    parser.add_argument("--timeout", type=float, default=30)
    args = parser.parse_args()
    if len(args.channels) != len(set(args.channels)) or any(not re.fullmatch(r"(?:can|kcan)[0-9]+", c) for c in args.channels):
        parser.error("Use distinct CAN interface names, e.g. --channels can0 can1")
    target = HOME if args.home else args.joints
    try:
        with controller_lock():
            run(args.channels, target, args.speed, args.timeout)
    except (RuntimeError, TimeoutError, ValueError) as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1
    except KeyboardInterrupt:
        print("Interrupted; motor disable was not sent.", file=sys.stderr)
        return 130
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
