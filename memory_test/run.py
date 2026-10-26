#!/usr/bin/env python3
"""Local, bounded RAM-only stressapptest runner with durable status and logs."""
import argparse
from datetime import datetime, timedelta, timezone
import json
import os
from pathlib import Path
import re
import signal
import subprocess
import time

DEFAULT_STATE = '/var/lib/xyzbox-memory-test'


def now():
    return datetime.now(timezone.utc).isoformat(timespec='seconds')


def boot_id():
    return Path('/proc/sys/kernel/random/boot_id').read_text().strip()


def kernel_cursor():
    result = subprocess.run(['journalctl', '-k', '-b', '-n', '0', '--show-cursor', '--no-pager'],
                            text=True, capture_output=True, check=True)
    cursor = re.search(r'-- cursor: (.+)', result.stdout)
    if not cursor:
        raise RuntimeError('Cannot establish the kernel log cursor before testing')
    return cursor[1].strip()


def save(path, data):
    tmp = path.with_suffix('.tmp')
    with tmp.open('w') as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
        f.write('\n')
        f.flush()
        os.fsync(f.fileno())
    tmp.chmod(0o644)
    os.replace(tmp, path)


def read_latest(base):
    return json.loads((base / 'latest/state.json').read_text())


def snapshot():
    mem = {}
    for line in Path('/proc/meminfo').read_text().splitlines():
        key, value = line.split(':', 1)
        if key in ('MemTotal', 'MemAvailable', 'SwapTotal', 'SwapFree'):
            mem[key + '_KiB'] = int(value.split()[0])
    temperatures = {}
    for hw in Path('/sys/class/hwmon').glob('hwmon*'):
        try:
            name = (hw / 'name').read_text().strip()
        except OSError:
            continue
        for sensor in hw.glob('temp*_input'):
            try:
                label_file = sensor.with_name(sensor.name.replace('_input', '_label'))
                label = label_file.read_text().strip() if label_file.exists() else sensor.stem
                temperatures[name + ':' + label] = int(sensor.read_text()) / 1000
            except (OSError, ValueError):
                continue
    return {'at': now(), 'loadavg': os.getloadavg(), 'memory': mem, 'temperatures_c': temperatures}


def status(base):
    state = read_latest(base)
    if state['status'] == 'running':
        alive = Path('/proc/' + str(state['pid'])).exists()
        if alive:
            try:
                alive = Path('/proc/' + str(state['pid']) + '/stat').read_text().split()[21] == state.get('process_start_ticks')
            except OSError:
                alive = False
        if state['boot_id'] != boot_id() or not alive:
            state = dict(state, status='interrupted',
                         error='Host rebooted or runner disappeared; no successful completion record')
    print(json.dumps(state, ensure_ascii=False, indent=2))
    return state


