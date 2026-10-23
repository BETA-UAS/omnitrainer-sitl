"""Standalone JSBSim comparison at the real log's 24 m/s cruise condition."""
import argparse,json,math
from pathlib import Path
import jsbsim
parser=argparse.ArgumentParser();parser.add_argument('--seconds',type=float,default=60);parser.add_argument('--throttle',type=float,default=.245);parser.add_argument('--elevator',type=float,default=None);parser.add_argument('--hold-level',action='store_true');parser.add_argument('--hold-roll',action='store_true');args=parser.parse_args()
p=Path(__file__).resolve().parents[1]/'assets/ardupilot/aircraft'
f=jsbsim.FGFDMExec(None);f.set_debug_level(0);f.set_aircraft_path(str(p));f.set_engine_path(str(p/'Omni-Trainer/Engines'));assert f.load_model('Omni-Trainer');f.set_dt(.01)
f['ic/h-sl-ft']=1500;f['ic/vc-kts']=24/.514444;f['ic/lat-geod-deg']=-7.34;f['ic/theta-deg']=1.3;f.run_ic();f['propulsion/engine/set-running']=1;f['fcs/engine-enabled-norm']=1;f['fcs/throttle-cmd-norm']=args.throttle
rows=[];gamma_int=0.0
for i in range(int(args.seconds/.01)):
 if args.elevator is not None:f['fcs/elevator-cmd-norm']=args.elevator
 if args.hold_level:
  gamma_int=max(-30,min(30,gamma_int+.01*f['flight-path/gamma-deg']))
  f['fcs/elevator-cmd-norm']=max(-.4,min(.4,.15*f['flight-path/gamma-deg']+.01*gamma_int+.7*f['velocities/q-rad_sec']))
 if args.hold_roll:f['fcs/aileron-cmd-norm']=max(-.3,min(.3,-.04*f['attitude/phi-deg']-.2*f['velocities/p-rad_sec']))
 f.run()
 if i%100==0:
  rows.append({'t':round(i*.01,1),'eas':f['velocities/vc-kts']*.514444,'tas':f['velocities/vt-fps']*.3048,'h':f['position/h-sl-ft']*.3048,'pitch':f['attitude/theta-deg'],'roll':f['attitude/phi-deg'],'alpha':f['aero/alpha-deg'],'rpm':f['propulsion/engine/engine-rpm'],'thrust_n':f['propulsion/engine/thrust-lbs']*4.44822,'drag_n':-f['forces/fwx-aero-lbs']*4.44822,'lift_n':-f['forces/fwz-aero-lbs']*4.44822,'gamma':f['flight-path/gamma-deg'],'ele':f['fcs/elevator-cmd-norm'],'elev_r':f['fcs/elevator-pos-rad'],'q_deg_s':f['velocities/q-rad_sec']*180/3.14159,'pitch_moment':f['moments/pitch-stab-aero-lbsft']})
print(json.dumps({'mass_kg':f['inertia/mass-slugs']*14.59390294,'first':rows[0],'last':rows[-1],'mid':rows[len(rows)//2]},indent=2))
