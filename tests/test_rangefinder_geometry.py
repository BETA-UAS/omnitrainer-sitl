"""Check native bridge geometry against the actual JSBSim aircraft model.
Run with: .venv/bin/python -m unittest discover -s tests
Requires the optional jsbsim Python package for the settled-aircraft test.
"""
import math
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]


def parameters():
    return dict(line.split()[:2] for line in
                (ROOT / 'params/omnitrainer_4.6.3_sitl.param').read_text().splitlines()
                if line.strip() and not line.lstrip().startswith('#'))


class RangefinderGeometry(unittest.TestCase):
    def test_mount_and_limits_consistent(self):
        p = parameters()
        self.assertEqual(p['RNGFND1_TYPE'], '100')
        self.assertEqual(p['RNGFND1_MAX_CM'], '4000')
        self.assertEqual(p['RNGFND1_GNDCLEAR'], '17')
        for axis in 'XYZ':
            self.assertEqual(p['RNGFND1_POS_' + axis], p['SIM_SONAR_POS_' + axis])
        self.assertEqual((ROOT / 'params/omnitrainer_4.6.3_sitl.param').read_bytes(),
                         (ROOT / 'assets/ardupilot/aircraft/Omni-Trainer/omni_trainer_sitl.parm').read_bytes())

    def test_native_profile_does_not_inject_duplicate_distance(self):
        from omni_launcher.config import load_profile
        from omni_launcher.efi_process import build_efi_command
        profile = load_profile(ROOT / 'profiles/omni_trainer_dle30_15kg.yaml')
        self.assertEqual(profile.rangefinder.backend, 'jsbsim')
        self.assertEqual(profile.rangefinder.max_cm, 4000)
        # Even a stale EFI option must not re-enable duplicate native readings.
        profile.efi.rng_inject = True
        command, _ = build_efi_command(profile, 'tcp:127.0.0.1:5762', '', 10, 2)
        self.assertNotIn('--rng-inject', ' '.join(command))

    def test_settled_model_clearance(self):
        try:
            import jsbsim
        except ImportError:
            self.skipTest('Optional jsbsim Python package is not installed')
        aircraft = ROOT / 'assets/ardupilot/aircraft'
        f = jsbsim.FGFDMExec(None)
        f.set_debug_level(0)
        f.set_aircraft_path(str(aircraft))
        f.set_engine_path(str(aircraft / 'Omni-Trainer/Engines'))
        self.assertTrue(f.load_model('Omni-Trainer'))
        f.set_dt(.001)
        f['ic/h-agl-ft'] = 1.3 / .3048
        f['ic/theta-deg'] = 13
        f.run_ic()
        for _ in range(20000):
            self.assertTrue(f.run())
        height = f['position/h-agl-ft'] * .3048
        down = math.cos(f['attitude/phi-rad']) * math.cos(f['attitude/theta-rad'])
        mount = float(parameters()['SIM_SONAR_POS_Z'])
        clearance = height - mount * down
        self.assertAlmostEqual(clearance, .17, delta=.005)
        self.assertAlmostEqual(clearance / down, .17, delta=.005)
        print(f'JSBSim CG AGL={height:.6f}m; sensor clearance={clearance:.6f}m')


if __name__ == '__main__':
    unittest.main()
