"""Open-loop short control pulses about a stabilized JSBSim cruise state."""
from pathlib import Path
import argparse,json,jsbsim
p=argparse.ArgumentParser();p.add_argument('--axis',choices=['roll','pitch','yaw'],required=True);p.add_argument('--input',type=float,default=.4);p.add_argument('--duration',type=float,default=.5);a=p.parse_args()
root=Path(__file__).resolve().parents[1]/'assets/ardupilot/aircraft';f=jsbsim.FGFDMExec(None);f.set_debug_level(0);f.set_aircraft_path(str(root));f.set_engine_path(str(root/'Omni-Trainer/Engines'));f.load_model('Omni-Trainer');f.set_dt(.01);f['ic/h-sl-ft']=1500;f['ic/vc-kts']=24/.514444;f['ic/lat-geod-deg']=-7.34;f['ic/theta-deg']=1.3;f.run_ic();f['propulsion/engine/set-running']=1;f['fcs/engine-enabled-norm']=1;f['fcs/throttle-cmd-norm']=.245
gamma_int=0
for i in range(16000):
 gamma_int=max(-30,min(30,gamma_int+.01*f['flight-path/gamma-deg']))
 f['fcs/elevator-cmd-norm']=max(-.4,min(.4,.15*f['flight-path/gamma-deg']+.01*gamma_int+.7*f['velocities/q-rad_sec']))
 f['fcs/aileron-cmd-norm']=max(-.3,min(.3,-.04*f['attitude/phi-deg']-.2*f['velocities/p-rad_sec']))
 f.run()
ref={k:f[k] for k in ['attitude/phi-deg','attitude/theta-deg','velocities/p-rad_sec','velocities/q-rad_sec','velocities/r-rad_sec','fcs/aileron-cmd-norm','fcs/elevator-cmd-norm','fcs/rudder-cmd-norm','velocities/vc-kts']}
prop={'roll':'fcs/aileron-cmd-norm','pitch':'fcs/elevator-cmd-norm','yaw':'fcs/rudder-cmd-norm'}[a.axis]
records=[]
for i in range(200):
 f[prop]=ref[prop]+(a.input if i*.01<a.duration else 0)
 f.run()
 if i%10==0:records.append({'t':i*.01,'roll':f['attitude/phi-deg'],'pitch':f['attitude/theta-deg'],'p':f['velocities/p-rad_sec']*57.2958,'q':f['velocities/q-rad_sec']*57.2958,'r':f['velocities/r-rad_sec']*57.2958})
rate_key={'roll':'p','pitch':'q','yaw':'r'}[a.axis]
print(json.dumps({'reference':ref,'peak_rate_degs':max(abs(r[rate_key]) for r in records),'records':records},indent=2))
