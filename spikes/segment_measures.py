"""Frame-free joint measures taken straight from joint centres.

The noise study and the proof of concept both failed the same way: a segment
frame built from a small landmark triangle inverts when the landmarks move, and
two arms then report the same angle by construction.

These measures avoid the problem. Each one is an angle between two long vectors
that joint centres define directly. There is no synthesised landmark, no plane
normal to flip, and no Euler sequence to hit gimbal lock. For a hinge such as the
elbow, the result is exactly the ISB flexion.

Use these for the quantities a coach acts on. Use the full ISB decomposition in
isb_angles.py when the segment frames come from real bony landmarks or from bone
orientations.
"""

from __future__ import annotations

import math

Vector = tuple[float, float, float]

_EPSILON = 1e-9


class SegmentMeasureError(ValueError):
    pass


def _subtract(left: Vector, right: Vector) -> Vector:
    return (left[0] - right[0], left[1] - right[1], left[2] - right[2])


def _dot(left: Vector, right: Vector) -> float:
    return left[0] * right[0] + left[1] * right[1] + left[2] * right[2]


def _length(vector: Vector) -> float:
    return math.sqrt(_dot(vector, vector))


def angle_between_degrees(first: Vector, second: Vector, name: str) -> float:
    """Return the angle between two vectors, in degrees, from 0 to 180."""
    first_length = _length(first)
    second_length = _length(second)
    if first_length < _EPSILON or second_length < _EPSILON:
        raise SegmentMeasureError(f"{name} has a zero-length vector")
    cosine = _dot(first, second) / (first_length * second_length)
    return math.degrees(math.acos(max(-1.0, min(1.0, cosine))))


def included_angle_degrees(
    first_point: Vector, pivot: Vector, second_point: Vector, name: str
) -> float:
    """Return the angle at the pivot, between the two other points."""
    return angle_between_degrees(
        _subtract(first_point, pivot), _subtract(second_point, pivot), name
    )


def elbow_flexion_degrees(
    *, shoulder: Vector, elbow: Vector, wrist: Vector
) -> float:
    """Return elbow flexion in degrees. A straight arm is zero.

    The elbow is a hinge, so flexion is the whole story for the sagittal plane.
    A straight arm puts the two segment vectors at 180 degrees to each other,
    which is zero flexion by the anatomical convention.
    """
    return 180.0 - included_angle_degrees(shoulder, elbow, wrist, "elbow")


def knee_flexion_degrees(*, hip: Vector, knee: Vector, ankle: Vector) -> float:
    """Return knee flexion in degrees. A straight leg is zero."""
    return 180.0 - included_angle_degrees(hip, knee, ankle, "knee")


def shoulder_elevation_degrees(
    *, pelvis: Vector, neck: Vector, shoulder: Vector, elbow: Vector
) -> float:
    """Return how far the upper arm is raised away from the trunk, in degrees.

    Arms hanging beside the trunk give zero. An arm straight overhead gives 180.
    The trunk supplies the reference direction, so the measure holds when the
    athlete leans, which a world-vertical reference would not.
    """
    trunk_down = _subtract(pelvis, neck)
    humerus = _subtract(elbow, shoulder)
    return angle_between_degrees(humerus, trunk_down, "shoulder elevation")


def trunk_lean_degrees(*, pelvis: Vector, neck: Vector, up: Vector) -> float:
    """Return how far the trunk leans away from the given up direction."""
    return angle_between_degrees(_subtract(neck, pelvis), up, "trunk lean")


def hip_flexion_degrees(
    *, neck: Vector, pelvis: Vector, knee: Vector
) -> float:
    """Return hip flexion in degrees. Standing upright is zero."""
    return 180.0 - included_angle_degrees(neck, pelvis, knee, "hip")


DEGREES = "degrees"
CENTIMETRES = "centimetres"

# THE UNIT OF EVERY MEASURE THE ENGINE WRITES, BY ITS OWN NAME.
#
# `measure_frame` produces these names and their values. Until now nothing
# recorded what they are IN, and every consumer read every column as degrees.
# One of them is not an angle: `footHeightGapCm` is a length. A reference file
# that announces itself as angles and carries a centimetre column is the
# units-across-a-boundary fault this project has recorded six times, and adding
# it deliberately would be worse than finding it.
#
# This lives here, in a module that imports `math` and nothing else, so a test
# and a stdlib-only consumer can both read it without a solver.
#
# The video lane keeps its OWN spelling of these units in `video_measures`, and
# that duplication is deliberate. Its gate asks whether the engine's declared
# unit matches the registry's, and that question is only worth asking while the
# two are spelled independently. Reading one from the other would make the
# check pass by construction, which is the tautology this project keeps
# finding. `test_measure_units.py` compares the two rather than merging them.
MEASURE_UNITS: dict[str, str] = {
    "trunkLeanDegrees": DEGREES,
    "trunkTurnDegrees": DEGREES,
    "leftElbowFlexionDegrees": DEGREES,
    "rightElbowFlexionDegrees": DEGREES,
    "leftShoulderElevationDegrees": DEGREES,
    "rightShoulderElevationDegrees": DEGREES,
    "leftKneeFlexionDegrees": DEGREES,
    "rightKneeFlexionDegrees": DEGREES,
    "footHeightGapCm": CENTIMETRES,
}


def unit_of(measure: str) -> str:
    """Return the unit a measure is in.

    RAISES for a measure that is not declared. It does not fall back to
    degrees, and it does not read the name's suffix.

    Both of those were considered and both are how this breaks quietly. A
    default makes the next length silently an angle. A suffix rule is a
    convention two lanes must hold in their heads, and this whole table exists
    because a five-item list drifted from a nine-item one while everyone
    believed they agreed.
    """
    try:
        return MEASURE_UNITS[measure]
    except KeyError:
        raise KeyError(
            f"{measure!r} has no declared unit. Add it to "
            "segment_measures.MEASURE_UNITS. It is NOT assumed to be degrees: "
            "one graded measure is centimetres, and a consumer that reads a "
            "length as an angle is the fault this table exists to prevent."
        ) from None
