# OMNI Trainer flight-log calibration

Source: `log_59_2026-7-22-15-23-04.bin` (22 July 2026). Full extraction and
flight analysis: `/home/beta-dev/Documents/ChatGPT/OMNI-Trainer/analysis/LAPORAN_OMNI_TRAINER.md`.
Known geometry: 2.7 m span, 0.75 m² wing, inverted V/A-tail, DLE30, fixed
18×10 propeller, 16 kg MTOW. The mass at this flight was not logged; the SITL
baseline remains **15 kg nominal**, comprising 30 lb dry plus 3.1 lb tank fuel.
The old model counted fuel both as a point mass and as tank fuel.

The September 2026 aircraft parameters are mirrored for flight limits:
`ROLL_LIMIT_DEG=30`, `PTCH_LIM_MAX_DEG=20`, `PTCH_LIM_MIN_DEG=-15`,
`AIRSPEED_CRUISE=24`, `AIRSPEED_MIN=19`, `AIRSPEED_MAX=27`,
`RLL2SRV_RMAX=75`, and `PTCH2SRV_RMAX_UP/DN=75`.

| Quantity | Flight-log estimate | JSBSim check |
| --- | ---: | ---: |
| Level EAS near 24.5% throttle | 23.92 m/s | 23.71 m/s |
| Level RPM | 5,568 | 5,547 |
| Level pitch | 1.32° | 1.46° |
| Roll-rate peak for comparable pulse | 62–73°/s | 67°/s (0.5 normalized pulse, 0.5 s) |
| RPM rise time constant | 0.53–0.64 s plus ~0.13 s delay | EFI injector 0.59 s plus 0.13 s; JSBSim 5,548→6,308 RPM in 1 s for 24.5→45% |

The JSBSim check uses a simple flight-path and bank-angle stabilizer in
`bench.py`, not ArduPilot. Commands to reproduce:

```bash
python calibration/bench.py --seconds 180 --throttle .245 --hold-level --hold-roll
python calibration/step_bench.py --axis roll --input .5 --duration .5
python calibration/step_bench.py --axis pitch --input .3 --duration .5
python calibration/engine_step.py
```

The model's effective shaft-power curve and propeller Cp/Ct are jointly
calibrated to cruise RPM, airspeed, and response. They are **not** measured
DLE30 torque or propeller wind-tunnel curves. At cruise the model needs about
19 N thrust to balance about 19 N drag and about 146 N lift; this constrains
the combined propulsion/drag system, not each coefficient uniquely. The EFI
MAVLink injector uses the log RPM/throttle bins and its own lag because the
current ArduPilot bridge does not expose JSBSim shaft RPM to that process.
Small differences between physical and telemetered RPM during transients are
therefore possible. CHT targets 150°C in cruise; EGT and fuel flow are disabled
by default because the corresponding flight-log readings were invalid/zero.

The log did not independently excite rudder and elevator or measure actual
ruddervator angles. The model preserves the 0.5 A-tail allocation as internal
left/right ruddervator outputs, while moment coefficients remain effective
pitch/yaw terms. Deflection limits, cross-coupling, yaw response, stall,
ground handling, high-throttle power, and mass/inertia away from the nominal
case are provisional. Verify these against dedicated flight maneuvers and
propeller/engine ground tests before using them for safety-critical tuning.

## Engine start and kill in SITL

The September 2026 aircraft parameter file sets `RC9_OPTION=179` (ICE
start/stop), `ICE_ENABLE=1`, `ICE_OPTIONS=12`, `ICE_START_DELAY=3 s`,
`ICE_STARTER_TIME=1 s`, `ICE_START_PCT=14%`, and `ICE_IDLE_PCT=5%`. SITL keeps
those values and assigns virtual outputs 7/8 to starter/ignition. The patched
ArduPilot JSBSim adapter allows engine power only after ignition and a starter
pulse; kill removes power immediately. The EFI injector uses the same outputs.

Procedure: keep RC9 low, arm the aircraft, then set RC9 high (at least 1700
PWM). Alternatively, leave RC9 neutral/unconnected and send
`MAV_CMD_DO_ENGINE_CONTROL` start. Wait for the start delay and starter cycle,
then fly. To stop, set RC9 low (at most 1300 PWM) or send the engine-stop
command; wait for RPM and ground speed to fall, then disarm. At RC9 neutral the
engine retains its current state. Switching high while disarmed cannot start
it, but leaving it high during arming will request a start immediately after
arming. The engine stays off on a fresh SITL launch even though `THR_MIN=6` leaves
the throttle servo at 1060 PWM.

SITL-specific differences from the aircraft: `EFI_TYPE=9` uses MAVLink instead
of the real Lutan serial backend (`3`); `ARSPD_TYPE=100` uses simulated
airspeed; `ICE_STARTCHN_MIN=800` ignores the zero RC9 value when no receiver is
connected while still accepting the 1000 PWM kill switch; `ARMING_CHECK=0`
avoids JSBSim ground-contact gyro checks that otherwise prevent arming. An
explicit arm is still required (`ARMING_REQUIRE=1`, `ICE_OPTIONS` bit 3).

`scripts/ensure_ardupilot_ice_bridge.py` installs the small ArduPilot 4.6.3
patch before a native SITL launch; `sim_vehicle.py` rebuilds the modified
binary. The Docker image includes the patch at build time.
