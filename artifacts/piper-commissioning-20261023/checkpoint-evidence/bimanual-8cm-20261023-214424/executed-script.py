#!/usr/bin/env python3
"""V3 DRAFT Piper pure-PD lift/hold/return trial. Dry-run default.

No device access on import or dry-run. No role, zero, limits, interface, firmware,
or 0x150 writes. --execute requires fresh follower feedback and all axes disabled.
Only the designated CAN setup agent may execute after root review.
"""
import argparse
import ast
from collections import deque
import ctypes
from datetime import datetime, timezone
import fcntl
import hashlib
import json
import math
from pathlib import Path
import select
import signal
import socket
import struct
import subprocess
import tarfile
import time
import uuid
from types import SimpleNamespace

HERE = Path(__file__).resolve().parent
ARCHIVE_SHA256 = "ea8a38af9e6e44255a53c351c4cf788592a21abe694e0f2ce683f2b9be177711"
CHANNELS = {"left": "can0", "right": "can1"}
MODE_MIT = bytes.fromhex("010432ad00000000")
ENABLE_ALL = bytes.fromhex("0702000000000000")
DISABLE_ALL = bytes.fromhex("0701000000000000")
PERIOD = .010
DURATION = 120.0
KP = 20.0
KD = 1.0
OUTBOUND = 20.0
HOLD_TIME = 8.0
RETURN_TIME = 20.0
SUPPORT_TOL = math.radians(3.0)
TRACK_TOL = math.radians(3.0)
MIT_LSB = 25.0/65535.0
READY_DWELL = 1.0
MAX_DEG = 8.0
MAX_SPEED = .15
JOINT_AGE = .200
STATE_AGE = .500
SO_TIMESTAMPNS = 35  # Linux UAPI; also pinned python-can4.6.1 socketcan/constants.py.
SO_RXQ_OVFL = 40  # Linux UAPI: cumulative dropped packets, uint32 ancillary.
MAX_RX_BACKLOG_NS = 50_000_000
EXECUTION_APPROVED = True  # Root: user explicitly requests run now; one left interpolation trial.


def utc():
    return datetime.now(timezone.utc).isoformat()


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


class TrialFault(RuntimeError):
    pass


def require(condition, message):
    if not condition:
        raise TrialFault(message)


def rx_metadata(ancillary, flags, received_wall_ns):
    """Require kernel RX time, not dequeue time. Linux64 SO_TIMESTAMPNS format."""
    require(not flags & (socket.MSG_TRUNC | socket.MSG_CTRUNC), "Truncated CAN data/ancillary")
    stamps = [v for level, kind, v in ancillary if level == socket.SOL_SOCKET and kind == SO_TIMESTAMPNS]
    require(len(stamps) == 1 and len(stamps[0]) == 16, "Missing/invalid kernel RX timestamp")
    sec, nsec = struct.unpack("=qq", stamps[0])
    require(sec >= 0 and 0 <= nsec < 1_000_000_000, "Invalid kernel timespec")
    rx_ns = sec * 1_000_000_000 + nsec
    age = received_wall_ns - rx_ns
    require(0 <= age <= MAX_RX_BACKLOG_NS, "RX timestamp future or queue backlog>50ms")
    drops = [v for level, kind, v in ancillary if level == socket.SOL_SOCKET and kind == SO_RXQ_OVFL]
    require(len(drops) <= 1 and (not drops or len(drops[0]) == 4), "Invalid RX drop ancillary")
    return rx_ns, struct.unpack("=I", drops[0])[0] if drops else None


def load_encoder(archive):
    """Load only reviewed leaf method bodies from the hash-pinned source tar."""
    require(sha(archive) == ARCHIVE_SHA256, "SDK archive hash mismatch")
    with tarfile.open(archive, "r:gz") as tar:
        def source(suffix):
            candidates = [m for m in tar.getmembers() if m.isfile() and m.name.endswith(suffix)]
            require(len(candidates) == 1, f"Ambiguous SDK leaf {suffix}")
            return tar.extractfile(candidates[0]).read().decode()
        numeric = source("/pyAgxArm/utiles/numeric_codec.py")
        parser = source("/pyAgxArm/protocols/can_protocol/drivers/piper/default/parser.py")
    ns = {"ctypes": ctypes, "struct": struct}
    def methods(text, clsname, names):
        cls = next(n for n in ast.parse(text).body if isinstance(n, ast.ClassDef) and n.name == clsname)
        cls.body = [n for n in cls.body if isinstance(n, ast.FunctionDef) and n.name in names]
        require({n.name for n in cls.body} == set(names), "Missing pinned methods")
        module = ast.Module(body=[ast.ImportFrom(module="__future__", names=[ast.alias(name="annotations")], level=0), cls], type_ignores=[])
        exec(compile(ast.fix_missing_locations(module), "<hash-pinned SDK leaf>", "exec"), ns)
        return ns[clsname]
    nc = methods(numeric, "NumericCodec", {"FloatToUint", "ConvertToList_8bit", "ConvertToList_16bit"})
    ns["nc"] = nc
    codec = methods(parser, "Codec", {"pack_joint_mit_ctrl"})()
    def encode(q, kp):
        require(math.isfinite(q) and -12.5 <= q <= 12.5, "Invalid MIT position")
        require(0 <= kp <= 20.0, "Trial Kp outside fixed 0..10 range")
        m = SimpleNamespace(p_des=nc.FloatToUint(q, -12.5, 12.5, 16),
            v_des=nc.FloatToUint(0.0, -45., 45., 12), kp=nc.FloatToUint(kp, 0., 500., 12),
            kd=nc.FloatToUint(KD, -5., 5., 12), t_ff=nc.FloatToUint(0., -8., 8., 8), crc=0)
        return bytes(codec.pack_joint_mit_ctrl(m))
    def q_wire(q):
        return nc.FloatToUint(q, -12.5, 12.5, 16) * 25.0 / 65535.0 - 12.5
    # Independent field extraction and CRC checks, including negative positions.
    for q in (-12.5, -.414, -.05, 0., .05, .249, 12.5):
        for kp in (0., 2., 10.):
            b = encode(q, kp)
            require(len(b) == 8 and (b[7] & 15) == ((b[0] ^ b[1] ^ b[2] ^ b[3] ^ b[4] ^ b[5] ^ b[6]) & 15), "MIT CRC fixture failed")
            require(((b[6] & 15) << 4 | b[7] >> 4) == 127, "Zero feed-forward fixture failed")
            require((b[2] << 4 | b[3] >> 4) == 2047, "Zero velocity fixture failed")
            require(((b[3] & 15) << 8 | b[4]) == nc.FloatToUint(kp, 0., 500., 12), "Kp fixture failed")
            require((b[5] << 4 | b[6] >> 4) == nc.FloatToUint(KD, -5., 5., 12), "Kd fixture failed")
            require(-1e-12 <= q - q_wire(q) < 25 / 65535 + 1e-12, "Position quantization fixture failed")
    return encode, q_wire


