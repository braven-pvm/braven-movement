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
from typing import Iterable, Mapping, Sequence

from segment_measures import CENTIMETRES, DEGREES, unit_of


MINIMUM_MEANINGFUL_BAND_DEGREES = 5.0

# THE SAME RULE FOR A LENGTH, DERIVED AND NOT SCALED FROM THE ONE ABOVE.
#
# The 5.0 above has TWO justifications that happen to agree, and only one of
# them survives the trip to centimetres:
#
#   - clinical practice calls an angle difference under 5 degrees meaningless.
#     That is an external figure about ANGLES. There is no clinical figure for
#     a length difference in this repository or in the manual.
#   - the landmark noise study (`opensim_crosscheck.run_noise_study`, tabulated
#     in README.md) perturbs every landmark with per-axis Gaussian noise and
#     reports the angle error: at 5 mm the mean is 1.53 degrees and the 95th
#     percentile 3.89. The floor sits above that percentile.
#
# SO THE LENGTH FLOOR IS DERIVED FROM THE SECOND ONLY, by propagating the SAME
# 5 mm through a length instead of an angle, with the same 400 samples and the
# same seed. Every length this engine writes is a difference of TWO landmark
# coordinates -- a height is `joint - ground`, and the foot gap is
# `|(L - g) - (R - g)| = |L - R|` -- so two independent perturbations enter it.
# MEASURED: mean 6.00 mm, 95th percentile 14.53 mm.
#
# THE FLOOR IS 2.0 cm, AND IT CARRIES THE SAME SAFETY MARGIN THE DEGREES FLOOR
# HAS. Two readings of that margin, taken from different statistics of the one
# study, land 0.93 mm apart and round to the same centimetre:
#
#     over the 95th percentile   5.0 / 3.89 = 1.285   x 14.53 mm = 18.68 mm
#     over the propagated mean   5.0 / 1.53 = 3.268   x  6.00 mm = 19.61 mm
#
# They share no numerator and no denominator, so the agreement is evidence and
# not arithmetic. THEY AGREE AT THE CENTIMETRE AND NOT MORE CLOSELY: 19.61
# against 18.68 is a 0.93 mm spread, about 5 per cent of either, and both round
# to 2.0. An earlier version of this comment said "within a tenth of a
# millimetre", which overstated two readings that differ by nine times that. A floor exists to keep noise out of coaching, so the wide
# side is the safe side, and both shipped centimetre bands (6.0 and 14.0) clear
# it either way, which keeps this a fix rather than a retune.
#
# BOTH RATIOS ARE POST-HOC AND THE IMPORT IS DELIBERATE. 5.0 was a CLINICAL
# figure first; nobody derived it from 3.89 or from 1.53, and it was found to
# clear them afterwards. So 1.285 and 3.268 describe the margin the degrees
# floor turned out to have rather than a rule anyone applied. The length floor
# imports that margin knowingly, because the clinical half of the degrees
# floor's justification has no length counterpart to import.
#
# TWO WRONG ROUTES, BOTH TRIED AND BOTH NAMED SO NOBODY RE-DERIVES THEM.
# Each takes a ratio from an OUTPUT and spends it on an INPUT: the 5 mm is the
# landmark noise that ENTERS the study, and 1.53 and 3.89 are what LEAVES it.
#
#     3.268 x 5.00 mm = 16.34 mm     the ratio spent on the input noise
#     3.3   x 5.00 mm = 16.50 mm     the same ratio rounded first
#                       16.5  mm     was then WRITTEN as "1.6 cm", which is a
#                                    third number and is guarded as one
#
# That is this project's recurring fault class, appearing in the derivation of
# the threshold meant to prevent it. `segment_measures` calls it the
# units-across-a-boundary fault and counts six; `docs/KNOWN_ISSUES.md` names
# instances up to a sixth. An earlier version of this comment said "twelve
# times", which is a count from a lane's own notes and not from anything in
# this repository -- a number without its inputs, in the comment that exists to
# insist on them. Tests assert the shipped constant is none of the three.
#
# WHAT IS MISSING IS NAMED RATHER THAN INVENTED: there is no coach's figure for
# a meaningful height difference. This floor therefore protects against noise
# only, and a coach's figure replaces it the way 5 degrees does for angles.
MINIMUM_MEANINGFUL_BAND_CENTIMETRES = 2.0

MINIMUM_MEANINGFUL_BAND: dict[str, float] = {
    DEGREES: MINIMUM_MEANINGFUL_BAND_DEGREES,
    CENTIMETRES: MINIMUM_MEANINGFUL_BAND_CENTIMETRES,
}


