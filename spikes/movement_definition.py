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

    def graded_measures(self) -> set[str]:
        """Every measure a checkpoint of this phase reads."""
        return {checkpoint.measure for checkpoint in self.checkpoints}


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

    def graded_measures(self) -> set[str]:
        """Every measure any checkpoint in this movement reads.

        WHAT IT IS FOR. Several things downstream pick their own list of
        measures and none of them was ever reconciled with what the coaching
        layer actually grades. `export_reference_curves.WANTED` is five angles
        chosen for what a two-camera lift can plausibly recover, and
        `leftKneeFlexionDegrees` — graded by every drill in the library — is
        not among them. A consumer that wants "the measures that matter" has
        had to hand-write a list and let it drift.

        This is the definition's own answer to that question, so a consumer
        can ask rather than guess. It is a SET: order is not meaningful, a
        measure graded at three phases appears once, and callers that want a
        stable order sort it themselves.

        It reads the definition alone and needs no solve, so a caller without
        a solver can ask it.
        """
        found: set[str] = set()
        for phase in self.phases:
            found |= phase.graded_measures()
        return found

    def separation(
        self, measurements_by_phase: Sequence[Mapping[str, float]]
    ) -> list["PhaseSeparation"]:
        """Report whether each phase can be told apart from the one before it.

        A checkpoint grades a measure at a phase. If that measure reads the
        same at this phase as at the previous one, the checkpoint cannot
        distinguish them, so it cannot fail. It will pass whatever the athlete
        does, and it inflates the library's score with a check that was never
        a check.

        This is the same rule `Checkpoint.__post_init__` already applies to
        band width, applied to phase separation instead. A band narrower than
        the measurement threshold reports noise as coaching. A phase closer to
        its predecessor than the measurement threshold does the same.

        It cannot live in `__post_init__`, because separation is a property of
        a solved movement and not of the definition alone. A definition is only
        wrong here once you see what it grades.
        """
        if not measurements_by_phase:
            raise MovementDefinitionError("no measurements supplied")
        last = len(measurements_by_phase) - 1
        report: list[PhaseSeparation] = []
        previous: Mapping[str, float] | None = None
        for phase in self.phases:
            frame = measurements_by_phase[round(phase.at_phase * last)]
            widest, measure = None, None
            if previous is not None:
                for checkpoint in phase.checkpoints:
                    if checkpoint.measure not in frame:
                        continue
                    moved = abs(
                        float(frame[checkpoint.measure])
                        - float(previous[checkpoint.measure])
                    )
                    if widest is None or moved > widest:
                        widest, measure = moved, checkpoint.measure
            report.append(
                PhaseSeparation(
                    phase=phase.name,
                    first=previous is None,
                    moved=widest,
                    measure=measure,
                )
            )
            previous = frame
        return report

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
class PhaseSeparation:
    """How far a phase's own checkpoints moved from the phase before it."""

    phase: str
    first: bool
    moved: float | None
    measure: str | None

    @property
    def distinguishable(self) -> bool:
        """A first phase has nothing to differ from, so it always counts."""
        if self.first:
            return True
        if self.moved is None:
            return False
        return self.moved >= MINIMUM_MEANINGFUL_BAND_DEGREES

    def why(self) -> str:
        if self.first:
            return f"{self.phase}: first phase, nothing to differ from"
        if self.moved is None:
            return f"{self.phase}: no checkpoints, so nothing is graded here"
        verdict = "" if self.distinguishable else "  CANNOT FAIL"
        return (
            f"{self.phase}: widest change {self.moved:.2f} on "
            f"{self.measure}{verdict}"
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


def definition_files(folder: Path) -> list[Path]:
    """Return every coaching definition in a folder, and nothing else.

    One movement owns several files: the coaching definition, the motion track,
    and now the ball trajectory. Only the plain ``<id>.json`` is a definition.
    Listing them by excluding the others broke the moment a third suffix
    arrived, so the rule is positive: a definition has one dot in its name.
    """
    return sorted(
        path for path in folder.glob("*.json") if path.name.count(".") == 1
    )


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
