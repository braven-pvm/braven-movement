import json
import math
import os
import subprocess
import tempfile
import unittest
from pathlib import Path


REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_CONFIG_PATH = REPOSITORY_ROOT / "config" / "reference_catch.v1.json"
GENERATOR_PATH = REPOSITORY_ROOT / "blender_mpfb_reference_catch.py"
BLENDER_PATH = Path(
    os.environ.get(
        "BRAVEN_BLENDER_EXE",
        r"C:\Program Files\Blender Foundation\Blender 4.5\blender.exe",
    )
)


@unittest.skipUnless(
    os.environ.get("BRAVEN_RUN_BLENDER_INTEGRATION") == "1",
    "set BRAVEN_RUN_BLENDER_INTEGRATION=1 to run Blender/MPFB integration",
)
class BlenderReferenceConfigIntegrationTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        if not BLENDER_PATH.is_file():
            raise AssertionError(f"Blender not found: {BLENDER_PATH}")
        data = json.loads(DEFAULT_CONFIG_PATH.read_text(encoding="utf-8"))
        data["movementId"] = "portable_config_probe"
        cls.temporary_directory = tempfile.TemporaryDirectory()
        cls.temporary = Path(cls.temporary_directory.name)
        config_path = cls.temporary / "reference.json"
        output_path = cls.temporary / "output"
        config_path.write_text(json.dumps(data), encoding="utf-8")
        cls.expected_config_sha256 = _sha256(config_path)
        completed = subprocess.run(
            [
                str(BLENDER_PATH),
                "-b",
                "--python-exit-code",
                "9",
                "-P",
                str(GENERATOR_PATH),
                "--",
                "--config",
                str(config_path),
                "--output",
                str(output_path),
            ],
            cwd=cls.temporary,
            text=True,
            capture_output=True,
            timeout=180,
            check=False,
        )
        if completed.returncode != 0:
            raise AssertionError(
                f"stdout:\n{completed.stdout}\nstderr:\n{completed.stderr}"
            )
        cls.receipt = json.loads(
            (output_path / "braven_mpfb_reference_catch.json").read_text(
                encoding="utf-8"
            )
        )

    @classmethod
    def tearDownClass(cls):
        cls.temporary_directory.cleanup()

    def test_generator_uses_the_supplied_config_for_the_receipt(self):
        self.assertEqual(self.receipt["movementId"], "portable_config_probe")
        self.assertEqual(self.receipt["configuration"]["schemaVersion"], 1)
        self.assertEqual(
            self.receipt["configuration"]["sha256"],
            self.expected_config_sha256,
        )

    def test_receipt_proves_the_panelled_netball_and_studio_presentation(self):
        presentation = self.receipt.get("presentation")
        self.assertIsNotNone(
            presentation,
            "receipt must identify the deterministic presentation treatment",
        )
        self.assertEqual(presentation["style"], "premium_coaching_studio")
        self.assertEqual(presentation["ball"]["type"], "panelled_netball")
        self.assertGreaterEqual(presentation["ball"]["seamLoops"], 6)
        self.assertEqual(
            presentation["ball"]["surface"],
            "procedural_dimple_grip",
        )
        self.assertEqual(
            presentation["ball"]["graphic"],
            "clean_three_colour_panel_graphic",
        )
        self.assertGreaterEqual(presentation["ball"]["diameterM"], 0.218)
        self.assertLessEqual(presentation["ball"]["diameterM"], 0.224)
        self.assertTrue(presentation["studio"]["cyclorama"])
        self.assertGreaterEqual(presentation["studio"]["lightCount"], 4)
        self.assertEqual(presentation["kit"]["footwear"], "sports_trainers")
        self.assertTrue(
            any(
                Path(asset["path"]).name == "shoes05.mhclo"
                for asset in self.receipt["source"]["assets"]
            ),
            "the presentation receipt must retain the trainer source asset",
        )

    def test_studio_background_covers_every_render_corner(self):
        for view_name in ("referenceCrop", "referenceMatch", "fullBody"):
            with self.subTest(view=view_name):
                corners = self.receipt["views"][view_name].get("cornerRgb")
                self.assertIsNotNone(
                    corners,
                    "render receipt must expose studio edge coverage",
                )
                for corner_name, rgb in corners.items():
                    with self.subTest(view=view_name, corner=corner_name):
                        self.assertGreater(
                            sum(rgb),
                            0.12,
                            "camera must not see past the cyclorama into black world",
                        )

    def test_render_preserves_the_approved_thumb_orientation(self):
        actual = self.receipt["calibration"]["actualPx"]
        for side in ("left", "right"):
            with self.subTest(side=side):
                self.assertGreater(
                    actual[f"{side}_thumb_tip"][0],
                    actual[f"{side}_palm"][0] + 20.0,
                    f"{side} thumb must remain on the approved side of its hand",
                )
                self.assertLessEqual(
                    self.receipt["anatomy"][f"{side}PalmNormalErrorDegrees"],
                    5.0,
                    f"{side} hand must retain its approved reference plane",
                )

    def test_ball_remains_at_eye_height_and_left_of_both_hands(self):
        actual = self.receipt["calibration"]["actualPx"]
        ball = actual["ball_center"]
        self.assertGreaterEqual(ball[1], 180.0)
        self.assertLessEqual(ball[1], 200.0)
        self.assertLess(ball[0], actual["left_palm"][0])
        self.assertLess(ball[0], actual["right_palm"][0])

    def test_ball_depth_sits_between_the_approved_hands(self):
        ordering = self.receipt["pose"].get("ballDepthOrdering")
        self.assertIsNotNone(
            ordering,
            "receipt must prove the ball is between the approved hands",
        )
        self.assertLess(
            ordering["foregroundHandBackDepthM"],
            ordering["ballCentreDepthM"],
        )
        self.assertLess(
            ordering["ballCentreDepthM"],
            ordering["rearHandFrontDepthM"],
        )

    def test_approved_hand_positions_remain_locked_in_world_space(self):
        arms = self.receipt["pose"]["armsM"]
        expected = {
            "l": (0.17887096, -0.4450906, 1.4323828),
            "r": (0.00722232, -0.39154312, 1.46621658),
        }
        for side, target in expected.items():
            with self.subTest(side=side):
                for actual, wanted in zip(arms[side]["wrist"], target):
                    self.assertAlmostEqual(actual, wanted, delta=0.00001)

    def test_raised_hands_enter_the_fixed_ball_path(self):
        actual = self.receipt["calibration"]["actualPx"]
        ball_height = actual["ball_center"][1]
        reachable_palm_offsets = {
            "left": (55.0, 68.0),
            "right": (25.0, 35.0),
        }
        for side, (minimum, maximum) in reachable_palm_offsets.items():
            with self.subTest(side=side):
                palm_offset = actual[f"{side}_palm"][1] - ball_height
                self.assertGreaterEqual(palm_offset, minimum)
                self.assertLessEqual(palm_offset, maximum)
        self.assertLessEqual(self.receipt["pose"]["leftPalmToBallSurfaceM"], 0.22)
        self.assertLessEqual(self.receipt["pose"]["rightPalmToBallSurfaceM"], 0.12)

    def test_raised_hands_keep_the_reference_arm_extension(self):
        for side in ("left", "right"):
            with self.subTest(side=side):
                angle = self.receipt["pose"][f"{side}ElbowDegrees"]
                self.assertGreaterEqual(angle, 95.0)
                self.assertLessEqual(angle, 145.0)

    def test_ball_side_shoulder_is_elevated_without_overcorrection(self):
        arms = self.receipt["pose"]["armsM"]
        height_difference = (
            arms["r"]["shoulder"][2] - arms["l"]["shoulder"][2]
        )
        self.assertGreaterEqual(
            height_difference,
            0.02,
            "the anatomical right, ball-side shoulder must be physically elevated",
        )
        self.assertLessEqual(
            height_difference,
            0.04,
            "the shoulder elevation must not compensate for the camera angle",
        )
        actual = self.receipt["calibration"]["actualPx"]
        projected_difference = (
            actual["left_shoulder"][1] - actual["right_shoulder"][1]
        )
        self.assertGreaterEqual(
            projected_difference,
            10.0,
            "the reference view must visibly show the diagonal shoulder line",
        )
        self.assertLessEqual(projected_difference, 35.0)

    def test_camera_presents_the_reference_three_quarter_profile(self):
        actual = self.receipt["calibration"]["actualPx"]
        shoulder_span = math.dist(
            actual["left_shoulder"],
            actual["right_shoulder"],
        )
        head_height = math.dist(actual["head_top"], actual["head_base"])
        self.assertGreaterEqual(shoulder_span / head_height, 1.15)
        self.assertLessEqual(shoulder_span / head_height, 1.5)

    def test_projected_elbows_follow_the_reference_arm_geometry(self):
        actual = self.receipt["calibration"]["actualPx"]
        expected_ranges = {
            "left": (85.0, 105.0),
            "right": (70.0, 90.0),
        }
        for side, (minimum, maximum) in expected_ranges.items():
            with self.subTest(side=side):
                angle = _screen_joint_angle(
                    actual[f"{side}_shoulder"],
                    actual[f"{side}_elbow"],
                    actual[f"{side}_wrist"],
                )
                self.assertGreaterEqual(angle, minimum)
                self.assertLessEqual(angle, maximum)

    def test_projected_elbow_positions_follow_the_reference_arm_triangles(self):
        actual = self.receipt["calibration"]["actualPx"]
        expected_ranges = {
            "left": ((0.35, 0.56), (-0.55, -0.38)),
            "right": ((0.45, 0.65), (-0.70, -0.50)),
        }
        for side, (along_range, offset_range) in expected_ranges.items():
            with self.subTest(side=side):
                along, offset = _screen_triangle_coordinates(
                    actual[f"{side}_shoulder"],
                    actual[f"{side}_elbow"],
                    actual[f"{side}_wrist"],
                )
                self.assertGreaterEqual(along, along_range[0])
                self.assertLessEqual(along, along_range[1])
                self.assertGreaterEqual(offset, offset_range[0])
                self.assertLessEqual(offset, offset_range[1])

    def test_arms_preserve_the_anatomical_hand_limits(self):
        anatomy = self.receipt["anatomy"]
        for side in ("left", "right"):
            with self.subTest(side=side):
                self.assertLessEqual(anatomy[f"{side}WristBendDegrees"], 45.0)
                self.assertLessEqual(anatomy[f"{side}ForearmRollDegrees"], 75.0)

    def test_fingers_have_a_shallow_non_flat_curl(self):
        minimum = self.receipt["anatomy"].get("minimumFingerJointBendDegrees")
        self.assertIsNotNone(
            minimum,
            "receipt must prove that every finger chain is no longer flat",
        )
        self.assertGreaterEqual(minimum, 6.0)
        self.assertLessEqual(
            self.receipt["anatomy"]["maxFingerJointBendDegrees"],
            25.0,
        )


def _sha256(path: Path) -> str:
    import hashlib

    return hashlib.sha256(path.read_bytes()).hexdigest()


def _screen_joint_angle(a, pivot, b):
    first = (a[0] - pivot[0], a[1] - pivot[1])
    second = (b[0] - pivot[0], b[1] - pivot[1])
    cosine = sum(x * y for x, y in zip(first, second)) / (
        math.hypot(*first) * math.hypot(*second)
    )
    return math.degrees(math.acos(max(-1.0, min(1.0, cosine))))


def _screen_triangle_coordinates(shoulder, elbow, wrist):
    axis = (wrist[0] - shoulder[0], wrist[1] - shoulder[1])
    length = math.hypot(*axis)
    forward = (axis[0] / length, axis[1] / length)
    perpendicular = (-forward[1], forward[0])
    elbow_offset = (
        (elbow[0] - shoulder[0]) / length,
        (elbow[1] - shoulder[1]) / length,
    )
    return (
        sum(x * y for x, y in zip(elbow_offset, forward)),
        sum(x * y for x, y in zip(elbow_offset, perpendicular)),
    )


if __name__ == "__main__":
    unittest.main()
