# Hardware, Wiring, and Identification

English | [简体中文](../02-hardware-and-can.md) · [Home](../../README.md)

## Distinguish the two observed adapters

| Device observed on site | USB identity / driver | Observation |
|---|---|---|
| Four-port adapter used on October 14, with PCAN-compatible firmware | `0c72:0011` / kcan | The driver/firmware combination exposed only two channels. Physical CAN3/CAN4 gave no feedback; moving the cables to CAN1/CAN2 restored communication. |
| M.2 USB four-channel adapter used on October 16 | `395e:0020 KCAN-USB X4` / kcan 1.4.2 | All four interfaces, can0–can3, enumerated correctly. Only CAN1/CAN2 were connected. |

These observations concern specific devices; they do not imply that every `0c72:0011` device has four ports.
The text shown by `lsusb` comes from device descriptors and the USB ID database. A “PEAK” string alone does not identify the actual manufacturer.
M.2 describes a form factor/connection arrangement. This adapter communicates over USB, not as a PCIe CAN controller.
When changing the M.2 slot or carrier board, confirm that the slot provides the USB signals required by the product.

## CAN settings

The verified external interface of the Nero arm uses:

```text
classic CAN (CAN 2.0), 1,000,000 bit/s, sample-point 0.75, MTU 16
```

The motor brand inside Nero does not determine its external bus protocol. Use the controller protocol implemented by the Nero SDK;
do not send bare Damiao motor MIT frames to the complete arm's interface.
The g1wh Damiao bench used CAN FD at 1M/2M. Those settings must not replace the verified Nero configuration.

## Physical wiring

- Connect the arm's CAN-H to H and CAN-L to L on the adapter. Follow the product instructions for ground and isolation.
- Check that terminals grip the conductor rather than insulation. Verify both pinouts when using circular connectors, DB9 connectors, or terminal adapters.
- The exact label and pinout of the new adapter were not fully recorded. **Do not infer pin numbers for other models from this repository.**
- Configure termination for the whole bus topology, normally one 120 Ω resistor at each end. Check the actual adapter manual for built-in termination, switches, and grounding.
- A green arm power indicator reports power/initialization status; it does not prove that CAN-H/L are connected.
- Access to the Ethernet management page does not prove that the USB CAN link works.

## Channels and arm identity

On the current four-channel adapter, physical CAN1/CAN2 map to can0/can1.
The right arm is wired to can0 and the left arm to can1 on this machine. A customer's wiring may differ.

Inspect `ip -details link show type can` and the USB topology first. Enable only connected channels and check passive feedback.
Previously recorded firmware response payloads from the same arm can assist comparison, but do not assume that every firmware version provides a unique, stable serial number.
Record the final mapping between physical port, system interface, and arm identity.

Do not send motion commands to an unidentified channel to guess left/right. The example accepts a channel list and has no built-in left/right assumption.

## Checks after replacing the adapter

```bash
lsusb
lsusb -t
ip -details -statistics link show type can
cat /proc/kcan
```

Enumeration is only the first step. Changes in USB ID, interface names, or channel count require another check of initialization rules and wiring.
Do not transmit probes on unconnected channels: missing ACKs can cause repeated retransmission.

## Pinned sources and wiring references

Driver and arm SDK sources, original documentation, and version checksums are in `vendor/`.
Install the pinned versions from this repository. Check pinouts and electrical specifications against the actual product label and supplied manual.
Third-party source information and original licenses are retained separately in the technical archives.
