#!/usr/bin/env bash
# Full, repeatable installer for supported Ubuntu/Debian Linux desktops.
set -euo pipefail

REPO_URL=https://github.com/BETA-UAS/omnitrainer-sitl.git
INSTALL_DIR="${OMNI_INSTALL_DIR:-${HOME}/Documents/omnitrainer-sitl}"
ARDUPILOT_DIR="${OMNI_ARDUPILOT_ROOT:-${HOME}/Documents/ardupilot-omnitrainer-sitl}"
APPIMAGE_DIR="${HOME}/Documents/omnitrainer-sitl-build"
JSBSIM_SOURCE="${APPIMAGE_DIR}/jsbsim-source"
JSBSIM_PREFIX="${APPIMAGE_DIR}/jsbsim"
APPIMAGE="${APPIMAGE_DIR}/OMNITrainer-SITL-$(uname -m).AppImage"
DESKTOP_DIR="${XDG_DESKTOP_DIR:-${HOME}/Desktop}"
SHORTCUT="${DESKTOP_DIR}/OMNITrainer-SITL.desktop"
MARKER='X-OMNITrainer-SITL-Installer=true'

die() { printf 'Error: %s\n' "$*" >&2; exit 1; }
log() { printf '[OMNITrainer-SITL] %s\n' "$*"; }

[[ "$(uname -s)" == Linux ]] || die 'Installer ini hanya mendukung Linux.'
command -v apt-get >/dev/null || die 'Saat ini setup native membutuhkan Ubuntu/Debian (apt-get).'
[[ "${EUID}" -ne 0 ]] || die 'Jalankan sebagai pengguna desktop biasa; sudo diminta oleh setup bila perlu.'
command -v sudo >/dev/null || die 'sudo diperlukan untuk memasang paket sistem.'
if ! command -v git >/dev/null || ! command -v curl >/dev/null; then
  log 'Memasang alat bootstrap (git, curl, sertifikat CA).'
  sudo apt-get update
  sudo apt-get install -y --no-install-recommends git curl ca-certificates
