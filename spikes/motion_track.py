"""Load a movement as keyframe data rather than as code.

The trajectory used to be a cosine curve written into a Python function. To
correct the movement a person had to edit code, which does not scale past one
skill. A movement is now a small JSON file of named keys, and correcting it
means changing three numbers.

Hand positions are held relative to the chest and scaled by the athlete's own
arm length, so a movement authored on one body retargets to another without
rewriting anything.

A key gives one set of offsets, used mirrored for both hands. A skill where the
hands do different things, such as a one-hand snatch, overrides either hand with
its own offsets.
"""

from __future__ import annotations

import json
import math
from dataclasses import dataclass
from pathlib import Path
from typing import Sequence

import numpy as np


# Trunk rotation over planted feet. Beyond this the feet have to move, which is
# a different drill from the ones the manual keeps static.
MAXIMUM_TURN_DEGREES = 70.0


class MotionTrackError(ValueError):
    pass


@dataclass(frozen=True)
class HandOffset:
    across: float
    up: float
    ahead: float

    def blend(self, other: "HandOffset", amount: float) -> "HandOffset":
        return HandOffset(
            self.across + (other.across - self.across) * amount,
            self.up + (other.up - self.up) * amount,
            self.ahead + (other.ahead - self.ahead) * amount,
        )


def _tangents(phases, values):
    """Return a slope at each key that is smooth but never overshoots.

    Fritsch and Carlson's method. A raised cosine between each pair of keys
    forced the speed to zero at every key, so a movement stopped and restarted
    at each one and read as jarring. A plain Catmull-Rom fixed the stopping but
    overshot badly on unevenly spaced keys, which is worse: it invents swings
    the author never asked for. This keeps the speed continuous through a key
    and stays inside the values the author wrote.
    """
    count = len(values)
    if count < 2:
        return [0.0] * count

    secants = []
    for index in range(count - 1):
        span = phases[index + 1] - phases[index]
        secants.append(
            0.0 if span <= 0.0 else (values[index + 1] - values[index]) / span
        )

    slopes = [0.0] * count
    slopes[0] = secants[0]
    slopes[-1] = secants[-1]
    for index in range(1, count - 1):
        before, after = secants[index - 1], secants[index]
        if before * after <= 0.0:
            # A turning point. A zero slope here is what stops the overshoot.
            slopes[index] = 0.0
        else:
            first = phases[index] - phases[index - 1]
            second = phases[index + 1] - phases[index]
            total = first + second
            slopes[index] = (3.0 * total) / (
                (total + second) / before + (total + first) / after
            )
    return slopes


def _sample(values, phase, phases):
    """Sample a list of per-key numbers smoothly at this phase."""
    if phase <= phases[0]:
        return values[0]
    if phase >= phases[-1]:
        return values[-1]

    index = 0
    for candidate in range(len(phases) - 1):
        if phases[candidate] <= phase <= phases[candidate + 1]:
            index = candidate
            break

    span = phases[index + 1] - phases[index]
    if span <= 0.0:
        return values[index]
    travel = (phase - phases[index]) / span

    slopes = _tangents(phases, values)
    t2 = travel * travel
    t3 = t2 * travel
    return (
        (2.0 * t3 - 3.0 * t2 + 1.0) * values[index]
        + (t3 - 2.0 * t2 + travel) * span * slopes[index]
        + (-2.0 * t3 + 3.0 * t2) * values[index + 1]
        + (t3 - t2) * span * slopes[index + 1]
    )


@dataclass(frozen=True)
class FootPlacement:
    """Where a foot is, relative to the hips, in arm lengths.

    ``up`` is zero when the foot is on the ground and positive when it is off it.
    A movement that never keys its feet leaves them where the athlete started,
    which is what every planted drill wants.
    """

    across: float
    ahead: float
    up: float

    def blend(self, other: "FootPlacement", amount: float) -> "FootPlacement":
        return FootPlacement(
            self.across + (other.across - self.across) * amount,
            self.ahead + (other.ahead - self.ahead) * amount,
            self.up + (other.up - self.up) * amount,
        )

    @property
    def airborne(self) -> bool:
        return self.up > 0.02


