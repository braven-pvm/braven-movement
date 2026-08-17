"""Load a movement as keyframe data rather than as code.

The trajectory used to be a cosine curve written into a Python function. To
correct the movement a person had to edit code, which does not scale past one
skill. A movement is now a small JSON file of named keys, and correcting it
means changing three numbers.

Hand positions are held relative to the chest and scaled by the athlete's own
arm length, so a movement authored on one body retargets to another without
rewriting anything.
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
class MotionKey:
    at_phase: float
    name: str
    across: float
    up: float
    ahead: float


@dataclass(frozen=True)
class MotionTrack:
    movement_id: str
    frames: int
    frames_per_second: float
    hip_drop_fraction: float
    keys: tuple[MotionKey, ...]

    def offsets_at(self, phase: float) -> tuple[float, float, float]:
        """Return the hand offsets at this phase, smoothly between the keys.

        A raised cosine between neighbouring keys keeps the speed zero at each
        key, so the movement eases rather than jerking from one pose to the next.
        """
        keys = self.keys
        if phase <= keys[0].at_phase:
            return (keys[0].across, keys[0].up, keys[0].ahead)
        if phase >= keys[-1].at_phase:
            return (keys[-1].across, keys[-1].up, keys[-1].ahead)

        for first, second in zip(keys, keys[1:]):
            if first.at_phase <= phase <= second.at_phase:
                span = second.at_phase - first.at_phase
                travel = 0.0 if span <= 0.0 else (phase - first.at_phase) / span
                eased = 0.5 - 0.5 * math.cos(math.pi * travel)
                return (
                    first.across + (second.across - first.across) * eased,
                    first.up + (second.up - first.up) * eased,
                    first.ahead + (second.ahead - first.ahead) * eased,
                )
        raise MotionTrackError(f"no key span covers phase {phase}")

    def key_phases(self) -> list[float]:
        return [key.at_phase for key in self.keys]

    def contact_phase(self) -> float:
        """Return the phase of the key named contact, or the furthest reach."""
        for key in self.keys:
            if key.name == "contact":
                return key.at_phase
        return max(self.keys, key=lambda key: key.ahead).at_phase


def load_motion(path: Path) -> MotionTrack:
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    keys = tuple(
        MotionKey(
            at_phase=float(key["atPhase"]),
            name=str(key["name"]),
            across=float(key["across"]),
            up=float(key["up"]),
            ahead=float(key["ahead"]),
        )
        for key in data["keys"]
    )
    if len(keys) < 2:
        raise MotionTrackError("a movement needs at least two keys")
    phases = [key.at_phase for key in keys]
    if phases != sorted(phases):
        raise MotionTrackError("keys must be ordered by atPhase")
    if not math.isclose(phases[0], 0.0) or not math.isclose(phases[-1], 1.0):
        raise MotionTrackError("keys must span phase 0 to phase 1")
    for key in keys:
        if key.ahead > 1.0:
            raise MotionTrackError(
                f"key {key.name} reaches {key.ahead:.2f} of arm length ahead, "
                "which is further than the arm can reach"
            )
    return MotionTrack(
        movement_id=str(data["movementId"]),
        frames=int(data["frames"]),
        frames_per_second=float(data["framesPerSecond"]),
        hip_drop_fraction=float(data["stance"]["hipDropFraction"]),
        keys=keys,
    )


def hand_targets_from_track(
    track: MotionTrack,
    phase: float,
    chest: np.ndarray,
    arm_length_cm: float,
) -> tuple[np.ndarray, np.ndarray]:
    """Return both hand targets at this phase, in the athlete's own scale."""
    across, up, ahead = track.offsets_at(phase)
    lateral = across * arm_length_cm
    vertical = up * arm_length_cm
    forward = ahead * arm_length_cm
    # MHR places the left side at positive X. Its l_uparm sits at x plus 17.6 and
    # r_uparm at x minus 17.6. Sending the left hand to negative X makes both
    # arms reach across the body, which crosses them and twists the hips.
    left = chest + np.array([lateral, vertical, forward], dtype=np.float32)
    right = chest + np.array([-lateral, vertical, forward], dtype=np.float32)
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
    return [
        f"{key.name:9s} at {key.at_phase:4.2f}  across {key.across:5.2f}  "
        f"up {key.up:6.2f}  ahead {key.ahead:5.2f}"
        for key in track.keys
    ]
