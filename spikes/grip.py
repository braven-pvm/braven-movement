"""Put a hand on a ball, using the hand the model already has.

The old contact was a wrist position plus a knuckle pointing along the arm. It
placed the hand near the ball and let the ball intersect it, because neither
constraint knew the ball existed.

This measures the athlete's own hand once, as a rigid shape in its own frame,
then places that shape against a sphere. Five real joints carry the placement:
the wrist, three knuckles and the thumb base. They are all joints the skeleton
already has, so nothing here depends on reading a quaternion convention
correctly.

Three points would be enough to fix a rigid body, and the first attempt used
wrist, middle knuckle and thumb base. It failed. The wrist and the middle
knuckle sit almost on the axis the hand rolls about, and the thumb base is only
4 cm from it, so rolling the hand right over barely moved any of the three. The
solver rolled the forearm to its pronation limit with the palm 163 degrees from
the ball and reported small errors. The index and little knuckles are 6 cm apart
across the palm, and adding them gives the roll something to pull against.

The hand frame
--------------

Built from joint positions alone, so it mirrors correctly without a special
case for each side:

- ``e1`` points along the hand, from the wrist to the middle knuckle.
- ``e2`` points out of the palm, the way the fingers curl.
- ``e3`` completes a right handed set.

The origin is the palm centroid, midway between the wrist and the knuckles.

What touches the ball is not that centroid. It is the skin over it, which the
LOD 0 mesh puts 3.50 cm out along ``e2`` at the midline of the palm, 2.75 cm on
the little finger side and 4.49 cm on the thumb side where the thenar eminence
is. The midline figure is the one used, and it is why the ball ends up in front
of the hand rather than inside it.
"""

from __future__ import annotations

import math
from dataclasses import dataclass

import numpy as np

# Measured on the athlete's own mesh, at the midline of the palm. Refer to the
# module docstring for how it varies across the palm.
PALM_SKIN_CM = 3.50

# The joints that carry the placement. The knuckles across the palm are what
# make the roll observable, so they are not optional.
CARRIED = ("wrist", "middle1", "index1", "pinky1", "thumb1")


class GripError(ValueError):
    pass


def _unit(vector: np.ndarray) -> np.ndarray:
    length = float(np.linalg.norm(vector))
    if length < 1e-9:
        raise GripError("cannot normalise a zero length direction")
    return np.asarray(vector, dtype=np.float64) / length


@dataclass(frozen=True)
class HandShape:
    """One athlete's hand, measured once, as coordinates in its own frame."""

    side: str
    # Joint name without the side prefix, to its local coordinates.
    local: dict[str, np.ndarray]
    # Where the fingertips sit, for measuring how much daylight a flat hand
    # leaves against a curved ball.
    tips: dict[str, np.ndarray]

    def place(self, origin: np.ndarray, axes: np.ndarray) -> dict[str, np.ndarray]:
        """Return world targets for the carried joints, in this pose.

        ``axes`` holds e1, e2 and e3 as rows, so a local coordinate triple
        multiplies straight through it.
        """
        return {
            f"{self.side}_{name}": origin + self.local[name] @ axes
            for name in CARRIED
        }

    def place_all(self, origin: np.ndarray, axes: np.ndarray) -> dict[str, np.ndarray]:
        """Return world positions for every measured point, carried joints and
        fingertips together. Used for checking, not for constraining."""
        placed = self.place(origin, axes)
        placed.update(
            {f"{self.side}_{name}": origin + local @ axes
             for name, local in self.tips.items()}
        )
        return placed


def hand_axes(
    wrist: np.ndarray,
    middle_knuckle: np.ndarray,
    index_knuckle: np.ndarray,
    pinky_knuckle: np.ndarray,
    middle_tip: np.ndarray,
) -> np.ndarray:
    """Return the hand's own frame as three rows, e1, e2, e3.

    The palm's facing is taken from the way the fingers curl, which is the only
    cue that mirrors correctly. Taking it from a cross product alone gives the
    two hands opposite normals and puts one palm on the wrong side of the ball.
    """
    e1 = _unit(middle_knuckle - wrist)
    across = index_knuckle - pinky_knuckle
    across = across - e1 * float(across @ e1)
    side = _unit(across)
    normal = _unit(np.cross(e1, side))
    if float((middle_tip - middle_knuckle) @ normal) < 0.0:
        normal = -normal
    # Orthogonalise once more, because the curl test only chose a sign.
    e2 = _unit(normal - e1 * float(normal @ e1))
    e3 = np.cross(e1, e2)
    return np.array([e1, e2, e3], dtype=np.float64)


def measure_hand(points: np.ndarray, index: dict[str, int], side: str) -> HandShape:
    """Measure one hand from a rest pose. Done once per athlete."""

    def at(name: str) -> np.ndarray:
        return np.asarray(points[index[f"{side}_{name}"]], dtype=np.float64)

    axes = hand_axes(
        wrist=at("wrist"),
        middle_knuckle=at("middle1"),
        index_knuckle=at("index1"),
        pinky_knuckle=at("pinky1"),
        middle_tip=at("middle3"),
    )
    knuckles = np.mean(
        [at(name) for name in ("index1", "middle1", "ring1", "pinky1")], axis=0
    )
    origin = (at("wrist") + knuckles) / 2.0
    return HandShape(
        side=side,
        local={name: axes @ (at(name) - origin) for name in CARRIED},
        tips={
            name: axes @ (at(name) - origin)
            for name in ("index3", "middle3", "ring3", "pinky3", "thumb3")
        },
    )


