"""The geometry of a closing finger, with no Blender in it.

This exists so that the knuckle can be tested. The renderer once built a
finger's chain of directions as `(0.0, first, first + second)`, which gave the
FIRST bone of every chain a rotation of zero. Only the middle and distal joints
bent, by 8 and 12 degrees. A grip flexes the knuckle hardest, and that one did
not flex it at all, so every finger pointed away from the ball while the render
looked plausible and the receipt read PASS.

That defect shipped 99 images. It had no guard for a day after it was fixed,
because the function that carries it is a closure inside a Blender module and a
test cannot import `bpy`. A guard written against the SOURCE TEXT would pass on
a file that computes the wrong angle, so it would be a guard in name only. The
honest guard calls the function and reads the angles, and this module is what
makes that possible.

Everything here is plain arithmetic on 3-tuples. The Blender side wraps the
result in `Vector` and does not repeat the mathematics.
"""

from __future__ import annotations

import math

Vector3 = tuple[float, float, float]


def normalise(vector: Vector3) -> Vector3:
    length = math.sqrt(sum(component * component for component in vector))
    if length < 1e-12:
        raise ValueError("cannot normalise a zero length vector")
    return (vector[0] / length, vector[1] / length, vector[2] / length)


def angle_between_degrees(first: Vector3, second: Vector3) -> float:
    """The angle between two directions, in degrees."""
    a, b = normalise(first), normalise(second)
    dot = max(-1.0, min(1.0, sum(x * y for x, y in zip(a, b))))
    return math.degrees(math.acos(dot))


def cumulative_angles(
    knuckle_degrees: float, curl_degrees: tuple[float, float]
) -> tuple[float, float, float]:
    """How far each bone of the chain has turned from the palm direction.

    The knuckle angle belongs to the FIRST bone and carries into the two after
    it, because each bone continues from the one before. Starting this tuple at
    zero is the defect: it holds the knuckle straight and bends only the joints
    beyond it, which points the finger away from what the hand is closing on.
    """
    first, second = curl_degrees
    return (
        knuckle_degrees,
        knuckle_degrees + first,
        knuckle_degrees + first + second,
    )


def dominant_axis(components: Vector3) -> int:
    """Index of the largest component by magnitude.

    `FLEXION_AXIS` names, per digit, which euler component of the knuckle is
    flexion. Everything else is treated as deviation and bounded by a different
    licence. If that name is wrong for a digit, the two are swapped: real
    flexion gets measured against the deviation limit and stopped early, or
    deviation gets the flexion licence and runs far past the joint. Neither
    raises. The finger simply ends up somewhere a hand cannot go.

    The test is DOMINANCE and not purity. The thumb's flexion is about its own
    Z and carries real components on the other two axes; demanding a clean
    single-axis rotation would fail on a correct rig.
    """
    return max(range(len(components)), key=lambda index: abs(components[index]))


Matrix3 = "tuple[tuple[float, float, float], ...]"


def relative_rotation(rest, now):
    """The rotation that takes `rest` to `now`, as a 3x3.

    This is `rest` inverted then `now`, and for a rotation matrix the inverse
    is the transpose. It exists as a separate function so that a test can CALL
    it: the obvious alternative, subtracting euler components, is not the delta
    at all, because rotations do not commute. Measured on the rig against this,
    the euler difference was wrong by up to 4.5 degrees on one axis under a
    large aim, and reading `now` alone carries the aim and the splay into a
    number that is meant to describe only the flexion.
    """
    transposed = tuple(
        tuple(rest[row][column] for row in range(3)) for column in range(3)
    )
    return tuple(
        tuple(
            sum(transposed[row][k] * now[k][column] for k in range(3))
            for column in range(3)
        )
        for row in range(3)
    )


