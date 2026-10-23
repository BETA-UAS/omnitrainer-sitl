#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
export OMNI_PYTHON="${ROOT}/.venv/bin/python3"
export PATH="${ROOT}/.venv/bin:/usr/games:${PATH}"
export PYTHONNOUSERSITE=1
if [ ! -x "${OMNI_PYTHON}" ]; then
  echo "Dependencies missing. Run ${ROOT}/install.sh first." >&2
  exit 1
fi
if [ -x "${ROOT}/omni-trainer-sitl" ]; then
  if [ "$#" -eq 0 ]; then
    set -- "${ROOT}/profiles/omni_trainer_dle30_15kg.yaml"
  elif [ "$#" -eq 1 ] && [ "$1" = "--check" ]; then
    set -- --check "${ROOT}/profiles/omni_trainer_dle30_15kg.yaml"
  fi
  exec "${ROOT}/omni-trainer-sitl" "$@"
fi
exec "${OMNI_PYTHON}" "${ROOT}/launcher.py" "$@"
