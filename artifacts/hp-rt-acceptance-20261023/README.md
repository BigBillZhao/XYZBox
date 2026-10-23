# HP clone + PREEMPT_RT + dual-Piper acceptance

- Host: `yikai-21c5e86e`, session address `192.168.110.12`.
- Internal boot disk: HP SSD EX900 Plus M.2 256GB, serial `HASI26340100227`.
- Kernel: `7.0.14-xyzbox-rt`; `/sys/kernel/realtime=1`.
- Scope: user replaced the Fanxiang SSD in the same box with the HP clone and confirmed reaching the desktop. This is not a test of another motherboard's empty UEFI NVRAM.
- Unchanged launcher SHA-256: `f37d6c4dcf568d24beb27ade5636e1665f9003e3a8e672172939ae2a692282db`.
- Unchanged arm controller SHA-256: `eb7702e8193ea875b6f92fa2115a5c2b6df83de0eaf833063521fcae098f43a5`.

Motion run: `/home/ubuntu/xyzbox-commissioning-20261023/bimanual-8cm-20261023-223147`.
Both arms completed the same nominal 8 cm target, 20 s outbound / 8 s hold / 20 s return sequence.
Both `summary.json` files report `trial_success=true`, confirmed return within the configured 3° tolerance and one-second stability window, and `six_drivers_confirmed_disabled`.
Recorded CAN error frame counts are zero. The following passive snapshot also found all twelve driver enable bits clear.

The `left/` and `right/` summaries are the executed controller's outputs, not reconstructed test results.
`boot-and-final-state.json` records the HP identity and final restored fan settings.

Fan discovery found IT8786E at 0xa40. `it87` loaded normally. Only the Super I/O detection step was selected; CPU, IPMI, arbitrary ISA and SMBus/I2C probing were skipped.
`pwm-trial.json` records the first 80% tests; `pwm2-trial-60.json` records the fan2-only follow-up.
Both scripts restore the original full-speed modes. Fan1 control is stable; fan2 has a response but unstable tachometer readings. Physical CPU/chassis mapping remains unconfirmed.
The user-provided Seavo manual, printed page 22 (PDF page 23), identifies connector 33 as CPU_FAN1 and 34 as SYS_FAN1.
Both have separate tach and control pins. This identifies the physical headers, but does not independently prove their Linux channel numbering.
See [fan monitoring](../../docs/10-fan-monitoring.md).
