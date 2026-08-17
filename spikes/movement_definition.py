"""The sport layer: what a skill is, and when it is performed correctly.

No library supplies this. A solver moves a skeleton, and a measurement layer
reports angles, but neither knows what a netball catch is or what a coach is
looking for. This module is that missing piece.

A movement definition names a skill, breaks it into phases, and gives each phase
the checkpoints a coach assesses. A checkpoint is one measured quantity with a
target band, a coaching cue in plain language, and a note on why it matters.

The bands are deliberately wider than the measurement error. The landmark noise
study put the honest budget at 5 mm and about 1.5 degrees, and clinical practice
calls a difference under 5 degrees meaningless. A band narrower than that would
report noise as coaching.

This module depends only on the standard library, so it runs anywhere the
measurement layer runs.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Mapping, Sequence


MINIMUM_MEANINGFUL_BAND_DEGREES = 5.0


class MovementDefinitionError(ValueError):
    pass


@dataclass(frozen=True)
class Checkpoint:
    """One thing a coach checks, with the band that counts as correct."""

    measure: str
    minimum_degrees: float
    maximum_degrees: float
    cue: str
    why: str

    def __post_init__(self) -> None:
        if self.maximum_degrees <= self.minimum_degrees:
            raise MovementDefinitionError(
                f"{self.measure}: the maximum must exceed the minimum"
            )
        width = self.maximum_degrees - self.minimum_degrees
        if width < MINIMUM_MEANINGFUL_BAND_DEGREES:
            raise MovementDefinitionError(
                f"{self.measure}: a band of {width:.1f} degrees is narrower than "
                f"the {MINIMUM_MEANINGFUL_BAND_DEGREES:.0f} degree measurement "
                "threshold, so it would report noise as coaching"
            )
        if not self.cue.strip():
            raise MovementDefinitionError(f"{self.measure}: a coaching cue is required")

    def assess(self, value: float) -> "CheckpointResult":
        if value < self.minimum_degrees:
            verdict = "below"
        elif value > self.maximum_degrees:
            verdict = "above"
        else:
            verdict = "within"
        return CheckpointResult(checkpoint=self, measured=value, verdict=verdict)


@dataclass(frozen=True)
class CheckpointResult:
    checkpoint: Checkpoint
    measured: float
    verdict: str

    @property
    def correct(self) -> bool:
        return self.verdict == "within"

    def feedback(self) -> str:
        """Return what a coach would say, not what a solver would print."""
        if self.correct:
            return f"{self.checkpoint.cue} Good."
        if self.verdict == "below":
            gap = self.checkpoint.minimum_degrees - self.measured
            direction = "more"
        else:
            gap = self.measured - self.checkpoint.maximum_degrees
            direction = "less"
        return (
            f"{self.checkpoint.cue} Needs {direction}: "
            f"{self.measured:.0f} degrees against a target of "
            f"{self.checkpoint.minimum_degrees:.0f} to "
            f"{self.checkpoint.maximum_degrees:.0f}, off by {gap:.0f}."
        )


@dataclass(frozen=True)
class Phase:
    """One named part of a skill, anchored at a point in the movement."""

    name: str
    at_phase: float
    checkpoints: tuple[Checkpoint, ...]

    def __post_init__(self) -> None:
        if not 0.0 <= self.at_phase <= 1.0:
            raise MovementDefinitionError(
                f"{self.name}: at_phase must lie between 0 and 1"
            )
        if not self.checkpoints:
            raise MovementDefinitionError(f"{self.name}: at least one checkpoint")


@dataclass(frozen=True)
class MovementDefinition:
    movement_id: str
    sport: str
    skill: str
    source: str
    phases: tuple[Phase, ...]

    def __post_init__(self) -> None:
        if not self.phases:
            raise MovementDefinitionError("a movement needs at least one phase")
        ordered = [phase.at_phase for phase in self.phases]
        if ordered != sorted(ordered):
            raise MovementDefinitionError("phases must be ordered by at_phase")

    def assess(
        self,
        measurements_by_phase: Sequence[Mapping[str, float]],
        measurement_valid: bool = True,
    ) -> "MovementAssessment":
        """Assess a solved movement, one phase at a time.

        ``measurements_by_phase`` is the per-frame measurement list a solver
        produced. Each phase reads the frame closest to its anchor.

        Set ``measurement_valid`` to False when the pose came from a source that
        cannot support a number, such as a single camera. The assessment then
        still gives the coaching cues, but withholds every figure. Refer to
        ``CheckpointResult.feedback``.
        """
        if not measurements_by_phase:
            raise MovementDefinitionError("no measurements supplied")
        last = len(measurements_by_phase) - 1
        results: dict[str, list[CheckpointResult]] = {}
        for phase in self.phases:
            frame = measurements_by_phase[round(phase.at_phase * last)]
            phase_results = []
            for checkpoint in phase.checkpoints:
                if checkpoint.measure not in frame:
                    raise MovementDefinitionError(
                        f"{phase.name}: no measurement named {checkpoint.measure}"
                    )
                phase_results.append(checkpoint.assess(float(frame[checkpoint.measure])))
            results[phase.name] = phase_results
        return MovementAssessment(
            definition=self, results=results, measurement_valid=measurement_valid
        )


@dataclass(frozen=True)
class MovementAssessment:
    definition: MovementDefinition
    results: dict[str, list[CheckpointResult]]
    measurement_valid: bool = True

    @property
    def correct(self) -> bool:
        return all(
            result.correct
            for phase_results in self.results.values()
            for result in phase_results
        )

    def coaching_notes(self) -> list[str]:
        """Return the coaching notes, with figures withheld when they are unsafe.

        A pose recovered from one camera carries an angle error larger than the
        clinical threshold, so a figure taken from it would mislead. The cue
        still helps a coach. The number does not.
        """
        notes: list[str] = []
        for phase_name, phase_results in self.results.items():
            for result in phase_results:
                if self.measurement_valid:
                    notes.append(f"[{phase_name}] {result.feedback()}")
                else:
                    notes.append(f"[{phase_name}] {result.checkpoint.cue}")
        return notes

    def to_receipt(self) -> dict:
        return {
            "movementId": self.definition.movement_id,
            "sport": self.definition.sport,
            "skill": self.definition.skill,
            "source": self.definition.source,
            "correct": self.correct,
            "measurementValid": self.measurement_valid,
            "phases": {
                phase_name: [
                    {
                        "measure": result.checkpoint.measure,
                        "measured": round(result.measured, 2),
                        "band": [
                            result.checkpoint.minimum_degrees,
                            result.checkpoint.maximum_degrees,
                        ],
                        "verdict": result.verdict,
                        "cue": result.checkpoint.cue,
                    }
                    for result in phase_results
                ]
                for phase_name, phase_results in self.results.items()
            },
        }


def load(path: Path) -> MovementDefinition:
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    return MovementDefinition(
        movement_id=str(data["movementId"]),
        sport=str(data["sport"]),
        skill=str(data["skill"]),
        source=str(data["source"]),
        phases=tuple(
            Phase(
                name=str(phase["name"]),
                at_phase=float(phase["atPhase"]),
                checkpoints=tuple(
                    Checkpoint(
                        measure=str(checkpoint["measure"]),
                        minimum_degrees=float(checkpoint["minimumDegrees"]),
                        maximum_degrees=float(checkpoint["maximumDegrees"]),
                        cue=str(checkpoint["cue"]),
                        why=str(checkpoint["why"]),
                    )
                    for checkpoint in phase["checkpoints"]
                ),
            )
            for phase in data["phases"]
        ),
    )
