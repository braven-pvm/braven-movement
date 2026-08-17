import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
if str(REPOSITORY_ROOT) not in sys.path:
    sys.path.insert(0, str(REPOSITORY_ROOT))

from reference_pose_config import (  # noqa: E402
    DEFAULT_CONFIG_PATH,
    ReferencePoseConfigError,
    load_reference_catch_config,
)


class ReferencePoseConfigTest(unittest.TestCase):
    def test_default_config_loads_outside_the_repository_working_directory(self):
        program = """
import json
from reference_pose_config import load_reference_catch_config

config = load_reference_catch_config()
print(json.dumps({
    "schemaVersion": config.schema_version,
    "movementId": config.movement_id,
    "framePx": config.reference_frame_px,
    "ballRadiusM": config.ball_radius_m,
    "rightThumbPx": config.reference_targets_px["right_thumb_tip"],
    "maxWristBendDegrees": config.anatomy_limits_degrees["wristBend"],
}))
"""
        environment = os.environ.copy()
        environment["PYTHONPATH"] = str(REPOSITORY_ROOT)
        with tempfile.TemporaryDirectory() as unrelated_directory:
            completed = subprocess.run(
                [sys.executable, "-c", program],
                cwd=unrelated_directory,
                env=environment,
                text=True,
                capture_output=True,
                check=False,
            )

        self.assertEqual(completed.returncode, 0, completed.stderr)
        self.assertEqual(
            json.loads(completed.stdout),
            {
                "schemaVersion": 1,
                "movementId": "drill_double_hand_snatches_first_contact",
                "framePx": [769, 665],
                "ballRadiusM": 0.1,
                "rightThumbPx": [318.0, 216.0],
                "maxWristBendDegrees": 45.0,
            },
        )

    def test_rejects_an_unknown_schema_version(self):
        data = json.loads(DEFAULT_CONFIG_PATH.read_text(encoding="utf-8"))
        data["schemaVersion"] = 2
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "reference.json"
            path.write_text(json.dumps(data), encoding="utf-8")

            with self.assertRaisesRegex(ReferencePoseConfigError, "schemaVersion.*1"):
                load_reference_catch_config(path)

    def test_exposes_pose_camera_and_reference_provenance(self):
        config = load_reference_catch_config()

        self.assertEqual(getattr(config, "licence", None), "CC0")
        self.assertIs(getattr(config, "publishable", None), True)
        self.assertEqual(
            getattr(config, "reference_asset_file", None),
            "references/two_hand_snatches_pull_in.png",
        )
        self.assertEqual(
            getattr(config, "reference_sha256", None),
            "d3ae61609bc1001a8e3cd541d73009f0391ed2d37b44469a4b240ff598c3e5d5",
        )
        self.assertEqual(
            getattr(config, "pixel_limits_px", None),
            {"ball": 5.0, "joints": 8.0, "fingertips": 10.0},
        )
        self.assertEqual(
            getattr(config, "ball_centre_m", None),
            (0.01131759, -0.58264951, 1.58630682),
        )
        self.assertEqual(
            getattr(config, "wrist_targets_m", None)["r"],
            (0.00722232, -0.39154312, 1.46621658),
        )
        self.assertEqual(
            getattr(config, "arm_poles", None)["l"],
            (-0.21203484, -0.34428039, -0.91461045),
        )
        self.assertEqual(
            getattr(config, "shoulder_targets_m", None),
            {
                "l": (0.14379841, -0.048, 1.291),
                "r": (-0.14793558, -0.038, 1.315),
            },
        )
        self.assertEqual(
            getattr(config, "hand_targets", None)["r"].finger_direction,
            (0.33437862, -0.28832047, 0.89725261),
        )
        self.assertEqual(
            getattr(config, "views", None)["referenceMatch"].resolution_px,
            (769, 665),
        )
        self.assertEqual(
            getattr(config, "views", None)["referenceMatch"].location_m,
            (2.818, -2.329, 1.92),
        )
        self.assertEqual(
            getattr(config, "views", None)["fullBody"].lens_mm,
            82.0,
        )

    def test_rejects_a_pose_vector_with_the_wrong_dimension(self):
        data = json.loads(DEFAULT_CONFIG_PATH.read_text(encoding="utf-8"))
        data["pose"]["ballCentreM"] = [1.0, 2.0]
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "reference.json"
            path.write_text(json.dumps(data), encoding="utf-8")

            with self.assertRaisesRegex(ReferencePoseConfigError, "ballCentreM.*3"):
                load_reference_catch_config(path)

    def test_rejects_pose_configuration_without_both_hands(self):
        data = json.loads(DEFAULT_CONFIG_PATH.read_text(encoding="utf-8"))
        data["pose"]["handTargets"].pop("r")
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "reference.json"
            path.write_text(json.dumps(data), encoding="utf-8")

            with self.assertRaisesRegex(ReferencePoseConfigError, "handTargets.*r"):
                load_reference_catch_config(path)

    def test_rejects_pose_configuration_without_both_shoulders(self):
        data = json.loads(DEFAULT_CONFIG_PATH.read_text(encoding="utf-8"))
        data["pose"]["shoulderTargetsM"] = {
            "l": [0.1469, 0.00423, 1.2762],
        }
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "reference.json"
            path.write_text(json.dumps(data), encoding="utf-8")

            with self.assertRaisesRegex(
                ReferencePoseConfigError,
                "shoulderTargetsM.*r",
            ):
                load_reference_catch_config(path)

    def test_rejects_an_incomplete_finger_curl_configuration(self):
        data = json.loads(DEFAULT_CONFIG_PATH.read_text(encoding="utf-8"))
        data["pose"]["fingerCurlDegrees"] = {
            "thumb": [6.0, 8.0],
            "index": [8.0, 12.0],
            "middle": [8.0, 12.0],
            "ring": [8.0, 12.0],
        }
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "reference.json"
            path.write_text(json.dumps(data), encoding="utf-8")

            with self.assertRaisesRegex(
                ReferencePoseConfigError,
                "fingerCurlDegrees.*pinky",
            ):
                load_reference_catch_config(path)


if __name__ == "__main__":
    unittest.main()
