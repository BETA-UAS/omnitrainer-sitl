#!/usr/bin/env bash
# Re-runnable native SITL installer for Ubuntu/Debian.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
ARDUPILOT_ROOT="${OMNI_ARDUPILOT_ROOT:-${HOME}/ardupilot}"
ARDUPILOT_URL="${OMNI_ARDUPILOT_URL:-https://github.com/ArduPilot/ardupilot.git}"
ARDUPILOT_REF="Plane-4.6.3"
VENV="${PROJECT_ROOT}/.venv"
export PYTHONNOUSERSITE=1

if ! command -v apt-get >/dev/null 2>&1; then
  echo "Ubuntu/Debian with apt-get is required for native installation." >&2
  exit 1
fi
if [ "${EUID}" -eq 0 ]; then
  APT=(apt-get)
elif command -v sudo >/dev/null 2>&1; then
  APT=(sudo apt-get)
else
  echo "Install sudo or run this script as root for system packages." >&2
  exit 1
fi

"${APT[@]}" update
"${APT[@]}" install -y --no-install-recommends \
  ca-certificates git curl rsync xterm flightgear build-essential cmake ccache gawk pkg-config \
  libxml2-dev libxslt1-dev libffi-dev libssl-dev \
  python3 python3-dev python3-pip python3-venv python3-setuptools python3-wheel \
  python3-pyqt5 python3-pyqt5.qtwebengine python3-pyqt5.qtwebchannel \
  python3-wxgtk4.0

if [ ! -x "${VENV}/bin/python3" ]; then
  python3 -m venv --system-site-packages "${VENV}"
fi
"${VENV}/bin/python3" -m pip install --upgrade pip setuptools wheel
"${VENV}/bin/python3" -m pip install -r "${PROJECT_ROOT}/requirements.txt"
"${VENV}/bin/python3" - <<'PY'
import yaml, pymavlink, MAVProxy, wx
from PyQt5 import QtWebChannel, QtWebEngineWidgets
print("Python launcher and helper dependencies: OK")
PY

mkdir -p "$(dirname "${ARDUPILOT_ROOT}")"
if [ ! -d "${ARDUPILOT_ROOT}/.git" ]; then
  if [ -e "${ARDUPILOT_ROOT}" ]; then
    echo "${ARDUPILOT_ROOT} exists but is not an ArduPilot Git checkout." >&2
    exit 1
  fi
  git clone --branch "${ARDUPILOT_REF}" --recurse-submodules "${ARDUPILOT_URL}" "${ARDUPILOT_ROOT}"
else
  git -C "${ARDUPILOT_ROOT}" submodule update --init --recursive
fi

if ! grep -q 'ArduPlane V4.6.3' "${ARDUPILOT_ROOT}/ArduPlane/version.h"; then
  echo "Expected ArduPlane V4.6.3 in ${ARDUPILOT_ROOT}; refusing to patch another version." >&2
  exit 1
fi
tag_commit="$(git -C "${ARDUPILOT_ROOT}" rev-parse "${ARDUPILOT_REF}^{commit}" 2>/dev/null || true)"
head_commit="$(git -C "${ARDUPILOT_ROOT}" rev-parse HEAD)"
if [ -z "${tag_commit}" ] || [ "${head_commit}" != "${tag_commit}" ]; then
  echo "ArduPilot HEAD must equal the ${ARDUPILOT_REF} tag. Current: ${head_commit}; tag: ${tag_commit:-missing}." >&2
  exit 1
fi

MODEL_SOURCE="${PROJECT_ROOT}/assets/ardupilot/aircraft/Omni-Trainer"
MODEL_TARGET="${ARDUPILOT_ROOT}/Tools/autotest/aircraft/Omni-Trainer"
test -f "${MODEL_SOURCE}/Omni-Trainer-JSBSim.xml"
test -f "${PROJECT_ROOT}/params/omnitrainer_4.6.3_sitl.param"
mkdir -p "${MODEL_TARGET}"
rsync -a "${MODEL_SOURCE}/" "${MODEL_TARGET}/"
"${VENV}/bin/python3" "${PROJECT_ROOT}/scripts/ensure_ardupilot_ice_bridge.py" --ardupilot-root "${ARDUPILOT_ROOT}"

# Build after applying the ICE bridge, with the same Python used at runtime.
export PATH="${VENV}/bin:/usr/games:${PATH}"
cd "${ARDUPILOT_ROOT}"
./waf configure --board sitl
./waf plane

test -x "${ARDUPILOT_ROOT}/build/sitl/bin/arduplane"
command -v JSBSim >/dev/null 2>&1 || command -v jsbsim >/dev/null 2>&1
echo "Setup complete. Run: ${PROJECT_ROOT}/launch.sh"
