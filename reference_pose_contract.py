from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping


class PoseContractError(ValueError):
    pass


@dataclass(frozen=True)
class ReferenceCatchReceipt:
    movement_id: str
    finger_bones: int
    reference_compared: bool
    pixel_calibrated: bool
    anatomically_valid: bool


def validate_reference_catch_receipt(
    payload: Mapping[str, Any],
) -> ReferenceCatchReceipt:
    calibration = payload.get("calibration")
    if not isinstance(calibration, Mapping):
        raise PoseContractError("pixel calibration against the reference is required")
    anatomy = payload.get("anatomy")
    if not isinstance(anatomy, Mapping):
        raise PoseContractError("wrist anatomy validation is required")
    try:
        movement_id = str(payload["movementId"])
        licence = str(payload["licence"])
        rig = payload["rig"]
        pose = payload["pose"]
        camera = payload["camera"]
        visual_qa = payload["visualQa"]
        rig_type = str(rig["type"])
        bones = int(rig["bones"])
        finger_bones = int(rig["fingerBones"])
        weighted_finger_groups = int(rig["weightedFingerGroups"])
        elbow_angles = (
            float(pose["leftElbowDegrees"]),
            float(pose["rightElbowDegrees"]),
        )
        palm_surface_distances = (
            float(pose["leftPalmToBallSurfaceM"]),
            float(pose["rightPalmToBallSurfaceM"]),
        )
        camera_type = str(camera["type"])
        width = int(camera["width"])
        height = int(camera["height"])
        reference_compared = bool(visual_qa["referenceCompared"])
        pixel_calibrated = str(calibration["status"]) == "passed"
        anatomically_valid = str(anatomy["status"]) == "passed"
        wrist_bends = (
            float(anatomy["leftWristBendDegrees"]),
            float(anatomy["rightWristBendDegrees"]),
        )
        forearm_rolls = (
            float(anatomy["leftForearmRollDegrees"]),
            float(anatomy["rightForearmRollDegrees"]),
        )
        max_finger_joint_bend = float(anatomy["maxFingerJointBendDegrees"])
        max_finger_base_deviation = float(
            anatomy["maxFingerBaseDeviationDegrees"]
        )
    except (KeyError, TypeError, ValueError) as error:
        raise PoseContractError(f"invalid reference pose receipt: {error}") from error

    if not movement_id.strip():
        raise PoseContractError("movement id must not be blank")
    if licence != "CC0":
        raise PoseContractError("reference pose assets must be CC0")
    if rig_type != "game_engine" or bones < 53:
        raise PoseContractError("reference pose must use the MPFB game_engine rig")
    if finger_bones != 30 or weighted_finger_groups != 30:
        raise PoseContractError("reference pose must retain all 30 finger bones and weights")
    if any(angle < 95.0 or angle > 145.0 for angle in elbow_angles):
        raise PoseContractError("catching elbow angles must stay between 95 and 145 degrees")
    if any(distance < 0.0 or distance > 0.12 for distance in palm_surface_distances):
        raise PoseContractError("each palm must stay within 0.12 m of the ball surface")
    if camera_type != "PERSP" or width != 1080 or height != 933:
        raise PoseContractError("reference crop must use the 1080x933 perspective camera")
    if not reference_compared:
        raise PoseContractError("visual comparison against the reference is required")
    if not pixel_calibrated:
        raise PoseContractError("pixel calibration against the reference must pass")
    if not anatomically_valid:
        raise PoseContractError("wrist anatomy validation must pass")
    if any(angle < 0.0 or angle > 45.0 for angle in wrist_bends):
        raise PoseContractError("wrist bend must stay between 0 and 45 degrees")
    if any(angle < 0.0 or angle > 75.0 for angle in forearm_rolls):
        raise PoseContractError("forearm roll must stay between 0 and 75 degrees")
    if max_finger_joint_bend < 0.0 or max_finger_joint_bend > 25.0:
        raise PoseContractError("finger joint bend must stay between 0 and 25 degrees")
    if max_finger_base_deviation < 0.0 or max_finger_base_deviation > 40.0:
        raise PoseContractError("finger base deviation must stay between 0 and 40 degrees")

    return ReferenceCatchReceipt(
        movement_id=movement_id,
        finger_bones=finger_bones,
        reference_compared=reference_compared,
        pixel_calibrated=pixel_calibrated,
        anatomically_valid=anatomically_valid,
    )
