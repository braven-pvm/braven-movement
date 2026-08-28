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
