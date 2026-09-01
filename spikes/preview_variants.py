"""The look options a coach is asked to choose between, applied for one run.

Marius wants each look decision watchable as A against B. A preview is the
library solved with ONE constant changed, exported in the coach pack's own
animation format, and put beside the current build on a page.

WHY THE VARIANT LIVES HERE AND NOT IN A REVERTED EDIT. Applying the change by
hand, running the exporter, and reverting produces a file nobody else can
regenerate: the only record of what made it is the author's word. These files
go in front of a coach, and someone will ask later exactly what produced the
thing she looked at. "My word plus an edit I undid" is not an answer this
project accepts anywhere else, so it is not one here.

WHAT KEEPS THIS FROM BEING A BACK DOOR INTO THE LIBRARY. Three guards, and the
third is the one that matters:

1. `preview_output` refuses the shipped location. A preview cannot overwrite
   the build the pack ships.
2. Every preview payload carries `preview` at its top level, so a consumer
   that does not understand the field cannot mistake it for a current build.
3. `test_preview_variants` proves a solve is UNCHANGED after a preview context
   has opened and closed. A monkeypatch that leaked would change the library
   quietly, and that test is what catches anyone who later reaches this
   machinery from the default path.

NOTHING HERE IS A PROPOSAL TO SHIP. Each variant is a decision waiting on Erin
and Marius, and the evidence for each is in docs/.
"""

from __future__ import annotations

import contextlib
import sys
from pathlib import Path

SPIKE_DIR = Path(__file__).resolve().parent
if str(SPIKE_DIR) not in sys.path:
    sys.path.insert(0, str(SPIKE_DIR))

# The one place the shipped coach pack reads. A preview may never write here.
SHIPPED = SPIKE_DIR / "poc-output" / "coach" / "animations.json"


def _pole(angle: float):
    """Read the pole angle against the population the manual's figure describes.

    38.6 cm is read from photographs of a two-handed snatch at contact. The
    whole-library mean agreed with it while no member of that population did,
    because two one-handed drills pulled it up. On the six two-handed drills
    the angle gives 36.4 cm; about 37.3 degrees is what would put those six on
    38.6. Refer to docs/KNOWN_ISSUES.md.
    """
    import contact_solve

    original = contact_solve.ELBOW_POLE_ANGLE_DEGREES
    contact_solve.ELBOW_POLE_ANGLE_DEGREES = angle
    return lambda: setattr(
        contact_solve, "ELBOW_POLE_ANGLE_DEGREES", original
    )


# THE "mirror" VARIANT WAS RETIRED ON 2026-09-01, when Marius ruled the fix
# ships. It previewed opening the right hand the way the left one opens; that
# is now what the engine does, so the variant would have produced a file
# identical to the shipped build.
#
# It was retired rather than kept as a no-op regression guard, and the reason
# is what this module is FOR. These variants are coach-facing: each one exists
# so a person can look at two renders and answer a question. A variant that
# renders the shipped build while a page labels it the alternative is exactly
# the failure this module was already caught committing once, when a preview
# went out byte-identical to the build it claimed to differ from.
#
# The regression it would have guarded is guarded better and closer to the
# rig, in `test_hand_mirror.py`: the right hand's fan must equal the left's
# and the fingertips must run in anatomical order. That fires on the negation
# returning, and it needs no preview machinery to do it.
VARIANTS = {
    "pole-37.3": {
        "constant": "contact_solve.ELBOW_POLE_ANGLE_DEGREES",
        "shipped": "31.3",
        "previewed": "37.3",
        "question": "How wide should the elbows sit at contact?",
        "evidence": "docs/KNOWN_ISSUES.md",
        "apply": lambda: _pole(37.3),
    },
}


@contextlib.contextmanager
def applied(variant: str | None):
    """Run the block with this variant in force, and without it afterwards.

    `None` is a no-op, so the default path through the exporter touches none of
    this. The undo runs even if the block raises, because a leaked patch would
    silently change every solve after it in the same process.
    """
    if variant is None:
        yield None
        return
    if variant not in VARIANTS:
        raise KeyError(
            f"{variant!r} is not a preview variant. Known: "
            f"{', '.join(sorted(VARIANTS))}"
        )
    undo = VARIANTS[variant]["apply"]()
    try:
        yield VARIANTS[variant]
    finally:
        undo()


def stamp(variant: str) -> dict:
    """What this preview is, for the top of its payload."""
    found = VARIANTS[variant]
    return {
        "variant": variant,
        "constant": found["constant"],
        "shipped": found["shipped"],
        "previewed": found["previewed"],
        "question": found["question"],
        "evidence": found["evidence"],
        "note": (
            "PREVIEW. One constant changed, nothing merged and nothing "
            "proposed. This is not the current build and must not be read as "
            "one."
        ),
    }


def preview_output(variant: str) -> Path:
    """Where a preview may be written, which is never where the pack reads.

    The refusal is the guard rather than the convention: a preview that could
    land on the shipped path is one bad argument away from replacing the build
    a coach is being asked to compare against.
    """
    where = SHIPPED.parent / f"preview-{variant}" / "animations.json"
    if where.resolve() == SHIPPED.resolve():
        raise ValueError(
            f"a preview may not be written to {SHIPPED}, which is the file the "
            "coach pack ships"
        )
    return where
