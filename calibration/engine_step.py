"""RPM step near cruise; first second is approximately constant airspeed."""
from pathlib import Path
import jsbsim,json
p=Path(__file__).resolve().parents[1]/'assets/ardupilot/aircraft';f=jsbsim.FGFDMExec(None);f.set_debug_level(0);f.set_aircraft_path(str(p));f.set_engine_path(str(p/'Omni-Trainer/Engines'));f.load_model('Omni-Trainer');f.set_dt(.01);f['ic/h-sl-ft']=1500;f['ic/vc-kts']=24/.514444;f['ic/lat-geod-deg']=-7.34;f['ic/theta-deg']=1.3;f.run_ic();f['propulsion/engine/set-running']=1;f['fcs/engine-enabled-norm']=1;f['fcs/throttle-cmd-norm']=.245
gi=0
for i in range(16000):
 gi=max(-30,min(30,gi+.01*f['flight-path/gamma-deg']));f['fcs/elevator-cmd-norm']=max(-.4,min(.4,.15*f['flight-path/gamma-deg']+.01*gi+.7*f['velocities/q-rad_sec']));f['fcs/aileron-cmd-norm']=max(-.3,min(.3,-.04*f['attitude/phi-deg']-.2*f['velocities/p-rad_sec']));f.run()
rows=[]
for i in range(1000):
 f['fcs/throttle-cmd-norm']=.45
 gi=max(-30,min(30,gi+.01*f['flight-path/gamma-deg']));f['fcs/elevator-cmd-norm']=max(-.4,min(.4,.15*f['flight-path/gamma-deg']+.01*gi+.7*f['velocities/q-rad_sec']));f['fcs/aileron-cmd-norm']=max(-.3,min(.3,-.04*f['attitude/phi-deg']-.2*f['velocities/p-rad_sec']));f.run()
 if i%10==0:rows.append({'t':i*.01,'rpm':f['propulsion/engine/engine-rpm'],'eas':f['velocities/vc-kts']*.514444,'thrust_n':f['propulsion/engine/thrust-lbs']*4.44822})
print(json.dumps(rows))
