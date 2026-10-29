# Omni Trainer SITL Launcher

Omni Trainer SITL Launcher is a Qt launcher for running the Omni Trainer fixed-wing aircraft in ArduPlane SITL. It keeps the original map-first workflow while moving aircraft, path, network, start location, map, aviation overlay, and EFI settings into a YAML profile.

## Aircraft Profile

The default profile is `profiles/omni_trainer_dle30_15kg.yaml`.

- Aircraft: Omni Trainer
- Engine: DLE30 gasoline engine
- Propeller: fixed-pitch 18x10
- Weight: 15 kg
- Wing area: 0.75 m2
- Cruise speed: 23.9 m/s
- Backend: ArduPlane `Plane-4.6.3` with Omni-Trainer JSBSim model
- EFI: MAVLink injector script

The default profile is portable. It uses:

```yaml
paths:
  ardupilot_root: "auto"
```

The launcher checks `OMNI_ARDUPILOT_ROOT`, then `~/ardupilot`, then legacy checkout paths. Set `OMNI_ARDUPILOT_ROOT` only if you want to use a different ArduPilot tree.

## Install

On Ubuntu/Debian:

```bash
./install.sh
```

The installer creates a local `.venv`, installs JSBSim through FlightGear, checks out ArduPilot at exactly `Plane-4.6.3`, applies the ICE starter patch, and builds ArduPlane SITL.

Bundled portable payloads:

- Aircraft model files: `assets/ardupilot/aircraft/Omni-Trainer`
- EFI injector: `scripts/omni_efi_mavlink_sim.py`
- Native JSBSim rangefinder: 0.10–40.00 m, approximately 0.17 m ground clearance
- Default SITL params: `params/omnitrainer_4.6.3_sitl.param`

To use an existing ArduPilot checkout:

```bash
OMNI_ARDUPILOT_ROOT=/path/to/ardupilot ./install.sh
```

The GUI uses PyQt5 QtWebEngine for the interactive Leaflet map. If the map widget fails to import, install:

```bash
sudo apt install python3-pyqt5 python3-pyqt5.qtwebengine python3-pyqt5.qtwebchannel
```

## Run

Recommended launcher command:

```bash
./run.sh --check
./run.sh
```

`run.sh` uses the project Python environment for EFI/rangefinder helpers. `--check` verifies the native installation without opening the GUI. `launch.sh` also provides an automatic repair preflight for the source checkout.

```bash
./launch.sh
```

You can also pass a profile path:

```bash
./run.sh profiles/omni_trainer_dle30_15kg.yaml
```

## Docker SITL

Docker mode runs ArduPilot SITL inside a container while keeping the launcher GUI and QGroundControl native on the host.

On a fresh device:

```bash
bash scripts/setup_ubuntu.sh
./launch.sh
```

In the GUI, enable **Docker SITL** before pressing **Start**. The first run builds the local image `omnitrainer-sitl:local`, so it can take several minutes. Later runs reuse the image.

Headless Docker SITL is also available:

```bash
bash scripts/docker_sitl.sh
```

Or with Compose:

```bash
docker compose up --build sitl
```

The GUI Docker mode sends QGroundControl telemetry to the Docker host gateway on UDP `14551`; the headless Compose mode uses host networking.

## Map Workflow

The map opens at the configured start location. Click the map or drag the marker to update latitude and longitude. The launcher fetches terrain elevation on opening and after moving the start point, then applies the altitude offset. If lookup fails or is still pending, home altitude defaults to **335 m MSL**, including after changing the start point. A manually entered altitude is preserved. **Refresh terrain** repeats the lookup; the altitude offset is in **Advanced settings**.

SITL, EFI, and rangefinder status are shown beside **Start**. The log is hidden until **Show log** is clicked. Connection, profile, and simulation options are in **Advanced settings**; the Start action validates them automatically.

The map includes selectable base layers and an aviation overlay. If tiles fail to load or the internet is unavailable, the launcher stays usable and the start marker still works.

## Aviation Overlay

The aviation overlay uses OurAirports public CSV data for airports and navaids near the selected operating area. The filter radius and cache age come from the YAML profile. Overlay data is cached under `~/.omni_trainer_sitl_launcher/aviation`.

Use **Refresh Aviation Overlay** to download and filter fresh data. If the download fails, the launcher uses cache when available. If no cache exists, it falls back to a WICM marker and logs a warning.

## Starting SITL

Use **Validate Setup** before launch. The validation checks:

- ArduPilot root
- `Tools/autotest/sim_vehicle.py`
- Omni Trainer aircraft model directory
- bundled EFI script when enabled
- bundled rangefinder script when enabled
- Python executable
- required Python modules

- `locations.txt`
- QtWebEngine availability

Use **Start** to write the selected start location into ArduPilot `locations.txt`, start ArduPlane SITL, wait for the telemetry TCP port, then start the EFI injector and rangefinder injector when enabled. **Stop** kills all launched processes.

The SITL option **Reset params** is enabled by default. Keep it enabled when changing bundled model/takeoff params, because ArduPilot SITL stores parameters between runs.

The bundled parameters include simulated accelerometer calibration and virtual RC
input ranges, matching standard ArduPilot Plane SITL. Fresh sessions therefore
do not need accelerometer or physical radio calibration, even with **Reset params**
enabled. After updating an existing installation, start once with **Reset params**
enabled to discard previously saved values. These calibration defaults are for
simulation only.

