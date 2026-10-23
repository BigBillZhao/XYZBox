"""Bounded fan2-only 60% duty trial, restoring the original it8786 settings afterwards."""
import json
from pathlib import Path
import signal
import time

base = next(p for p in Path('/sys/class/hwmon').glob('hwmon*') if (p/'name').read_text().strip() == 'it8786')
cpu = next(p for p in Path('/sys/class/hwmon').glob('hwmon*') if (p/'name').read_text().strip() == 'coretemp')
out = Path('/home/ubuntu/xyzbox-fans-20261023/pwm2-trial-60.json')
original = {n: {k: (base/f'pwm{n}{k}').read_text().strip() for k in ('', '_enable')} for n in (1, 2)}
assert all(v['_enable'] == '0' for v in original.values()), original
result = {'chip': str(base), 'duty': 153, 'original': original, 'samples': []}

def record(stage):
    sample = {'stage': stage, 'time': time.time(), 'cpu_c': int((cpu/'temp1_input').read_text())/1000}
    sample['rpm'] = {str(n): int((base/f'fan{n}_input').read_text()) for n in (1, 2)}
    sample['pwm'] = {str(n): int((base/f'pwm{n}').read_text()) for n in (1, 2)}
    sample['mode'] = {str(n): int((base/f'pwm{n}_enable').read_text()) for n in (1, 2)}
    result['samples'].append(sample)
    out.write_text(json.dumps(result, indent=2)+'\n')
    print(json.dumps(sample), flush=True)
    return sample

def restore(n):
    # Mode 0 first restores full-speed operation, then the ignored duty register.
    (base/f'pwm{n}_enable').write_text(original[n]['_enable'])
    (base/f'pwm{n}').write_text(original[n][''])

def interrupt(signum, frame):
    raise SystemExit(f'signal {signum}')

for sig in (signal.SIGINT, signal.SIGTERM, signal.SIGHUP):
    signal.signal(sig, interrupt)
try:
    sample = record('baseline')
    assert sample['cpu_c'] < 60 and min(sample['rpm'].values()) > 1000
    for n in (2,):
        (base/f'pwm{n}').write_text('153')
        (base/f'pwm{n}_enable').write_text('1')
        for _ in range(6):
            time.sleep(2)
            sample = record(f'pwm{n}-60pct')
            assert sample['cpu_c'] < 65 and min(sample['rpm'].values()) > 500, sample
        restore(n)
        time.sleep(3)
        record(f'pwm{n}-restored')
finally:
    for n in (1, 2):
        restore(n)
    result['restored'] = {str(n): {k: (base/f'pwm{n}{k}').read_text().strip() for k in ('', '_enable')} for n in (1, 2)}
    out.write_text(json.dumps(result, indent=2)+'\n')
    print(json.dumps({'restored': result['restored']}), flush=True)
