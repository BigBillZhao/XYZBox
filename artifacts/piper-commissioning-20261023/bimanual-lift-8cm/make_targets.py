import json,math
import numpy as np
from scipy.optimize import least_squares
from scipy.spatial.transform import Rotation
from sdk_constants import ROBOT_MDH_PRESET
homes={'left':[1.216,-2.938,1.732,5.621,14.296,-23.730],'right':[-2.786,-2.310,1.776,-1.117,7.395,3.187]}
def fk(q):
 T=np.eye(4)
 for (d,a,alpha,off),angle in zip(ROBOT_MDH_PRESET['piper'],q):
  ca,sa=np.cos(alpha),np.sin(alpha);ct,st=np.cos(angle+off),np.sin(angle+off)
  T=T@np.array([[ct,-st,0,a],[ca*st,ca*ct,-sa,-sa*d],[sa*st,sa*ct,ca,ca*d],[0,0,0,1]])
 return T[:3,3],T[:3,:3]
lo=np.radians([-149,1,-169,-99,-69,-179]);hi=np.radians([149,179,-1,99,69,179]);out={}
for side,deg in homes.items():
 q0=np.radians(deg);p0,R0=fk(q0);desired=p0+np.array([0,0,.08])
 def residual(q):
  p,R=fk(q);return np.r_[100*(p-desired),10*Rotation.from_matrix(R@R0.T).as_rotvec(),.001*(q-q0)]
 q=least_squares(residual,np.clip(q0,lo+1e-7,hi-1e-7),bounds=(lo,hi),xtol=1e-12,ftol=1e-12,gtol=1e-12,max_nfev=1000).x
 p,R=fk(q);err=float(np.linalg.norm(p-desired));assert err<.0005,(side,err)
 out[side]={'home_rad':q0.tolist(),'home_deg':deg,'target_rad':q.tolist(),'target_deg':np.degrees(q).tolist(),'lift_m':float(p[2]-p0[2]),'position_error_m':err,'orientation_error_deg':float(np.degrees(Rotation.from_matrix(R@R0.T).magnitude()))}
print(json.dumps(out,indent=2))
