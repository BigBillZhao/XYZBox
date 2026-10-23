import os,json,time,subprocess,socket,struct,math
from pathlib import Path
base=Path('/home/ubuntu/xyzbox-commissioning-20261023');stamp=time.strftime('%Y%m%d-%H%M%S');out=base/('bimanual-8cm-'+stamp);out.mkdir()
script=base/'install/artifacts/piper-commissioning-20261023/can-diagnostics/driver-review/bimanual_lift_arm.py'

# Read a fresh initial pose on every invocation so the sequence is repeatable.
ss={};current={c:{} for c in ('can0','can1')}
for c in current:
 sock=socket.socket(socket.PF_CAN,socket.SOCK_RAW,socket.CAN_RAW);sock.bind((c,));sock.setblocking(False);ss[c]=sock
until=time.monotonic()+0.7
while time.monotonic()<until:
 for c,sock in ss.items():
  try:packet=sock.recv(16)
  except BlockingIOError:continue
  frame_id,length,payload=struct.unpack('=IB3x8s',packet)
  if frame_id in (0x2A5,0x2A6,0x2A7) and length==8:current[c][frame_id]=payload
for sock in ss.values():sock.close()
for side,c in [('left','can0'),('right','can1')]:
 if len(current[c])!=3:raise RuntimeError(side+' has no complete standard joint feedback')
 q=[v*math.pi/180000 for i in (0x2A5,0x2A6,0x2A7) for v in struct.unpack('>ii',current[c][i])]
 p=base/(side+'-lift-8cm.json');data=json.loads(p.read_text());data['start_rad']=q;p.write_text(json.dumps(data,indent=2))

procs={};readers={};last_live={};done=set()
for side in ['left','right']:
 log=out/(side+'.log');w=log.open('w')
 cmd=['python3','-u',str(script),'--channel',side,'--limits-report',str(base/('angle-limits-'+side+'-01/summary.json')),'--trajectory-report',str(base/(side+'-lift-8cm.json')),'--supported-release-file',str(out/(side+'-supported-release.json')),'--sdk-archive',str(base/'install/vendor/pyAgxArm-1ae40ad.tar.gz'),'--out',str(out/side),'--supported-confirmed','--execute']
 procs[side]=subprocess.Popen(cmd,stdout=w,stderr=subprocess.STDOUT);w.close();readers[side]=log.open();last_live[side]=0
print(json.dumps({'run_dir':str(out),'pids':{k:p.pid for k,p in procs.items()}}),flush=True)
while True:
 for side,r in readers.items():
  for line in r.readlines():
   try:d=json.loads(line)
   except Exception:continue
   if not isinstance(d,dict) or 'event' not in d:continue
   if d['event']=='TRIAL_LIVE' and time.monotonic()-last_live[side]<3:continue
   if d['event']=='TRIAL_LIVE':last_live[side]=time.monotonic()
   print(json.dumps({'arm':side,**d}),flush=True)
  if procs[side].poll() is not None and side not in done:
   done.add(side);print(json.dumps({'arm':side,'exit_code':procs[side].returncode}),flush=True)
 if len(done)==2:break
 time.sleep(.2)
print(json.dumps({'finished':True,'run_dir':str(out),'exit_codes':{k:p.returncode for k,p in procs.items()}}),flush=True)
