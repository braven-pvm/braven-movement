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


@dataclass(frozen=True)
class MotionKey:
    at_phase: float
    name: str
    left: HandOffset
    right: HandOffset


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
        if phase <= keys[0].at_phase:
            return (keys[0].left, keys[0].right)
        if phase >= keys[-1].at_phase:
            return (keys[-1].left, keys[-1].right)

        for first, second in zip(keys, keys[1:]):
            if first.at_phase <= phase <= second.at_phase:
                span = second.at_phase - first.at_phase
                travel = 0.0 if span <= 0.0 else (phase - first.at_phase) / span
                eased = 0.5 - 0.5 * math.cos(math.pi * travel)
                return (
                    first.left.blend(second.left, eased),
                    first.right.blend(second.right, eased),
                )
        raise MotionTrackError(f"no key span covers phase {phase}")

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


def load_motion(path: Path) -> MotionTrack:
    data = json.loads(Path(path).read_text(encoding="utf-8"))
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
                at_phase=float(entry["atPhase"]), name=name, left=left, right=right
            )
        )

    if len(keys) < 2:
        raise MotionTrackError("a movement needs at least two keys")
    phases = [key.at_phase for key in keys]
    if phases != sorted(phases):
        raise MotionTrackError("keys must be ordered by atPhase")
    if not math.isclose(phases[0], 0.0) or not math.isclose(phases[-1], 1.0):
        raise MotionTrackError("keys must span phase 0 to phase 1")
    for key in keys:
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
    left = chest + np.array(
        [
            left_offset.across * arm_length_cm,
            left_offset.up * arm_length_cm,
            left_offset.ahead * arm_length_cm,
        ],
        dtype=np.float32,
    )
    right = chest + np.array(
        [
            -right_offset.across * arm_length_cm,
            right_offset.up * arm_length_cm,
            right_offset.ahead * arm_length_cm,
        ],
        dtype=np.float32,
    )
    return left, right


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
