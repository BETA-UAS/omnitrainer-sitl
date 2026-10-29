from __future__ import annotations

import os
import shlex
import signal
import uuid
from pathlib import Path

import psutil
from PyQt5.QtCore import QObject, QProcess, QProcessEnvironment, pyqtSignal

from .config import LauncherProfile
from .process_utils import python_executable


DOCKER_IMAGE = "omnitrainer-sitl:local"
DOCKER_CONTAINER = "omnitrainer-sitl"
ARDUPILOT_REF = "Plane-4.6.3"

# QGC berjalan di host dan listen UDP 14551.
# Container mengirim MAVLink ke host gateway Docker yang aktif.
# Jangan publish/bind UDP port 14551 di docker run, karena port itu dipakai QGC.
DOCKER_GCS_OUT = "udpout:host.docker.internal:14551"


class ProcessRunner(QObject):
    output = pyqtSignal(str)
    started = pyqtSignal(str)
    ready = pyqtSignal(str)
    finished = pyqtSignal(str, int)
    failed_to_start = pyqtSignal(str)

    def __init__(self, name: str):
        super().__init__()
        self.name = name
        self.proc: QProcess | None = None
        self._session: str | None = None

    def is_running(self) -> bool:
        return self.proc is not None and self.proc.state() != QProcess.NotRunning

    def start(self, cmd: list[str], cwd: Path | None = None) -> bool:
        if self.is_running():
            self.output.emit(f"[{self.name}] already running.")
            return False
        # A previous wrapper may have exited while its children survived.
        if self._session:
            self.stop()

        self.proc = QProcess(self)
        self.proc.setProcessChannelMode(QProcess.MergedChannels)
        self._session = uuid.uuid4().hex
        environment = QProcessEnvironment.systemEnvironment()
        environment.insert("OMNI_LAUNCH_SESSION", self._session)
        self.proc.setProcessEnvironment(environment)

        if cwd:
            self.proc.setWorkingDirectory(str(cwd))

        self.proc.readyReadStandardOutput.connect(self._read_output)
        self.proc.started.connect(lambda: self.started.emit(self.name))
        self.proc.finished.connect(self._finished)
        self.proc.errorOccurred.connect(self._error)

        self.output.emit(f"[{self.name}] $ {' '.join(cmd)}")
        self.proc.start(cmd[0], cmd[1:])
        return True

    def stop(self) -> None:
        if self.proc is None and self._session is None:
            return

        self.output.emit(f"[{self.name}] stopping process session...")
        if self._session:
            # sim_vehicle catches SIGINT and runs its own session cleanup.
            for child in self._owned_processes():
                try:
                    if any("sim_vehicle.py" in arg for arg in child.cmdline()):
                        child.send_signal(signal.SIGINT)
                except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
                    pass
            psutil.wait_procs(self._owned_processes(), timeout=2)

            # JSBSim creates a new session and MAVProxy can leave children
            # behind, so a process-group kill is insufficient. The marker is
            # inherited even when those children are reparented to systemd.
            owned = self._owned_processes()
            for child in owned:
                try:
                    child.terminate()
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    pass
            _, alive = psutil.wait_procs(owned, timeout=2)
            for child in alive:
                try:
                    child.kill()
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    pass
            psutil.wait_procs(alive, timeout=2)
            remaining = self._owned_processes()
            if remaining:
                self.output.emit(f"[{self.name}] WARNING: processes still alive: {[p.pid for p in remaining]}")

        if self.proc is not None and self.proc.state() != QProcess.NotRunning:
            self.proc.terminate()
            if not self.proc.waitForFinished(1000):
                self.proc.kill()
                self.proc.waitForFinished(1000)

        self.proc = None
        self._session = None

    def _owned_processes(self) -> list[psutil.Process]:
        if not self._session:
            return []
        owned = []
        for child in psutil.process_iter(["pid", "uids"]):
            try:
                if child.pid == os.getpid() or child.info["uids"].real != os.getuid():
                    continue
                if child.environ().get("OMNI_LAUNCH_SESSION") == self._session:
                    owned.append(child)
            except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess, AttributeError):
                continue
        return owned

    def _read_output(self) -> None:
        if not self.proc:
            return

        text = bytes(self.proc.readAllStandardOutput()).decode("utf-8", errors="replace")

        for line in text.rstrip().splitlines():
            self.output.emit(f"[{self.name}] {line}")
            if line.startswith("[READY]"):
                self.ready.emit(self.name)

    def _finished(self, exit_code: int, _exit_status: QProcess.ExitStatus) -> None:
        self.output.emit(f"[{self.name}] finished. exit_code={exit_code}")
        self.finished.emit(self.name, int(exit_code))

    def _error(self, error: QProcess.ProcessError) -> None:
        self.output.emit(f"[{self.name}] ERROR: process error {int(error)}")

        if error == QProcess.FailedToStart:
            self.failed_to_start.emit(self.name)


