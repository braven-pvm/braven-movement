import importlib.util
import sys
import unittest
from pathlib import Path


MODULE_DIR = Path(__file__).resolve().parents[1]
MODULE_PATH = MODULE_DIR / "reference_pose_contract.py"
GENERATOR_PATH = MODULE_DIR / "blender_mpfb_reference_catch.py"
if str(MODULE_DIR) not in sys.path:
    sys.path.insert(0, str(MODULE_DIR))

from reference_pose_config import load_reference_catch_config  # noqa: E402


def load_contract_module():
    if not MODULE_PATH.is_file():
        raise AssertionError("reference pose contract has not been implemented")
    spec = importlib.util.spec_from_file_location("reference_pose_contract", MODULE_PATH)
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def valid_receipt():
    return {
        "movementId": "drill_double_hand_snatches_first_contact",
        "licence": "CC0",
        "rig": {
            "type": "game_engine",
            "bones": 53,
            "fingerBones": 30,
            "weightedFingerGroups": 30,
        },
        "pose": {
            "leftElbowDegrees": 118.0,
            "rightElbowDegrees": 112.0,
            "leftPalmToBallSurfaceM": 0.045,
            "rightPalmToBallSurfaceM": 0.052,
        },
        "camera": {"type": "PERSP", "width": 1080, "height": 933},
        "visualQa": {"referenceCompared": True},
        "calibration": {"status": "passed"},
        "anatomy": {
            "status": "passed",
            "leftWristBendDegrees": 32.0,
            "rightWristBendDegrees": 28.0,
            "leftForearmRollDegrees": 55.0,
            "rightForearmRollDegrees": 48.0,
            "maxFingerJointBendDegrees": 12.0,
            "maxFingerBaseDeviationDegrees": 34.0,
        },
    }


class ReferencePoseContractTest(unittest.TestCase):
    def test_generator_resolves_mpfb_assets_from_blender_user_extensions(self):
        source = GENERATOR_PATH.read_text(encoding="utf-8")

        self.assertIn('bpy.utils.user_resource("EXTENSIONS")', source)
        self.assertNotIn(r"C:\Users\Marius", source)

    def test_default_configuration_exposes_anatomical_limits(self):
        limits = load_reference_catch_config().anatomy_limits_degrees

        self.assertEqual(limits["forearmRoll"], 75.0)
        self.assertEqual(limits["wristBend"], 45.0)
        self.assertEqual(limits["fingerJointBend"], 25.0)
        self.assertEqual(limits["fingerBaseDeviation"], 40.0)

    def test_accepts_cc0_gameengine_pose_with_all_weighted_finger_bones(self):
        module = load_contract_module()

        result = module.validate_reference_catch_receipt(valid_receipt())

        self.assertEqual(result.movement_id, "drill_double_hand_snatches_first_contact")
        self.assertEqual(result.finger_bones, 30)
        self.assertTrue(result.reference_compared)

    def test_rejects_pose_when_any_finger_bone_is_missing(self):
        module = load_contract_module()
        receipt = valid_receipt()
        receipt["rig"]["fingerBones"] = 29

        with self.assertRaisesRegex(module.PoseContractError, "30 finger bones"):
            module.validate_reference_catch_receipt(receipt)

    def test_rejects_hands_that_are_not_close_to_the_ball_surface(self):
        module = load_contract_module()
        receipt = valid_receipt()
        receipt["pose"]["rightPalmToBallSurfaceM"] = 0.24

        with self.assertRaisesRegex(module.PoseContractError, "ball surface"):
            module.validate_reference_catch_receipt(receipt)

    def test_rejects_reference_compared_receipt_without_pixel_calibration(self):
        module = load_contract_module()
        receipt = valid_receipt()
        receipt.pop("calibration")

        with self.assertRaisesRegex(module.PoseContractError, "pixel calibration"):
            module.validate_reference_catch_receipt(receipt)

    def test_rejects_receipt_without_anatomical_wrist_validation(self):
        module = load_contract_module()
        receipt = valid_receipt()
        receipt.pop("anatomy")

        with self.assertRaisesRegex(module.PoseContractError, "wrist anatomy"):
            module.validate_reference_catch_receipt(receipt)

    def test_rejects_painful_wrist_bend_or_excessive_forearm_roll(self):
        module = load_contract_module()
        receipt = valid_receipt()
        receipt["anatomy"]["leftWristBendDegrees"] = 58.0

        with self.assertRaisesRegex(module.PoseContractError, "wrist bend"):
            module.validate_reference_catch_receipt(receipt)

        receipt = valid_receipt()
        receipt["anatomy"]["rightForearmRollDegrees"] = 105.0
        with self.assertRaisesRegex(module.PoseContractError, "forearm roll"):
            module.validate_reference_catch_receipt(receipt)

        receipt = valid_receipt()
        receipt["anatomy"]["maxFingerJointBendDegrees"] = 31.0
        with self.assertRaisesRegex(module.PoseContractError, "finger joint"):
            module.validate_reference_catch_receipt(receipt)

        receipt = valid_receipt()
        receipt["anatomy"]["maxFingerBaseDeviationDegrees"] = 44.0
        with self.assertRaisesRegex(module.PoseContractError, "finger base"):
            module.validate_reference_catch_receipt(receipt)


if __name__ == "__main__":
    unittest.main()
