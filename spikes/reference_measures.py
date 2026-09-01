"""Which measures get a reference curve, and why each one is on the list.

SEPARATE FROM THE EXPORTER ON PURPOSE. This rule is the thing most likely to
drift back to a hand-written list, so it has to be reachable by a test on a
machine with no solver. `export_reference_curves` imports the solver at its
top, so a rule living there can be read by eye and by nothing else. That is
how the five-item list drifted from the nine-item one in the first place.

Nothing here imports anything heavier than `movement_definition`, which
imports the standard library.
"""

from __future__ import annotations

from typing import Iterable

from movement_definition import MovementDefinition, union_of_graded

# The measures a two-camera lift can plausibly recover. Elbow flexion is the
# one the video deliverable asks for; the others cost nothing extra and a
# shoot finding may turn on which of them survive the video.
#
# THIS IS A FLOOR, NOT THE LIST. It was the whole list until the widening, and
# that was the defect: chosen for what video can recover, never reconciled
# with what the coaching layer grades, so `leftKneeFlexionDegrees` — graded by
# every drill in the library — had no reference curve at all. The question it
# answers is still a good one, so a measure a lift can recover keeps its curve
# even where no checkpoint reads it today.
RECOVERABLE: tuple[str, ...] = (
    "leftElbowFlexionDegrees",
    "rightElbowFlexionDegrees",
    "leftShoulderElevationDegrees",
    "rightShoulderElevationDegrees",
    "trunkLeanDegrees",
)


def wanted(definitions: Iterable[MovementDefinition]) -> tuple[str, ...]:
    """Every measure that gets a curve: GRADED OR RECOVERABLE.

    DERIVED, NOT TYPED. A definition that starts grading a tenth measure gets
    its curve without anybody remembering to edit a list, which is the exact
    failure this repairs.

    Sorted, so the file's `measures` list and its curve keys are stable across
    runs and a diff of two exports shows content rather than ordering.
    """
    return tuple(sorted(union_of_graded(definitions) | set(RECOVERABLE)))