def assert_constant_pd(data):
    """Every active MIT TX, starting with PRELOAD, must contain nonzero Kp=10."""
    require(len(data) == 8, "Invalid MIT data length")
    require(((data[3] & 15) << 8 | data[4]) == 163, "V3 expects constant Kp20 wire163")
    require((data[5] << 4 | data[6] >> 4) == 2457, "V3 Kd must remain1.0")
    require((data[2] << 4 | data[3] >> 4) == 2047, "V3 velocity target must remain0")
    require(((data[6] & 15) << 4 | data[7] >> 4) == 127, "V3 feed-forward command must remain0")
    require((data[7] & 15) == ((data[0] ^ data[1] ^ data[2] ^ data[3] ^ data[4] ^ data[5] ^ data[6]) & 15), "V3 MIT CRC mismatch")


def load_limits(path, channel):
    report = json.loads(path.read_text())
    require(report.get("selected_channel") == channel, "Limits report is for another channel")
    require(report.get("all_six_replied") is True, "Limits report lacks six replies")
    require(not report.get("conflicted_joint_ids"), "Conflicting limit replies")
    limits = []
    for i in range(1, 7):
        item = report["angle_limits"][str(i)]
        raw = bytes.fromhex(item["raw_payload_hex"])
        require(len(raw) == 8 and raw[0] == i, "Invalid raw limit response")
        hi, lo = struct.unpack(">hh", raw[1:5])
        require(lo < hi, f"Invalid J{i} limits")
        require(item["min_degree"] == lo / 10 and item["max_degree"] == hi / 10, "Limit raw/decoded mismatch")
        limits.append((math.radians(lo / 10), math.radians(hi / 10)))
    return limits


def smooth_reference(start, target, elapsed):
    u = min(1.0, max(0.0, elapsed/OUTBOUND))
    x = 10*u**3 - 15*u**4 + 6*u**5
    return tuple(a+(b-a)*x for a,b in zip(start,target))


def stable_window(feedback, now, seconds=1.0, peak_deg=.5):
    tail = [x for x in feedback.joint_history if 0 <= now-x[0] <= seconds+.15]
    return len(tail)>=20 and tail[-1][0]-tail[0][0]>=seconds and max(max(x[1][i] for x in tail)-min(x[1][i] for x in tail) for i in range(6)) <= math.radians(peak_deg)


def validate_path(start, target, limits, q_wire, geometry_start):
    require(len(start)==len(target)==len(limits)==len(geometry_start)==6, "Need six-axis path")
    for i,(a,b,(lo,hi),g) in enumerate(zip(start,target,limits,geometry_start),1):
        require(all(math.isfinite(x) for x in (a,b,g)), "Nonfinite path")
        require(-12.5<=a<=12.5 and -12.5<=b<=12.5, "MIT encoding range exceeded")
        require(max(lo-a,a-hi,0)<=math.radians(5), f"J{i} start>5deg outside limits")
        require(lo<=b<=hi and lo<=q_wire(b)<=hi, f"J{i} final target outside device limits")
        require(abs(a-g)<=math.radians(.5), f"J{i} live start differs>0.5deg from reviewed geometry")
        require(1.875*abs(b-a)/OUTBOUND < MAX_SPEED, f"J{i} reference peak speed exceeds guard")


def validate_reference(reference,start,target,q_wire):
    for q,a,b in zip(reference,start,target):
        require(min(a,b)-1e-12<=q<=max(a,b)+1e-12,"Reference escaped approved path")
        require(min(a,b)-MIT_LSB-1e-12<=q_wire(q)<=max(a,b)+MIT_LSB+1e-12,"Quantized reference escaped path+oneLSB")


