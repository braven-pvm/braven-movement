"""What each graded measure needs from video, and whether video can carry it.

ONE TABLE, BUILT FROM THE ENGINE'S OWN NAMES. A checkpoint grades a measure —
`Checkpoint.measure` on `MovementDefinition` — and the dry-run gate has to ask
its eight questions of every measure a checkpoint reads, not of the one measure
somebody happened to instrument first. This is the table that makes that
possible: for each graded measure, the landmarks it needs, its UNIT, and
whether this modality contains the quantity at all.

NO SECOND DEFINITION IS INVENTED HERE. Every reader below calls
`segment_measures`, which is the same module `build_library` grades with. A
video curve computed from a differently-defined angle would be the
units-across-a-boundary fault this project has removed six times, and the elbow
spike caught exactly that before it published a number: the engine's
`elbow_flexion_degrees` is `180 - included`, where a straight arm is ZERO, and
the first video version had the opposite convention.

THREE KINDS OF ANSWER, AND THEY ARE NOT THE SAME
------------------------------------------------

- **carriable and read** — the lift has the landmarks and `segment_measures`
  has the function. A number comes out and the gate can judge it.
- **carriable in principle, absent in this footage** — the quantity is in the
  modality, and these two cameras did not see it. That is a shoot finding.
  `rightElbowFlexionDegrees` is the example: **zero** readings in 735 frame
  pairs, because a 90-degree pair sees one side of the body in profile.
- **not carriable at all** — the quantity is not in the modality and no camera
  quality fixes it. `trunkTurnDegrees` is the example, and it is the one worth
  understanding: it is `track.turn_at(phase)`, the athlete's facing along the
  drill's TRACK, and `VIDEO_KEYPOINT_SCHEMA.md` says in its own words that the
  world landmarks describe a POSE and not a position in the gym.

The gate must tell these three apart. A measure nothing read is not a measure
that passed, and a measure the modality cannot hold is not a measure waiting
for a better camera.

UNITS ARE CARRIED, BECAUSE ONE MEASURE IS NOT AN ANGLE
------------------------------------------------------

`footHeightGapCm` is a LENGTH in centimetres. Every threshold in the gate is
degrees, including the derived one, so applying the clinical five-degree band
to it would be the same fault in a new coat. `unit` travels with every measure
and the gate refuses the degree conditions where the unit is not degrees.
"""

from __future__ import annotations

import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Mapping, Sequence

SPIKE_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(SPIKE_DIR))

from segment_measures import (  # noqa: E402
    elbow_flexion_degrees,
    knee_flexion_degrees,
    shoulder_elevation_degrees,
    trunk_lean_degrees,
)

DEGREES = "degrees"
CENTIMETRES = "centimetres"

# UP IN THE LIFT'S OWN FRAME. `video_lift_3d.py` builds each point as
# (across, up, ahead) with up taken as the negated pixel row, so up is +Y here.
# It is written down because a lifted tuple looks like any other triple and the
# sign came from an image row rather than from a world.
LIFT_UP = (0.0, 1.0, 0.0)

# A joint the video reads as the midpoint of two landmarks. The engine's
# `pelvis` and `neck` are single joints on the skeleton; the pose model has no
# such landmarks, and `video_lift_3d.py` already ties the two views' scale by
# the torso — shoulder midpoint to hip midpoint — so these are the same two
# midpoints that file uses rather than a new convention.
MIDPOINTS = {
    "pelvis": ("left_hip", "right_hip"),
    "neck": ("left_shoulder", "right_shoulder"),
}


class MeasureError(ValueError):
    """A measure was asked for something it cannot answer."""


@dataclass(frozen=True)
class Measure:
    """One graded quantity, and what video would need to read it."""

    name: str
    unit: str
    landmarks: tuple[str, ...]
    engine_definition: str
    reader: Callable[[Mapping[str, Sequence[float]]], float] | None
    unreadable_because: str | None = None

    @property
    def carriable(self) -> bool:
        """False when the MODALITY lacks the quantity, whatever the cameras did.

        This is not "was it seen". A measure can be carriable and absent from a
        particular clip, which is a shoot finding; a measure that is not
        carriable is a modelling fact and no shoot fixes it.
        """
        return self.reader is not None

    def read(self, points: Mapping[str, Sequence[float]]) -> float | None:
        """The measure's value from lifted 3D points, or None if a joint is missing.

        None means a landmark this measure needs was not in the frame. It never
        means zero, and the gate must not read it as a small value.
        """
        if self.reader is None:
            raise MeasureError(
                f"{self.name} is not carriable by video: {self.unreadable_because}")
        needed = dict(points)
        for joint, (first, second) in MIDPOINTS.items():
            if first in needed and second in needed:
                needed[joint] = tuple(
                    (a + b) / 2.0 for a, b in zip(needed[first], needed[second]))
        if any(name not in needed for name in self.landmarks):
            return None
        return self.reader(needed)


def _elbow(side: str) -> Callable:
    def read(points):
        return elbow_flexion_degrees(
            shoulder=points[f"{side}_shoulder"],
            elbow=points[f"{side}_elbow"],
            wrist=points[f"{side}_wrist"])
    return read