def axis_share(components: Vector3, axis: int) -> float:
    """What fraction of the largest component the named axis carries.

    RANK is the wrong test. Measured on the real rig at the solved grip, the
    thumb turns on a diagonal: x=+21.1 and z=+20.0 on the left hand. Which of
    those two "dominates" is decided by one degree, and on the right hand the
    same pose decides it the other way. A rank test on the thumb returns a coin
    toss that changes with the hand, the phase and the rig, so a first version
    of this check fired on a correct thumb and killed a render.
    """
    largest = max(abs(value) for value in components)
    if largest <= 0.0:
        return 0.0
    return abs(components[axis]) / largest


# Measured over 90 knuckle rotations, 5 drills, several phases, on the real
# rig, using the relative rotation and not a difference of euler angles.
#
#   index, middle, ring, pinky   share 1.000 in every one of 72 readings
#   thumb                        share 0.600 to 1.000, median 0.831
#
# A wrong name is wrong by an order of magnitude: naming Y for the index would
# carry 0.08 and naming Z would carry 0.16. So for the four fingers a floor of
# 0.5 sits a factor of six clear of both sides and is safe.
#
# THE THUMB IS NOT ASSERTED, and the reason is measurement and not caution.
# Its observed floor of 0.600 is close to its worst plausible value: the curl
# plane runs 47 to 61 degrees off the thumb's flexion axis, per the measured
# note in `within_limits`, and cos(61) is 0.48. A threshold safe for the
# fingers could fire on a correct thumb in a pose nobody has rendered yet, and
# three of the eight drills are still unmeasured. The thumb's share is RECORDED
# in the receipt every phase, so the calibration finishes with data rather than
# with a guess.
ASSERTED_DIGITS = ("index", "middle", "ring", "pinky")
MIN_AXIS_SHARE = 0.5


def axis_complaint(
    digit: str,
    turned: Vector3,
    axis: int,
    *,
    floor_degrees: float,
    min_share: float = MIN_AXIS_SHARE,
) -> str | None:
    """Why this knuckle's named flexion axis is wrong, or None if it is not.

    `turned` is the rotation the FLEXION added, taken as the relative rotation
    between the unflexed pose and this one. It must never be a difference of
    euler angles: euler components do not subtract for rotations that do not
    commute, and under a large aim the error reached 4.5 degrees on one axis.

    Returns a message rather than raising, so that the rule can be called by a
    test. The only guard this rule had before was an `assertIn` on the source
    text, which is the guard class this project's worst defect was fixed to
    stop relying on.
    """
    if digit not in ASSERTED_DIGITS:
        return None
    largest = max(abs(value) for value in turned)
    if largest < floor_degrees:
        return None
    share = axis_share(turned, axis)
    if share >= min_share:
        return None
    return (
        f"{digit} is set to flex about axis {axis}, which carries only "
        f"{share:.2f} of the turn: x={turned[0]:.1f} y={turned[1]:.1f} "
        f"z={turned[2]:.1f} degrees. The flexion and deviation limits are "
        "being applied to the wrong components."
    )


def dominance_margin(components: Vector3) -> float:
    """How far the largest component exceeds the next largest.

    Carried into the receipt so that a rig drifting towards an axis flip is
    visible BEFORE it flips. A margin falling towards zero says the assumption
    is going; a margin that has gone negative says it went.
    """
    ordered = sorted((abs(value) for value in components), reverse=True)
    return ordered[0] - ordered[1]


def curl_directions(
    base: Vector3,
    bend: Vector3,
    knuckle_degrees: float,
    curl_degrees: tuple[float, float],
) -> list[Vector3]:
    """Unit directions for the three bones of one finger.

    `base` points along the finger when the hand is open. `bend` is the
    direction the finger closes towards, already square to `base`. Each bone
    turns from `base` towards `bend` by its cumulative angle.
    """
    base, bend = normalise(base), normalise(bend)
    return [
        normalise(
            tuple(
                base[axis] * math.cos(math.radians(angle))
                + bend[axis] * math.sin(math.radians(angle))
                for axis in range(3)
            )
        )
        for angle in cumulative_angles(knuckle_degrees, curl_degrees)
    ]