@dataclass(frozen=True)
class MotionKey:
    at_phase: float
    name: str
    left: HandOffset
    right: HandOffset
    # How far the hips sit below standing at this key, as a fraction of arm
    # length. A drill with a steady stance leaves this at the movement default.
    # A jump needs it to change: load, rise, land.
    hip_drop: float
    # How far the trunk is turned away from square, in degrees, positive to the
    # athlete's left. A ball to the side is caught by turning, not only by
    # reaching, and the feet stay planted while the trunk turns over them.
    turn_degrees: float
    # Where the feet are, and how far the hips have travelled. All None on a
    # planted drill, which leaves the feet where the athlete started.
    foot_left: FootPlacement | None
    foot_right: FootPlacement | None
    root_across: float
    root_ahead: float


@dataclass(frozen=True)
class MotionTrack:
    movement_id: str
    frames: int
    frames_per_second: float
    hip_drop_fraction: float
    keys: tuple[MotionKey, ...]

    def offsets_at(self, phase: float) -> tuple[HandOffset, HandOffset]:
        """Return both hand offsets at this phase, smoothly between the keys.

        A raised cosine between neighbouring keys keeps the speed zero at each
        key, so the movement eases rather than jerking from one pose to the next.
        """
        keys = self.keys
        phases = [key.at_phase for key in keys]
        if phase <= phases[0]:
            return (keys[0].left, keys[0].right)
        if phase >= phases[-1]:
            return (keys[-1].left, keys[-1].right)

        def side(pick):
            return HandOffset(
                across=_sample([pick(k).across for k in keys], phase, phases),
                up=_sample([pick(k).up for k in keys], phase, phases),
                ahead=_sample([pick(k).ahead for k in keys], phase, phases),
            )

        return (side(lambda k: k.left), side(lambda k: k.right))

    def hip_drop_at(self, phase: float) -> float:
        """Return the hip drop at this phase, smoothly between the keys."""
        phases = [key.at_phase for key in self.keys]
        return _sample([key.hip_drop for key in self.keys], phase, phases)

    def turn_at(self, phase: float) -> float:
        """Return the trunk turn at this phase, smoothly between the keys."""
        phases = [key.at_phase for key in self.keys]
        return _sample([key.turn_degrees for key in self.keys], phase, phases)

    def feet_at(self, phase: float) -> tuple[FootPlacement, FootPlacement] | None:
        """Return both foot placements, or None when this drill keeps them still."""
        keys = self.keys
        if not self.moves_feet():
            return None
        phases = [key.at_phase for key in keys]
        if phase <= phases[0]:
            return (keys[0].foot_left, keys[0].foot_right)  # type: ignore[return-value]
        if phase >= phases[-1]:
            return (keys[-1].foot_left, keys[-1].foot_right)  # type: ignore[return-value]

        def foot(pick):
            across = _sample([pick(k).across for k in keys], phase, phases)
            ahead = _sample([pick(k).ahead for k in keys], phase, phases)
            up = _sample([pick(k).up for k in keys], phase, phases)
            # A spline can dip below the floor between two planted keys, and a
            # foot does not go through the ground.
            return FootPlacement(across, ahead, max(0.0, up))

        return (foot(lambda k: k.foot_left), foot(lambda k: k.foot_right))

    def root_offset_at(self, phase: float) -> tuple[float, float]:
        """Return how far the hips have travelled across and ahead, in arm lengths."""
        phases = [key.at_phase for key in self.keys]
        return (
            _sample([key.root_across for key in self.keys], phase, phases),
            _sample([key.root_ahead for key in self.keys], phase, phases),
        )

    def moves_feet(self) -> bool:
        return all(
            key.foot_left is not None and key.foot_right is not None
            for key in self.keys
        )

    def airborne_phases(self) -> list[float]:
        """Return the phases where both feet have left the ground."""
        return [
            key.at_phase
            for key in self.keys
            if key.foot_left is not None
            and key.foot_right is not None
            and key.foot_left.airborne
            and key.foot_right.airborne
        ]

    def turns(self) -> bool:
        return any(abs(key.turn_degrees) > 0.5 for key in self.keys)

    def has_moving_stance(self) -> bool:
        return len({key.hip_drop for key in self.keys}) > 1

    def key_phases(self) -> list[float]:
        return [key.at_phase for key in self.keys]

    def contact_phase(self) -> float:
        """Return the phase of the key named contact, or the furthest reach."""
        for key in self.keys:
            if key.name == "contact":
                return key.at_phase
        return max(self.keys, key=lambda key: key.left.ahead).at_phase

    def is_symmetric(self) -> bool:
        return all(key.left == key.right for key in self.keys)


