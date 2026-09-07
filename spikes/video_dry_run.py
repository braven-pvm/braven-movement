"""Grade a filmed repetition end to end, and refuse when it cannot be graded.

THE COMMAND THAT RUNS ON DAY ONE OF THE SHOOT. It reads what the pipeline
already produced — keypoints, the lift, the elbow curve, the phase alignment,
and a calibration file if one exists — puts every reading through one gate, and
writes a report a coach could be shown.

On session 1.0 that report says NO NUMBER MAY BE SHOWN, and that is the correct
output rather than a failure of this tool. The footage has no calibration
reference, no clap, and a drill the library does not contain. A dry run whose
only possible answer were "yes" would be a decoration.

    pixi run python video_dry_run.py --set 0.1

THE GATE, AND WHY IT IS NOT A CHECKLIST
---------------------------------------

Twelve conditions, and they split in two.

**Six belong to the CAPTURE** and are asked once — two views, a calibration,
enough camera separation, a sync, whether the filmed drill is one the engine
models, and whether A BALL IS IN THE PICTURE. A second camera and a clap are
not properties of an elbow.

The last of those is the newest and it was found the hard way. Cutting clips
for the coach page, the repetition the whole-curve scoring ranked BEST of
twelve turned out to contain no ball at all — the athlete standing and
gesturing. An elbow curve fits a gesture as happily as a catch, and every
reading the gate had was computed from that curve. Refer to
`video_ball_in_frame.py`.

**Six belong to a MEASURE** and are asked of EVERY measure a checkpoint reads:
does the modality carry it, were its landmarks seen, does an engine curve
exist, do the units agree, do two readings of it agree, do two alignments of it
agree. The right elbow being invisible says nothing about the left knee.

WHICH measures those are comes from `MovementDefinition.graded_measures()` and
never from a list written here. Four consumers had each picked their own set
and none was reconciled with what the coaching layer grades, which is how
`leftKneeFlexionDegrees` — graded by every drill in the library — came to have
no reference curve at all.

Each condition carries a READING, a THRESHOLD, and where the threshold came
from, because a bar somebody invented and a bar something measured are not the
same kind of claim and a reader must be able to tell them apart:

- **measured** — the number came off this material or an earlier one.
- **derived** — the number follows from another number by arithmetic written
  down here.
- **chosen** — somebody picked it. Every chosen threshold says why, and a
  reader may disagree with it without disagreeing with any measurement.

A condition that CANNOT BE ANSWERED from the material is not a pass. It blocks,
and it blocks LOUDLY, marked `unmeasured`. That matters more per measure than
per capture: today two instruments exist and both read one measure, so most
measures reach most of their conditions unread, and every one of those says so
and names the instrument that does not exist. Where a change touches something
nothing reads, the absence of the measure IS the risk, and a gate that treated
silence as consent would be the politest possible way of shipping a wrong
number to a coach.

WHAT "ILLUSTRATIVE" MEANS HERE
------------------------------

The report's own language, taken from `docs/VIDEO_CAPTURE_FINDINGS.md`: the
shape is right and the numbers are not; in fast phases the lift is illustrative
and NEVER A MEASUREMENT AT THIS CALIBRATION. Every figure this writes while the
gate is shut carries that phrase, and the phrase is the reason the figure is
allowed to appear at all.

EVERY NUMBER CARRIES ITS UNCERTAINTY, OR SAYS WHAT IS MISSING
-------------------------------------------------------------

A reading with no uncertainty is not modest, it is unfinished. Where no second
instrument read a quantity, this writes `uncertainty: null` and NAMES THE
INSTRUMENT THAT DOES NOT EXIST, so a reader can tell "small error" from "nobody
looked".
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import numpy as np

SPIKE_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(SPIKE_DIR))

from ball_track import MOVEMENT_DIR  # noqa: E402
from build_stamp import generated_from  # noqa: E402
from movement_definition import load as load_definition  # noqa: E402
from video_ball_in_frame import BallAnnotationError  # noqa: E402
from video_ball_in_frame import judge as judge_ball  # noqa: E402
from video_ball_in_frame import annotation_path, load_annotation  # noqa: E402
from video_measures import DEGREES, scarcest_landmark  # noqa: E402
from video_measures import measure as video_measure  # noqa: E402
from video_phase_align import featureless_share  # noqa: E402

OUTPUT = SPIKE_DIR / "poc-output" / "video"
SCHEMA_VERSION = "video-dry-run-1"

# The clinical threshold for a difference worth showing a coach. It is
# `multi_camera_fit.MEANINGFUL_DEGREES`, imported as a number rather than a
# module because that module imports the solver.
MEANINGFUL_DEGREES = 5.0
# Below this separation the two cameras see the same thing.
MINIMUM_SEPARATION_DEGREES = 45.0
# The fastest a hand moves in these drills, from the speed banding in
# VIDEO_SPIKE_NOTES.md. Used to turn a sync error into millimetres.
FAST_HAND_METRES_PER_SECOND = 2.0

# THE OPEN QUESTIONS. These are not grading conditions and they must never be
# mixed with them: a capture can be perfectly gradeable and still be unable to
# answer a question the engine has not settled. They are asked separately and
# they carry their own verdict.
RELEASE_RAMP_SECONDS = 0.067
RELEASE_RAMP_SAMPLES = 5
RELEASE_FRAME_RATE = 120.0
ADDRESSABLE_KEYFRAME_SECONDS = 1.0


def reading(
    value, uncertainty, units: str, instrument: str, note: str | None = None
) -> dict:
    """One number, with what is known about how wrong it is.

    `uncertainty` of None is not "small". It means nothing measured this twice,
    and `instrument` then has to name the instrument that does not exist.
    """
    return {
        "value": value,
        "uncertainty": uncertainty,
        "units": units,
        "instrument": instrument,
        **({"note": note} if note else {}),
    }


def tidy(value, places: int = 4):
    """Round a float for a report. A bar of 0.03333333333333333 is noise."""
    return round(value, places) if isinstance(value, float) else value


def condition(
    name: str, question: str, reading_value, units: str, threshold,
    threshold_kind: str, threshold_why: str, passes: bool | None,
    why: str, instrument: str,
) -> dict:
    """One gate condition.

    `threshold_kind` is a SEPARATE FIELD from the prose that explains it, and
    that is deliberate. A first version packed both into one string and the
    report then read the kind back out by splitting on the first colon, which
    turned a sentence containing two colons into a table cell containing half
    a sentence. A field a reader has to parse is not a field.
    """
    if threshold_kind not in ("measured", "derived", "chosen", "unavailable"):
        raise ValueError(f"a threshold is measured, derived or chosen, not {threshold_kind!r}")
    return {
        "name": name,
        "question": question,
        "reading": tidy(reading_value),
        "units": units,
        "threshold": tidy(threshold),
        "thresholdKind": threshold_kind,
        "thresholdWhy": threshold_why,
        "passes": passes,
        "why": why,
        "instrument": instrument,
    }


def phase_bound_degrees(curve: list[float], meaningful: float = MEANINGFUL_DEGREES):
    """How closely two alignments must agree, DERIVED from the curve's steepness.

    A phase error costs degrees at the rate the reference curve is climbing. So
    the tolerable phase error is the clinical threshold divided by the steepest
    slope in the informative part of the curve. Nothing is chosen here except
    the clinical threshold, which the product already chose.

    Returns the bound and the slope it came from, so a reader can redo the
    division rather than trust it.
    """
    values = np.asarray([v for v in curve if v is not None], dtype=np.float64)
    if len(values) < 3:
        return None, None
    phase = np.linspace(0.0, 1.0, len(values))
    start = int(featureless_share(values) * (len(values) - 1))
    informative = slice(max(start, 1), len(values))
    # A CURVE THAT NEVER MOVES HAS NO INFORMATIVE PART, and `np.gradient` on
    # the one sample that leaves raises an IndexError from inside numpy rather
    # than saying so. A refusal is the answer, not a traceback: nothing can be
    # derived from a reference that does nothing.
    if len(values[informative]) < 2:
        return None, None
    slope = np.abs(np.gradient(values[informative], phase[informative]))
    steepest = float(np.percentile(slope, 90))
    if steepest <= 0.0:
        return None, None
    return meaningful / steepest, steepest


def load(path: Path) -> dict | None:
    return json.loads(path.read_text(encoding="utf-8")) if path.exists() else None


def gather(set_id: str) -> dict:
    """Every artefact the gate reads, and None for each one that is absent."""
    return {
        "front": load(OUTPUT / f"keypoints-front-{set_id}.json"),
        "side": load(OUTPUT / f"keypoints-side-{set_id}.json"),
        "lift": load(OUTPUT / f"lift-3d-{set_id}.json"),
        "elbow": load(OUTPUT / f"elbow-curve-{set_id}.json"),
        "alignment": load(OUTPUT / f"phase-alignment-{set_id}.json"),
        "reference": load(OUTPUT / "reference-curves.json"),
        "calibration": load(OUTPUT / f"calibration-{set_id}.json"),
        # THE ANNOTATION IS LOADED HERE, not in the gate, so there is ONE way
        # into `judge_capture` — a dict — rather than a dict for a test and a
        # path for a run. A refusal is carried as text beside it instead of
        # raised, because a stale annotation must shut the gate loudly and must
        # not cost the reader the rest of the report.
        **_ball_annotation(set_id),
    }


def _ball_annotation(set_id: str) -> dict:
    """The annotation and any refusal, from the COMMITTED path.

    Committed rather than `poc-output`: an annotation is a person watching
    footage, and it is the only artefact in this chain a machine cannot
    rebuild.
    """
    try:
        return {"ballAnnotation": load_annotation(annotation_path(set_id)),
                "ballAnnotationRefusal": None}
    except BallAnnotationError as refusal:
        return {"ballAnnotation": None, "ballAnnotationRefusal": str(refusal)}


# The artefacts a run cannot start without. AN ALLOWLIST OF WHAT IS REQUIRED,
# never a denylist of what is optional.
REQUIRED_ARTEFACTS = ("front", "side", "lift", "elbow", "alignment", "reference")


def missing_artefacts(evidence: dict) -> list[str]:
    """Which required artefacts are absent, in a testable place.

    THIS LIVED INSIDE `main` AND THAT IS WHY IT BROKE UNCAUGHT. The check was
    once written as a denylist — "every key whose value is None, except the
    calibration" — so the first OPTIONAL key added after it stopped the run
    from starting at all. The key was the ball annotation, whose absence is the
    normal case, and the failure was `these artefacts are missing:
    ballAnnotationRefusal` on a set with nothing wrong with it.

    Restoring that denylist left all 81 tests green, because nothing could
    reach the check: only a real run touched it. Lifting it out of `main` is
    the fix, and the test that an optional key at None does not stop a run is
    the point of lifting it.

    A rule written as "everything except the exceptions I know about" breaks on
    the next exception, and it breaks where nobody is looking.
    """
    return [name for name in REQUIRED_ARTEFACTS if evidence.get(name) is None]


def graded_measures(movement: str) -> list[str]:
    """The measures this movement's checkpoints read, from the definition itself.

    `MovementDefinition.graded_measures()`, never a list written here. Four
    downstream consumers had each picked their own set and none was reconciled
    with what the coaching layer grades, which is how `leftKneeFlexionDegrees` —
    graded by every drill in the library — came to have no reference curve.

    `MOVEMENT_DIR` comes from `ball_track`, NOT from `movement_engine`, whose
    `library` is a directory glob living in a module that imports the solver.
    That import turned eleven checks into one error twice.
    """
    path = MOVEMENT_DIR / f"{movement}.json"
    if not path.exists():
        raise SystemExit(
            f"{path} does not exist, so nothing can be said about what "
            f"{movement} grades. A gate that guessed the measures would cover "
            "whatever it guessed.")
    return sorted(load_definition(path).graded_measures())


def reference_curve(evidence: dict, movement: str, name: str) -> tuple[list | None, str | None]:
    """A measure's engine curve and its declared unit, across both file shapes.

    TWO SHAPES ARE READ ON PURPOSE. Today `curves[measure]` is the list itself
    and no unit is declared anywhere. The widening designed in
    `docs/REFERENCE_CURVE_WIDENING.md` makes it `{"unit": ..., "values": [...]}`
    because `footHeightGapCm` is centimetres and the file announces itself as
    angles. Reading both means this gate works before and after that export,
    and reports the unit as UNDECLARED rather than assuming degrees in the
    meantime — which is the assumption the widening exists to remove.
    """
    drill = (evidence.get("reference") or {}).get("movements", {}).get(movement)
    if not drill:
        return None, None
    curve = drill.get("curves", {}).get(name)
    if curve is None:
        return None, None
    if isinstance(curve, dict):
        return curve.get("values"), curve.get("unit")
    return curve, None


def judge_capture(evidence: dict, movement: str) -> list[dict]:
    """The conditions that belong to the CAPTURE, not to any one measure.

    Six of them. They are asked once, because a second camera, a clap and a
    ball in the picture are not properties of an elbow.
    """
    found = []

    views = [name for name in ("front", "side") if evidence.get(name)]
    found.append(condition(
        "two views", "Did two cameras see this repetition?",
        len(views), "cameras", 2, "measured",
        "one camera gave 49 degrees of mean angle error against 0.04 from two, "
        "in multi_camera_fit's own spike",
        len(views) >= 2,
        "One camera cannot resolve depth, so a single view may show a shape and "
        "never a figure.",
        "the keypoint files present for this set",
    ))

    calibration = evidence.get("calibration")
    found.append(condition(
        "calibration", "Is there a calibration for this rig, and does it hold?",
        None if calibration is None else calibration["extrinsics"]["worked"]["residualMetres"],
        "metres", 0.010, "chosen",
        "a consumer tolerance loose enough for an honest fit and tight enough "
        "that any sign error fails it by a hundredfold",
        None if calibration is None else True,
        "Without a calibration the depth axis is scaled by matching a body "
        "length between two cameras at unknown distances with unknown lenses, "
        "and there is no way to check that scale at all — not to confirm it and "
        "not to rule it out.",
        "calibration-<set>.json, written by video_calibration.py",
    ))

    separation = (
        None if calibration is None
        else calibration["extrinsics"]["separationDegrees"])
    found.append(condition(
        "camera separation", "Are the cameras far enough apart to see depth?",
        separation, "degrees", MINIMUM_SEPARATION_DEGREES, "measured",
        "multi_camera_fit's spike found the pair adds nothing below it",
        None if separation is None else separation >= MINIMUM_SEPARATION_DEGREES,
        "The 90 degrees this material assumes is an ASSUMPTION written in "
        "video_lift_3d.py, not a reading. Nothing in the footage measures it.",
        "the calibration's extrinsics; unmeasured without one",
    ))

    sync = (evidence["side"] or {}).get("sync", {})
    uncertainty = sync.get("offsetUncertaintySeconds")
    step = 1.0 / 30.0
    found.append(condition(
        "sync", "Are the two views on one clock to within a frame?",
        uncertainty, "seconds", step, "chosen",
        "one frame, because that is the finest this material can resolve and a "
        "clap reaches it. The DERIVED bound is far tighter: the lift's own "
        f"15 mm residual over a hand at {FAST_HAND_METRES_PER_SECOND} m/s "
        f"allows only {0.015 / FAST_HAND_METRES_PER_SECOND * 1000:.0f} ms. The "
        "looser bar is used because a sub-frame claim cannot be verified here "
        "at all, and a bar nothing can check is not a bar.",
        None if uncertainty is None else uncertainty <= step,
        "A hand at 2 m/s is displaced 30 cm between the views at 150 ms, so "
        "every two-view figure in a fast phase inherits that.",
        "the sync block in the keypoint file",
    ))

    alignment = evidence.get("alignment") or {}
    ranks = alignment.get("askedDrillRanks") or []
    found.append(condition(
        "the drill is in the library",
        "Is the filmed movement one the engine models?",
        None if not ranks else alignment.get("askedDrillRanksFirstOn"),
        f"of {len(ranks)} repetitions ranking it first" if ranks else "repetitions",
        len(ranks) or None, "chosen",
        "a drill the engine models should win its own null test on EVERY "
        "repetition, not on most of them",
        None if not ranks else alignment.get("askedDrillRanksFirstOn") == len(ranks),
        "Every library drill is fed by a PASSER. Session 1.0 is a self-fed "
        "toss, so the ball arrives slowly, vertically, and at a moment she "
        "chose. A perfect two-camera capture of a self-toss still grades "
        "nothing, and no calibration fixes that.",
        "the null test in phase-alignment-<set>.json",
    ))

    # A BALL IN THE PICTURE, which no curve can tell you. Capture-wide because
    # the ball's presence does not vary with the measure — the same frame either
    # shows one or does not, whatever joint is read — and its READING is per
    # repetition because that is where it does vary.
    rows = (evidence.get("alignment") or {}).get("alignments") or []
    stale = evidence.get("ballAnnotationRefusal")
    if stale:
        ball = {"withBall": [], "total": len(rows), "passes": None,
                "detail": f"THE ANNOTATION WAS REFUSED: {stale}"}
    else:
        try:
            ball = judge_ball(evidence.get("ballAnnotation"), rows)
        except BallAnnotationError as refusal:
            stale = str(refusal)
            ball = {"withBall": [], "total": len(rows), "passes": None,
                    "detail": f"THE ANNOTATION WAS REFUSED: {stale}"}
    found.append(condition(
        "a ball is in the picture",
        "Was a ball in frame for every repetition the readings came from?",
        len(ball["withBall"]), f"of {ball['total']} repetitions confirmed",
        ball["total"] or None, "chosen",
        "every repetition, because every reading in this report is computed "
        "ACROSS the repetitions, so one gesture among them contaminates the set",
        ball["passes"],
        "AN ELBOW CURVE FITS A GESTURE AS HAPPILY AS A CATCH. On session 1.0 "
        "the repetition the whole-curve scoring ranked BEST of twelve — 0.02369 "
        "against 0.06093 for the next — contains no ball at all: a frame strip "
        "shows the athlete standing and gesturing. It ranks 1 of 8 drills on "
        "BOTH scorings, so the null test does not see it either. The "
        "informative scoring placed it fifth of twelve, which is luck "
        "rather than detection. " + ball["detail"],
        f"ball-in-frame-<set>.json, a human reading frame strips per repetition"
        if ball["passes"] is not None or stale else
        "THE INSTRUMENT THAT DOES NOT EXIST: no ball detector is built, and "
        "the only instrument that has ever answered this is a person reading "
        "frame strips. Write ball-in-frame-<set>.json and it is read.",
    ))
    return found


def judge_open_questions(evidence: dict, movement: str) -> list[dict]:
    """Can this capture answer what the ENGINE cannot yet author?

    SEPARATE FROM THE GRADING CONDITIONS ON PURPOSE, and the separation is the
    point. `judge_capture` and `judge_measure` decide whether a number may be
    shown to a coach. These decide whether the footage can settle a question
    the model has left open. A capture can pass every grading condition and
    fail every one of these, and that is not a contradiction: grading reads
    angles at named phases, and these read a rate of change over a few frames.
    Folding them into one verdict would fail gradeable footage for missing a
    measurement nobody was grading.
    """
    found = []

    # BOTH VIEWS, and the worse of the two. A hand speed read in one image is a
    # PROJECTION and therefore a lower bound, exactly as the wrist reading is,
    # so the measurement needs the pair. Reading only the front would also have
    # missed the very fault that put the keyframe condition here: the ten-second
    # keyframe interval of session 1.0 is on the SIDE file, and the front's is
    # one second.
    def reading_of(field, pick):
        values = []
        for view in ("front", "side"):
            value = ((evidence.get(view) or {}).get("source") or {}).get(field)
            if value is None:
                return None
            values.append(value)
        return pick(values)

    rate = reading_of("framesPerSecondMeasured", min)
    found.append(condition(
        "the release is resolved",
        "Are there enough frames in the release to see the hand accelerate?",
        rate, "frames per second", RELEASE_FRAME_RATE, "derived",
        "the athlete's own ramp, measured on this footage: her wrist goes from "
        f"0.7 to 6.3 cm per frame in {RELEASE_RAMP_SECONDS * 1000:.0f} ms at "
        f"the rep 7 toss. {RELEASE_RAMP_SAMPLES} samples inside that ramp is a "
        f"CHOSEN minimum and needs "
        f"{RELEASE_RAMP_SAMPLES / RELEASE_RAMP_SECONDS:.0f} fps, so the next "
        "standard rate above it. The engine's own claim is a difference "
        "between two ADJACENT frames of a 60 fps track, so below 60 fps there "
        "is no frame pair that corresponds to it at all.",
        None if rate is None else rate >= RELEASE_FRAME_RATE,
        "The engine's hands move 0.72 cm in the frame before release and "
        "7.37 cm in the frame after, a factor of 10.2, so NOTHING DRIVES THE "
        "BALL at the moment it leaves. Whether the carry should accelerate "
        "before release is decided by this measurement and by nothing else "
        "available. At 30 fps one frame spans both of the engine's, so the two "
        "are averaged together and the step cannot be seen even in principle.",
        "framesPerSecondMeasured in BOTH keypoint files' source blocks, "
        "the SLOWER of the two; unmeasured unless both record it",
    ))

    keyframes = reading_of("keyframeIntervalSecondsMeasured", max)
    found.append(condition(
        "the release moment is addressable",
        "Can a reader ask for the release frame and receive that frame?",
        keyframes, "seconds", ADDRESSABLE_KEYFRAME_SECONDS, "chosen",
        "one second, because that is what the front camera of session 1.0 "
        "actually did and nothing about it caused trouble",
        None if keyframes is None else keyframes <= ADDRESSABLE_KEYFRAME_SECONDS,
        "SEPARATE FROM THE FRAME RATE, and it has already cost this project a "
        "reading. The side file of session 1.0 carries THREE keyframes, at "
        "0.000, 9.996 and 19.992 seconds. Any keyframe-snapping reader asked "
        "for 16.93 on it lands at 9.996, and 9.996 is where repetition 2's "
        "catch lives, so repetition 2's catch appeared under a repetition 7 "
        "label. A capture can run at 240 fps and still put the one frame that "
        "matters out of reach.",
        "keyframeIntervalSecondsMeasured in BOTH source blocks, the LONGER "
        "of the two, because one unreachable view is enough to lose the "
        "frame. No tool in this repository records it yet, so this reads "
        "unmeasured on every set until video_keypoints.py writes it",
    ))

    found.append(condition(
        "the floor is in view",
        "If the ball touches the floor, do both cameras see the contact?",
        None, "cameras seeing the contact", None, "unavailable",
        "THERE IS NO BAR TO SET. The engine has no floor, so no drill in the "
        "library can declare that its ball bounces, and the gate cannot ask "
        "the question of a capture at all.",
        None,
        "A released ball is ONE UNBROKEN PARABOLA in this engine. A bounce "
        "pass cannot be represented today, so it cannot be graded and it "
        "cannot be authored either. If the floor is ruled in, the rebound "
        "ratio must be MEASURED from footage and never typed: ball height "
        "before the floor contact and after it, at a known distance, in both "
        "cameras. A typed ratio would be a number with no instrument behind "
        "it, which is the shape of every figure this lane has had to withdraw.",
        f"MovementDefinition for {movement} has no floor and no bounce, so "
        "nothing reads this",
    ))
    return found


def instrument_readings(evidence: dict) -> dict[str, dict]:
    """What each measure has actually been read by, KEYED BY MEASURE NAME.

    A FIRST VERSION ASKED "IS THIS THE ELBOW", and that was wrong in a way
    worth writing down. It hard-coded today's single instrument into the gate's
    logic, so the day a knee reader exists the gate would still have reported
    the knee as unread — and, worse, no synthetic evidence could ever open the
    gate for any measure but one, which would have quietly retired the property
    that this gate CAN open.

    So the question is "does evidence exist FOR THIS MEASURE", answered by a
    lookup. Today two instruments exist and both read one measure, so this
    returns one entry on real footage. When a second reader lands it populates
    another entry and the gate opens for it without a line changing here.

    The elbow curve names its arm rather than its measure, so the arm is
    translated once, here, rather than at each use.
    """
    found: dict[str, dict] = {}
    elbow = evidence.get("elbow") or {}
    named = elbow.get("measure") or {
        "left": "leftElbowFlexionDegrees",
        "right": "rightElbowFlexionDegrees",
    }.get(elbow.get("arm"))
    agreement = (elbow.get("agreementDegrees") or {}).get("median")
    if named and agreement is not None:
        found.setdefault(named, {})["agreementDegrees"] = agreement
    for row in (evidence.get("alignment") or {}).get("alignments", []) or []:
        name = row.get("measure")
        phase = (row.get("agreementPhase") or {}).get("median")
        if not name or phase is None:
            continue
        entry = found.setdefault(name, {})
        entry["alignmentPhase"] = max(entry.get("alignmentPhase", phase), phase)
    return found


def judge_measure(evidence: dict, movement: str, name: str) -> list[dict]:
    """The conditions that belong to ONE graded measure.

    A CONDITION THAT IS MEANINGLESS FOR A MEASURE IS NOT SILENTLY PASSED. It
    is marked unmeasured and its `instrument` names what does not exist, so a
    reader can tell "this measure was checked and is fine" from "nothing has
    ever read this measure".
    """
    entry = video_measure(name)
    found = []

    found.append(condition(
        "the modality carries it",
        "Is this quantity in video at all, whatever the cameras did?",
        entry.carriable, "", True, "measured",
        "read from the video measure registry, which records for each measure "
        "whether a reader exists at all",
        entry.carriable,
        entry.unreadable_because or
        "The quantity is joint geometry, which two views of the athlete "
        "contain.",
        "video_measures.MEASURES",
    ))

    lift = evidence.get("lift") or {}
    counts: dict[str, int] = {}
    for row in lift.get("rows", []):
        counts[row["name"]] = counts.get(row["name"], 0) + 1
    pairs = (lift.get("residualMetres") or {}).get("framePairs")
    joint, seen = scarcest_landmark(entry, counts) if entry.carriable else ("", 0)
    found.append(condition(
        "the graded joint was seen",
        "Did both cameras see the landmarks this measure needs?",
        seen if entry.carriable else None,
        f"readings of {joint}" if joint else "readings",
        100, "chosen",
        "a hundred readings, because the findings report's own rule is that a "
        "curve drawn on 28 would be a drawing rather than a measurement, and a "
        "round number well above it is the honest place to put the bar",
        None if not (entry.carriable and counts) else seen >= 100,
        f"The scarcest landmark this measure needs is {joint or 'none'}, seen "
        f"{seen} times in {pairs} frame pairs. A measure is only as available "
        "as its rarest joint: averaging would call a measure well seen on the "
        "strength of a shoulder while the elbow it needs appears zero times."
        if entry.carriable else
        "Not asked. The modality does not carry this measure, so no landmark "
        "count would make it readable.",
        "counted per landmark from lift-3d-<set>.json's own rows",
    ))

    curve, declared_unit = reference_curve(evidence, movement, name)
    found.append(condition(
        "the engine half exists",
        "Is there an engine reference curve for this measure?",
        curve is not None, "", True, "measured",
        "the measure is either a key in reference-curves.json or it is not",
        curve is not None,
        "The engine curve is the thing a video reading is compared against. "
        "Without it there is nothing to compare to, and the comparison is not "
        "wrong — it does not exist. `export_reference_curves` writes five "
        "measures chosen for what a lift can recover; the library grades nine.",
        "reference-curves.json, per docs/REFERENCE_CURVE_WIDENING.md",
    ))

    found.append(condition(
        "the units agree",
        "Does the engine curve declare the same unit this measure is in?",
        declared_unit, "", entry.unit,
        "measured" if declared_unit else "unavailable",
        f"the registry holds this measure as {entry.unit}; the reference curve "
        + (f"declares {declared_unit}" if declared_unit else
           "declares no unit at all, which is what the widening exists to fix"),
        None if declared_unit is None else declared_unit == entry.unit,
        "One graded measure is CENTIMETRES and every threshold here is degrees. "
        "Two lanes spelling a unit independently is where this fault class "
        "lives, so the two spellings are compared rather than assumed equal.",
        "video_measures.MEASURES against reference-curves.json"
        if declared_unit else
        "video_measures.MEASURES against THE INSTRUMENT THAT DOES NOT EXIST: a "
        "unit declaration in reference-curves.json, which today declares none "
        "for any curve. The registry's own unit is known and is not the "
        "question — the question is whether the two agree, and one side is "
        "silent.",
    ))

    readings = instrument_readings(evidence).get(name, {})
    disagreement = readings.get("agreementDegrees")
    found.append(condition(
        "two instruments agree",
        "Do two independent readings of this measure agree?",
        disagreement, entry.unit, MEANINGFUL_DEGREES, "measured",
        "the clinical threshold the product already uses for a difference "
        "worth showing a coach",
        None if disagreement is None else disagreement <= MEANINGFUL_DEGREES,
        "Two independent readings that differ by more than the threshold mean "
        "neither is a measurement of that quantity."
        if disagreement is not None else
        "NO SECOND INSTRUMENT EXISTS FOR THIS MEASURE. video_elbow_curve.py "
        "reads one joint on one arm and produces the only paired reading in "
        "the pipeline. Until a second reader exists for this measure, nothing "
        "can say whether one reading of it would be confirmed.",
        "elbow-curve-<set>.json, the lift against the side view"
        if disagreement is not None else
        "the instrument that does not exist: a second reader for this measure",
    ))

    worst_phase = readings.get("alignmentPhase")
    is_aligned = worst_phase is not None
    aligned_measure = ", ".join(sorted(instrument_readings(evidence))) or "nothing"
    bound, slope = (None, None)
    if curve and entry.unit == DEGREES:
        bound, slope = phase_bound_degrees(curve)
    found.append(condition(
        "alignment agrees",
        "Do the two alignments place this measure's repetition alike?",
        worst_phase, "phase", None if bound is None else round(bound, 4),
        "derived" if slope else "unavailable",
        (f"the clinical threshold divided by the 90th percentile slope of the "
         f"reference's informative part, {slope:.1f} degrees per unit phase. "
         "Nothing is chosen here but the clinical threshold."
         if slope else
         "no engine curve in degrees for this measure, so no bound can be "
         "derived from its steepness"),
        None if (worst_phase is None or bound is None) else worst_phase <= bound,
        "A phase error costs degrees at the rate the reference is climbing."
        if is_aligned else
        "NO ALIGNMENT HAS BEEN COMPUTED FOR THIS MEASURE. video_phase_align.py "
        "aligns one measure per run, and the runs on record read "
        f"{aligned_measure}.",
        "phase-alignment-<set>.json, anchored against warped"
        if is_aligned else
        "the instrument that does not exist: an alignment of this measure",
    ))
    return found
def tally(conditions: list[dict], state) -> list[str]:
    """The blocking condition names, each once, with how many measures it hit.

    DEDUPLICATED AND COUNTED, because the same condition is now asked of every
    graded measure. A first version listed each occurrence, so a four-measure
    drill produced "the units agree, the units agree, the units agree, the
    units agree" in the one sentence a reader is most likely to read. A list
    that repeats itself is harder to read than the table it summarises, which
    defeats the summary.
    """
    order: list[str] = []
    counts: dict[str, int] = {}
    for row in conditions:
        if row["passes"] is not state:
            continue
        if row["name"] not in counts:
            order.append(row["name"])
        counts[row["name"]] = counts.get(row["name"], 0) + 1
    return [name + (f" (x{counts[name]})" if counts[name] > 1 else "")
            for name in order]


def verdict(conditions: list[dict]) -> dict:
    blocked = [row for row in conditions if row["passes"] is not True]
    unmeasured = tally(conditions, None)
    failed = tally(conditions, False)
    return {
        "mayShowNumbers": not blocked,
        "blockedBy": tally(conditions, None) + tally(conditions, False),
        "unmeasured": unmeasured,
        "failed": failed,
        "reason": (
            "Every condition passes. Figures may be presented as measurements, "
            "each with its uncertainty."
            if not blocked else
            "Figures may NOT be presented as measurements. "
            + (f"Failed on a reading: {', '.join(failed)}. " if failed else "")
            + (f"UNMEASURED, which blocks just as hard: {', '.join(unmeasured)}. "
               if unmeasured else "")
            + "Show the shape and withhold the figures."
        ),
        "unmeasuredNote": (
            "An unmeasured condition is not a near-miss. Nothing read it, so "
            "nothing can say whether it would have passed, and a gate that let "
            "silence count as consent would be the politest way of putting a "
            "wrong number in front of a coach."
        ),
    }


ILLUSTRATIVE = (
    "ILLUSTRATIVE, NEVER A MEASUREMENT AT THIS CALIBRATION. The shape is right "
    "and the numbers are not."
)


def shape_section(evidence: dict, movement: str) -> dict | None:
    """The shape comparison, which is all this material can honestly carry."""
    alignment = evidence.get("alignment")
    if not alignment or not alignment.get("alignments"):
        return None
    rows = alignment["alignments"]
    levels = [row["medianLevelGapDegrees"] for row in rows]
    named = min(rows, key=lambda row: abs(row["window"]["catchSeconds"] - 9.13))
    hand = named["handColumns"]
    return {
        "status": ILLUSTRATIVE,
        "movement": movement,
        "repetitions": len(rows),
        "namedRepetition": {
            "why": "the one holding the 9.13 s catch the findings report read by hand",
            "startSeconds": named["window"]["startSeconds"],
            "catchSeconds": named["window"]["catchSeconds"],
            "endSeconds": named["window"]["endSeconds"],
        },
        "columns": {
            "note": (
                "Degrees in the engine's convention, a straight arm at zero. "
                "THE 'BEFORE' COLUMN IS THE WEAKEST OF THE THREE and it looks "
                "like the strongest, because it is the one where the two "
                "numbers are furthest apart. It is read a quarter of a phase "
                "before contact, which on this reference is inside the "
                "featureless lead, so the engine's value there is simply its "
                "rest pose and the video's is whatever the window's stretch "
                "put underneath it. Read 'at contact' and 'pulling in'."
            ),
            "before": {
                "video": hand["videoBeforeDegrees"],
                "engine": hand["engineBeforeDegrees"]},
            "atContact": {
                "video": hand["videoAtContactDegrees"],
                "engine": hand["engineAtContactDegrees"]},
            "pullingIn": {
                "video": hand["videoPullInDegrees"],
                "engine": hand["enginePullInDegrees"]},
        },
        "levelGapDegrees": reading(
            round(float(np.median(levels)), 1),
            round(float((max(levels) - min(levels)) / 2.0), 1),
            "degrees",
            "the spread across all twelve repetitions of this one clip, "
            "half the full range",
            "Video minus engine. It swings from "
            f"{min(levels):+.1f} to {max(levels):+.1f} across repetitions of "
            "the SAME clip, so one repetition's level is not the clip's level.",
        ),
        "featurelessSharePhase": reading(
            rows[0]["featurelessSharePhase"], None, "phase",
            "no second instrument: this is a property of the engine curve and "
            "there is only one engine curve",
            "The share of the reference that has not left rest. Over it, no "
            "alignment is better than any other.",
        ),
    }


def render(document: dict) -> str:
    """The report a person reads. Markdown, and it leads with the verdict."""
    found = document["verdict"]
    lines = [
        f"# Dry run — session {document['set']}",
        "",
        f"Written by `video_dry_run.py` from build "
        f"`{(document['generatedFrom'].get('commit') or '?')[:8]}`, tree clean: "
        f"{document['generatedFrom'].get('treeWasClean')}.",
        "",
        "## The verdict",
        "",
        f"**{'NUMBERS MAY BE SHOWN' if found['mayShowNumbers'] else 'NO NUMBER MAY BE SHOWN'}**",
        "",
        found["reason"],
        "",
    ]
    if found["unmeasured"]:
        lines += [f"> {found['unmeasuredNote']}", ""]
    def table(rows: list[dict]) -> list[str]:
        out = ["| condition | reading | bar | source of the bar | verdict |",
               "|---|---|---|---|---|"]
        for row in rows:
            mark = {True: "pass", False: "FAIL", None: "UNMEASURED"}[row["passes"]]
            value = ("not read" if row["reading"] is None
                     else f"{row['reading']} {row['units']}".strip())
            bar = ("—" if row["threshold"] is None
                   else f"{row['threshold']} {row['units']}".strip())
            out.append(f"| {row['name']} | {value} | {bar} | "
                       f"{row['thresholdKind']} | **{mark}** |")
        return out

    lines += ["## The capture", "",
              "Asked once. A second camera and a clap are not properties of "
              "an elbow.", ""]
    lines += table(document["capture"]) + [""]

    opened = document.get("openQuestions")
    if opened:
        lines += ["## The open questions", "",
                  "**"
                  + ("This capture can answer the ones that can be asked."
                     if opened["canAnswer"]
                     else "This capture cannot answer them.")
                  + "**", ""]
        if opened.get("cannotBeAsked"):
            lines += [
                "And "
                + ", ".join(f"`{name}`" for name in opened["cannotBeAsked"])
                + " CANNOT BE ASKED AT ALL — the bar does not exist, so no "
                  "capture settles it and none is being blamed for failing to.",
                ""]
        lines += [opened["note"], ""]
        lines += table(opened["conditions"]) + [""]

    measures = document.get("measures") or {}
    lines += [f"## The {len(measures)} measures this drill grades", "",
              document.get("measuresNote", ""), "",
              "| measure | unit | verdict | blocked by |", "|---|---|---|---|"]
    for name, block in measures.items():
        blocked = [row["name"] for row in block["conditions"]
                   if row["passes"] is not True]
        state = "may be shown" if block["verdict"]["mayShowNumbers"] else "withheld"
        lines.append(f"| `{name}` | {block['unit']} | **{state}** | "
                     f"{', '.join(blocked) if blocked else 'nothing'} |")
    lines.append("")
    for name, block in measures.items():
        lines += [f"### {name}", ""] + table(block["conditions"]) + [""]

    lines += ["### Why each bar is where it is", ""]
    seen: set[str] = set()
    for row in document["capture"] + [
        row for block in measures.values() for row in block["conditions"]
    ]:
        if row["name"] in seen:
            continue
        seen.add(row["name"])
        lines += [f"**{row['name']}** — {row['question']}", "",
                  f"- Bar: {row['threshold']} {row['units']}".rstrip() + ", "
                  f"**{row['thresholdKind']}** — {row['thresholdWhy']}",
                  f"- Instrument: {row['instrument']}",
                  f"- {row['why']}", ""]

    shape = document.get("shape")
    if shape:
        lines += [
            "## The shape",
            "",
            f"**{shape['status']}**",
            "",
            f"{shape['repetitions']} repetitions found. The columns below are "
            f"for {shape['namedRepetition']['why']} — "
            f"{shape['namedRepetition']['startSeconds']} to "
            f"{shape['namedRepetition']['endSeconds']} s.",
            "",
            "| | before | at contact | pulling in |",
            "|---|---|---|---|",
            f"| from the video | {shape['columns']['before']['video']} | "
            f"{shape['columns']['atContact']['video']} | "
            f"{shape['columns']['pullingIn']['video']} |",
            f"| the engine | {shape['columns']['before']['engine']} | "
            f"{shape['columns']['atContact']['engine']} | "
            f"{shape['columns']['pullingIn']['engine']} |",
            "",
            shape["columns"]["note"],
            "",
            f"Level gap: **{shape['levelGapDegrees']['value']:+.1f} ± "
            f"{shape['levelGapDegrees']['uncertainty']:.1f} degrees**. "
            f"{shape['levelGapDegrees']['note']}",
            "",
            f"The engine curve is featureless for its first "
            f"{shape['featurelessSharePhase']['value'] * 100:.0f} percent. "
            f"{shape['featurelessSharePhase']['note']}",
            "",
        ]
    lines += [
        "## What was read, and which build made it",
        "",
        "| artefact | present | build |",
        "|---|---|---|",
    ]
    for name, stamp in document["provenance"].items():
        lines.append(
            f"| {name} | {'yes' if stamp else 'ABSENT'} | "
            f"{stamp if stamp else '—'} |")
    lines += ["", document["provenanceNote"], ""]
    return "\n".join(lines)


def provenance(evidence: dict) -> dict:
    found = {}
    for name, document in evidence.items():
        if document is None:
            found[name] = None
            continue
        stamp = document.get("generatedFrom") if isinstance(document, dict) else None
        if isinstance(stamp, dict):
            found[name] = (
                f"{str(stamp.get('commit'))[:8]}, clean="
                f"{stamp.get('treeWasClean')}, {stamp.get('utcTimestamp')}")
        else:
            found[name] = "no stamp; its provenance is the file it came from"
    return found


def assemble(evidence: dict, set_id: str, movement: str) -> dict:
    """The whole document, as a function of the evidence.

    SEPARATED FROM main() SO THE SEPARATION CAN BE TESTED. The grading verdict
    is built from the capture conditions and the measure conditions and from
    NOTHING ELSE; the open questions travel in their own block with their own
    answer. That is an invariant rather than a habit, and while this assembly
    lived inside main() no test could reach it to say so.
    """
    capture = judge_capture(evidence, movement)
    open_questions = judge_open_questions(evidence, movement)
    measures = {
        name: judge_measure(evidence, movement, name)
        for name in graded_measures(movement)
    }
    # THE MOVEMENT'S VERDICT IS EVERY CONDITION AT ONCE, capture-wide and
    # per-measure together, because a coach grading a drill needs all of its
    # checkpoints and a drill is not gradeable on three of four. A per-measure
    # verdict travels beside it so a reader can see WHICH measure blocks rather
    # than only that something did. THE OPEN QUESTIONS ARE NOT IN IT.
    everything = capture + [row for rows in measures.values() for row in rows]
    askable = [row for row in open_questions
               if row["thresholdKind"] != "unavailable"]
    document = {
        "schemaVersion": SCHEMA_VERSION,
        "set": set_id,
        "movement": movement,
        "verdict": verdict(everything),
        "capture": capture,
        "measures": {
            name: {
                "unit": video_measure(name).unit,
                "carriable": video_measure(name).carriable,
                "verdict": verdict(capture + rows),
                "conditions": rows,
            }
            for name, rows in measures.items()
        },
        "measuresNote": (
            "The measures this movement's checkpoints read, taken from "
            "MovementDefinition.graded_measures() rather than from a list "
            "written here. A measure's own verdict includes the capture-wide "
            "conditions, because no measure can be shown on a capture that "
            "cannot carry a number at all."
        ),
        "openQuestions": {
            # A row whose threshold kind is `unavailable` HAS NO BAR and can
            # never pass, so counting it made canAnswer a constant False and
            # the report told a perfect 240 fps capture that it could answer
            # nothing. The two are different states and the field says which:
            # `canAnswer` is about the questions a capture CAN be asked, and
            # `cannotBeAsked` names the ones no capture can settle while the
            # engine lacks the thing they are about.
            # `askable` cannot be empty while this group holds a derived and a
            # chosen condition, so the emptiness guard never fires TODAY. It
            # stays because without it an all-unavailable group would report
            # canAnswer TRUE — `all()` of nothing is true — which is the one
            # wrong answer this field must never give.
            "canAnswer": bool(askable) and all(
                row["passes"] is True for row in askable),
            "cannotBeAsked": [row["name"] for row in open_questions
                              if row["thresholdKind"] == "unavailable"],
            "conditions": open_questions,
            "note": (
                "THESE DO NOT GATE GRADING and they are not part of the "
                "verdict above. They ask a different question: can this "
                "footage settle something the ENGINE has not settled? A "
                "capture can grade every checkpoint cleanly and answer none "
                "of these. They are here because a shoot is the only chance "
                "to record them, and a question that is only written in a "
                "document is a question nobody measures."
            ),
        },
        "shape": shape_section(evidence, movement),
        "provenance": provenance(evidence),
        "provenanceNote": (
            "MORE THAN ONE BUILD MEETS HERE, and that is a property of the "
            "answer rather than a footnote. The video half comes from the "
            "keypoint files; the engine half from whichever build wrote the "
            "reference curves. A comparison across two builds is only as good "
            "as its older half."
        ),
        "generatedFrom": generated_from(),
    }
    return document


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--set", dest="set_id", default="0.1")
    parser.add_argument("--movement", default="netball_two_hand_snatch_pull_in")
    parser.add_argument("--out", default=None)
    arguments = parser.parse_args(argv[1:])

    evidence = gather(arguments.set_id)
    missing = missing_artefacts(evidence)
    if missing:
        raise SystemExit(
            f"these artefacts are missing for set {arguments.set_id}: "
            f"{', '.join(missing)}. Run video_keypoints.py, video_lift_3d.py, "
            "video_elbow_curve.py and video_phase_align.py first.")

    document = assemble(evidence, arguments.set_id, arguments.movement)
    capture = document["capture"]
    open_questions = document["openQuestions"]["conditions"]
    measures = document["measures"]

    where = Path(arguments.out) if arguments.out else (
        OUTPUT / f"dry-run-{arguments.set_id}.json")
    where.write_text(json.dumps(document, indent=1) + "\n", encoding="utf-8")
    report = where.with_suffix(".md")
    report.write_text(render(document) + "\n", encoding="utf-8")

    found = document["verdict"]
    print(f"session {arguments.set_id}, {arguments.movement[8:]}\n")
    print("  " + ("NUMBERS MAY BE SHOWN" if found["mayShowNumbers"]
                  else "NO NUMBER MAY BE SHOWN"))
    print("\n  THE CAPTURE")
    for row in capture:
        mark = {True: "pass      ", False: "FAIL      ", None: "UNMEASURED"}[row["passes"]]
        value = "not read" if row["reading"] is None else f"{row['reading']}"
        print(f"    {mark}  {row['name']:28s} {value}")
    print("\n  THE OPEN QUESTIONS (these do not gate grading)")
    for row in open_questions:
        mark = {True: "pass      ", False: "FAIL      ", None: "UNMEASURED"}[row["passes"]]
        value = "not read" if row["reading"] is None else f"{row['reading']}"
        print(f"    {mark}  {row['name']:28s} {value}")
    print(f"\n  THE {len(measures)} MEASURES THIS DRILL GRADES")
    for name, block in measures.items():
        blocked = [row["name"] for row in block["conditions"]
                   if row["passes"] is not True]
        print(f"    {name:32s} {video_measure(name).unit:12s} "
              f"{'clear' if not blocked else ', '.join(blocked)}")
    print(f"\n  {found['reason']}")
    print(f"\nwritten -> {where}\nwritten -> {report}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
