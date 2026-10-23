#!/usr/bin/env bash
# A fresh, relocatable source package. Includes the binary when built.
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
STAGE="${ROOT}/dist/release/omni-trainer-sitl"
ARCHIVE="${ROOT}/dist/omni-trainer-sitl-$(uname -m).tar.gz"
rm -rf "${STAGE}"
mkdir -p "${STAGE}"
for path in launcher.py launch.sh run.sh install.sh requirements.txt README.md README-DISTRIBUTION.md QUICK-START.txt docker-compose.yml .dockerignore; do
  cp "${ROOT}/${path}" "${STAGE}/"
done
for path in omni_launcher profiles params patches assets scripts docker; do
  cp -a "${ROOT}/${path}" "${STAGE}/"
done
if [ -s "${ROOT}/dist/omni-trainer-sitl" ]; then
  cp "${ROOT}/dist/omni-trainer-sitl" "${STAGE}/"
fi
find "${STAGE}" -type d -name __pycache__ -prune -exec rm -rf {} +
find "${STAGE}" -type f -name '*.pyc' -delete
find "${STAGE}" -type f \( -name '*.tlog' -o -name '*.tlog.raw' \) -delete
for path in install.sh run.sh launcher.py profiles/omni_trainer_dle30_15kg.yaml \
  params/omnitrainer_4.6.3_sitl.param patches/ardupilot-4.6.3-jsbsim-ice.patch \
  assets/ardupilot/aircraft/Omni-Trainer/Omni-Trainer-JSBSim.xml \
  assets/ardupilot/aircraft/Omni-Trainer/Engines/DLE30_EFI.xml \
  assets/ardupilot/aircraft/Omni-Trainer/Engines/18x10.xml; do
  test -s "${STAGE}/${path}" || { echo "Missing release payload: ${path}" >&2; exit 1; }
done
(
  cd "${ROOT}/dist/release"
  tar -czf "${ARCHIVE}" omni-trainer-sitl
)
(
  cd "${ROOT}/dist"
  sha256sum "$(basename "${ARCHIVE}")" > "$(basename "${ARCHIVE}").sha256"
)
echo "Created ${ARCHIVE}"
cat "${ARCHIVE}.sha256"
