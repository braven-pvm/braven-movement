"""ISB-convention joint angles measured from 3D landmarks.

This module is the measurement layer. It answers one question: what angle does a
sport scientist report for this pose? It deliberately depends on nothing but the
Python standard library, so the same code runs in a test, in a Blender session,
in a solver loop, and on a server.

Conventions follow the International Society of Biomechanics recommendations.
Wu et al. 2002 covers the ankle, hip, and spine. Wu et al. 2005 covers the
shoulder, elbow, wrist, and hand. Each joint decomposes the rotation of the
distal segment relative to the proximal segment with the Euler sequence the ISB
names for that joint.

A segment frame here is a rotation matrix whose columns are the segment X, Y,
and Z axes expressed in global coordinates. Y points proximally along the
segment for the limbs, matching the ISB definition.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Mapping, Sequence


Vector = tuple[float, float, float]
Matrix = tuple[Vector, Vector, Vector]

_EPSILON = 1e-9


class IsbAngleError(ValueError):
    pass


def _subtract(left: Vector, right: Vector) -> Vector:
    return (left[0] - right[0], left[1] - right[1], left[2] - right[2])


def _add(left: Vector, right: Vector) -> Vector:
    return (left[0] + right[0], left[1] + right[1], left[2] + right[2])


def _scale(vector: Vector, factor: float) -> Vector:
    return (vector[0] * factor, vector[1] * factor, vector[2] * factor)


def _dot(left: Vector, right: Vector) -> float:
    return left[0] * right[0] + left[1] * right[1] + left[2] * right[2]


def _cross(left: Vector, right: Vector) -> Vector:
    return (
        left[1] * right[2] - left[2] * right[1],
        left[2] * right[0] - left[0] * right[2],
        left[0] * right[1] - left[1] * right[0],
    )


def _normalise(vector: Vector, name: str) -> Vector:
    length = math.sqrt(_dot(vector, vector))
    if length < _EPSILON:
        raise IsbAngleError(f"{name} has zero length")
    return _scale(vector, 1.0 / length)


def midpoint(left: Vector, right: Vector) -> Vector:
    return _scale(_add(left, right), 0.5)


def frame_from_axes(x_axis: Vector, y_axis: Vector, z_axis: Vector) -> Matrix:
    """Return the rotation matrix whose columns are the three axes."""
    return (
        (x_axis[0], y_axis[0], z_axis[0]),
        (x_axis[1], y_axis[1], z_axis[1]),
        (x_axis[2], y_axis[2], z_axis[2]),
    )


def transpose(matrix: Matrix) -> Matrix:
    return (
        (matrix[0][0], matrix[1][0], matrix[2][0]),
        (matrix[0][1], matrix[1][1], matrix[2][1]),
        (matrix[0][2], matrix[1][2], matrix[2][2]),
    )


def multiply(left: Matrix, right: Matrix) -> Matrix:
    return tuple(  # type: ignore[return-value]
        tuple(
            sum(left[row][index] * right[index][column] for index in range(3))
            for column in range(3)
        )
        for row in range(3)
    )


def relative_rotation(proximal: Matrix, distal: Matrix) -> Matrix:
    """Return the rotation of the distal segment seen from the proximal segment."""
    return multiply(transpose(proximal), distal)


def build_segment_frame(
    *,
    distal_point: Vector,
    proximal_point: Vector,
    lateral_point: Vector,
    name: str,
) -> Matrix:
    """Build an ISB-style limb-segment frame.

    ``Y`` runs from the distal point to the proximal point. ``X`` is normal to
    the plane that the three points define, so it points anteriorly for a limb
    in the anatomical position. ``Z`` completes a right-handed frame and runs
    laterally along the joint axis.
    """
    y_axis = _normalise(_subtract(proximal_point, distal_point), f"{name} Y axis")
    in_plane = _subtract(lateral_point, distal_point)
    x_seed = _cross(in_plane, y_axis)
    x_axis = _normalise(x_seed, f"{name} X axis")
    z_axis = _cross(x_axis, y_axis)
    return frame_from_axes(x_axis, y_axis, z_axis)


def build_thorax_frame(
    *,
    suprasternale: Vector,
    c7: Vector,
    xiphoid: Vector,
    t8: Vector,
) -> Matrix:
    """Build the ISB thorax frame from the four trunk landmarks.

    ``Y`` points cranially. ``Z`` points to the subject's right. ``X`` points
    anteriorly.
    """
    lower = midpoint(xiphoid, t8)
    upper = midpoint(suprasternale, c7)
    y_axis = _normalise(_subtract(upper, lower), "thorax Y axis")
    z_seed = _cross(_subtract(suprasternale, lower), y_axis)
    z_axis = _normalise(z_seed, "thorax Z axis")
    x_axis = _cross(y_axis, z_axis)
    return frame_from_axes(x_axis, y_axis, z_axis)


def euler_zxy_degrees(rotation: Matrix) -> tuple[float, float, float]:
    """Decompose a rotation as Z, then X, then Y, in degrees.

    The ISB names this sequence for the elbow, the knee, the hip, and the ankle.
    The first angle is flexion, the second is ad/abduction, and the third is
    axial rotation.
    """
    sine_x = max(-1.0, min(1.0, rotation[2][1]))
    second = math.asin(sine_x)
    if abs(sine_x) > 1.0 - 1e-7:
        raise IsbAngleError("gimbal lock: the ZXY sequence is degenerate here")
    first = math.atan2(-rotation[0][1], rotation[1][1])
    third = math.atan2(-rotation[2][0], rotation[2][2])
    return (math.degrees(first), math.degrees(second), math.degrees(third))


def euler_yxy_degrees(rotation: Matrix) -> tuple[float, float, float]:
    """Decompose a rotation as Y, then X, then Y, in degrees.

    The ISB names this sequence for the shoulder. The first angle is the plane
    of elevation, the second is the elevation, and the third is axial rotation.
    """
    cosine = max(-1.0, min(1.0, rotation[1][1]))
    second = math.acos(cosine)
    if abs(cosine) > 1.0 - 1e-7:
        raise IsbAngleError("gimbal lock: the YXY sequence is degenerate here")
    first = math.atan2(rotation[0][1], rotation[2][1])
    third = math.atan2(rotation[1][0], -rotation[1][2])
    return (math.degrees(first), math.degrees(second), math.degrees(third))


@dataclass(frozen=True)
class JointAngles:
    joint: str
    sequence: str
    names: tuple[str, str, str]
    degrees: tuple[float, float, float]

    def as_dict(self) -> dict[str, float]:
        return {
            name: round(value, 2)
            for name, value in zip(self.names, self.degrees)
        }


def elbow_angles(*, humerus: Matrix, forearm: Matrix) -> JointAngles:
    rotation = relative_rotation(humerus, forearm)
    return JointAngles(
        joint="elbow",
        sequence="zxy",
        names=("flexion", "carryingAngle", "pronation"),
        degrees=euler_zxy_degrees(rotation),
    )


def knee_angles(*, femur: Matrix, tibia: Matrix) -> JointAngles:
    rotation = relative_rotation(femur, tibia)
    return JointAngles(
        joint="knee",
        sequence="zxy",
        names=("flexion", "adduction", "internalRotation"),
        degrees=euler_zxy_degrees(rotation),
    )


def hip_angles(*, pelvis: Matrix, femur: Matrix) -> JointAngles:
    rotation = relative_rotation(pelvis, femur)
    return JointAngles(
        joint="hip",
        sequence="zxy",
        names=("flexion", "adduction", "internalRotation"),
        degrees=euler_zxy_degrees(rotation),
    )


def shoulder_angles(*, thorax: Matrix, humerus: Matrix) -> JointAngles:
    rotation = relative_rotation(thorax, humerus)
    return JointAngles(
        joint="shoulder",
        sequence="yxy",
        names=("planeOfElevation", "elevation", "axialRotation"),
        degrees=euler_yxy_degrees(rotation),
    )


@dataclass(frozen=True)
class RangeLimit:
    minimum_degrees: float
    maximum_degrees: float
    source: str


# Clinical norms from the American Academy of Orthopaedic Surgeons. These are
# guidance for a healthy adult. An athlete population needs its own bands.
AAOS_LIMITS: dict[str, RangeLimit] = {
    "elbow.flexion": RangeLimit(0.0, 150.0, "AAOS"),
    "elbow.pronation": RangeLimit(-80.0, 80.0, "AAOS"),
    "knee.flexion": RangeLimit(0.0, 135.0, "AAOS"),
    "hip.flexion": RangeLimit(-30.0, 120.0, "AAOS"),
    "hip.adduction": RangeLimit(-45.0, 30.0, "AAOS"),
    "hip.internalRotation": RangeLimit(-45.0, 45.0, "AAOS"),
    "shoulder.elevation": RangeLimit(0.0, 180.0, "AAOS"),
    "shoulder.axialRotation": RangeLimit(-90.0, 70.0, "AAOS"),
}


@dataclass(frozen=True)
class RangeViolation:
    key: str
    measured_degrees: float
    limit: RangeLimit

    def describe(self) -> str:
        return (
            f"{self.key} is {self.measured_degrees:.1f} degrees, outside "
            f"{self.limit.minimum_degrees:.0f} to {self.limit.maximum_degrees:.0f} "
            f"({self.limit.source})"
        )


def check_ranges(
    angles: Sequence[JointAngles],
    limits: Mapping[str, RangeLimit] | None = None,
) -> list[RangeViolation]:
    """Return every measured angle that falls outside its range of motion."""
    table = AAOS_LIMITS if limits is None else limits
    violations: list[RangeViolation] = []
    for joint_angles in angles:
        for name, value in zip(joint_angles.names, joint_angles.degrees):
            key = f"{joint_angles.joint}.{name}"
            limit = table.get(key)
            if limit is None:
                continue
            if value < limit.minimum_degrees or value > limit.maximum_degrees:
                violations.append(RangeViolation(key, value, limit))
    return violations