def _knee(side: str) -> Callable:
    def read(points):
        return knee_flexion_degrees(
            hip=points[f"{side}_hip"],
            knee=points[f"{side}_knee"],
            ankle=points[f"{side}_ankle"])
    return read


def _shoulder(side: str) -> Callable:
    def read(points):
        return shoulder_elevation_degrees(
            pelvis=points["pelvis"], neck=points["neck"],
            shoulder=points[f"{side}_shoulder"], elbow=points[f"{side}_elbow"])
    return read


def _trunk_lean(points):
    return trunk_lean_degrees(
        pelvis=points["pelvis"], neck=points["neck"], up=LIFT_UP)


def _foot_gap(points):
    """The height difference between the feet, in CENTIMETRES.

    The lift is in metres and this measure is not. `movement_engine` computes it
    as `abs(left_up - right_up)` on a skeleton already in centimetres, so the
    hundred is a unit conversion and not a scale factor somebody chose.
    """
    return abs(points["left_ankle"][1] - points["right_ankle"][1]) * 100.0


MEASURES: dict[str, Measure] = {
    "leftElbowFlexionDegrees": Measure(
        name="leftElbowFlexionDegrees", unit=DEGREES,
        landmarks=("left_shoulder", "left_elbow", "left_wrist"),
        engine_definition="segment_measures.elbow_flexion_degrees",
        reader=_elbow("left")),
    "rightElbowFlexionDegrees": Measure(
        name="rightElbowFlexionDegrees", unit=DEGREES,
        landmarks=("right_shoulder", "right_elbow", "right_wrist"),
        engine_definition="segment_measures.elbow_flexion_degrees",
        reader=_elbow("right")),
    "leftKneeFlexionDegrees": Measure(
        name="leftKneeFlexionDegrees", unit=DEGREES,
        landmarks=("left_hip", "left_knee", "left_ankle"),
        engine_definition="segment_measures.knee_flexion_degrees",
        reader=_knee("left")),
    "rightKneeFlexionDegrees": Measure(
        name="rightKneeFlexionDegrees", unit=DEGREES,
        landmarks=("right_hip", "right_knee", "right_ankle"),
        engine_definition="segment_measures.knee_flexion_degrees",
        reader=_knee("right")),
    "leftShoulderElevationDegrees": Measure(
        name="leftShoulderElevationDegrees", unit=DEGREES,
        landmarks=("left_hip", "right_hip", "left_shoulder", "right_shoulder",
                   "left_elbow"),
        engine_definition="segment_measures.shoulder_elevation_degrees",
        reader=_shoulder("left")),
    "rightShoulderElevationDegrees": Measure(
        name="rightShoulderElevationDegrees", unit=DEGREES,
        landmarks=("left_hip", "right_hip", "left_shoulder", "right_shoulder",
                   "right_elbow"),
        engine_definition="segment_measures.shoulder_elevation_degrees",
        reader=_shoulder("right")),
    "trunkLeanDegrees": Measure(
        name="trunkLeanDegrees", unit=DEGREES,
        landmarks=("left_hip", "right_hip", "left_shoulder", "right_shoulder"),
        engine_definition="segment_measures.trunk_lean_degrees",
        reader=_trunk_lean),
    "footHeightGapCm": Measure(
        name="footHeightGapCm", unit=CENTIMETRES,
        landmarks=("left_ankle", "right_ankle"),
        engine_definition="movement_engine: abs(left_up - right_up)",
        reader=_foot_gap),
    "trunkTurnDegrees": Measure(
        name="trunkTurnDegrees", unit=DEGREES,
        landmarks=(),
        engine_definition="movement_engine: track.turn_at(phase)",
        reader=None,
        unreadable_because=(
            "it is the athlete's facing along the drill's TRACK, not joint "
            "geometry. VIDEO_KEYPOINT_SCHEMA.md states that the world "
            "landmarks describe a POSE and not a position in the gym, so the "
            "quantity is not in this modality and no camera quality supplies "
            "it. A gym-frame track would have to come from somewhere else."
        )),
}


def measure(name: str) -> Measure:
    """The registry entry, or a refusal that names the gap.

    A KeyError here means the engine grades something this table has never
    heard of, which is a gap in the table and not a reason to skip the measure.
    Silently ignoring an unknown measure is how a gate comes to cover less than
    it claims.
    """
    if name not in MEASURES:
        raise MeasureError(
            f"{name} is graded by a checkpoint and is not in the video measure "
            "registry. Add it, or record why video cannot carry it — do not "
            "let the gate skip a measure it has never considered."
        )
    return MEASURES[name]


def scarcest_landmark(entry: Measure, counts: Mapping[str, int]) -> tuple[str, int]:
    """The least-seen landmark this measure needs, and how many times it appears.

    The SCARCEST, because a measure is only as available as its rarest joint.
    Averaging the counts would report `rightElbowFlexionDegrees` as well seen
    on the strength of a shoulder that appears 735 times, while the elbow it
    needs appears zero.
    """
    if not entry.landmarks:
        return ("", 0)
    needed = set(entry.landmarks)
    for joint, (first, second) in MIDPOINTS.items():
        if joint in needed:
            needed.discard(joint)
            needed.update({first, second})
    return min(((name, counts.get(name, 0)) for name in sorted(needed)),
               key=lambda pair: pair[1])
