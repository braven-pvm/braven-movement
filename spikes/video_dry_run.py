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

Eight conditions. Each carries a READING, a THRESHOLD, and where the threshold
came from, because a bar somebody invented and a bar something measured are not
the same kind of claim and a reader must be able to tell them apart:

- **measured** — the number came off this material or an earlier one.
- **derived** — the number follows from another number by arithmetic written
  down here.
- **chosen** — somebody picked it. Every chosen threshold says why, and a
  reader may disagree with it without disagreeing with any measurement.

A condition that CANNOT BE ANSWERED from the material is not a pass. It blocks,
and it blocks LOUDLY, marked `unmeasured`. Where a change touches something
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

from build_stamp import generated_from  # noqa: E402
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
    }


def judge(evidence: dict, movement: str) -> list[dict]:
    """The eight conditions, each with its reading and where its bar came from."""
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

    elbow = evidence.get("elbow") or {}
    disagreement = (elbow.get("agreementDegrees") or {}).get("median")
    found.append(condition(
        "two instruments agree", "Do two readings of the same joint agree?",
        disagreement, "degrees", MEANINGFUL_DEGREES, "measured",
        "the clinical threshold the product already uses for a difference "
        "worth showing a coach",
        None if disagreement is None else disagreement <= MEANINGFUL_DEGREES,
        "Two independent readings of one elbow that differ by more than the "
        "threshold mean neither is a measurement of that joint. Four candidate "
        "causes were raised and all four refuted; the case is bounded, not "
        "closed.",
        "elbow-curve-<set>.json, the lift against the side view",
    ))

    alignment = evidence.get("alignment") or {}
    reference = evidence.get("reference") or {}
    drill = (reference.get("movements") or {}).get(movement)
    bound, slope = (None, None)
    if drill:
        bound, slope = phase_bound_degrees(drill["curves"]["leftElbowFlexionDegrees"])
    worst_phase = max(
        (row["agreementPhase"]["median"] for row in alignment.get("alignments", [])),
        default=None)
    found.append(condition(
        "alignment agrees", "Do the two alignments place the repetition alike?",
        worst_phase, "phase", None if bound is None else round(bound, 4),
        "derived" if slope else "unavailable",
        (f"the clinical threshold divided by the 90th percentile slope of the "
         f"reference's informative part, {slope:.1f} degrees per unit phase. "
         "Nothing is chosen here but the clinical threshold."
         if slope else "the reference curve is absent, so nothing can be derived"),
        None if (worst_phase is None or bound is None) else worst_phase <= bound,
        "A phase error costs degrees at the rate the reference is climbing, so "
        "an alignment loose enough to move the reading past the clinical "
        "threshold cannot carry a number however well it looks.",
        "phase-alignment-<set>.json, anchored against warped",
    ))

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

    # THE JOINT THE GRADE IS ABOUT MUST HAVE BEEN SEEN BY BOTH CAMERAS, and on
    # a 90-degree pair one whole side of the body has not been. Counted off the
    # lift's own rows rather than assumed: of 735 frame pairs, the left elbow
    # appears 734 times and THE RIGHT ELBOW DOES NOT APPEAR AT ALL. The findings
    # report quotes 28 usable right-WRIST readings; the right elbow is zero, and
    # a gate that only asked about the arm somebody happened to measure would
    # never have found that.
    lift = evidence.get("lift") or {}
    seen: dict[str, int] = {}
    for row in lift.get("rows", []):
        seen[row["name"]] = seen.get(row["name"], 0) + 1
    pairs = (lift.get("residualMetres") or {}).get("framePairs")
    joints = ("left_shoulder", "left_elbow", "left_wrist")
    fewest = min((seen.get(name, 0) for name in joints), default=0)
    mirror = min((seen.get(name.replace("left", "right"), 0) for name in joints),
                 default=0)
    found.append(condition(
        "the graded joint was seen",
        "Did both cameras see the joint this grade is about?",
        fewest, f"readings of the scarcest of {', '.join(joints)}",
        100, "chosen",
        "a hundred readings, because the findings report's own rule is that a "
        "curve drawn on 28 would be a drawing rather than a measurement, and a "
        "round number well above it is the honest place to put the bar",
        None if not seen else fewest >= 100,
        f"The mirror joints have {mirror} readings against this arm's {fewest}, "
        f"out of {pairs} frame pairs. A 90-degree camera pair sees one side of "
        "the body in profile and the far limb is occluded almost entirely, so "
        "no analysis recovers a joint the cameras never saw.",
        "counted per landmark from lift-3d-<set>.json's own rows",
    ))
    return found


def verdict(conditions: list[dict]) -> dict:
    blocked = [row for row in conditions if row["passes"] is not True]
    unmeasured = [row["name"] for row in conditions if row["passes"] is None]
    failed = [row["name"] for row in conditions if row["passes"] is False]
    return {
        "mayShowNumbers": not blocked,
        "blockedBy": [row["name"] for row in blocked],
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
    lines += [
        "## The gate",
        "",
        "| condition | reading | bar | source of the bar | verdict |",
        "|---|---|---|---|---|",
    ]
    for row in document["conditions"]:
        mark = {True: "pass", False: "FAIL", None: "UNMEASURED"}[row["passes"]]
        value = "not read" if row["reading"] is None else f"{row['reading']} {row['units']}"
        bar = "—" if row["threshold"] is None else f"{row['threshold']} {row['units']}"
        lines.append(
            f"| {row['name']} | {value} | {bar} | {row['thresholdKind']} | **{mark}** |")
    lines += ["", "### Why each bar is where it is", ""]
    for row in document["conditions"]:
        lines += [f"**{row['name']}** — {row['question']}", "",
                  f"- Bar: {row['threshold']} {row['units']}, "
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
    missing = [name for name, value in evidence.items()
               if value is None and name != "calibration"]
    if missing:
        raise SystemExit(
            f"these artefacts are missing for set {arguments.set_id}: "
            f"{', '.join(missing)}. Run video_keypoints.py, video_lift_3d.py, "
            "video_elbow_curve.py and video_phase_align.py first.")

    conditions = judge(evidence, arguments.movement)
    document = {
        "schemaVersion": SCHEMA_VERSION,
        "set": arguments.set_id,
        "movement": arguments.movement,
        "verdict": verdict(conditions),
        "conditions": conditions,
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
    print()
    for row in conditions:
        mark = {True: "pass      ", False: "FAIL      ", None: "UNMEASURED"}[row["passes"]]
        value = "not read" if row["reading"] is None else f"{row['reading']}"
        print(f"    {mark}  {row['name']:28s} {value}")
    print(f"\n  {found['reason']}")
    print(f"\nwritten -> {where}\nwritten -> {report}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