def run(args):
    if os.geteuid() != 0:
        raise RuntimeError('Root is required for locked RAM and kernel log collection')
    base = Path(args.state_dir)
    base.mkdir(parents=True, exist_ok=True)
    current = snapshot()
    if current['memory']['MemAvailable_KiB'] < (args.memory_mb + 1024) * 1024:
        raise RuntimeError('Insufficient free RAM to retain a 1 GiB system reserve')
    run_id = datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')
    directory = base / run_id
    directory.mkdir(mode=0o755)
    link = base / 'latest.new'
    link.unlink(missing_ok=True)
    link.symlink_to(run_id)
    link.replace(base / 'latest')
    started = time.monotonic()
    state = {'run_id': run_id, 'status': 'running', 'pid': os.getpid(), 'boot_id': boot_id(),
             'kernel_cursor': kernel_cursor(),
             'process_start_ticks': Path('/proc/self/stat').read_text().split()[21],
             'hostname': os.uname().nodename, 'started_at': now(), 'requested_seconds': args.seconds,
             'expected_finish_at': (datetime.now(timezone.utc) + timedelta(seconds=args.seconds)).isoformat(timespec='seconds'),
             'memory_mb': args.memory_mb, 'threads': args.threads, 'disk_stress': False,
             'directory': str(directory), 'elapsed_seconds': 0, 'initial': current}
    save(directory / 'state.json', state)
    command = ['/usr/bin/stressapptest', '-s', str(args.seconds), '-M', str(args.memory_mb),
               '-m', str(args.threads), '-W', '--stop_on_errors', '--printsec', '60',
               '-l', str(directory / 'memory.log')]
    # No -f, -d, --findfiles or network workers: all test buffers are in RAM.
    state['command'] = command
    save(directory / 'state.json', state)
    interrupted = False
    child = None

    def terminate(signum, frame):
        nonlocal interrupted
        interrupted = True
        if child is not None and child.poll() is None:
            child.terminate()

    signal.signal(signal.SIGTERM, terminate)
    signal.signal(signal.SIGINT, terminate)
    peaks = {}
    exit_code = None
    error = None
    print(json.dumps({'started': state}), flush=True)
    try:
        with (directory / 'stdout.log').open('w') as output, (directory / 'telemetry.jsonl').open('a') as telemetry:
            child = subprocess.Popen(command, stdout=output, stderr=subprocess.STDOUT)
            next_sample = 0
            while child.poll() is None:
                elapsed = time.monotonic() - started
                if elapsed >= next_sample:
                    sample = snapshot()
                    telemetry.write(json.dumps(sample) + '\n')
                    telemetry.flush()
                    for label, value in sample['temperatures_c'].items():
                        peaks[label] = max(peaks.get(label, value), value)
                    state.update(elapsed_seconds=round(elapsed), latest=sample, peak_temperatures_c=peaks)
                    save(directory / 'state.json', state)
                    print(json.dumps({'elapsed_seconds': state['elapsed_seconds'], 'memory_available_KiB': sample['memory']['MemAvailable_KiB'], 'temperatures_c': sample['temperatures_c']}), flush=True)
                    next_sample = elapsed + 60
                if elapsed > args.seconds + 180:
                    error = 'Memory tool exceeded its deadline'
                    child.terminate()
                    break
                time.sleep(1)
            try:
                exit_code = child.wait(timeout=30)
            except subprocess.TimeoutExpired:
                child.kill()
                exit_code = child.wait()
                error = error or 'Memory tool did not stop normally'
    except BaseException as exc:
        error = str(exc)
    finally:
        if child is not None and child.poll() is None:
            child.kill()
            child.wait()
        kernel = subprocess.run(['journalctl', '-k', '-b', '--after-cursor', state['kernel_cursor'],
                                 '--utc', '--no-pager', '-o', 'short-iso'], text=True, capture_output=True)
        (directory / 'kernel.log').write_text(kernel.stdout + kernel.stderr)
        alerts = [line for line in kernel.stdout.splitlines() if re.search(
            r'hardware error|machine check|\bmce:.*(?:error|bank)|\bedac.*(?:error|uncorrect)|out of memory|oom-kill|segfault|kernel panic|\bBUG:', line, re.I)]
        text = (directory / 'memory.log').read_text(errors='replace') if (directory / 'memory.log').exists() else ''
        passed = (exit_code == 0 and bool(re.search(r'Status:\s*PASS\b', text)) and
                  time.monotonic() - started >= args.seconds - 5 and kernel.returncode == 0 and not alerts and not interrupted and not error)
        state.update(status='passed' if passed else 'interrupted' if interrupted else 'failed',
                     finished_at=now(), elapsed_seconds=round(time.monotonic() - started),
                     exit_code=exit_code, error=error, peak_temperatures_c=peaks,
                     stressapptest_pass=bool(re.search(r'Status:\s*PASS\b', text)),
                     kernel_alerts=alerts, kernel_collection_exit_code=kernel.returncode,
                     coverage='Online test of allocated RAM; excludes RAM occupied by OS/other processes')
        save(directory / 'state.json', state)
        save(directory / 'summary.json', state)
        print(json.dumps({'finished': state}), flush=True)
    return 0 if state['status'] == 'passed' else 1


def finalize(base):
    try:
        state = read_latest(base)
    except FileNotFoundError:
        return
    if state['status'] == 'running':
        state.update(status='interrupted', finished_at=now(),
                     error='systemd stopped the job before a completion record',
                     service_result=os.environ.get('SERVICE_RESULT', 'unknown'))
        directory = Path(state['directory'])
        save(directory / 'state.json', state)
        save(directory / 'summary.json', state)


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('operation', choices=['run', 'status', 'finalize'])
    parser.add_argument('--state-dir', default=DEFAULT_STATE)
    parser.add_argument('--seconds', type=int, default=36000)
    parser.add_argument('--memory-mb', type=int, default=5120)
    parser.add_argument('--threads', type=int, default=4)
    args = parser.parse_args()
    if args.operation == 'run':
        if args.seconds < 10 or args.memory_mb < 128 or args.threads < 1:
            parser.error('Invalid memory test parameters')
        raise SystemExit(run(args))
    elif args.operation == 'status':
        status(Path(args.state_dir))
    else:
        finalize(Path(args.state_dir))
