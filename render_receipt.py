"""What a render run may claim about itself, with no Blender in it.

The renderer's console line is what a person and a script both read first. It
said PASS whenever the function reached its end, which is not the same as
having rendered or measured anything.

`--no-stills` without `--animate` skips the phase loop entirely. Run that way
over the eight drills it printed PASS eight times and wrote eight receipts
carrying zero phases. The receipts were honest; the word was not.

This is the same fault this lane reports in other instruments, in its own file:
an absence of measurement read as a clean result. It lives here so that a test
can call it, because the renderer imports `bpy` and its tests skip.
"""

from __future__ import annotations

PASS = "PASS"
NOTHING_RENDERED = "NOTHING RENDERED"
SOME_PHASES_FAILED = "SOME PHASES FAILED"


# THE BUILD STAMP IS NOT HERE, AND IT WAS, FOR A DAY.
#
# `spikes/build_stamp.py` already wrote one, in a shape the whole repository
# shares, before this module wrote a second. Two names for one concept —
# `generatedFrom` there, `build` here — and the older one is RICHER: it carries
# `uncommittedPaths` and `uncommittedDiffSha256`, so two dirty builds can be
# told apart rather than merely flagged. It is also cached for the life of the
# process, so every receipt of one run carries the same stamp and a directory
# can be recognised as one set.
#
# The consequence was not theoretical. `spikes/archive_receipts.py` reads
# `generatedFrom` and REFUSED this lane's archive outright, so an irreplaceable
# set had to be hashed and described by hand.
#
# This lane filed a defect about two sources of truth for a HAND and then
# created a second source of truth for a BUILD on the same day, without looking
# for the first. Look for the existing one first.


def render_outcome(phase_count: int, animation: object | None,
                   failed_count: int = 0) -> str:
    """PASS only when the run actually produced something and nothing failed.

    A run that posed no phase and exported no animation has measured nothing.
    It has not failed either, and it must not say so, because a legitimate
    `--turntable`-only or `--animate`-only run is not a defect. It says what
    happened, which is that nothing was rendered.

    A run with a FAILED phase is different, and it outranks both. Something was
    asked for and could not be drawn, so the word must not be PASS even though
    other phases succeeded. It is checked FIRST for that reason: a run of one
    good phase and one failure is not a pass.
    """
    if failed_count > 0:
        return SOME_PHASES_FAILED
    if phase_count <= 0 and not animation:
        return NOTHING_RENDERED
    return PASS


# NOTHING RENDERED EXITS 0 AND A FAILED PHASE DOES NOT.
#
# NOTHING RENDERED is not a failure: a turntable-only or animation-only run is
# legitimate, and so is a phase filter that matches nothing in this job.
#
# A FAILED PHASE IS A FAILURE and the run exits non-zero, after every other
# drill has been rendered and every receipt written. On 2026-09-07 one
# unposable phase of one drill aborted the whole library render and cost eleven
# good drills and forty minutes. One bad phase should cost one figure. But a
# run that carries on must not then report success, or the loop would have
# traded a loud failure for a quiet one, which is the fault this module exists
# to prevent.
#
# So a caller that wants to know whether anything was measured must still read
# the receipt's `phases`, or match this word on the console. Reading the exit
# code alone is how eight empty runs looked like eight clean ones.


def undrawn_phases(receipt: dict) -> list[dict]:
    """The phases a run could not draw, from its receipt.

    `failedPhases` is newer than every reader of these receipts. A reader that
    predates it sees a SHORT `phases` list and nothing else, which is a partial
    drill wearing the shape of a complete one.
    """
    return list(receipt.get("failedPhases") or [])


def undrawn_complaint(movement_id: str, undrawn: list[dict]) -> str:
    """One sentence naming what could not be drawn, and why.

    The reason is carried, not just the name. A reader told only that `ready`
    is missing has to go and find the run's console to learn that a knuckle
    turned about the wrong axis.
    """
    named = ", ".join(
        f"{entry.get('name', '?')} ({entry.get('error', 'no reason recorded')})"
        for entry in undrawn
    )
    return f"{movement_id} could not draw {len(undrawn)} phase(s): {named}."


# The reason for refusing, added only when the caller IS refusing. It was once
# part of the sentence above, so a run that had passed --allow-partial printed
# "Refusing ... Pass --allow-partial" after being allowed.
WHY_REFUSED = (
    " A page or an archive built from this receipt would show fewer figures "
    "than the drill has and say nothing about it. Pass --allow-partial to "
    "proceed deliberately."
)


def refuse_partial_receipt(movement_id: str, receipt: dict,
                           allow_partial: bool = False) -> list[dict]:
    """Raise unless the run drew every phase. Returns what it could not draw.

    THIS IS THE HALF THE RENDER LOOP DID NOT FIX. The loop now records a
    failure and carries on, which is right, but it also CREATED a receipt for a
    drill that could not be fully drawn. Before that, a failing drill produced
    no receipt at all and no reader could be fooled. The producer widened its
    shape and its readers stayed on the old assumption, so a three-phase drill
    became a two-figure page that exited 0 and said nothing.

    `allow_partial` is deliberate and explicit. It does not silence the
    finding: a caller that passes it must still show the reader what is
    missing.
    """
    undrawn = undrawn_phases(receipt)
    if undrawn and not allow_partial:
        raise SystemExit(
            undrawn_complaint(movement_id, undrawn) + WHY_REFUSED
        )
    return undrawn
