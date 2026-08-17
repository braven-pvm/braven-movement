import importlib.util
import sys
import unittest
from pathlib import Path


MODULE_DIR = Path(__file__).resolve().parents[1]
MODULE_PATH = MODULE_DIR / "reference_pose_calibration.py"


def load_calibration_module():
    if not MODULE_PATH.is_file():
        raise AssertionError("reference pose calibration has not been implemented")
    spec = importlib.util.spec_from_file_location("reference_pose_calibration", MODULE_PATH)
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


class ReferencePoseCalibrationTest(unittest.TestCase):
    def test_uses_the_actual_supplied_reference_frame_dimensions(self):
        module = load_calibration_module()

        self.assertEqual(module.REFERENCE_FRAME_PX, (769, 665))

    def test_wrist_landmarks_use_the_anatomical_joint_not_the_watch_edge(self):
        module = load_calibration_module()

        self.assertEqual(module.REFERENCE_TARGETS_PX["left_wrist"], (420.0, 323.0))
        self.assertEqual(module.REFERENCE_TARGETS_PX["left_palm"], (398.0, 288.0))
        self.assertEqual(module.REFERENCE_TARGETS_PX["right_wrist"], (357.0, 273.0))
        self.assertEqual(module.REFERENCE_TARGETS_PX["right_palm"], (361.0, 236.0))

    def test_fingertip_labels_follow_left_and_right_hand_anatomy(self):
        module = load_calibration_module()

        self.assertEqual(module.REFERENCE_TARGETS_PX["left_thumb_tip"], (431.0, 246.0))
        self.assertEqual(module.REFERENCE_TARGETS_PX["left_index_tip"], (414.0, 261.0))
        self.assertEqual(module.REFERENCE_TARGETS_PX["left_middle_tip"], (393.0, 280.0))
        self.assertEqual(module.REFERENCE_TARGETS_PX["left_ring_tip"], (376.0, 294.0))
        self.assertEqual(module.REFERENCE_TARGETS_PX["left_pinky_tip"], (375.0, 319.0))
        self.assertEqual(module.REFERENCE_TARGETS_PX["right_thumb_tip"], (318.0, 216.0))

    def test_solves_a_reachable_pixel_ray_without_flipping_the_joint(self):
        module = load_calibration_module()

        point = module.point_on_camera_ray_at_radius(
            pixel=(50.0, 50.0),
            centre=(0.0, 0.0, -10.0),
            radius=1.0,
            preferred_direction=(0.0, 0.0, -1.0),
            camera_location=(0.0, 0.0, 0.0),
            camera_target=(0.0, 0.0, -1.0),
            frame=(100, 100),
            lens=50.0,
            sensor_width=100.0,
        )

        self.assertAlmostEqual(point[0], 0.0)
        self.assertAlmostEqual(point[1], 0.0)
        self.assertAlmostEqual(point[2], -11.0)

    def test_rejects_an_unreachable_pixel_ray(self):
        module = load_calibration_module()

        with self.assertRaisesRegex(module.PoseCalibrationError, "unreachable"):
            module.point_on_camera_ray_at_radius(
                pixel=(100.0, 50.0),
                centre=(0.0, 0.0, -10.0),
                radius=0.1,
                preferred_direction=(0.0, 0.0, -1.0),
                camera_location=(0.0, 0.0, 0.0),
                camera_target=(0.0, 0.0, -1.0),
                frame=(100, 100),
                lens=50.0,
                sensor_width=100.0,
            )

    def test_reference_target_schema_requires_both_complete_arm_and_hand_chains(self):
        module = load_calibration_module()
        self.assertTrue(
            hasattr(module, "validate_reference_target_schema"),
            "calibration target schema not implemented",
        )

        module.validate_reference_target_schema(
            module.REFERENCE_FRAME_PX,
            module.REFERENCE_TARGETS_PX,
        )
        incomplete = dict(module.REFERENCE_TARGETS_PX)
        incomplete.pop("right_wrist")

        with self.assertRaisesRegex(module.PoseCalibrationError, "right_wrist"):
            module.validate_reference_target_schema(module.REFERENCE_FRAME_PX, incomplete)

    def test_reports_hand_derived_pixel_errors_and_group_maxima(self):
        module = load_calibration_module()
        targets = {
            "ball_center": (10.0, 20.0),
            "left_elbow": (30.0, 40.0),
            "left_index_tip": (50.0, 60.0),
        }
        actual = {
            "ball_center": (13.0, 24.0),
            "left_elbow": (36.0, 48.0),
            "left_index_tip": (50.0, 72.0),
        }

        result = module.compare_projected_landmarks(targets, actual)

        self.assertEqual(result.errors_px["ball_center"], 5.0)
        self.assertEqual(result.errors_px["left_elbow"], 10.0)
        self.assertEqual(result.errors_px["left_index_tip"], 12.0)
        self.assertEqual(result.group_max_px["ball"], 5.0)
        self.assertEqual(result.group_max_px["joints"], 10.0)
        self.assertEqual(result.group_max_px["fingertips"], 12.0)

    def test_rejects_a_receipt_when_any_required_landmark_is_missing(self):
        module = load_calibration_module()

        with self.assertRaisesRegex(module.PoseCalibrationError, "missing.*left_elbow"):
            module.compare_projected_landmarks(
                {"ball_center": (10.0, 20.0), "left_elbow": (30.0, 40.0)},
                {"ball_center": (10.0, 20.0)},
            )

    def test_acceptance_requires_ball_joints_and_fingertips_within_policy(self):
        module = load_calibration_module()
        targets = {
            "ball_center": (10.0, 20.0),
            "left_elbow": (30.0, 40.0),
            "left_index_tip": (50.0, 60.0),
        }
        actual = {
            "ball_center": (14.0, 20.0),
            "left_elbow": (36.0, 40.0),
            "left_index_tip": (59.0, 60.0),
        }

        result = module.compare_projected_landmarks(targets, actual)
        module.validate_pixel_calibration(result)

        actual["left_elbow"] = (39.0, 40.0)
        result = module.compare_projected_landmarks(targets, actual)
        with self.assertRaisesRegex(module.PoseCalibrationError, "joints.*8.0"):
            module.validate_pixel_calibration(result)


if __name__ == "__main__":
    unittest.main()
