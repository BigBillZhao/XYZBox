# Nero Joint Control Example

English | [简体中文](../04-nero-example.md) · [Home](../../README.md)

Entry point: [`examples/nero_joint_control.py`](../../examples/nero_joint_control.py).
It uses the pinned official pyAgxArm SDK directly and reads by default.

## Read without enabling

```bash
.venv/bin/python examples/nero_joint_control.py --channels can0 --read
.venv/bin/python examples/nero_joint_control.py --channels can0 can1 --read
```

The sequence is:

1. Passively wait for joint/status feedback. If none arrives, exit without a firmware request to avoid repeated transmission on a disconnected bus.
2. Request firmware up to three times per channel, without enabling or changing the motion mode during detection.
3. Select the protocol through SDK `resolve_firmware_profile`; firmware 1.12 maps to v112.
4. Wait for seven joint angles and arm status, then print the results.

“Read” permits firmware queries, but does not enable the arm, send targets, home, or disable it.
Older firmware ≤1.11 may require CAN feedback to be enabled according to the manufacturer's instructions. Do not blindly enable motion just to pass detection.

## Explicit joint motion

After checking clearance, support, and wiring, the on-site operator runs:

```bash
# One arm:
.venv/bin/python examples/nero_joint_control.py --channels can0 --home --speed 10

# Both arms, using the same joint target:
.venv/bin/python examples/nero_joint_control.py --channels can0 can1 --home --speed 10

# Seven absolute joint angles in radians, not relative increments:
.venv/bin/python examples/nero_joint_control.py --channels can0 \
  --joints 0 0.35 0 1.75 0 0 -0.6 --speed 10 --timeout 30
```

The `--home` target is:

```text
[0, 0.35, 0, 1.75, 0, 0, -0.6] rad
```

This is the fixture's ready pose. **It is not the manufacturer's mechanical zero and does not calibrate or zero encoders.**
Recheck the target if the customer's assembly, coordinate frames, or workspace differ.

The example validates seven finite angles, SDK joint limits, and NORMAL arm status before enabling and calling `move_j`.
`--speed` accepts 1–20 and represents a controller percentage, not rad/s.
Arrival requires every joint error to remain below 0.03 rad for three consecutive samples. Timeout or stale feedback returns an error.

## Exit and hold behavior

The example uses the controller's `move_j` joint position mode; it does not add a 90 Hz MIT/gravity compensation thread.
Completion, an exception, or Ctrl+C closes SDK communication without automatically calling `disable()`, to avoid dropping an unsupported raised arm by disabling it.
An exception, timeout, or Ctrl+C also does not automatically cancel a target already received by the controller.
Closing communication is not an emergency stop, and this example does not establish what the controller watchdog will do or whether the arm will hold after disconnection.
Applications requiring continuous host-side PD must separately validate their control loop and stopping policy.

The new example's motion branch has only been tested offline. Dual-arm home was validated with the existing on-site LeRobot MIT + gravity compensation path.
The new example therefore still needs its own first-use physical acceptance check; these two validation scopes must remain distinct.

## One control source

The example uses `/run/user/<uid>/nero-teleop-<uid>.lock` for the current user, shared with the original on-site launcher.
This lock cannot block CAN programs that ignore it, other users, or other devices. Check for other control sources before running.

The example does not operate grippers, cameras, PICO, arm network addresses, or device firmware.
