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
    # THREE LENGTHS, NOT ONE. `leftFootHeightCm` and `rightFootHeightCm` were
    # written by both solvers and declared by neither, so `unit_of` raised for
    # two measures the engine produces on every frame of every drill. Nothing
    # caught it: the units test asks whether every GRADED measure has a unit,
    # and these two are written and not yet graded. The first drill to grade a
    # foot height would have raised instead of grading it. A guard that solves
    # a drill and diffs the WRITTEN keys against this table now covers them.
    "leftFootHeightCm": CENTIMETRES,
    "rightFootHeightCm": CENTIMETRES,
    "footHeightGapCm": CENTIMETRES,
    # THE BALL CENTRE ABOVE THE COURT, y = 0, AND NOT ABOVE THE REST ANKLE.
    #
    # The three foot heights above measure from the REST LEFT FOOT, which is
    # the `l_foot` ANKLE joint and sits 7.3886 cm above the court. That zero is
    # right for a foot: it reads how far the foot has lifted from where it
    # rests, and it is zero at rest. IT IS WRONG FOR A BALL. A coach saying
    # "pull the ball up as high as arm can go" means above the floor, and
    # `netball_one_hand_high_pass` already quotes 199.95 cm, which is the world
    # figure; the same frame reads 192.56 above the rest ankle.
    #
    # Two measures called a height in centimetres, measured above different
    # zeros, is the fault this table exists to prevent, so the two zeros are
    # named here rather than left to a reader to discover by subtracting.
    "ballHeightCm": CENTIMETRES,
    # THE SIX HAND-ORIENTATION MEASURES, WHICH ARE REPORTED AND NOT GRADED.
    #
    # `hand_orientation` writes them into receipts with a REPORTED verdict and
    # no band, because bands are coaching content and no coach has seen these
    # numbers. Reported is not the same as unitless: the values are angles, and
    # `unit_of` raised for all six.
    #
    # NOTHING CAUGHT IT, because the guard over written keys stands at the two
    # SOLVERS' measurement rows and this is a third writer. Their names all end
    # in "Degrees", which is exactly the suffix rule `unit_of` refuses to
    # apply: a reader would have guessed right and the table would still have
    # been silent.
    "leftThumbUpDegrees": DEGREES,
    "rightThumbUpDegrees": DEGREES,
    "leftFingerUpDegrees": DEGREES,
    "rightFingerUpDegrees": DEGREES,
    "leftThumbToBallDegrees": DEGREES,
    "rightThumbToBallDegrees": DEGREES,
}

# MEASURES ONLY ONE SOLVER CAN WRITE, AND WHY THAT IS NOT A DEFECT.
#
# `possession_solve` has a ball and `movement_engine.solve` does not, so a ball
# measure exists on one path and not the other. That is a real asymmetry and it
# is named here rather than hidden, because the guard over written keys asks
# whether the two writers agree and would otherwise read this as a fault.
#
# A drill without a ball cannot grade one of these. That is the correct
# outcome: the alternative is a fiction with no inputs.
POSSESSION_ONLY: frozenset[str] = frozenset({"ballHeightCm"})


# WHAT A MEASUREMENT ROW CARRIES THAT IS NOT A MEASURE.
#
# The solvers write these beside the measures: the phase the frame sits at, and
# what the athlete is doing with the ball. They have no unit because they are
# not quantities a coach grades, and they must not be added to the table above
# to silence a guard.
#
# They are named so that the written-versus-declared guard can be TOTAL. That
# guard asks whether every key a solver writes is either a declared measure or
# a named state column, so a new key forces a decision instead of passing
# unnoticed. Two centimetre measures were written and undeclared for weeks
# because no guard asked the question at all.
STATE_COLUMNS: frozenset[str] = frozenset(
    {"phase", "ballState", "holdingTheBall", "handsOnTheBall"}
)


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