fi
[[ "${INSTALL_DIR}" = /* && "${ARDUPILOT_DIR}" = /* ]] || die 'Path instalasi dan ArduPilot harus absolut.'
case "${INSTALL_DIR%/}" in
  /|"${HOME}"|"${DESKTOP_DIR}"|"${HOME}/Desktop"|"${HOME}/Documents"|"${ARDUPILOT_DIR%/}") die 'Path instalasi tidak aman.' ;;
esac
[[ "${INSTALL_DIR%/}" != "${DESKTOP_DIR%/}/"* ]] || die 'Jangan memasang source di dalam Desktop.'
[[ ! -L "${INSTALL_DIR}" && ! -L "${APPIMAGE_DIR}" && ! -L "${DESKTOP_DIR}" ]] || die 'Symlink pada path instalasi/Desktop tidak didukung.'
[[ ! -L "$APPIMAGE" && ! -L "${APPIMAGE}.part" && ! -L "$SHORTCUT" && ! -e "${SHORTCUT}.part" && ! -L "${SHORTCUT}.part" ]] || die 'Ditemukan symlink atau file sementara yang tidak aman; periksa path installer.'

if [[ -e "${INSTALL_DIR}" ]]; then
  command -v git >/dev/null || die 'git diperlukan untuk memeriksa checkout.'
  [[ -d "${INSTALL_DIR}/.git" ]] || die "${INSTALL_DIR} sudah ada dan bukan checkout Git. Tidak akan ditimpa."
  origin="$(git -C "${INSTALL_DIR}" remote get-url origin 2>/dev/null || true)"
  case "${origin}" in
    "$REPO_URL"|git@github.com:BETA-UAS/omnitrainer-sitl.git) ;;
    *) die "Checkout ${INSTALL_DIR} memiliki remote origin lain: ${origin}" ;;
  esac
  log "Memakai checkout yang sudah ada: ${INSTALL_DIR}"
  if [[ -z "$(git -C "${INSTALL_DIR}" status --porcelain)" ]]; then
    git -C "${INSTALL_DIR}" pull --ff-only
  else
    log 'Checkout memiliki perubahan lokal; pembaruan source dilewati.'
  fi
else
  command -v git >/dev/null || die 'git belum tersedia. Pasang git terlebih dahulu.'
  mkdir -p "$(dirname "${INSTALL_DIR}")"
  git clone "$REPO_URL" "$INSTALL_DIR"
fi

[[ -f "${INSTALL_DIR}/scripts/setup_ubuntu.sh" && -f "${INSTALL_DIR}/omni_trainer.spec" ]] || die 'Checkout tidak lengkap.'
if ! dpkg-query -W -f='${Status}' python3-wxgtk4.0 2>/dev/null | grep -Fq 'install ok installed'; then
  log 'Memasang wxPython untuk tampilan MAVProxy console/map.'
  sudo apt-get update
  sudo apt-get install -y --no-install-recommends python3-wxgtk4.0
fi
export OMNI_ARDUPILOT_ROOT="${ARDUPILOT_DIR}"
if [[ -x "${INSTALL_DIR}/.venv/bin/python3" && -x "${ARDUPILOT_DIR}/build/sitl/bin/arduplane" ]] && \
   { command -v JSBSim >/dev/null || command -v jsbsim >/dev/null || [[ -x /usr/games/JSBSim ]]; } && \
   "${INSTALL_DIR}/.venv/bin/python3" -c 'import yaml, pymavlink, MAVProxy, wx; from PyQt5 import QtWebEngineWidgets' >/dev/null 2>&1; then
  log 'Dependency, JSBSim, dan ArduPlane SITL sudah tersedia; setup dilewati.'
else
  log 'Menjalankan setup native (dependency, JSBSim, dan ArduPlane SITL).'
  bash "${INSTALL_DIR}/scripts/setup_ubuntu.sh"
fi

# JSBSim is built in a private prefix, leaving system packages and other checkouts alone.
if [[ ! -x "${JSBSIM_PREFIX}/bin/JSBSim" && ! -x "${JSBSIM_PREFIX}/bin/jsbsim" ]]; then
  command -v cmake >/dev/null || die 'cmake diperlukan untuk build JSBSim. Jalankan setup lagi.'
  mkdir -p "$APPIMAGE_DIR"
  if [[ -e "$JSBSIM_SOURCE" ]]; then
    [[ -d "$JSBSIM_SOURCE/.git" ]] || die "${JSBSIM_SOURCE} sudah ada dan bukan checkout Git."
    [[ "$(git -C "$JSBSIM_SOURCE" remote get-url origin)" == https://github.com/JSBSim-Team/jsbsim.git ]] || die 'Checkout JSBSim memiliki remote yang tidak sesuai.'
  else
    git clone https://github.com/JSBSim-Team/jsbsim.git "$JSBSIM_SOURCE"
  fi
  cmake -S "$JSBSIM_SOURCE" -B "${JSBSIM_SOURCE}/build-omni" -DCMAKE_INSTALL_PREFIX="$JSBSIM_PREFIX" -DBUILD_TESTING=OFF
  cmake --build "${JSBSIM_SOURCE}/build-omni" --parallel "$(nproc)"
  cmake --install "${JSBSIM_SOURCE}/build-omni"
fi
export PATH="${JSBSIM_PREFIX}/bin:${PATH}"

BINARY="${INSTALL_DIR}/dist/omni-trainer-sitl"
if [[ ! -s "$BINARY" ]] || \
   [[ -n "$(find "${INSTALL_DIR}/omni_launcher" "${INSTALL_DIR}/omni_trainer.spec" "${INSTALL_DIR}/launcher.py" -type f -newer "$BINARY" -print -quit)" ]]; then
  log 'Membangun binary aplikasi.'
  bash "${INSTALL_DIR}/build_binary.sh"
fi

mkdir -p "$APPIMAGE_DIR"
if [[ ! -s "$APPIMAGE" || "$BINARY" -nt "$APPIMAGE" ]]; then
  command -v curl >/dev/null || die 'curl diperlukan untuk mengunduh appimagetool.'
  command -v python3 >/dev/null || die 'python3 diperlukan untuk memilih appimagetool.'
  arch="$(uname -m)"
  case "$arch" in x86_64|aarch64) ;; *) die "Belum ada appimagetool resmi untuk arsitektur ${arch}." ;; esac
  tool="${APPIMAGE_DIR}/appimagetool-${arch}.AppImage"
  if [[ ! -s "$tool" ]]; then
    log 'Mengunduh appimagetool untuk arsitektur perangkat.'
    api="$(curl -fsSL https://api.github.com/repos/AppImage/appimagetool/releases/latest)"
    url="$(printf '%s' "$api" | python3 -c 'import json,sys; a=sys.argv[1]; d=json.load(sys.stdin); print(next((x["browser_download_url"] for x in d["assets"] if x["name"] == "appimagetool-"+a+".AppImage"), ""))' "$arch")"
    [[ -n "$url" ]] || die "Asset appimagetool ${arch} tidak ditemukan."
    curl -fL --retry 3 "$url" -o "${tool}.part"
    chmod 755 "${tool}.part"
    mv "${tool}.part" "$tool"
  fi

  stage="$(mktemp -d "${APPIMAGE_DIR}/appdir.XXXXXXXX")"
  trap '[[ -z "${stage:-}" ]] || rm -rf -- "$stage"' EXIT
  mkdir -p "$stage/usr/bin"
  cp "${INSTALL_DIR}/dist/omni-trainer-sitl" "$stage/usr/bin/omni-trainer-sitl"
  cat > "$stage/AppRun" <<EOF
#!/usr/bin/env bash
export PATH="${JSBSIM_PREFIX}/bin:${INSTALL_DIR}/.venv/bin:/usr/games:\${PATH}"
export PYTHONNOUSERSITE=1
export OMNI_PYTHON="${INSTALL_DIR}/.venv/bin/python3"
export OMNI_JSBSIM_BIN="${JSBSIM_PREFIX}/bin/JSBSim"
export OMNI_ARDUPILOT_ROOT="${ARDUPILOT_DIR}"
exec "\${APPDIR}/usr/bin/omni-trainer-sitl" "${INSTALL_DIR}/profiles/omni_trainer_dle30_15kg.yaml" "\$@"
EOF
  chmod 755 "$stage/AppRun"
  cat > "$stage/OMNITrainer-SITL.desktop" <<'EOF'
[Desktop Entry]
Type=Application
Name=OMNITrainer-SITL
Exec=AppRun
Icon=omnitrainer-sitl
Categories=Education;Science;
Terminal=false
EOF
  cat > "$stage/omnitrainer-sitl.svg" <<'EOF'
<svg xmlns="http://www.w3.org/2000/svg" width="256" height="256" viewBox="0 0 256 256"><rect width="256" height="256" rx="48" fill="#163b61"/><path d="M30 126h196M128 34v188M47 87l162 82M47 169l162-82" stroke="#65d7ed" stroke-width="17" stroke-linecap="round"/><circle cx="128" cy="128" r="32" fill="#fff"/></svg>
EOF
  log 'Membangun AppImage.'
  APPIMAGE_EXTRACT_AND_RUN=1 ARCH="$arch" "$tool" "$stage" "${APPIMAGE}.part"
  chmod 755 "${APPIMAGE}.part"
  mv "${APPIMAGE}.part" "$APPIMAGE"
  cp "$stage/omnitrainer-sitl.svg" "${APPIMAGE_DIR}/omnitrainer-sitl.svg"
  rm -rf -- "$stage"
  stage=''
fi

if [[ -e "$SHORTCUT" || -L "$SHORTCUT" ]]; then
  [[ -f "$SHORTCUT" && ! -L "$SHORTCUT" ]] && grep -Fxq "$MARKER" "$SHORTCUT" || die "Shortcut ${SHORTCUT} sudah ada dan bukan milik installer ini."
fi
mkdir -p "$DESKTOP_DIR"
cat > "${SHORTCUT}.part" <<EOF
[Desktop Entry]
Type=Application
Version=1.0
Name=OMNITrainer-SITL
Exec=${APPIMAGE}
Icon=${APPIMAGE_DIR}/omnitrainer-sitl.svg
Terminal=false
Categories=Education;Science;
${MARKER}
EOF
mv "${SHORTCUT}.part" "$SHORTCUT"
chmod 755 "$SHORTCUT"
log "Selesai. AppImage: ${APPIMAGE}; shortcut: ${SHORTCUT}"