def minimum_meaningful_band(measure: str) -> tuple[float, str | None]:
    """Return the narrowest honest band for a measure, and its unit.

    An UNDECLARED measure gets the STRICTEST floor of any unit and a unit of
    `None`. It does not get degrees. A default of degrees is how the next
    length becomes an angle, which is the whole reason `unit_of` refuses to
    guess; and a default of the loosest floor would let an unknown measure
    carry a band no declared measure could.

    `None` travels with it so a caller can decline to name a unit it does not
    know, rather than printing one.
    """
    try:
        unit = unit_of(measure)
    except KeyError:
        return max(MINIMUM_MEANINGFUL_BAND.values()), None
    return MINIMUM_MEANINGFUL_BAND[unit], unit


class MovementDefinitionError(ValueError):
    pass


# THE BAND FIELDS, ONE PAIR PER UNIT.
#
# A checkpoint's bounds are in the unit of the measure it grades, and until now
# the file said "Degrees" whatever that unit was. `footHeightGapCm` is a length
# and its three shipped checkpoints hold their bounds in `minimumDegrees`. The
# ledger has carried that as "Centimetres are stored in a field called degrees"
# since it was found.
#
# A NAME THAT DOES NOT SAY WHAT IT HOLDS IS HOW `fingerBaseDeviation` CAME TO
# BOUND A FLEXION AXIS, and that cost a day. So the spelling now carries the
# unit, and `read_band` refuses a pair whose unit is not the measure's -- in
# BOTH directions, because a degrees measure carrying centimetre bounds is the
# same fault wearing the other hat.
BAND_FIELDS: dict[str, tuple[str, str]] = {
    DEGREES: ("minimumDegrees", "maximumDegrees"),
    CENTIMETRES: ("minimumCentimetres", "maximumCentimetres"),
}

# THE CHECKPOINTS THAT STILL SPELL A CENTIMETRE BAND IN DEGREES FIELDS.
#
# Exactly three, all on one drill, and they are the reason this list exists
# rather than a straight refusal. They live in `spikes/movements/`, which is
# GATE 4: a change there is a key retune whose proposal goes to Marius with its
# evidence before anything is edited. Renaming their two keys changes no number
# any checkpoint reads, so it may well be ruled a correction rather than a
# retune -- but that is his ruling and not this lane's, and the alternative was
# to ship a loader that cannot read the shipped library.
#
# IT IS A LIST THAT MUST ONLY SHRINK. A test pins its size and asserts every
# entry is a real checkpoint on a real drill, so it cannot quietly grow, and a
# new centimetre checkpoint anywhere else is refused. It reaches zero when the
# ruling lands.
BANDS_AWAITING_A_GATE_FOUR_RULING: frozenset[tuple[str, str, str]] = frozenset({
    ("netball_double_foot_landing", "flight", "footHeightGapCm"),
    ("netball_double_foot_landing", "land", "footHeightGapCm"),
    ("netball_double_foot_landing", "absorb", "footHeightGapCm"),
})


