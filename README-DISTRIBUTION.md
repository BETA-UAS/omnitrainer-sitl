# Distribusi OMNI Trainer SITL

Paket ini ditujukan untuk Ubuntu/Debian dengan desktop X11/Wayland. ArduPilot dikunci tepat pada tag `Plane-4.6.3`; installer menolak checkout pada commit lain. Model JSBSim, propeler 18x10, parameter pesawat, dan patch starter ICE disertakan.

## Menyiapkan paket pada komputer pengembang

```bash
# Paket source, dapat dijalankan tanpa PyInstaller
bash scripts/package_release.sh

# Opsional: sertakan executable GUI untuk arsitektur Linux yang sama
bash build_binary.sh
bash scripts/package_release.sh
```

Arsip ada di `dist/omni-trainer-sitl-<arsitektur>.tar.gz`, dengan checksum aktual di file `.sha256` di sebelahnya. Bangun binary pada distro/arsitektur target yang kompatibel; binary PyInstaller tidak menggantikan ArduPilot, JSBSim, atau Python untuk proses telemetry.
Direktori `dist_pkg/` di checkout lama adalah snapshot historis; gunakan arsip baru dari `scripts/package_release.sh`.

## Instalasi pada perangkat lain

```bash
tar xzf omni-trainer-sitl-<arsitektur>.tar.gz
cd omni-trainer-sitl
./install.sh
./run.sh --check
./run.sh
```

`install.sh` memasang pustaka sistem dan FlightGear (yang menyediakan `/usr/games/JSBSim` pada Ubuntu), membuat `.venv`, mengunduh tag ArduPilot 4.6.3, memasang model/patch starter ICE, membangun ArduPlane SITL, lalu memeriksa hasilnya. Perlu koneksi internet, hak sudo, serta ruang disk yang cukup untuk source/build ArduPilot dan FlightGear. Instalasi dapat dijalankan ulang setelah koneksi terputus. Jangan menjalankan instalasi sebagai root bila ingin checkout ArduPilot di home pengguna biasa.

Gunakan `OMNI_ARDUPILOT_ROOT=/path/checkout ./install.sh` untuk checkout lain yang sudah berada tepat di tag `Plane-4.6.3`. Perubahan lokal pada checkout tidak dihapus; patch dan model disinkronkan. Jika check gagal, jalankan `./install.sh` kembali. `./run.sh --check` hanya memeriksa tanpa membuka GUI.

## Docker

Docker bersifat opsional. Mode Docker di GUI atau `bash scripts/docker_sitl.sh` memerlukan Docker Engine yang dapat diakses pengguna. Image memuat ArduPilot 4.6.3 dan JSBSim; build pertama memerlukan internet. Paket native tidak mengaktifkan Docker secara otomatis. Untuk Docker, ikuti instruksi resmi instalasi Docker bagi distro perangkat tersebut.