## Commands

SITL command shape:

```bash
./Tools/autotest/sim_vehicle.py -v ArduPlane -f jsbsim:Omni-Trainer -L GUI_OMNI --console --map --out=udp:127.0.0.1:14550
```

The launcher also adds the bundled parameter file with `--add-param-file`, enabling EFI and the native JSBSim rangefinder for SITL.

EFI command shape:

```bash
python3 scripts/omni_efi_mavlink_sim.py --connect tcp:127.0.0.1:5762 --rate 10 --print-rate 2
```

The default rangefinder runs inside the JSBSim bridge (`RNGFND1_TYPE=100`).
It uses the model's actual ground clearance, body attitude, and sensor mounting
position instead of estimating distance from home-relative or sea-level altitude.
The sensor points downward and measures 0.10–40.00 m along its beam; distances
above 40 m produce no distance reading instead of showing a raw value above
the sensor limit or a false valid reading at 40 m.
ArduPilot sends the resulting range telemetry directly to the GCS.

The sensor is provisionally directly below the CG. Its 0.1806 m body-down offset
was derived from the settled model to match the specified **17 cm ground
clearance**. Forward/right offsets are zero because they have not been measured.
`SIM_SONAR_POS_*` and `RNGFND1_POS_*` must stay equal. See
`calibration/RANGEFINDER.md` for the coordinate conversion and verification.

The older MAVLink injectors remain available for legacy profiles using
`rangefinder.backend: mavlink`. The default profile uses `backend: jsbsim` and
`efi.rng_inject: false`, so it does not launch or mirror an altitude-based injector.
Native range and mounting settings are in the bundled parameter file; the GUI
shows them as read-only. Restart with **Reset params** checked after this update.

The profile stores additional EFI engine values for future use, but the launcher only passes parameters supported by the current injector command.

## Engine procedure

Keep the RC9 starter/kill switch low before arming. Arm the aircraft, then move
RC9 high (at least 1700 PWM) to request engine start. ArduPilot waits three
seconds, runs the starter for one second, then maintains 5% idle throttle.
To shut down, move RC9 low (at most 1300 PWM), wait for RPM and ground speed to
reach zero, then disarm. RC9 neutral holds the current engine state. If no RC9
input is connected, use MAVLink `MAV_CMD_DO_ENGINE_CONTROL` start/stop after
arming. A low RC9 switch blocks a MAVLink start command.

The bundled SITL profile matches the aircraft's 30° roll limit, +20°/−15°
pitch limits, 24 m/s cruise, 19–27 m/s airspeed range, and ICE timing. Native
launches install the small ArduPilot 4.6.3 JSBSim ICE bridge and rebuild the
SITL binary when needed; Docker includes the bridge in its image. The engine
has no propulsive power before the starter cycle. See
`calibration/CALIBRATION.md` for measured fit and SITL-only parameter changes.

Ground steering uses servo 6 (ArduPlane GroundSteering). The dedicated wheel
brake uses RC11 passthrough to servo 12: approximately 1000 PWM releases it and
2000 PWM applies it. RC2 pitch input is reversed; RC4 yaw input is normal.

## Troubleshooting

- **Map is blank:** check QtWebEngine packages. Online tiles are optional; marker selection still works once the widget loads.

- **EFI or rangefinder does not start:** confirm SITL exposes `tcp:127.0.0.1:5762`. The launcher waits for that TCP port before launching telemetry injectors.
- **GCS does not show rangefinder:** check `DISTANCE_SENSOR` on the autopilot telemetry connection and confirm `RNGFND1_TYPE=100`. EFI mirroring is configured separately with `network.telemetry_gcs_out`.
- **Terrain lookup fails:** enter Home altitude MSL manually.
- **Aviation overlay fails:** refresh when online, or use cached/fallback overlay for simulation.

## Known Limitations

OurAirports data is not authoritative for real flight. The launcher is for simulation workflows. Propeller, high-throttle, and ruddervator effects outside the logged maneuvers remain provisional.

# Instalasi penuh dari GitHub

Pada Ubuntu/Debian Linux desktop (x86_64 atau aarch64), unduh `install_omnisitl.sh` dari repo lalu jalankan sebagai pengguna biasa:

```bash
curl -fL https://raw.githubusercontent.com/BETA-UAS/omnitrainer-sitl/main/install_omnisitl.sh -o install_omnisitl.sh
bash install_omnisitl.sh
```

Installer ini meng-clone repo ke `~/Documents/omnitrainer-sitl` bila belum ada, membangun ArduPlane SITL di `~/Documents/ardupilot-omnitrainer-sitl`, serta membangun JSBSim dan menyimpan AppImage di `~/Documents/omnitrainer-sitl-build`. Shortcut dibuat di `~/Desktop/OMNITrainer-SITL.desktop`. Jalankan ulang untuk melanjutkan instalasi yang terputus. Checkout, dependency, binary, dan AppImage yang sudah tersedia akan dipakai kembali. `OMNI_INSTALL_DIR` dan `OMNI_ARDUPILOT_ROOT` dapat mengubah lokasi source dan ArduPilot; checkout source yang sudah ada harus berasal dari repo BETA-UAS. AppImage memerlukan instalasi source dan backend pada perangkat yang sama.
