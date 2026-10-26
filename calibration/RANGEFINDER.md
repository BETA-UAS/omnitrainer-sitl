# JSBSim rangefinder placement and measurement

The requested 17 cm is sensor-to-ground clearance at rest, not the sensor's
body-frame displacement from the center of gravity. The requested maximum is
40 m (4000 cm); the minimum is 10 cm.

## Placement

The model uses JSBSim structural coordinates in inches: X aft, Y right, Z up.
Empty-aircraft CG is (34.5, 0, 0); with the default fuel load the mass CG is
approximately (34.45317, 0, 0). Main-wheel contacts are at Z=-13.8 in and the
nose-wheel contact at Z=-14.2 in. These are unloaded geometry; spring compression
and pitch must be included before deriving sensor clearance.

After 20 seconds settling with engine off, the model gives CG AGL=0.350537 m
and pitch=1.155728 degrees. A downward mount at body coordinates
(0, 0, 0.1806) m produces vertical clearance 0.169974 m and beam distance
0.170008 m. Body coordinates are forward/right/down relative to CG.
The equivalent structural point at the default load is approximately
(34.45317, 0, -7.11024) inches. This is a derived virtual mount: forward and
sideways positions were not supplied, so zero is provisional. Fuel loading,
gear compression and attitude can change actual ground readings slightly.

Both SIM_SONAR_POS_Z and RNGFND1_POS_Z are 0.1806; both X/Y pairs are zero.
RNGFND1_GNDCLEAR=17 is centimetres. Orientation 25 points body-down.

## Measurement

The bridge reads JSBSim FlightGear FDM `agl` in metres. With body-to-earth
rotation R, mount p and down beam b=(0,0,1), it computes:

    sensor_height = agl - (R*p).z
    beam_distance = max(0, sensor_height / (R*b).z)

An upward/horizontal beam or a target beyond 40 m produces no reading.
The 10 cm minimum is handled by ArduPilot as below range. No distance above
40 m is published as a live measurement. There is no stale MAVLink altitude
fallback or 30 cm floor.
This measures the JSBSim contact surface, not online terrain tiles: the current
JSBSim simulation uses a local ground surface and does not model arbitrary
obstacles or terrain slope along the laser beam.

## Checks

Run `.venv/bin/python -m unittest discover -s tests` (the settled model check
requires the optional `jsbsim` Python package). The native bridge must be rebuilt
and a session reset must be used when switching from MAVLink type 10 to native
SITL type 100. No BETAGroundControl changes are required.