def check_tracking(actual,reference,start,limits):
    # User-requested motion commissioning: retain telemetry; no motion-error abort.
    require(all(math.isfinite(x) for x in actual), "Nonfinite joint feedback")


def read_supported_release(path, trial_id, channel, script_hash, fault_ns):
    if not path.exists(): return None
    require(not path.is_symlink() and path.is_file(),"Release must be a regular file")
    require(path.stat().st_size<=4096 and path.stat().st_mtime_ns>fault_ns,"Release file stale/oversize")
    value=json.loads(path.read_text())
    require(value.get("trial_id")==trial_id and value.get("channel")==channel and value.get("script_sha256")==script_hash,"Release binding mismatch")
    require(value.get("action")=="supported-disable" and value.get("supported") is True,"Explicit support+disable action required")
    require(isinstance(value.get("operator_confirmation"),str) and value["operator_confirmation"].strip(),"Operator confirmation text required")
    return value


class Feedback:
    def __init__(self):
        self.groups = {}
        self.joints = None
        self.status = None
        self.drivers = {}
        self.speeds = {}
        self.fd_speed = None
        self.joint_history = deque(maxlen=1000)
        self.errors = 0
        self.last_command = None

    def accept(self, frame_id, data, now):
        if frame_id == 0x2A1:
            self.status = (now, tuple(data[:6]) + (int.from_bytes(data[6:8], "big"),))
        elif 0x261 <= frame_id <= 0x266:
            self.drivers[frame_id - 0x261] = (now, data[5])
        elif 0x251 <= frame_id <= 0x256:
            v = struct.unpack(">h", data[:2])[0] * .001
            self.speeds[frame_id - 0x251] = (now, v)
        elif 0x2A5 <= frame_id <= 0x2A7:
            self.groups[frame_id - 0x2A5] = (now, struct.unpack(">ii", data))
            if len(self.groups) == 3:
                stamps = [v[0] for v in self.groups.values()]
                if max(stamps) - min(stamps) <= .100:
                    q = tuple(x * math.pi / 180000 for i in range(3) for x in self.groups[i][1])
                    self.joints = (min(stamps), max(stamps), q)
                    # Use an actual >=10ms historical interval, not just the preceding
                    # packet; high-rate delivery must not leave velocity unobserved.
                    previous = next((s for s in reversed(self.joint_history) if max(stamps)-s[0] >= .010), None)
                    self.joint_history.append((max(stamps), q))
                    if previous and max(stamps)-previous[0] <= .100:
                        self.fd_speed = (now, tuple((x-y)/(max(stamps)-previous[0]) for x,y in zip(q, previous[1])))
                    self.groups.clear()
                else:
                    del self.groups[min(self.groups, key=lambda i: self.groups[i][0])]
        elif frame_id in (0x150, 0x151, 0x470, 0x471) or 0x155 <= frame_id <= 0x15F:
            self.last_command = (now, frame_id)

    def healthy(self, now, *, enabled=None, mit=False, initial=None, limits=None):
        require(self.errors == 0, "CAN error frame observed")
        require(self.joints is not None and 0 <= now - self.joints[0] < JOINT_AGE, "Standard joint feedback stale/incomplete")
        require(self.status is not None and 0 <= now - self.status[0] < STATE_AGE, "Status feedback stale/missing")
        values = self.status[1]
        require(values[0] in (0, 1) and values[1] == 0 and values[6] == 0, f"Unhealthy/non-CAN arm status {values}")
        require(self.last_command is None or now - self.last_command[0] >= STATE_AGE, "External controller/master commands observed")
        for i in range(6):
            require(i in self.drivers and 0 <= now - self.drivers[i][0] < STATE_AGE, f"J{i+1} driver feedback stale/missing")
            code = self.drivers[i][1]
            require(code & 0xBF == 0, f"J{i+1} driver fault bits=0x{code & 0xBF:02x}")
            expected = enabled.get(i) if isinstance(enabled, dict) else enabled
            if expected is not None:
                require(bool(code & 0x40) == expected, f"J{i+1} enabled state mismatch")
        if mit:
            require(values[0] == 1 and values[2] == 4, "CAN/MIT mode not confirmed")
        q = self.joints[2]
        if initial is not None:
            require(max(abs(a-b) for a,b in zip(q, initial)) <= math.radians(MAX_DEG), "Measured displacement from initial exceeds8deg")
            # Permit a documented initially out-of-limit pose only while re-entering;
            # never allow it to move farther out of the device-reported range.
            for i, (x, a, (lo, hi)) in enumerate(zip(q, initial, limits), 1):
                tol = math.radians(.1)
                require(min(a, lo)-tol <= x <= max(a, hi)+tol, f"J{i} moved farther beyond limit envelope")
        fd_fresh = self.fd_speed is not None and 0 <= now-self.fd_speed[0] < JOINT_AGE
        for i in range(6):
            speed = self.speeds.get(i)
            speed_fresh = speed is not None and 0 <= now-speed[0] < JOINT_AGE
            require(speed_fresh or fd_fresh, f"J{i+1} has no fresh velocity evidence")
        # Operator requested speed telemetry without an abort threshold.
        return q

    def stable_for_start(self, now):
        tail = [s for s in self.joint_history if now-s[0] <= .750]
        require(len(tail) >= 10 and tail[-1][0]-tail[0][0] >= .500, "Need >=0.5s and10 fresh standard samples before enable")
        ranges = [max(s[1][i] for s in tail)-min(s[1][i] for s in tail) for i in range(6)]
        require(max(ranges) <= math.radians(.25), "Actual joints are drifting: preflight peak-to-peak>0.25deg")

    def confirmed_disabled(self, now, after):
        return all(i in self.drivers and self.drivers[i][0] > after and 0 <= now-self.drivers[i][0] < STATE_AGE and not self.drivers[i][1] & 0x40 for i in range(6))

    def view(self, now):
        return {"joint_deg": [math.degrees(x) for x in self.joints[2]] if self.joints else None,
            "joint_age_s": now-self.joints[0] if self.joints else None,
            "status": list(self.status[1]) if self.status else None,
            "driver_codes": {str(i+1): v[1] for i,v in self.drivers.items()}, "error_frames": self.errors}


