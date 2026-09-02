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

    Five of them. They are asked once, because a second camera and a clap are
    not properties of an elbow.
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
        "informative scoring placed it fourth, which is luck rather than "
        "detection. " + ball["detail"],
        f"ball-in-frame-<set>.json, a human reading frame strips per repetition"
        if ball["passes"] is not None or stale else
        "THE INSTRUMENT THAT DOES NOT EXIST: no ball detector is built, and "
        "the only instrument that has ever answered this is a person reading "
        "frame strips. Write ball-in-frame-<set>.json and it is read.",
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


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--set", dest="set_id", default="0.1")
    parser.add_argument("--movement", default="netball_two_hand_snatch_pull_in")
    parser.add_argument("--out", default=None)
    arguments = parser.parse_args(argv[1:])

    evidence = gather(arguments.set_id)
    # AN ALLOWLIST OF WHAT IS REQUIRED, not a denylist of what is optional. The
    # check used to be "everything that is not the calibration", so the first
    # optional key added after it — a ball annotation, whose absence is the
    # normal case — made the run refuse to start at all. A rule written as
    # "everything except the exceptions I know about" breaks on the next one.
    REQUIRED = ("front", "side", "lift", "elbow", "alignment", "reference")
    missing = [name for name in REQUIRED if evidence.get(name) is None]
    if missing:
        raise SystemExit(
            f"these artefacts are missing for set {arguments.set_id}: "
            f"{', '.join(missing)}. Run video_keypoints.py, video_lift_3d.py, "
            "video_elbow_curve.py and video_phase_align.py first.")

    capture = judge_capture(evidence, arguments.movement)
    measures = {
        name: judge_measure(evidence, arguments.movement, name)
        for name in graded_measures(arguments.movement)
    }
    # THE MOVEMENT'S VERDICT IS EVERY CONDITION AT ONCE, capture-wide and
    # per-measure together, because a coach grading a drill needs all of its
    # checkpoints and a drill is not gradeable on three of four. A per-measure
    # verdict travels beside it so a reader can see WHICH measure blocks rather
    # than only that something did.
    everything = capture + [row for rows in measures.values() for row in rows]
    document = {
        "schemaVersion": SCHEMA_VERSION,
        "set": arguments.set_id,
        "movement": arguments.movement,
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
        "shape": shape_section(evidence, arguments.movement),
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
    print(f"\n  THE {len(measures)} MEASURES THIS DRILL GRADES")
    for name, rows in measures.items():
        blocked = [row["name"] for row in rows if row["passes"] is not True]
        print(f"    {name:32s} {video_measure(name).unit:12s} "
              f"{'clear' if not blocked else ', '.join(blocked)}")
    print(f"\n  {found['reason']}")
    print(f"\nwritten -> {where}\nwritten -> {report}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