def _hand(data: dict, fallback: HandOffset | None, name: str) -> HandOffset:
    source = dict(data)
    if fallback is not None:
        source = {
            "across": data.get("across", fallback.across),
            "up": data.get("up", fallback.up),
            "ahead": data.get("ahead", fallback.ahead),
        }
    try:
        return HandOffset(
            across=float(source["across"]),
            up=float(source["up"]),
            ahead=float(source["ahead"]),
        )
    except KeyError as error:
        raise MotionTrackError(f"key {name} is missing {error}") from None


def _foot(data: dict | None, name: str) -> FootPlacement | None:
    if data is None:
        return None
    try:
        return FootPlacement(
            across=float(data["across"]),
            ahead=float(data["ahead"]),
            up=float(data.get("up", 0.0)),
        )
    except KeyError as error:
        raise MotionTrackError(f"foot in key {name} is missing {error}") from None


def load_motion(path: Path) -> MotionTrack:
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    default_drop = float(data["stance"]["hipDropFraction"])
    default_turn = float(data["stance"].get("turnDegrees", 0.0))
    keys: list[MotionKey] = []
    for entry in data["keys"]:
        name = str(entry["name"])
        # The shared offsets are the default. Either hand may override them.
        shared = _hand(entry, None, name)
        left = _hand(entry.get("left", {}), shared, name) if "left" in entry else shared
        right = (
            _hand(entry.get("right", {}), shared, name) if "right" in entry else shared
        )
        keys.append(
            MotionKey(
                at_phase=float(entry["atPhase"]),
                name=name,
                left=left,
                right=right,
                hip_drop=float(entry.get("hipDrop", default_drop)),
                turn_degrees=float(entry.get("turnDegrees", default_turn)),
                foot_left=_foot(entry.get("footLeft"), name),
                foot_right=_foot(entry.get("footRight"), name),
                root_across=float(entry.get("rootAcross", 0.0)),
                root_ahead=float(entry.get("rootAhead", 0.0)),
            )
        )

    if len(keys) < 2:
        raise MotionTrackError("a movement needs at least two keys")
    phases = [key.at_phase for key in keys]
    if phases != sorted(phases):
        raise MotionTrackError("keys must be ordered by atPhase")
    if not math.isclose(phases[0], 0.0) or not math.isclose(phases[-1], 1.0):
        raise MotionTrackError("keys must span phase 0 to phase 1")
    keyed_feet = [
        key.foot_left is not None and key.foot_right is not None for key in keys
    ]
    if any(keyed_feet) and not all(keyed_feet):
        raise MotionTrackError(
            "a movement must key both feet on every key or on none. Keying some "
            "of them would leave the feet jumping between placed and planted."
        )
    for key in keys:
        if abs(key.turn_degrees) > MAXIMUM_TURN_DEGREES:
            raise MotionTrackError(
                f"key {key.name} turns the trunk {key.turn_degrees:.0f} degrees, "
                f"beyond the {MAXIMUM_TURN_DEGREES:.0f} degrees a person can "
                "produce over planted feet"
            )
        for side, offset in (("left", key.left), ("right", key.right)):
            if offset.ahead > 1.0:
                raise MotionTrackError(
                    f"key {key.name} sends the {side} hand {offset.ahead:.2f} of "
                    "arm length ahead, which is further than the arm can reach"
                )
    return MotionTrack(
        movement_id=str(data["movementId"]),
        frames=int(data["frames"]),
        frames_per_second=float(data["framesPerSecond"]),
        hip_drop_fraction=float(data["stance"]["hipDropFraction"]),
        keys=tuple(keys),
    )


