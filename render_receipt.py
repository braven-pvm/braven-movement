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

# EVERY REFUSAL IN THIS MODULE RAISES `SystemExit`, AND THAT CONSTRAINS ANY TEST
# OF ONE. Raised by the movement lane on 2026-09-09.
#
#   catch `SystemExit`, never `Exception`   it inherits from BaseException
#   NEVER call a refusal from `setUpClass`  `unittest` wraps that in
#                                           `except Exception`, so the raise
#                                           ESCAPES the runner and silently kills
#                                           every later test in the module
#
# This repository has already had two mutations exit 1 that way and be read as
# failures. The type is not being changed: `SystemExit` is this module's
# convention across all seven refusals, and these are called from scripts that
# must stop with a message. Changing one would make the module inconsistent and
# changing all seven is its own unit with its own callers to check.


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


# WHAT THE SOLVE WAS SET TO, WHICH THE RECEIPT DID NOT RECORD UNTIL 2026-09-09.
#
# `docs/COACH_REVIEW_SPEC_INTERFACE.md` section 4 gives this lane the form
# `render_pair(parameter, value_a, value_b)`, and a receipt could not verify one.
# Two jobs at two parameter values have two different `jobSha256`, so the
# receipts are DISTINGUISHABLE. Nothing said which hash meant which value.
#
# The name and the value are the PRODUCER's fact, so they belong in the job and
# this lane copies them through rather than inventing them. That direction
# matters: `docs/FLEXION_AXIS_PAPER.md` refuses to send a euler component index
# the other way for the same reason, and this lane's shoulder positions in
# metres were withdrawn for it on 4 September.
#
# A caller cannot supply it. `blender_movement_render.py` already refuses a
# caller-supplied build stamp, because a stamp a caller supplies is a claim
# about a build rather than a reading of one, and a parameter is the same shape.
# A PRODUCER IMPORTS THIS CONSTANT. `spikes/export_blender_job.py` uses it
# rather than spelling the key, so there is ONE spelling and a rename moves
# both ends together. That is what closes the rename hole, and it closes it
# BY CONSTRUCTION rather than by a test.
#
# DO NOT MOVE OR RENAME IT THINKING IT IS PRIVATE, and do not remove the
# import at the other end. `tests/test_solve_parameters.py` deliberately does
# NOT assert the key, so removing the import opens the hole and leaves the
# suite green.
SOLVE_PARAMETERS = "solveParameters"

NO_SOLVE_PARAMETERS = (
    "the job records no `solveParameters`, so nothing can say which parameter "
    "value produced this picture"
)


MALFORMED_SOLVE_PARAMETERS = (
    "the job's `{field}` is a {kind}, not a mapping of name to value. A job that "
    "says something unreadable is not a job that says nothing, and rendering it "
    "would write a receipt claiming no parameters were recorded."
)


def solve_parameters(job: dict) -> dict | None:
    """What the job says the solve was set to. None when it says nothing.

    ABSENCE IS RECORDED, NEVER SILENTLY DROPPED. A receipt with the key missing
    and a receipt with the key set to null read the same to a careless reader
    and mean different things: one predates the field and one was rendered from
    a job that carried no parameters. The renderer writes null for the second.

    AND A THIRD STATE WAS COLLAPSED INTO THE SECOND UNTIL THE CHARACTER AND
    ANIMATION LANE READ THIS. A job whose `solveParameters` is a list or a
    string returned None, so the receipt said null, which reads as "this job
    carried no parameters". It carried some and they were unreadable. That is
    the same fault this docstring was written to guard, one state further along.

    So a WRONG TYPE now raises. It is not this lane's fact to correct and not
    this lane's fact to paper over: a broken contract is refused rather than
    guessed at. An EMPTY mapping still returns None, because `{}` is a
    well-formed statement that there are none.
    """
    if SOLVE_PARAMETERS not in job:
        return None
    found = job[SOLVE_PARAMETERS]
    if found is None:
        return None
    if not isinstance(found, dict):
        raise SystemExit("REFUSED: " + MALFORMED_SOLVE_PARAMETERS.format(
            field=SOLVE_PARAMETERS, kind=type(found).__name__))
    return found or None


def refuse_unverifiable_pair(parameter: str, receipt_a: dict,
                             receipt_b: dict) -> tuple[object, object]:
    """Raise unless these two receipts are a pair differing only in `parameter`.

    FOUR THINGS MUST HOLD, and each one has a way of being wrong that reads as
    success:

    1. Both receipts name the parameter. Without it the pair is two pictures.
    2. Their values DIFFER. Two pictures at one value are not a pair, and a
       caller that fetched the same job twice would otherwise be told they are.
    3. Every OTHER parameter is EQUAL. A pair whose second parameter also moved
       shows a difference the caption attributes to the first one.

       THIS RULE IS CORRECT AND TODAY IT IS DORMANT, and calling it "the rule
       that carries the weight" was wrong. The producer records exactly ONE
       parameter, so `set(left) | set(right)` holds one key, `key != parameter`
       empties it, and `moved` is ALWAYS `[]`. It cannot fire against any
       receipt this repository can currently produce.

       It has no power for the same reason a reproduction test on a square
       athlete had none: the thing it compares cannot differ. The tests build a
       two-key pair and prove it CAN fail, which is a different claim from its
       being able to fail on real data.

       WHAT MAKES IT LIVE is the producer recording a second parameter.
       `contact_solve.py` holds fifteen module-level constants and the movement
       lane names four as affecting the solve and unrecorded. Until then, every
       unrecorded parameter is equal BY CONSTRUCTION rather than by check,
       because both jobs of a pair are built in one process from one build.

       SO THE HAZARD IS A PAIR SPANNING TWO BUILDS. It could differ in all four
       and pass every refusal, and the caption would attribute the whole
       difference to the one recorded parameter. A coach-morning comparison is
       exactly that case.
    4. Both are the same drill. Two drills are not a pair however the parameters
       read.
    """
    for name, receipt in (("a", receipt_a), ("b", receipt_b)):
        if not isinstance(receipt.get(SOLVE_PARAMETERS), dict):
            raise SystemExit(
                f"REFUSED: receipt {name} has no `{SOLVE_PARAMETERS}`. "
                + NO_SOLVE_PARAMETERS
            )
    left = receipt_a[SOLVE_PARAMETERS]
    right = receipt_b[SOLVE_PARAMETERS]
    for name, found in (("a", left), ("b", right)):
        if parameter not in found:
            raise SystemExit(
                f"REFUSED: receipt {name} does not name `{parameter}`, so it "
                "cannot be one half of a pair about it."
            )
    if left[parameter] == right[parameter]:
        raise SystemExit(
            f"REFUSED: both receipts carry `{parameter}` = {left[parameter]}. "
            "Two pictures at one value are not a pair."
        )
    if receipt_a.get("movementId") != receipt_b.get("movementId"):
        raise SystemExit(
            f"REFUSED: {receipt_a.get('movementId')} against "
            f"{receipt_b.get('movementId')}. Two drills are not a pair."
        )
    moved = sorted(
        key for key in set(left) | set(right)
        if key != parameter and left.get(key) != right.get(key)
    )
    if moved:
        raise SystemExit(
            f"REFUSED: {len(moved)} other parameter(s) also differ: "
            f"{', '.join(moved)}. A difference in the pictures could not be "
            f"attributed to `{parameter}`."
        )
    return left[parameter], right[parameter]
