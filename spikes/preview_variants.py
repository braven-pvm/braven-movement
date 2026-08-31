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


def _mirror():
    """Open the right hand the way the rig mirrors, not the way the code does.

    `finger_wrap.spread_fingers` negates every value on the right. The rig
    mirrors on the SAME sign — measured on the rest pose, which is symmetric
    about x=0 to 0.00005 cm, where the same value on both hands mirrors to
    within 0.02 degrees and the negation breaks it by up to 80.21. As shipped
    the right hand's fan collapses from 14.37 cm to 1.75 with its fingertips
    out of order. Refer to docs/HAND_MIRROR_EVIDENCE.md.
    """
    import finger_wrap
    import possession_solve

    # BOTH BINDINGS. `possession_solve` does `from finger_wrap import
    # spread_fingers`, which copies the function object into its own module
    # namespace, so patching `finger_wrap.spread_fingers` alone leaves the
    # solve calling the original.
    #
    # A first version patched only the module. The preview it produced was
    # BYTE-IDENTICAL to the shipped build, carrying a stamp saying it was the
    # fixed version — a file that would have gone in front of a coach as the
    # option she was being asked to choose. It was caught by the test that
    # solves rather than the one that inspects the binding, which is why the
    # guard is written on the solve.
    patched = [finger_wrap, possession_solve]
    originals = [getattr(where, "spread_fingers") for where in patched]

    def same_sign(character, parameters, sides):
        import numpy as np

        names = list(character.parameter_transform.names)
        opened = np.asarray(parameters, dtype=np.float32).copy()
        for side in sides:
            for suffix, value in finger_wrap.SPREAD.items():
                name = f"{side}_{suffix}"
                if name in names:
                    opened[names.index(name)] = value
        return opened

    for where in patched:
        where.spread_fingers = same_sign

    def undo():
        for where, original in zip(patched, originals):
            where.spread_fingers = original

    return undo


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


VARIANTS = {
    "mirror": {
        "constant": "finger_wrap.spread_fingers, the sign on the right hand",
        "shipped": "negated",
        "previewed": "the same sign as the left",
        "question": "Should the right hand open the way the left one does?",
        "evidence": "docs/HAND_MIRROR_EVIDENCE.md",
        "apply": _mirror,
    },
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
