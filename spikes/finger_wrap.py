"""Close the fingers around the ball instead of leaving them straight.

All 104 finger parameters were frozen, so the hand met the ball as a flat plate
and touched it at one point. Measured on the size 5 netball, the fingertips
finished 7.4 cm off the surface with the palm exactly on it. A coach looking at
that does not see a catch, and "fingers up, thumbs in the middle" is a finger
instruction, so the grip is where a frozen hand shows.

What a wrap actually asks for is a distance, not a place. A fingertip has to end
up touching the ball; where on the ball is the finger's own business. That is
why this uses a distance error rather than a position target: giving each tip a
place to be would be authoring the grip again, one joint further down.

The fingers are also held open. The manual's first instruction for a two hand
catch is "Keep fingers up, thumbs in the middle", and its photographs show a
wide fan, but the model's hand at rest measures 7.7 cm from index tip to little
finger tip and the solve was closing it to 5.7 cm against a 22 cm ball. The
spread is set as a posture rather than solved: letting the distance term reach
it sent the little finger across the palm to touch the ball by the shortest
route, which is not what a hand does.
"""

from __future__ import annotations

import numpy as np

# The chains that close. Each finger flexes at three joints, and the thumb has
# its own.
FINGERS = ("index", "middle", "ring", "pinky")
THUMB_JOINTS = ("thumb1", "thumb2", "thumb3")
# Curl only. The spread is set rather than solved, below.
CURL_SUFFIX = "_rz"
# How far each digit fans out, in radians. The index and the little finger
# carry the fan; the middle and ring fingers sit between them and moving them
# does not change the span. The model allows 45.8 degrees either way.
SPREAD = {"index1_ry": 0.70, "middle1_ry": 0.18, "ring1_ry": -0.22,
          "pinky1_ry": -0.70, "thumb0_ry": 0.25, "thumb1_ry": 0.12}
# The thumb opens less than it looks like it should. Taken out to where the
# manual's photographs put it, it goes 1.4 cm into the ball and stays there,
# because only its curl is solved and the opening is fixed. At 0.25 the four
# fingers still fan to 12.3 cm across, the thumb sits 6.2 cm off the index, and
# nothing is inside the ball by more than a millimetre.

# Where a finger touches. The pad, not the bone, so a tip sits its own skin
# thickness outside the ball surface.
FINGER_SKIN_CM = 0.8
# The tips carry the wrap. The middle joints only stop a finger folding through
# the ball to get its tip there.
TIP_WEIGHT = 3.0
MIDDLE_WEIGHT = 1.0
THUMB_WEIGHT = 2.0


def curl_parameters(character, sides: tuple[str, ...]) -> list[str]:
    """Return the parameter names that close these hands."""
    names = set(character.parameter_transform.names)
    wanted: list[str] = []
    for side in sides:
        for finger in FINGERS:
            for segment in (1, 2, 3):
                name = f"{side}_{finger}{segment}{CURL_SUFFIX}"
                if name in names:
                    wanted.append(name)
        for joint in THUMB_JOINTS:
            name = f"{side}_{joint}{CURL_SUFFIX}"
            if name in names:
                wanted.append(name)
    return wanted


def enable_curl(character, enabled: np.ndarray, sides: tuple[str, ...]) -> np.ndarray:
    """Return the enabled mask with these hands' curl parameters switched on."""
    names = list(character.parameter_transform.names)
    freed = enabled.copy()
    for name in curl_parameters(character, sides):
        freed[names.index(name)] = True
    return freed


def spread_fingers(character, parameters: np.ndarray, sides: tuple[str, ...]):
    """Open the hand, as a posture that holds for the whole drill.

    These parameters are never optimised, so setting them once on the pose the
    solver starts from carries them through every frame. A hand waiting for a
    ball is already open, which is what the manual's photographs show.
    """
    names = list(character.parameter_transform.names)
    opened = np.asarray(parameters, dtype=np.float32).copy()
    for side in sides:
        for suffix, value in SPREAD.items():
            name = f"{side}_{suffix}"
            if name in names:
                # THE SAME VALUE ON BOTH HANDS. This negated the right until
                # 2026-09-01, on the stated belief that "the left and right
                # hands fan in opposite directions". The rig disagrees, and it
                # was measured rather than argued: the rest pose is symmetric
                # about x=0 to within 0.00005 cm, and setting the same value on
                # both hands mirrors to within 0.02 degrees, while negating it
                # breaks the mirror by up to 80.21. The negation collapsed the
                # right hand's fan from 14.37 cm to 1.75 and put its fingertips
                # out of anatomical order. Refer to docs/HAND_MIRROR_EVIDENCE.md
                # for all six pieces. The rig mirrors; the code does not need to.
                opened[names.index(name)] = value
    return opened


def wrap_joints(sides: tuple[str, ...]) -> dict[str, float]:
    """Return every joint that must reach the ball, and how hard it tries."""
    joints: dict[str, float] = {}
    for side in sides:
        for finger in FINGERS:
            joints[f"{side}_{finger}3"] = TIP_WEIGHT
            joints[f"{side}_{finger}2"] = MIDDLE_WEIGHT
        joints[f"{side}_thumb3"] = THUMB_WEIGHT
        joints[f"{side}_thumb2"] = MIDDLE_WEIGHT
    return joints


def wrap_constraints(
    character,
    index: dict[str, int],
    ball_centre_cm: np.ndarray,
    radius_cm: float,
    sides: tuple[str, ...],
):
    """Ask every finger to touch the ball, without saying where.

    The solver is imported here rather than at the top so the rest of this
    module, which is arithmetic, stays testable without it.
    """
    import pymomentum.solver2 as solver2

    error = solver2.DistanceErrorFunction(character, weight=1.0)
    origin = np.asarray(ball_centre_cm, dtype=np.float32)
    reach = float(radius_cm + FINGER_SKIN_CM)
    for joint, weight in wrap_joints(sides).items():
        if joint not in index:
            continue
        error.add_constraint(
            origin=origin,
            target=reach,
            parent=index[joint],
            offset=np.zeros(3, dtype=np.float32),
            weight=weight,
        )
    return error


def wrap_report(
    points: np.ndarray,
    index: dict[str, int],
    ball_centre_cm: np.ndarray,
    radius_cm: float,
    sides: tuple[str, ...],
) -> dict:
    """Report how far every finger ended up from the ball surface."""
    centre = np.asarray(ball_centre_cm, dtype=np.float64)
    gaps: dict[str, dict[str, float]] = {}
    for side in sides:
        tips = {}
        for name in [f"{finger}3" for finger in FINGERS] + ["thumb3"]:
            joint = f"{side}_{name}"
            if joint not in index:
                continue
            distance = float(np.linalg.norm(points[index[joint]] - centre))
            tips[name] = round(distance - radius_cm - FINGER_SKIN_CM, 2)
        gaps[side] = tips
    everything = [value for tips in gaps.values() for value in tips.values()]
    return {
        "fingertipGapCm": gaps,
        "worstFingertipGapCm": round(max(abs(value) for value in everything), 2),
        # A negative gap means a finger has gone into the ball.
        "deepestFingerInsideBallCm": round(-min(everything + [0.0]), 2),
    }