def turn_matrix(turn_degrees: float) -> np.ndarray:
    """Return the rotation about the vertical axis. MHR is Y up."""
    angle = math.radians(turn_degrees)
    cosine, sine = math.cos(angle), math.sin(angle)
    return np.array(
        [[cosine, 0.0, sine], [0.0, 1.0, 0.0], [-sine, 0.0, cosine]],
        dtype=np.float64,
    )


def hand_targets_from_track(
    track: MotionTrack,
    phase: float,
    chest: np.ndarray,
    arm_length_cm: float,
) -> tuple[np.ndarray, np.ndarray]:
    """Return both hand targets at this phase, in the athlete's own scale.

    MHR places the left side at positive X, so the left hand takes the positive
    lateral offset. Reversing this crosses the arms and twists the trunk.
    """
    left_offset, right_offset = track.offsets_at(phase)
    rotation = turn_matrix(track.turn_at(phase))
    left = chest + rotation @ np.array(
        [
            left_offset.across * arm_length_cm,
            left_offset.up * arm_length_cm,
            left_offset.ahead * arm_length_cm,
        ],
        dtype=np.float64,
    )
    right = chest + rotation @ np.array(
        [
            -right_offset.across * arm_length_cm,
            right_offset.up * arm_length_cm,
            right_offset.ahead * arm_length_cm,
        ],
        dtype=np.float64,
    )
    return left.astype(np.float32), right.astype(np.float32)


def torso_length(points: np.ndarray, index: dict[str, int]) -> float:
    """Return the athlete's torso, hips to neck.

    Where a ball sits once she is holding it is measured in these. Where you
    hold a ball against your chest depends on your chest and on the ball, not
    on how long your arm is: two athletes of the same height whose reach
    differs by a tenth have the same torso and should hold it in the same
    place, and in arm lengths they did not.
    """
    return float(np.linalg.norm(points[index["c_neck"]] - points[index["root"]]))


def leg_length(points: np.ndarray, index: dict[str, int], side: str = "l") -> float:
    """Return the athlete's leg length, hip to knee to ankle.

    Stance is measured in these rather than in arm lengths. How far the hips
    drop, where the feet go and how far they travel are all things the legs do,
    and expressing them in arm lengths made them depend on the wrong limb: two
    athletes of the same height with the same legs, differing only in reach,
    came out with knees 5 degrees apart.
    """
    hip = points[index[f"{side}_upleg"]]
    knee = points[index[f"{side}_lowleg"]]
    ankle = points[index[f"{side}_foot"]]
    thigh = float(np.linalg.norm(knee - hip))
    shank = float(np.linalg.norm(ankle - knee))
    return thigh + shank


def arm_length(points: np.ndarray, index: dict[str, int], side: str = "l") -> float:
    """Return the athlete's arm length, shoulder to elbow to wrist."""
    shoulder = points[index[f"{side}_uparm"]]
    elbow = points[index[f"{side}_lowarm"]]
    wrist = points[index[f"{side}_wrist"]]
    upper = float(np.linalg.norm(elbow - shoulder))
    fore = float(np.linalg.norm(wrist - elbow))
    return upper + fore


def describe(track: MotionTrack) -> Sequence[str]:
    lines = []
    for key in track.keys:
        if key.left == key.right:
            lines.append(
                f"{key.name:9s} at {key.at_phase:4.2f}  across {key.left.across:5.2f}  "
                f"up {key.left.up:6.2f}  ahead {key.left.ahead:5.2f}"
            )
        else:
            lines.append(
                f"{key.name:9s} at {key.at_phase:4.2f}  "
                f"L {key.left.across:5.2f}/{key.left.up:5.2f}/{key.left.ahead:5.2f}  "
                f"R {key.right.across:5.2f}/{key.right.up:5.2f}/{key.right.ahead:5.2f}"
            )
    return lines