def build_sitl_command(
    profile: LauncherProfile,
    console: bool,
    mavproxy_map: bool,
    gcs_out: str,
    wipe_params: bool = False,
) -> tuple[list[str], Path]:
    args = [
        "./Tools/autotest/sim_vehicle.py",
        "-v",
        profile.aircraft.vehicle,
        "-f",
        profile.aircraft.frame,
        "-L",
        profile.start_location.name,
        # ArduPlane 4.6.3 sim_vehicle only opens SERIAL0 by default.  Expose a
        # dedicated second MAVLink endpoint for the combined EFI/rangefinder
        # injector so it never competes with MAVProxy on TCP 5760.
        "--sitl-instance-args=--serial1=tcp:2",
    ]

    if console:
        args.append("--console")

    if mavproxy_map:
        args.append("--map")

    if gcs_out.strip():
        args.append(f"--out={gcs_out.strip()}")

    if wipe_params:
        args.append("-w")

    param_file = profile.paths.resolve_project_path(profile.paths.param_file)

    if param_file.exists():
        args.append(f"--add-param-file={param_file}")

    bridge_script = profile.paths.project_root / "scripts" / "ensure_ardupilot_ice_bridge.py"
    bridge_cmd = " ".join(shlex.quote(arg) for arg in [
        "python3", str(bridge_script), "--ardupilot-root", str(profile.paths.ardupilot_root),
    ])
    helper_bin = str(Path(python_executable()).parent)
    jsbsim_binary = Path(os.environ.get(
        "OMNI_JSBSIM_BIN",
        Path.home() / "Documents" / "omnitrainer-sitl-build" / "jsbsim" / "bin" / "JSBSim",
    )).expanduser()
    jsbsim_dir = str(jsbsim_binary.parent) if jsbsim_binary.is_file() else ""
    path_prefix = ":".join(part for part in (helper_bin, jsbsim_dir, "/usr/games") if part)
    shell_cmd = (
        "export PATH=" + shlex.quote(path_prefix) + ":\"$PATH\""
        + "; " + bridge_cmd + " && " + " ".join(shlex.quote(arg) for arg in args)
    )

    return ["bash", "-lc", shell_cmd], profile.paths.ardupilot_root


def build_docker_sitl_command(
    profile: LauncherProfile,
    console: bool,
    mavproxy_map: bool,
    gcs_out: str,
    wipe_params: bool = False,
) -> tuple[list[str], Path]:
    project_root = profile.paths.project_root
    dockerfile = project_root / "docker" / "Dockerfile"
    param_file = profile.paths.resolve_project_path(profile.paths.param_file)

    sim_args = [
        "./Tools/autotest/sim_vehicle.py",
        "-v",
        profile.aircraft.vehicle,
        "-f",
        profile.aircraft.frame,
        "-L",
        profile.start_location.name,
        "--sitl-instance-args=--serial1=tcp:2",
    ]

    if console:
        sim_args.append("--console")

    if mavproxy_map:
        sim_args.append("--map")

    sim_args.append(f"--out={DOCKER_GCS_OUT}")

    if wipe_params:
        sim_args.append("-w")

    if param_file.exists():
        sim_args.append(
            f"--add-param-file=/workspace/omnitrainer-sitl/{param_file.relative_to(project_root)}"
        )

    inspect_cmd = (
        "docker image inspect --format "
        + shlex.quote('{{ index .Config.Labels "io.omnitrainer.ardupilot-ref" }} {{ index .Config.Labels "io.omnitrainer.ice-bridge" }}')
        + " "
        + shlex.quote(DOCKER_IMAGE)
        + " | grep -Fxq "
        + shlex.quote(ARDUPILOT_REF + " 5")
    )

    build_cmd = " ".join(
        shlex.quote(arg)
        for arg in [
            "docker",
            "build",
            "-t",
            DOCKER_IMAGE,
            "--build-arg",
            f"ARDUPILOT_REF={ARDUPILOT_REF}",
            "-f",
            str(dockerfile),
            str(project_root),
        ]
    )

    run_cmd = [
        "docker",
        "run",
        "--rm",
        "--name",
        DOCKER_CONTAINER,
        "--add-host",
        "host.docker.internal:host-gateway",

        # TCP ports only. Do not publish UDP 14551 because QGC uses it on the host.
        "-p",
        "5760:5760/tcp",
        "-p",
        "5762:5762/tcp",

        "-e",
        "OMNI_WORKSPACE=/workspace/omnitrainer-sitl",
        "-e",
        f"OMNI_LOCATION_NAME={profile.start_location.name}",
        "-e",
        f"OMNI_LOCATION_LAT={profile.start_location.lat:.7f}",
        "-e",
        f"OMNI_LOCATION_LNG={profile.start_location.lng:.7f}",
        "-e",
        f"OMNI_LOCATION_ALT_MSL={profile.start_location.alt_msl_m:.2f}",
        "-e",
        f"OMNI_LOCATION_HEADING={profile.start_location.heading_deg:.1f}",
        "-v",
        f"{project_root}:/workspace/omnitrainer-sitl:ro",
        DOCKER_IMAGE,
        *sim_args,
    ]

    cleanup_cmd = f"docker rm -f {DOCKER_CONTAINER} >/dev/null 2>&1 || true"

    shell_cmd = (
        f"({inspect_cmd} >/dev/null 2>&1 || {build_cmd}) "
        f"&& ({cleanup_cmd}) && "
        + " ".join(shlex.quote(arg) for arg in run_cmd)
    )

    return ["bash", "-lc", shell_cmd], project_root
