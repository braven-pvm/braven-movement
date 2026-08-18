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

Only the joints that curl are freed. The spread across the hand is left alone,
because a netball is caught with the fingers spread as they already are, and
freeing the spread let the little finger swing across the palm to reach the
ball by the shortest route.
"""

from __future__ import annotations

import numpy as np

# The chains that close. Each finger flexes at three joints, and the thumb has
# its own.
FINGERS = ("index", "middle", "ring", "pinky")
THUMB_JOINTS = ("thumb1", "thumb2", "thumb3")
# Curl only. Spread and the small side to side rock stay frozen.
CURL_SUFFIX = "_rz"

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