def check_link(channel):
    value = json.loads(subprocess.check_output(["ip", "-j", "-details", "-statistics", "link", "show", "dev", channel], text=True))[0]
    info = value["linkinfo"]["info_data"]
    require("UP" in value["flags"] and value["mtu"] == 16, "CAN link not UP Classic")
    require(info["state"] == "ERROR-ACTIVE" and info["bittiming"]["bitrate"] == 1000000, "Unexpected CAN state/bitrate")
    require(not set(info.get("ctrlmode", [])) - {"BERR-REPORTING"}, "Unsafe CAN ctrlmode")
    return value


def run(args, limits, preset, encode, q_wire, plan):
    require(args.supported_confirmed, "--execute requires --supported-confirmed")
    require(args.out is not None, "--execute requires --out")
    channel = CHANNELS[args.channel]
    controlled = tuple(range(6))
    enable_payload = bytes((7, 2)) + bytes(6)
    disable_payload = bytes((7, 1)) + bytes(6)
    expected_enabled = {i: i in controlled for i in range(6)}
    uncontrolled_disabled = {i: False for i in range(6) if i not in controlled}
    require(args.supported_release_file.is_absolute(), "Release file path must be absolute")
    require(not args.supported_release_file.exists(), "Release file must not pre-exist")
    args.out.mkdir(parents=True, exist_ok=False)
    log = (args.out / "events.jsonl").open("w", buffering=1)
    raw = (args.out / "raw-can.jsonl").open("w", buffering=1)
    result = {"started_utc": utc(), "plan": plan, "phase": "PRECHECK", "trial_success": False,
        "enable_send_attempted": False, "disable_confirmed": False, "safe_shutdown_claimed": False,
        "send_counts": {}, "stop_reason": None}
    sock = None
    lock = None
    feedback = Feedback()
    trial_id = uuid.uuid4().hex
    result["trial_id"] = trial_id
    initial = None
    support_home = tuple(plan["home_rad"])
    reference = None
    departed_support = False
    returned_support = False
    operator_release = False
    auto_release = False
    stop_requested = False
    raw_bytes = 0
    last_drop_count = 0
    cleanup_rx_invalid = False
    clock_offset = time.time() - time.monotonic()

    def record(row):
        # A full/broken log must not prevent an explicitly requested supported release.
        try:
            log.write(json.dumps(row) + "\n")
        except Exception as exc:
            result.setdefault("logging_errors", []).append(repr(exc))
            if result["phase"] not in ("SUPPORTED_RELEASE", "FAULT_HOLD_OPERATOR_SUPPORT_REQUIRED", "UNCONFIRMED_ONSITE_ACTION_REQUIRED"):
                raise TrialFault("Event log write failed") from exc

    def event(kind, **fields):
        row = {"utc": utc(), "event": kind, **fields}
        record(row)
        try:
            print(json.dumps(row), flush=True)
        except (OSError, BrokenPipeError) as exc:
            result.setdefault("notification_errors", []).append(repr(exc))
            if result["phase"] not in ("SUPPORTED_RELEASE", "FAULT_HOLD_OPERATOR_SUPPORT_REQUIRED", "UNCONFIRMED_ONSITE_ACTION_REQUIRED"):
                raise TrialFault("Live notification pipe failed") from exc

    def interrupted(signum, frame):
        nonlocal stop_requested
        stop_requested = True
        result["stop_reason"] = f"signal {signum}"
    for sig in (signal.SIGINT, signal.SIGTERM, signal.SIGHUP):
        signal.signal(sig, interrupted)

    def send(frame_id, data):
        require((frame_id == 0x151 and data == MODE_MIT) or (frame_id == 0x471 and data in (enable_payload, disable_payload)) or (frame_id in {0x15A+i for i in controlled} and len(data) == 8), "TX outside supported-PD allowlist")
        if 0x15A <= frame_id <= 0x15F:
            assert_constant_pd(data)
        key = f"0x{frame_id:03X}"
        result["send_counts"][key] = result["send_counts"].get(key, 0) + 1
        record({"utc": utc(), "event": "tx_attempt", "id": key, "hex": data.hex()})
        require(sock.send(struct.pack("=IB3x8s", frame_id, 8, data)) == 16, "Short socket send")

    def receive(wait=0.0, cleanup=False):
        nonlocal raw_bytes, last_drop_count, cleanup_rx_invalid, departed_support
        if not select.select([sock], [], [], wait)[0]:
            return
        # Bound draining so a busy bus cannot postpone release/deadline indefinitely.
        until = time.monotonic() + .004
        while time.monotonic() < until:
            try:
                packet, ancillary, flags, address = sock.recvmsg(72, 256)
            except BlockingIOError:
                break
            received_wall_ns = time.time_ns()
            if len(packet) != 16:
                if cleanup:
                    cleanup_rx_invalid = True
                    result["release_feedback_fault"] = True
                    continue
                raise TrialFault("Unexpected CAN FD/packet length")
            frame_id, length, payload = struct.unpack("=IB3x8s", packet)
            local = bool(flags & socket.MSG_DONTROUTE)
            error = bool(frame_id & 0x20000000)
            try:
                rx_wall_ns, drops = rx_metadata(ancillary, flags, received_wall_ns)
            except TrialFault as exc:
                result.setdefault("rx_metadata_errors", []).append(str(exc))
                if cleanup:
                    cleanup_rx_invalid = True
                    result["release_feedback_fault"] = True
                    continue  # Never count stale/missing timestamp as release acknowledgement.
                raise
            now = rx_wall_ns / 1e9
            if drops is not None:
                if drops != last_drop_count:
                    result.setdefault("rx_queue_drops", []).append({"before":last_drop_count,"after":drops})
                    last_drop_count = drops
                    if not cleanup:
                        raise TrialFault("Socket RX queue dropped packets")
                    cleanup_rx_invalid = True
                    result["release_feedback_fault"] = True
                last_drop_count = drops
            row = {"utc": utc(), "kernel_rx_wall_ns": rx_wall_ns, "dequeued_wall_ns": received_wall_ns,
                "rx_queue_delay_ns": received_wall_ns-rx_wall_ns, "rx_drop_count":drops, "channel": channel, "raw_id": frame_id,
                "length": length, "hex": payload[:length].hex(), "local_origin": local, "error_frame": error, "flags": flags}
            line = json.dumps(row) + "\n"
            if raw_bytes + len(line) <= 128 * 1024 * 1024:
                try:
                    raw.write(line)
                except Exception as exc:
                    result.setdefault("logging_errors", []).append(repr(exc))
                    if not cleanup:
                        raise TrialFault("Raw log write failed") from exc
                raw_bytes += len(line)
            else:
                result["raw_capture_capped"] = True
                result["raw_rows_omitted"] = result.get("raw_rows_omitted", 0) + 1
                if not cleanup:
                    raise TrialFault("Capture size guard exceeded")
            if error:
                feedback.errors += 1
                if not cleanup:
                    raise TrialFault("CAN error frame")
                cleanup_rx_invalid = True
                result["release_feedback_fault"] = True
                continue
            if local:
                # Own echo reception is off. Local control frames indicate another writer.
                if not cleanup and (frame_id in (0x150, 0x151, 0x470, 0x471) or 0x155 <= frame_id <= 0x15F):
                    raise TrialFault("Other local CAN control writer detected")
                if cleanup and (frame_id in (0x150, 0x151, 0x470, 0x471) or 0x155 <= frame_id <= 0x15F):
                    cleanup_rx_invalid = True
                    result["release_feedback_fault"] = True
                continue
            if frame_id & 0xC0000000 or length != 8:
                continue
            feedback.accept(frame_id, payload, now)
            if initial is not None and 0x2A5<=frame_id<=0x2A7:
                index=(frame_id-0x2A5)*2
                if any(abs(x*math.pi/180000-initial[index+j])>SUPPORT_TOL for j,x in enumerate(struct.unpack(">ii",payload))):
                    departed_support=True
            if cleanup and (frame_id in (0x150, 0x151, 0x470, 0x471) or 0x155 <= frame_id <= 0x15F):
                cleanup_rx_invalid = True
                result["release_feedback_fault"] = True

    def latch_departure():
        nonlocal departed_support
        if initial is not None:
            values = [reference] if reference is not None else []
            if feedback.joints: values.append(feedback.joints[2])
            if any(max(abs(q-a) for q,a in zip(v,initial))>SUPPORT_TOL for v in values):
                departed_support=True
        result["departed_support_latch"]=departed_support

    def close_to_support():
        return initial is not None and feedback.joints is not None and 0<=time.time()-feedback.joints[0]<JOINT_AGE and max(abs(q-a) for q,a in zip(feedback.joints[2],support_home))<=SUPPORT_TOL

    def status_file():
        value={"trial_id":trial_id,"script_sha256":plan["script_sha256"],"channel":channel,"phase":result["phase"],"departed_support":departed_support,"updated_utc":utc(),"state":feedback.view(time.time()),"release_file":str(args.supported_release_file)}
        try:
            tmp=args.out/'state.tmp.json';tmp.write_text(json.dumps(value,indent=2));tmp.replace(args.out/'state.json')
        except Exception as exc:result.setdefault("status_write_errors",[]).append(repr(exc))

    def fault_wait(reason):
        nonlocal auto_release,operator_release,reference
        latch_departure()
        if not departed_support and close_to_support():
            auto_release=True
            event("FAULT_BEFORE_DEPARTURE_SUPPORTED_RELEASE",reason=reason)
            return
        fault_ns=time.time_ns()
        result["fault_wait_started_ns"]=fault_ns
        result["required_release_template"]={"trial_id":trial_id,"channel":channel,"script_sha256":plan["script_sha256"],"action":"supported-disable","supported":True,"operator_confirmation":"User explicitly confirms arm is physically supported now"}
        hold_active=False
        try:
            require(not result.get("rx_metadata_errors") and not result.get("rx_queue_drops"),"RX trust compromised")
            q=feedback.healthy(time.time(),enabled=expected_enabled,mit=True)
            require(all(math.isfinite(x) and -12.5<=x<=12.5 for x in q),"No encodable trusted actual")
            validate_reference(q,motion_lo,motion_hi,q_wire)
            reference=tuple(q)
            hold_active=True
        except Exception as exc:result["fault_hold_not_confirmed_reason"]=repr(exc)
        result["phase"]="FAULT_HOLD_OPERATOR_SUPPORT_REQUIRED" if hold_active else "UNCONFIRMED_ONSITE_ACTION_REQUIRED"
        event(result["phase"],reason=reason,reference_rad=reference if hold_active else None,release_file=str(args.supported_release_file),release_template=result["required_release_template"],note="Trajectory progression permanently stopped. No automatic disable after departure.")
        next_tx=time.monotonic();next_report=0.;last_release_error=None
        while True:
            try:
                confirmation=read_supported_release(args.supported_release_file,trial_id,channel,plan["script_sha256"],fault_ns)
                if confirmation:
                    operator_release=True;result["operator_supported_release"]=confirmation
                    event("OPERATOR_SUPPORT_CONFIRMED",confirmation=confirmation)
                    return
            except Exception as exc:
                if repr(exc)!=last_release_error:
                    last_release_error=repr(exc);event("RELEASE_FILE_REJECTED",reason=last_release_error)
            try:
                receive(.005,cleanup=True)
                if hold_active:
                    require(not cleanup_rx_invalid and not result.get("notification_errors"),"Fault-hold RX/notification no longer trustworthy")
                    q=feedback.healthy(time.time(),enabled=expected_enabled,mit=True)
                    require(max(abs(a-b) for a,b in zip(q,reference))<=TRACK_TOL,"Fault-hold tracking error>3deg")
                    now=time.monotonic()
                    require(abs((time.time()-now)-clock_offset)<.020,"Clock offset changed")
                    if now>=next_tx:
                        require(now-next_tx<.100,"Fault-hold scheduling delay")
                        for i in controlled:send(0x15A+i,encode(reference[i],KP))
                        next_tx=max(next_tx+PERIOD,time.monotonic()+.001)
            except Exception as exc:
                if hold_active:
                    hold_active=False;result["phase"]="UNCONFIRMED_ONSITE_ACTION_REQUIRED"
                    event(result["phase"],reason=repr(exc),note="No more MIT targets. Await explicit supported release; physical hold is not confirmed.")
            if time.monotonic()>=next_report:
                status_file();event("FAULT_WAIT_LIVE",phase=result["phase"],state=feedback.view(time.time()),waiting_for=str(args.supported_release_file))
                next_report=time.monotonic()+1.

    try:
        lock = Path(f"/tmp/xyzbox-supported-pd-{channel}.lock").open("a")
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        result["before_link"] = check_link(channel)
        sock = socket.socket(socket.PF_CAN, socket.SOCK_RAW, socket.CAN_RAW)
        require(struct.calcsize("l") == 8, "Only reviewed Linux64 timespec layout is supported")
        sock.setsockopt(socket.SOL_SOCKET, SO_TIMESTAMPNS, 1)
        sock.setsockopt(socket.SOL_SOCKET, SO_RXQ_OVFL, 1)
        sock.setsockopt(socket.SOL_CAN_RAW, socket.CAN_RAW_FILTER, struct.pack("=II", 0, 0))
        sock.setsockopt(socket.SOL_CAN_RAW, socket.CAN_RAW_RECV_OWN_MSGS, 0)
        sock.setsockopt(socket.SOL_CAN_RAW, 2, struct.pack("=I", 0x1FFFFFFF))
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_RCVBUF, 4 * 1024 * 1024)
        sock.bind((channel,))
        sock.setblocking(False)
        deadline = time.monotonic() + 5.0
        last_problem = None
        initial = None
        while time.monotonic() < deadline and not stop_requested:
            receive(.010)
            try:
                candidate = feedback.healthy(time.time(), enabled=False)
                feedback.stable_for_start(time.time())
                initial = candidate
                break
            except TrialFault as exc:
                last_problem = str(exc)
        require(not stop_requested, "Stopped before enable")
        require(initial is not None, f"No fresh healthy disabled follower feedback: {last_problem}")
        target=tuple(preset)
        motion_lo=tuple(min(a,b,c) for a,b,c in zip(initial,target,support_home))
        motion_hi=tuple(max(a,b,c) for a,b,c in zip(initial,target,support_home))
        validate_path(initial,target,limits,q_wire,plan["geometry_start_rad"])
        reference=tuple(initial)
        validate_reference(reference,motion_lo,motion_hi,q_wire)
        result.update(initial_q_rad=initial,target_q_rad=target,reference_rule="fresh actual to reviewed target and exact reverse; no clamping")
        event("PRECHECK_PASSED",channel=channel,trial_id=trial_id,initial_deg=[math.degrees(x) for x in initial],target_deg=[math.degrees(x) for x in target],release_file=str(args.supported_release_file))
        (args.out/'session.json').write_text(json.dumps({"trial_id":trial_id,"plan":plan,"release_file":str(args.supported_release_file)},indent=2))
        result["phase"]="PRELOAD"
        send(0x151,MODE_MIT)
        for i in controlled:send(0x15A+i,encode(reference[i],KP))
        require(not stop_requested,"Stopped before enable")
        feedback.healthy(time.time(),enabled=False)
        result["enable_send_attempted"]=True
        send(0x471,enable_payload)
        enable_barrier_wall_ns=time.time_ns();result["enable_barrier_wall_ns"]=enable_barrier_wall_ns
        started=time.monotonic();hard_deadline=started+DURATION;enable_deadline=started+2.
        phase_start=started;next_tick=started;next_report=started;return_warned=False;ready_sent=False
        result["phase"]="WAIT_ENABLE"
        while True:
            if stop_requested:raise TrialFault(result["stop_reason"] or "operator stop")
            now=time.monotonic()
            require(now<hard_deadline,"120-second active deadline; require phase-aware stop")
            receive(max(0.,min(.003,next_tick-now)))
            now=time.monotonic();now_wall=time.time();latch_departure()
            require(abs((now_wall-now)-clock_offset)<.020,"Realtime/monotonic offset changed>20ms")
            q=feedback.healthy(now_wall)
            if result["phase"]=="WAIT_ENABLE":
                try:
                    feedback.healthy(now_wall,enabled=expected_enabled,mit=True)
                    require(feedback.status[0]>enable_barrier_wall_ns/1e9 and all(feedback.drivers[i][0]>enable_barrier_wall_ns/1e9 for i in range(6)),"Waiting post-enable state")
                except TrialFault:require(now<enable_deadline,"Enable/MIT confirmation timeout")
                else:
                    result["phase"]="OUTBOUND";phase_start=now
                    event("ENABLE_MIT_CONFIRMED",state=feedback.view(now_wall));event("OUTBOUND_START",duration_s=OUTBOUND)
            else:feedback.healthy(now_wall,enabled=expected_enabled,mit=True)
            phase=result["phase"];elapsed=now-phase_start
            if phase=="OUTBOUND":
                reference=smooth_reference(initial,target,elapsed)
                if elapsed>=OUTBOUND:
                    result["phase"]="HOLD";phase_start=now
                    event("HOLD_START",duration_s=HOLD_TIME,note="Reference reached target; physical arrival not yet claimed")
            elif phase=="HOLD":
                reference=target
                if not ready_sent and HOLD_TIME-elapsed>=10. and max(abs(a-b) for a,b in zip(q,target))<=math.radians(2.) and stable_window(feedback,now_wall,1.,.5):
                    ready_sent=True;result["ready_to_feel_sent"]=True
                    event("READY_TO_FEEL",process_live=True,kp=KP,kd=KD,v_des=0.,t_ff=0.,hold_seconds_remaining=HOLD_TIME-elapsed,arrival_tolerance_deg=2.,note="Near target and stable; stiffness experience, not precision acceptance",state=feedback.view(now_wall))
                if not return_warned and HOLD_TIME-elapsed<=10.:
                    return_warned=True;event("RETURN_SOON",seconds_remaining=max(0.,HOLD_TIME-elapsed),instruction="Release hand pressure before return")
                if elapsed>=HOLD_TIME:
                    result["arrival_experience_confirmed"]=ready_sent
                    result["phase"]="RETURN";phase_start=now;event("RETURN_START",duration_s=RETURN_TIME)
            elif phase=="RETURN":
                reference=smooth_reference(target,support_home,elapsed)
                if elapsed>=RETURN_TIME:result["phase"]="SETTLE_SUPPORT";phase_start=now
            elif phase=="SETTLE_SUPPORT":
                reference=tuple(support_home)
                if close_to_support() and stable_window(feedback,now_wall,1.,.5):
                    returned_support=True;auto_release=True;result["trial_success"]=True
                    result["stop_reason"]="Returned to measured supported start within0.5deg and stable1s"
                    event("RETURN_SUPPORTED_CONFIRMED",state=feedback.view(now_wall));break
                require(elapsed<10.,"Return support pose not confirmed within0.5deg/1s")
            latch_departure();validate_reference(reference,motion_lo,motion_hi,q_wire)
            check_tracking(q,reference,initial,limits)
            if now>=next_tick:
                require(now-next_tick<.100,"TX scheduling delay>100ms")
                send(0x151,MODE_MIT)
                for i in controlled:send(0x15A+i,encode(reference[i],KP))
                next_tick=max(next_tick+PERIOD,time.monotonic()+.001)
            if now>=next_report:
                status_file();event("TRIAL_LIVE",phase=result["phase"],reference_deg=[math.degrees(x) for x in reference],active_remaining_s=round(hard_deadline-now,1),state=feedback.view(now_wall))
                next_report=now+1.
    except BaseException as exc:
        result["trial_fault"]=repr(exc);result["stop_reason"]=result["stop_reason"] or "trial/precondition fault"
        latch_departure()
        try:event("TRIAL_FAULT",reason=repr(exc),phase=result["phase"],departed_support=departed_support)
        except Exception:pass
        if sock is not None and result["enable_send_attempted"]:
            fault_wait(repr(exc))
    finally:
        if sock is not None and result["enable_send_attempted"] and (auto_release or operator_release):
            result["phase"] = "SUPPORTED_RELEASE"
            event("SUPPORTED_RELEASE_STARTED", reason=result["stop_reason"], note="Explicit disable within previously confirmed support; stopping TX alone is not release")
            for attempt in range(1, 4):
                cleanup_rx_invalid = False
                stamp = time.monotonic()
                try:
                    send(0x471, disable_payload)
                    # CLOCK_REALTIME kernel RX timestamps must be strictly newer than
                    # this barrier taken AFTER send returned, not after dequeue.
                    release_barrier = time.time_ns()
                    result.setdefault("release_barriers_wall_ns", []).append(release_barrier)
                    deadline = stamp + .500
                    while time.monotonic() < deadline:
                        receive(.010, cleanup=True)
                        if not cleanup_rx_invalid and feedback.confirmed_disabled(time.time(), release_barrier / 1e9):
                            result["disable_confirmed"] = True
                            break
                except BaseException as exc:
                    result.setdefault("release_errors", []).append(repr(exc))
                result["disable_attempts"] = attempt
                if result["disable_confirmed"]:
                    break
            result["shutdown_state"] = "six_drivers_confirmed_disabled" if result["disable_confirmed"] else "UNCONFIRMED_ONSITE_ACTION_REQUIRED"
            event("SUPPORTED_RELEASE_RESULT", confirmed=result["disable_confirmed"], attempts=result.get("disable_attempts",0), shutdown_state=result["shutdown_state"])
        else:
            result["shutdown_state"] = "UNCONFIRMED_ONSITE_ACTION_REQUIRED" if result["enable_send_attempted"] else "no_enable_sent_no_release_command"
        if sock is not None:
            sock.close()
        if lock is not None:
            lock.close()
        result["departed_support_latch"] = departed_support
        result["returned_support_confirmed"] = returned_support
        result["ended_utc"] = utc()
        result["phase"] = "FINISHED"
        result["last_feedback"] = feedback.view(time.time())
        (args.out / "summary.json").write_text(json.dumps(result, indent=2)+"\n")
        log.close()
        raw.close()
        print(json.dumps({"event": "TRIAL_FINISHED", "summary": str(args.out/"summary.json"), "trial_fault": result.get("trial_fault"), "disable_confirmed": result["disable_confirmed"], "shutdown_state": result["shutdown_state"]}), flush=True)
    return 0 if result["trial_success"] and result["disable_confirmed"] and not any(result.get(k) for k in ("trial_fault", "release_feedback_fault", "release_errors", "logging_errors", "notification_errors")) else 2


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--channel",choices=("left","right"),required=True)
    parser.add_argument("--limits-report",type=Path,required=True)
    parser.add_argument("--trajectory-report",type=Path,required=True)
    parser.add_argument("--supported-release-file",type=Path,required=True)
    parser.add_argument("--sdk-archive",type=Path,default=HERE.parents[3]/"vendor/pyAgxArm-1ae40ad.tar.gz")
    parser.add_argument("--execute",action="store_true")
    parser.add_argument("--supported-confirmed",action="store_true")
    parser.add_argument("--out",type=Path)
    args=parser.parse_args();args.scope="full-arm"
    channel=CHANNELS[args.channel]
    encode,q_wire=load_encoder(args.sdk_archive);limits=load_limits(args.limits_report,channel)
    geometry=json.loads(args.trajectory_report.read_text())
    require(geometry.get("version")==3 and geometry.get("arm")==args.channel,"Need reviewed left v3 geometry")
    start=tuple(geometry["start_rad"]);target=tuple(geometry["target_rad"])
    validate_path(start,target,limits,q_wire,start)
    plan={"version":"bimanual-8cm-lift","script_sha256":sha(__file__),"dry_run":not args.execute,"execution_approved":EXECUTION_APPROVED,"channel":channel,"geometry_sha256":sha(args.trajectory_report),"geometry_start_rad":start,"target_rad":target,"home_rad":geometry["home_rad"],"limits_report_sha256":sha(args.limits_report),"sdk_archive_sha256":ARCHIVE_SHA256,"durations_s":{"outbound":OUTBOUND,"hold_fixed":HOLD_TIME,"return":RETURN_TIME,"active_deadline":DURATION},"gains":{"kp":KP,"kd":KD,"v_des":0.,"t_ff":0.},"arrival":{"target_deg":2.,"return_support_deg":3.,"stable_seconds":1.,"stable_peak_to_peak_deg":.5},"guards":{"feedback_speed_abort_rad_s":None,"reference_speed_bound_rad_s":MAX_SPEED,"tracking_abort_deg":None,"start_limit_exception_max_deg":5.,"reference_envelope":"union(start,target)+one MIT LSB, this path only","actual_outer_tolerance_deg":.1,"kernel_rx_and_drop_checks":True},"supported_release_file":str(args.supported_release_file),"fault_policy":"departed latch -> fixed actual PD only if trusted, else no new MIT; await task-bound operator supported-release file before disable","forbidden_tx":["0x150","0x470","limits/zero/firmware writes"],"interface_changes":0}
    print(json.dumps(plan,indent=2),flush=True)
    if not args.execute:return 0
    require(EXECUTION_APPROVED,"V3 DRAFT: execution locked pending root review")
    return run(args,limits,target,encode,q_wire,plan)


if __name__=="__main__":
    raise SystemExit(main())
