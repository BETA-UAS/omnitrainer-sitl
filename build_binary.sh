#!/usr/bin/env bash
# Build on the oldest Linux distribution that the binary must support.
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PYTHON="${ROOT}/.venv/bin/python3"
export PYTHONNOUSERSITE=1
if [ ! -x "${PYTHON}" ]; then
  echo "Missing project venv. Run ./install.sh first." >&2
  exit 1
fi
"${PYTHON}" -m pip install 'PyInstaller==6.22.3'
rm -f "${ROOT}/dist/omni-trainer-sitl"
cd "${ROOT}"
"${PYTHON}" -m PyInstaller --noconfirm --clean --distpath "${ROOT}/dist" --workpath "${ROOT}/build" omni_trainer.spec
BINARY="${ROOT}/dist/omni-trainer-sitl"
test -s "${BINARY}" || { echo "PyInstaller did not produce a binary." >&2; exit 1; }
file "${BINARY}"
sha256sum "${BINARY}"
echo "Binary ready: ${BINARY}"
echo "Package it with: bash scripts/package_release.sh"
