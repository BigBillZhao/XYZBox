# Delivered Software and Directories

English | [简体中文](../06-delivery-software.md) · [Home](../../README.md)

Inventory date: October 16, 2026. The customer PC's main entry point is `~/nero-delivery/README.md`, with a desktop copy named `XYZBox-使用说明.md`.
Existing desktop labels and paths below are retained as installed so they can be located on the machine.

## Available components

| Component | Actual location | Description |
|---|---|---|
| IK, controller pose mapping, and state machine | `~/nero-workspace/repos/lerobot/src/lerobot/teleoperators/pico_nero_teleop/` | `placo_kinematics.py`, `pose_mapper.py`, `teleop_state_machine.py`, smoothing, and XR interface |
| Dual-arm teleoperation | Same repository, `teleoperators/bi_pico_nero_teleop/` | Left/right controller and arm configuration, shared XR client |
| Arm execution and compensation | Same repository, `robots/nero_follower/`, `robots/bi_nero_follower/` | CAN SDK adaptation, shared targets, execution loop, Pinocchio gravity compensation |
| Original recording workflow | Same repository, `scripts/lerobot_raw_record.py` | Original keyboard controls, state/action recording, multi-camera capture |
| Model assets | Same repository, `assets/nero/` | URDF, meshes, gripper, and end-effector frames |
| Active SDK | `~/nero-workspace/vendor/pyAgxArm-1ae40ad/` | Pinned sources supporting Nero 1.12 / v112 |
| Installed XRoboToolkit | `/opt/apps/roboticsservice` | PC Service and desktop UI; installed package version 1.0.0.0 |
| XR Python bindings and reference sources | `~/nero-workspace/XRoboToolkit-Teleop-Sample-Python/dependencies/` | Binding sources, headers, and runtime libraries; active Python module version 1.0.2 |
| Python environment | `~/nero-control/.venv-teleop` | Placo 0.9.16, Pinocchio 3.4.0, CPU PyTorch 2.10.0, and other dependencies |
| Camera support | LeRobot camera modules and the active Python environment | Three-camera configuration and device rules; related ROS sources retained for reference |

Project-specific code includes pose mapping, IK integration, state machines, driver adaptation, and recording integration.
Placo, Pinocchio, XRoboToolkit, and other libraries/tools remain third-party components with their original licenses.
A complete ROS runtime is not deployed. Retained ROS sources do not establish that a ROS control path has been validated.

## Customer entry points

- Desktop **关节回位（会运动）** (“Joint home — causes motion”): no camera or headset required; moves to the ready pose and continues PD.
- XRoboToolkit: connect PICO.
- Desktop **双臂遥操与录制** (“Dual-arm teleoperation and recording”): the original workflow, requiring the headset and three explicitly configured cameras.
- Desktop **交付资料** (“Delivery materials”): software inventory, acceptance sample, data archive, and maintenance archive.

Motion is not started automatically at boot. Home and recording launchers are mutually exclusive; exiting their control process ends its PD command loop.

## Network and display

Configuration read during delivery organization on October 16, 2026: management interface `enp2s0` uses DHCP, with address `192.168.110.7/20`.
Device interface `eno1` uses `10.90.0.10/24` and `192.168.10.20/24`, with no gateway and no default route.
The second device-network address reflects the machine's actual configuration and differs from early migration records. Network settings were not changed during organization.
The arm management page is `http://10.90.0.151/` and requires the device-network cable to be connected.
The display fix `video=eDP-1:d` is retained to disable a falsely reported internal panel output; the physical display uses HDMI.

## Organization and retained files

- Preserve `~/nero-workspace` and the existing dependency paths to keep model and shared-library references valid.
- `nero-workspace` still resolves to `~/nero-control/migration-20261014/import/workspace`. Do not delete that target.
- Retired session experiments, old tests, temporary build/test environments, migration snapshots, and old guides were moved to `~/nero-control/maintenance-archive/20261016/`.
- Some old paths remain as compatibility symlinks for access to earlier diagnostics. They are not additional background services.
- The complete acceptance sample is retained: 846 frames, 846 images from each of three cameras, approximately 28.8 seconds. Its archive hash remains
  `4afe0c5b8febbf405f67b60b02d5eee62bf3a2b6e34d63e654ec99fbdd8c6c37`.
- Early state/action-only recordings without images are archived separately from the complete sample.
- New recordings default to `~/nero-data/raw/nero_capture_YYYYMMDD` instead of appending to the acceptance sample.
- Existing SSH public-key access is retained for after-sales maintenance by explicit instruction. Passwords and private keys are not stored in the repository.

## Manifests and rechecks

`~/nero-delivery/manifests/` contains actual software paths/versions, the Python package list, offline checks, and sample checksums.
After organization, 11 key modules, 628 Python files, 42 model resource references, FK, and gravity compensation were checked without connecting to hardware.

The full teleoperation environment and this repository's minimal USB CAN example have different installation scopes.
This repository restores USB CAN and the standalone joint example. Full teleoperation also requires the machine's workspace, models, XR desktop application/bindings, and camera dependencies.
Copying a venv to a different Python version or architecture is not sufficient to restore the full environment.
Workspace and data symlinks in the delivery directory provide navigation, not independent backups. Back up their actual targets before reinstalling.
RT kernel packages, the companion configuration, and source archives are stored separately in `~/nero-delivery/realtime-packages/` and
`~/nero-delivery/realtime-source/`, with another copy kept off the machine.
