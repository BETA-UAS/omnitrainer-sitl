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
    patch = Path(__file__).resolve().parents[1] / "patches" / "ardupilot-4.6.3-jsbsim-ice.patch"
    version = root / "ArduPlane" / "version.h"
    if not version.exists() or 'ArduPlane V4.6.3' not in version.read_text():
        raise SystemExit(f"Expected ArduPlane 4.6.3 at {root}")

    def check(*flags):
        return subprocess.run(
            ["git", "-C", str(root), "apply", *flags, "--check", str(patch)],
            stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True,
        )

    if check("--reverse").returncode == 0:
        print("Omni-Trainer ICE bridge already installed")
        return
    if check().returncode != 0:
        raise SystemExit("ArduPilot JSBSim source differs from the supported 4.6.3 patch; cannot safely install ICE bridge")
    subprocess.run(["git", "-C", str(root), "apply", str(patch)], check=True)
    print("Installed Omni-Trainer ICE bridge; sim_vehicle will rebuild ArduPlane")


if __name__ == "__main__":
    main()
