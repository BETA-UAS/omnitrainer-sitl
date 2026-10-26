#!/usr/bin/env python3
"""Apply the Omni-Trainer-only JSBSim starter bridge to ArduPilot 4.6.3."""

import argparse
from pathlib import Path
import subprocess


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--ardupilot-root", type=Path, required=True)
    args = parser.parse_args()
    root = args.ardupilot_root.expanduser().resolve()
    patches = Path(__file__).resolve().parents[1] / "patches"
    patch = patches / "ardupilot-4.6.3-jsbsim-ice.patch"
    previous_patches = [patches / f"ardupilot-4.6.3-jsbsim-ice-v{v}.patch" for v in (4, 3, 2)]
    version = root / "ArduPlane" / "version.h"
    if not version.exists() or 'ArduPlane V4.6.3' not in version.read_text():
        raise SystemExit(f"Expected ArduPlane 4.6.3 at {root}")

    def check(candidate, *flags):
        return subprocess.run(
            ["git", "-C", str(root), "apply", *flags, "--check", str(candidate)],
            stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True,
        )

    if check(patch, "--reverse").returncode == 0:
        print("Omni-Trainer JSBSim bridge already installed")
        return
    if check(patch).returncode == 0:
        subprocess.run(["git", "-C", str(root), "apply", str(patch)], check=True)
        print("Installed Omni-Trainer JSBSim bridge; sim_vehicle will rebuild ArduPlane")
        return
    previous_patch = next((p for p in previous_patches if check(p, "--reverse").returncode == 0), None)
    if previous_patch is None:
        raise SystemExit("ArduPilot JSBSim source differs from the supported 4.6.3 patches; cannot safely install bridge")
    subprocess.run(["git", "-C", str(root), "apply", "--reverse", str(previous_patch)], check=True)
    try:
        if check(patch).returncode != 0:
            raise RuntimeError("New JSBSim bridge does not apply after removing the previous bridge")
        subprocess.run(["git", "-C", str(root), "apply", str(patch)], check=True)
    except BaseException:
        subprocess.run(["git", "-C", str(root), "apply", str(previous_patch)], check=True)
        raise
    print("Upgraded Omni-Trainer JSBSim bridge; sim_vehicle will rebuild ArduPlane")


if __name__ == "__main__":
    main()