def read_band(
    checkpoint: Mapping[str, object],
    movement_id: str,
    phase_name: str,
) -> tuple[float, float]:
    """Return a checkpoint's bounds, refusing a spelling that is not its unit.

    Four ways to be wrong, and each raises rather than guessing:
    neither pair present, both pairs present, a pair whose unit is not the
    measure's, and a measure with no declared unit at all.
    """
    measure = str(checkpoint["measure"])
    unit = unit_of(measure)
    present = [
        found for found, (low, _) in BAND_FIELDS.items() if low in checkpoint
    ]
    if not present:
        wanted = " and ".join(BAND_FIELDS[unit])
        raise MovementDefinitionError(
            f"{movement_id}/{phase_name}/{measure}: no band. It is measured "
            f"in {unit}, so it wants {wanted}"
        )
    if len(present) > 1:
        raise MovementDefinitionError(
            f"{movement_id}/{phase_name}/{measure}: two bands, in "
            f"{' and '.join(sorted(present))}. A checkpoint has one band and "
            "the file cannot say which is meant"
        )
    spelled = present[0]
    if spelled != unit:
        excused = (movement_id, phase_name, measure)
        if excused not in BANDS_AWAITING_A_GATE_FOUR_RULING:
            raise MovementDefinitionError(
                f"{movement_id}/{phase_name}/{measure}: the band is spelled "
                f"in {spelled} and the measure is in {unit}. A bound must "
                f"name the unit it is in; use {' and '.join(BAND_FIELDS[unit])}"
            )
    low, high = BAND_FIELDS[spelled]
    return float(checkpoint[low]), float(checkpoint[high])


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
        floor, unit = minimum_meaningful_band(self.measure)
        if width < floor:
            named = unit or "unknown-unit"
            raise MovementDefinitionError(
                f"{self.measure}: a band of {width:.1f} is narrower than the "
                f"{floor:.1f} {named} measurement threshold, so it would "
                "report noise as coaching"
            )
        if not self.cue.strip():
            raise MovementDefinitionError(f"{self.measure}: a coaching cue is required")

    @property
    def minimum(self) -> float:
        """The lower bound, in the measure's own unit.

        The stored field is still called `minimum_degrees` and holds
        centimetres for a length, which is the same fault one layer in. The
        rename reaches 45 call sites across 13 modules, so it is its own unit
        of work; these two names exist so that nothing written from here on
        has to spell a length "degrees".
        """
        return self.minimum_degrees

    @property
    def maximum(self) -> float:
        """The upper bound, in the measure's own unit."""
        return self.maximum_degrees

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
        """Return what a coach would say, not what a solver would print.

        IT SAID "degrees" FOR EVERY MEASURE, INCLUDING THE ONES THAT ARE NOT
        ANGLES. `netball_double_foot_landing` grades `footHeightGapCm` at three
        phases, and this sentence told the coach "Needs less: 17 degrees
        against a target of 0 to 14" about a distance in centimetres. The
        measure names its own unit now, and a measure with no declared unit
        gets no unit word rather than a wrong one.
        """
        if self.correct:
            return f"{self.checkpoint.cue} Good."
        if self.verdict == "below":
            gap = self.checkpoint.minimum_degrees - self.measured
            direction = "more"
        else:
            gap = self.measured - self.checkpoint.maximum_degrees
            direction = "less"
        _, unit = minimum_meaningful_band(self.checkpoint.measure)
        named = f" {unit}" if unit else ""
        return (
            f"{self.checkpoint.cue} Needs {direction}: "
            f"{self.measured:.0f}{named} against a target of "
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
            # THE WINNER IS CHOSEN IN UNITS OF EACH MEASURE'S OWN FLOOR,
            # because `max` over raw values compares centimetres with degrees.
            # A phase grading a length and an angle together would pick
            # whichever number is larger, which is not a question with an
            # answer. Dividing each movement by the floor its own unit carries
            # makes the comparison unit-free and asks the question that
            # matters: how many meaningful steps did this checkpoint move?
            #
            # INERT IN TODAY'S LIBRARY AND REAL IN THE CODE, measured ON
            # THE POSSESSION PATH, which is the one `build_library` uses for
            # this drill. The only mixed phases are `netball_double_foot_
            # landing`'s, graded at frames 54, 89 and 109 of 110. Across those
            # three transitions `footHeightGapCm` moves 0.01, 0.00 and 0.01 cm
            # while the angles move 1.92, 0.13 and 25.07, so the raw maximum
            # happens to pick the angle every time. The gap's largest value
            # anywhere in the clip is 1.22 cm, at frame 30, which no phase
            # grades.
            widest, measure, scale = None, None, None
            if previous is not None:
                for checkpoint in phase.checkpoints:
                    if checkpoint.measure not in frame:
                        continue
                    moved = abs(
                        float(frame[checkpoint.measure])
                        - float(previous[checkpoint.measure])
                    )
                    floor, _ = minimum_meaningful_band(checkpoint.measure)
                    if scale is None or moved / floor > scale:
                        widest, measure = moved, checkpoint.measure
                        scale = moved / floor
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
        """A first phase has nothing to differ from, so it always counts.

        The floor is the one this measure's own unit carries. Held against
        the degrees floor, a centimetre movement was asked to clear 5.0 when
        its own propagated noise is 1.45 cm and its floor 2.0, so a length had
        to move two and a half times as far as its own rule requires before a
        phase counted as distinct.
        """
        if self.first:
            return True
        if self.moved is None or self.measure is None:
            return False
        floor, _ = minimum_meaningful_band(self.measure)
        return self.moved >= floor

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


def _checkpoint(
    checkpoint: Mapping[str, object], movement_id: str, phase_name: str
) -> Checkpoint:
    """One checkpoint, with its band read in the unit its measure declares."""
    low, high = read_band(checkpoint, movement_id, phase_name)
    return Checkpoint(
        measure=str(checkpoint["measure"]),
        minimum_degrees=low,
        maximum_degrees=high,
        cue=str(checkpoint["cue"]),
        why=str(checkpoint["why"]),
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
                    _checkpoint(
                        checkpoint, str(data["movementId"]), str(phase["name"])
                    )
                    for checkpoint in phase["checkpoints"]
                ),
            )
            for phase in data["phases"]
        ),
    )


def union_of_graded(definitions: Iterable[MovementDefinition]) -> set[str]:
    """Every measure ANY of these movements grades.

    The library-wide answer to the question `graded_measures` answers for one
    movement. It is a free function taking definitions rather than a method
    reading a directory, so a caller with a solver and a test without one can
    both use it on the same definitions.

    An empty input gives an empty set. A caller widening a curve file on that
    would write no curves, so callers combine it with their own floor rather
    than trusting it alone.
    """
    found: set[str] = set()
    for definition in definitions:
        found |= definition.graded_measures()
    return found
