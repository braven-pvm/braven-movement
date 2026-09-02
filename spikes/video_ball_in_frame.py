"""Whether a ball was in the picture, which no curve can tell you.

THE BLIND SPOT THIS EXISTS FOR. Cutting clips for the coach page, a repetition
that the alignment scored BEST IN THE SET was rejected on sight: it contains no
ball. A frame strip across its whole window shows the athlete standing and
gesturing. **An elbow curve fits a gesture as happily as a catch**, and every
reading the gate had — warp distance, library rank, phase agreement, level gap —
is computed from that curve.

The gate asked eleven questions and not one of them was "is this a catch".

WHAT THE NUMBERS ACTUALLY SAID, measured rather than repeated
-------------------------------------------------------------

Repetition 0 of session 1.0, the window 5.267 to 5.833 s, on build bb7dc4c:

- **whole-curve scoring: 0.02369, the BEST of the twelve**, against 0.06093 for
  the next best. A margin of 2.6 times.
- **informative scoring: 0.02213, which is FIFTH**, behind 0.00435 (rep 6),
  0.00626 (rep 3), 0.01623 (rep 4) and 0.01743 (rep 7).
- **rank 1 of 8 drills on BOTH scorings.** It passes the null test either way.

So the superlative depends on which scoring is quoted, and the conclusion does
not: **neither scoring detects a missing ball.** The informative scoring
happened to rank it fifth, which is luck and not detection — fifth of twelve is
comfortably inside any band a person would pick from, and the clip lane picked
it.

A first version of this docstring said FOURTH. The place was read off a list of
three values rather than computed, and rep 7 at 0.01743 was left out of the
list. The argument does not move and the number was still wrong, which is the
whole reason places get computed here now.

One reading was odd about that repetition and nothing acted on it: its
`videoStillSharePhase` is 35 percent, more than double the next highest at 16.
The athlete is motionless for a third of the window. That is a symptom of
"nothing is happening here" and it is not a measure of whether a ball exists,
which is why it is recorded here and not promoted into a proxy.

WHY THIS IS A CAPTURE CONDITION AND NOT A PER-MEASURE ONE
----------------------------------------------------------

The gate splits its conditions into capture-wide and per-measure. This one is
capture-wide, and the argument is that the ball's presence **does not vary with
the measure**. The same frame either shows a ball or does not, whatever joint is
being read, so asking it per measure would assert a variation that does not
exist and would repeat one fact once per graded measure in a verdict that
already has to deduplicate its blockers.

It varies per REPETITION, which is a third scope the gate does not have. The
precedent settles it: `the drill is in the library` is already capture-wide and
is computed from per-repetition rankings. So this follows that shape — one
capture condition whose READING is per repetition, and which NAMES the
repetitions that fail rather than collapsing them to a count.

THE INSTRUMENT, AND THE TWO THAT DO NOT EXIST
----------------------------------------------

1. **A ball detector.** Not built. And a detector cannot gate anything until it
   has been validated against something, because a detector that fires on a
   bright patch of floor is worse than no detector: it would answer the
   question wrongly and confidently, which is the failure this whole gate is
   built to avoid.
2. **A human reading frame strips, per repetition.** THIS IS THE ONLY
   INSTRUMENT THAT EXISTS. It is what actually caught the fault, and this module
   is the file format it writes into.
3. **A shoot-day protocol** — the ball visibly in frame through every graded
   repetition, and a slate between repetitions. That is PREVENTION rather than
   measurement, and it belongs in the shoot specification.

Until an annotation exists the condition reads UNMEASURED and names the
instrument that does not exist. It does not pass.

TWO FIELDS, BECAUSE ONE BOOLEAN RECORDED SOMETHING FALSE
--------------------------------------------------------

`ballVisible` is asked **at the anchored moment** — the pull-in onset through
the peak, which is the part of the window a catch actually happens in. That is
the question "is this a catch rather than a gesture", and it is the one that
blocks.

`ballVisibleThroughout` is optional and asks whether the ball is in frame for
the WHOLE window. It exists because session 1.0 forced it: the clip lane's own
record says of repetition 1 that "she stands empty-handed for 2+ seconds before
it, then the ball drops in from off-frame". A single boolean would have had to
call that repetition either a catch with no empty lead or a gesture, and it is
neither. Recording it as one field would have put something false in a file
whose whole purpose is to be the honest one.

It is OPTIONAL because an annotator who only watched the catch must not be
made to guess about the lead. Absent means not asked, which is not "no".

A STALE ANNOTATION IS WORSE THAN NONE
--------------------------------------

Repetition indices are not stable. The alignment tooling changed twice in one
evening, and one of those changes — a lookback widened from 0.5 s to 1.0 s —
moved every window in the file. An annotation keyed on index alone would have
silently reattached to different footage and reported a human's judgement about
one repetition as though it were about another.

So every annotation carries the WINDOW it looked at, and loading refuses the
whole file if any window has moved. Refusing everything is deliberate: a file
that is half stale is a file nobody can tell the halves apart in.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Mapping, Sequence

SCHEMA_VERSION = "ball-in-frame-1"

# COMMITTED, NOT IN poc-output, and the distinction is the point. Everything
# else in the video chain is regenerable: run the extractor again and the
# keypoints come back. An annotation is a person watching footage, and it is
# the ONLY artefact in this pipeline a machine cannot rebuild. Left in a
# gitignored output directory it is one worktree teardown from not existing,
# and this lane has already destroyed 4.5 GB that way.
ANNOTATION_DIR = Path(__file__).resolve().parent / "video-annotations"


def annotation_path(set_id: str) -> Path:
    return ANNOTATION_DIR / f"ball-in-frame-{set_id}.json"

# How far a window may have moved and still be the same repetition. A tenth of
# a second is three frames at 30 fps: wide enough for a tooling change that
# nudges an onset by a frame or two, far narrower than the 0.567 s of the
# shortest repetition in session 1.0, so it cannot let one repetition's
# annotation land on its neighbour.
WINDOW_TOLERANCE_SECONDS = 0.1

# WHY A REPETITION CAN CARRY NO BALL, and they are not the same problem.
# `gesture` — the athlete was not catching; no ball anywhere in the window.
# `framing` — a genuine catch whose ball had left the picture by the anchored
#   moment, because the camera does not frame the flight.
# The first is answered by a slate between repetitions, the second by framing
# for the ball's flight, so the gate names which rather than sending a reader
# to the annotation to find out.
CAUSES = ("gesture", "framing")

# A pass resting on this many frames or fewer is reported as NARROW rather than
# as a plain pass. TWO, because the anchor itself is located "to about one
# frame and no better" (video_phase_align), so a pass inside two frames is
# inside the uncertainty of the question being asked.
NARROW_MARGIN_FRAMES = 2


class BallAnnotationError(ValueError):
    """The annotation cannot be trusted, so it is not used at all."""


def load_annotation(path: Path) -> dict | None:
    """Read an annotation file, or None when there is none.

    None is not an empty annotation. It means nobody has looked, and the
    condition must say so rather than reading an absence as a pass.
    """
    path = Path(path)
    if not path.exists():
        return None
    document = json.loads(path.read_text(encoding="utf-8"))
    if document.get("schemaVersion") != SCHEMA_VERSION:
        raise BallAnnotationError(
            f"{path} is {document.get('schemaVersion')!r}, not {SCHEMA_VERSION!r}")
    seen: set[int] = set()
    for row in document.get("repetitions", []):
        for field in ("index", "startSeconds", "endSeconds", "ballVisible", "evidence"):  # noqa: E501
            if field not in row:
                raise BallAnnotationError(
                    f"{path}: a repetition is missing {field!r}. Every "
                    "annotation carries the window it looked at and the "
                    "evidence for what it saw; an annotation without evidence "
                    "is an opinion.")
        for field in ("ballVisible", "ballVisibleThroughout"):
            if row.get(field) not in (True, False, None):
                raise BallAnnotationError(
                    f"{path}: {field} is {row.get(field)!r}. It is true, "
                    "false, or null for 'not looked at' — and null is not "
                    "false.")
        if row.get("cause") not in (None, *CAUSES):
            raise BallAnnotationError(
                f"{path}: cause is {row['cause']!r}, and it is one of "
                f"{', '.join(CAUSES)}. The two need different shoot "
                "instructions, so a row that blocks says which.")
        margin = row.get("marginFrames")
        if margin is not None and (not isinstance(margin, int) or margin < 0):
            raise BallAnnotationError(
                f"{path}: marginFrames is {margin!r}. It is a count of frames "
                "or null for 'not counted'.")
        if row["index"] in seen:
            raise BallAnnotationError(
                f"{path}: repetition {row['index']} is annotated twice, so "
                "which annotation wins is whichever was written last.")
        seen.add(row["index"])
    return document


def check_windows(
    annotation: Mapping, alignments: Sequence[Mapping],
    tolerance: float = WINDOW_TOLERANCE_SECONDS,
) -> None:
    """Refuse the whole annotation if any window has moved.

    THE WHOLE FILE, not the rows that moved. A half-stale annotation is one
    nobody can tell the halves apart in, and the failure it would produce is a
    human's judgement about one repetition presented as judgement about
    another.
    """
    for row in annotation.get("repetitions", []):
        index = row["index"]
        if index >= len(alignments):
            raise BallAnnotationError(
                f"the annotation covers repetition {index} and the alignment "
                f"has {len(alignments)}. The tooling has changed since it was "
                "written; look again rather than trusting the overlap.")
        window = alignments[index]["window"]
        moved = max(
            abs(float(window["startSeconds"]) - float(row["startSeconds"])),
            abs(float(window["endSeconds"]) - float(row["endSeconds"])))
        if moved > tolerance:
            raise BallAnnotationError(
                f"repetition {index} was annotated over "
                f"{row['startSeconds']}-{row['endSeconds']} s and the "
                f"alignment now places it at {window['startSeconds']}-"
                f"{window['endSeconds']} s, {moved:.3f} s away. The annotation "
                "is stale and none of it is used.")


def judge(annotation: Mapping | None, alignments: Sequence[Mapping]) -> dict:
    """Was a ball in the picture for every repetition the readings came from?

    Returns the reading, the verdict and the repetitions that carry it. The
    verdict is three-valued for the same reason every other condition's is: a
    repetition nobody looked at is not a repetition with a ball.
    """
    total = len(alignments)
    if annotation is None:
        # `withBall` IS A LIST ON EVERY PATH. A first version returned 0 here
        # and a list below — one field with two types, which a caller taking
        # `len()` of it discovers only on the path it did not test. Every
        # repetition list here is a list of indices, empty when there are none.
        return {
            "annotated": 0, "total": total,
            "withBall": [], "withoutBall": [], "notLookedAt": list(range(total)),
            "passes": None,
            "detail": (
                "No annotation exists for this set, so nothing has looked at "
                "whether a ball is in the picture in any of the "
                f"{total} repetitions."),
        }
    check_windows(annotation, alignments)
    by_index = {row["index"]: row for row in annotation.get("repetitions", [])}
    without = sorted(n for n, row in by_index.items() if row["ballVisible"] is False)
    causes = {n: by_index[n].get("cause") for n in without}
    narrow = sorted(
        n for n, row in by_index.items()
        if row["ballVisible"] is True
        and row.get("marginFrames") is not None
        and row["marginFrames"] <= NARROW_MARGIN_FRAMES)
    unlooked = sorted(
        set(range(total)) - {n for n, row in by_index.items()
                             if row["ballVisible"] is not None})
    with_ball = sorted(n for n, row in by_index.items() if row["ballVisible"] is True)
    named = ", ".join(
        f"{n} ({causes[n]})" if causes.get(n) else str(n) for n in without)
    # THE ACTUAL MARGIN, not the threshold it fell under. A first version said
    # "pass on 2 frames or fewer" of two repetitions that each pass on ONE, and
    # reporting the bar instead of the reading is the fault this gate spends
    # its whole design avoiding.
    spans = [f"{n} ({by_index[n]['marginFrames']} "
             f"{'frame' if by_index[n]['marginFrames'] == 1 else 'frames'})"
             for n in narrow]
    thin = (
        f" NARROW PASSES: {', '.join(spans)}. The anchor is itself located to "
        "about one frame and no better, and the two views are synchronised to "
        "no better than 0.25 s, so a margin this thin is inside the "
        "uncertainty of the question — read them as narrow, not as clear."
        if narrow else "")
    if without:
        passes = False
        detail = (
            f"{len(without)} of {total} repetitions have NO BALL IN FRAME: "
            f"{named}. Every reading in this report is computed across the "
            "repetitions, so any one of them without a ball contaminates the "
            "set. The two causes need different shoot instructions: a "
            "`gesture` is answered by a slate between repetitions, a `framing` "
            "by framing for the ball's flight." + thin)
    elif unlooked:
        passes = None
        detail = (
            f"{len(unlooked)} of {total} repetitions have not been looked at: "
            f"{', '.join(str(n) for n in unlooked)}. Not looked at is not "
            "'no ball' and it is not 'ball'.")
    else:
        passes = True
        detail = (
            f"All {total} repetitions were looked at and every one shows a "
            "ball in frame." + thin)
    return {
        "annotated": len(by_index), "total": total,
        "withBall": with_ball, "withoutBall": without, "notLookedAt": unlooked,
        "causes": causes, "narrowPasses": narrow,
        "passes": passes, "detail": detail,
    }