@dataclass(frozen=True)
class Contact:
    """Where one hand meets the ball."""

    side: str
    # Where the palm skin touches the sphere.
    skin: np.ndarray
    # Where the palm centroid must sit for the skin to touch there.
    origin: np.ndarray
    axes: np.ndarray

    @property
    def palm_normal(self) -> np.ndarray:
        return self.axes[1]


def contacts(
    ball_centre: np.ndarray,
    radius_cm: float,
    toward_catcher: np.ndarray,
    up: np.ndarray,
    spread_degrees: float,
    sides: tuple[str, ...] = ("l", "r"),
) -> dict[str, Contact]:
    """Return where each hand meets the ball.

    The hands sit ``spread_degrees`` apart around the ball, half that angle
    either side of the direction back toward the catcher. The catcher is used
    rather than the ball's own velocity because a grip is symmetric about the
    body that is taking the ball, not about the path it arrived on. For a pass
    straight down the middle the two are the same direction anyway.

    Every palm faces the ball centre. That is the whole of "fingers up, thumbs
    in the middle" that a sphere can express: the fingers are the tangent that
    points upward, and the thumbs follow from the anatomy of each hand.

    A single hand has nothing to spread against, so it takes the ball on the
    near side rather than half a spread off it. Spreading one hand puts the
    palm 45 degrees round a ball it is holding on its own.
    """
    centre = np.asarray(ball_centre, dtype=np.float64)
    near = _unit(toward_catcher)
    vertical = _unit(np.asarray(up, dtype=np.float64))
    lateral = np.cross(near, vertical)
    if float(np.linalg.norm(lateral)) < 1e-6:
        raise GripError(
            "the ball sits directly above or below the catcher, so there is no "
            "left and right to spread the hands into"
        )
    # Positive toward the athlete's left, matching MHR.
    lateral = _unit(lateral)
    half = math.radians(spread_degrees) / 2.0 if len(sides) > 1 else 0.0

    found: dict[str, Contact] = {}
    for side in sides:
        sign = 1.0 if side == "l" else -1.0
        outward = _unit(
            math.cos(half) * near + sign * math.sin(half) * lateral
        )
        skin = centre + radius_cm * outward
        # The palm faces the ball, so the palm normal is the inward direction.
        e2 = -outward
        fingers = vertical - e2 * float(vertical @ e2)
        if float(np.linalg.norm(fingers)) < 1e-6:
            raise GripError(
                "the palm faces straight up or down, so the fingers have no "
                "upward tangent to point along"
            )
        e1 = _unit(fingers)
        axes = np.array([e1, e2, np.cross(e1, e2)], dtype=np.float64)
        found[side] = Contact(
            side=side,
            skin=skin,
            origin=skin + PALM_SKIN_CM * outward,
            axes=axes,
        )
    return found


def grip_targets(
    shapes: dict[str, HandShape],
    found: dict[str, Contact],
) -> dict[str, np.ndarray]:
    """Return every joint target that puts these hands on this ball."""
    targets: dict[str, np.ndarray] = {}
    for side, contact in found.items():
        targets.update(shapes[side].place(contact.origin, contact.axes))
    return targets


def palm_skin(origin: np.ndarray, axes: np.ndarray) -> np.ndarray:
    """Where the palm skin is, given where the palm centroid and axes are.

    ``axes[1]`` points out of the palm, which is toward whatever the hand is
    holding. Taking the skin along its negative puts it on the back of the hand,
    which reads as a 7 cm miss on a ball the palm is actually touching.
    """
    return np.asarray(origin, dtype=np.float64) + PALM_SKIN_CM * axes[1]


def skin_distance_cm(
    placed: dict[str, np.ndarray],
    shape: HandShape,
    contact: Contact,
    ball_centre: np.ndarray,
    radius_cm: float,
) -> float:
    """How far the palm skin ends up from the ball surface, after solving.

    Positive is outside the ball. The palm skin is not a joint, so it is
    reconstructed from where the three carried joints actually landed.
    """
    origin, axes = reconstruct(placed, shape)
    return (
        float(np.linalg.norm(palm_skin(origin, axes) - np.asarray(ball_centre)))
        - radius_cm
    )


def reconstruct(
    placed: dict[str, np.ndarray], shape: HandShape
) -> tuple[np.ndarray, np.ndarray]:
    """Recover the hand's frame from where its joints actually landed.

    The solver does not have to hit the targets, so what the hand did has to be
    read back from the pose rather than assumed from the request.
    """
    # Solve for the frame that carries the local points onto the world ones.
    # A small orthogonal Procrustes, with the reflection ruled out so a hand
    # can never be reported inside out.
    local = np.array([shape.local[name] for name in CARRIED], dtype=np.float64)
    world = np.array(
        [
            np.asarray(placed[f"{shape.side}_{name}"], dtype=np.float64)
            for name in CARRIED
        ],
        dtype=np.float64,
    )
    local_mean = local.mean(axis=0)
    world_mean = world.mean(axis=0)
    covariance = (local - local_mean).T @ (world - world_mean)
    u, _, vt = np.linalg.svd(covariance)
    correction = np.diag([1.0, 1.0, float(np.sign(np.linalg.det(vt.T @ u.T)))])
    rotation = vt.T @ correction @ u.T
    axes = rotation.T
    origin = world_mean - local_mean @ axes
    return origin, axes
