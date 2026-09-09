"""The inclusion test for population A2: numbers inside structures.

    python scripts/register_inclusion_structures.py
    python scripts/register_inclusion_structures.py --show INCLUDE

THE TEST IS THE SAME AS A1'S. A number belongs in the register if changing it
changes what the engine CLAIMS A HUMAN BODY DID, or SHOULD DO.

**THE UNIT OF DECISION IS THE SITE, NOT THE LITERAL.** A correspondence table
of sixteen numbers is one decision, not sixteen. Classifying each literal would
report 702 judgments where 78 were made, and a count of judgments nobody made
is the fault this register exists to catch.

**A SITE THIS LANE HAS NOT READ IS FILED AS `not-yet-read`, NOT GUESSED.** The
name of a structure is not enough to classify it. `ENGINE` sounds like
configuration and holds 144 measured body positions. `CARRY` sounds like
authored technique and is a test default. Every site in `not-yet-read` is
listed by name, so the register can never report it as decided.

Every site lands in EXACTLY ONE rule and the run fails otherwise, as in A1. A
new structure is therefore a failure until somebody files it, including into
`not-yet-read`, which is a deliberate act rather than an omission.

    exit 0  every site matched exactly one rule
    exit 2  at least one matched none, or more than one
"""

from __future__ import annotations

import argparse
import ast
import platform
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from register_survey_constants import literal, tip  # noqa: E402
from register_survey_structures import numbers_in  # noqa: E402

INCLUDE = "INCLUDE"
EXCLUDE = "EXCLUDE"
CONTESTED = "CONTESTED"

RULES: list[tuple[str, str, str, set[tuple[str, str]]]] = [
    (
        "anthropometry", INCLUDE,
        "A measured length, proportion or shape of a human body. "
        "`landmark_comparison.MINE` and `THEIRS` are rest-pose landmarks in "
        "torso lengths, measured by scripts/rest_landmarks.py and saying so. "
        "`ATHLETIC_FEMALE` is a body in SMPL-X shape coefficients, and its own "
        "comment states the measured range each coefficient spans.",
        {
            ("scripts/landmark_comparison.py", "MINE"),
            ("scripts/landmark_comparison.py", "THEIRS"),
            ("spikes/smplx_retarget.py", "ATHLETIC_FEMALE"),
            ("spikes/video_lift_3d.py", "SHOULDER_WIDTH_METRES"),
        },
    ),
    (
        "range-of-motion", INCLUDE,
        "A limit on how far a joint may go. A coach or a clinical source can "
        "rule on it. AAOS_LIMITS is the highest-leverage row in the register: "
        "eight joints, sixteen numbers, and build_library.py checks every "
        "drill in the library against all of them.",
        {
            ("spikes/isb_angles.py", "AAOS_LIMITS"),
            ("spikes/export_blender_job.py", "ANATOMY_LIMITS"),
        },
    ),
    (
        "anatomical-axis", INCLUDE,
        "A direction defined on a body part: which way a joint bends, or where "
        "a pole puts a limb. It is a claim about anatomy and a wrong one bends "
        "a joint in a direction a person does not.",
        {
            ("spikes/contact_solve.py", "UPPER_ARM_LOCAL_AXIS"),
            ("blender_mpfb_reference_catch.py", "FLEXION_AXIS"),
            ("blender_movement_render.py", "KNEE_POLE"),
        },
    ),
    (
        "correspondence", INCLUDE,
        "A table pairing one body model's landmarks with another's joints. IT "
        "IS A CLAIM, and the strongest argument for A2 existing: a wrong "
        "pairing moves every measurement taken through it, and both tables "
        "hold their numbers on the KEY side where the A1 extractor could not "
        "see them at all.",
        {
            ("spikes/smplx_retarget.py", "CORRESPONDENCE"),
            ("spikes/fit_from_photo.py", "LANDMARK_TO_JOINT"),
            # READ 2026-09-09 out of not-yet-read. `CHANNEL` maps a joint name
            # to its POSITION in a clip frame and its own comment says "the
            # order is positional and must not be rearranged". That is the
            # correspondence hazard stated by the author: a wrong pairing
            # reads one joint's angle as another's, in the artefact the
            # consumer repository grades.
            ("spikes/verify_tactics_clip.py", "CHANNEL"),
            ("spikes/verify_tactics_clip.py", "REPORTED_ONLY"),
        },
    ),
    (
        "authored-technique", INCLUDE,
        "A number deciding how a body part is placed during a drill. "
        "`finger_wrap.SPREAD` is how far each digit fans, in radians, and its "
        "comment traces the thumb's value to the manual's photographs.",
        {
            ("spikes/finger_wrap.py", "SPREAD"),
            ("spikes/video_measures.py", "LIFT_UP"),
        },
    ),
    (
        "measured-snapshot", INCLUDE,
        "ANOTHER LANE'S MEASUREMENTS, TRANSCRIBED INTO THIS TREE. "
        "`ball_anchor_verdict.ENGINE` and `BALL_TO_HEAD` hold 187 solved body "
        "positions in centimetres, and the file says plainly that they are the "
        "movement lane's values reported on a date. They are claims about a "
        "body, so they are in. They are also the register's own hazard in "
        "miniature: a snapshot carries a DATE and no build hash, so nothing "
        "says whether the engine has moved under them.",
        {
            ("scripts/ball_anchor_verdict.py", "ENGINE"),
            ("scripts/ball_anchor_verdict.py", "BALL_TO_HEAD"),
            # READ 2026-09-09 out of not-yet-read. Both are per-drill readings
            # from the solve, and BOTH ARE BETTER PROVENANCED THAN THE 187
            # ABOVE. STANCE_DEGREES names the build it came from and records
            # that the overhead pass read -0.0110 against the movement lane's
            # independently measured -0.011. KNEE_GAP_CEILING_DEGREES records
            # that three runs agree to 0.0000 cm, so nothing in it is a
            # sampled average, and states that the number must not be
            # re-fitted to whatever new keys produce.
            ("spikes/test_waiting_hand.py", "STANCE_DEGREES"),
            ("spikes/test_waiting_hand.py", "KNEE_GAP_CEILING_DEGREES"),
        },
    ),
    (
        "footage-observation", INCLUDE,
        "An event this project says it saw in a recording, or a floor it says "
        "the footage can resolve. `RELEASES` names the frame of each release "
        "and grades the reading crisp or soft, which is a claim about the "
        "athlete and about what the camera could see.",
        {
            ("spikes/video_hand_speed.py", "RELEASES"),
            ("spikes/video_hand_speed.py", "HELD_REPETITION"),
            ("spikes/video_hand_speed.py", "NO_RELEASE"),
            ("spikes/video_flick_requirement.py", "MEASURED_FLOOR"),
            ("spikes/video_flick_requirement.py", "ASSUMED"),
        },
    ),
    (
        "solver-weight", CONTESTED,
        "A relative weight in the solver's objective, held out on the same "
        "ground as A1's sixteen: no coach can rule on one, and a register a "
        "coach cannot read is a different document. The ground is a judgment.",
        {
            ("spikes/contact_solve.py", "CONTACT_WEIGHT"),
        },
    ),
    (
        "solver-search", CONTESTED,
        "The starting twists the solver tries before keeping the best. Its own "
        "comment says why they exist: from rest the hand rolled the wrong way "
        "and jammed against the pronation limit, and several seeds remove that "
        "failure. IT IS NOT A CLAIM ABOUT A BODY. But a seed set decides which "
        "basin is found, and this repository has a recorded finding that joint "
        "continuity separates a basin from an edge, so changing it can change "
        "the pose reported. Held on the same ground as the solver weights, and "
        "the ground is a judgment.",
        {
            ("spikes/contact_solve.py", "TWIST_SEEDS"),
        },
    ),
    (
        "not-yet-read", CONTESTED,
        "THIS LANE HAS NOT OPENED THESE SITES. They are not classified and "
        "must never be counted as decided. A structure's NAME is not enough: "
        "ENGINE sounds like configuration and holds 144 measured body "
        "positions, and CARRY sounds like authored technique and is a test "
        "default. Filing them here is a deliberate act that keeps them "
        "visible, and it is the honest state until somebody reads each one.",
        # EMPTY, AND THE RULE STAYS. All nine were read on 2026-09-09 and
        # filed below. The rule remains so a future site can be filed here
        # deliberately rather than guessed, and so an empty bucket is visible
        # as a state rather than absent as an omission.
        set(),
    ),
    (
        "reporting-bucket", EXCLUDE,
        "A set of thresholds an instrument sorts its own output into, or a "
        "rounding derived from another number's precision. It changes how a "
        "result is PRESENTED or compared, never what the result says about a "
        "body. QUANTISATION_CM is half the 0.1 cm the export rounds to, along "
        "the worst diagonal, so it is the export's precision restated.",
        {
            ("spikes/measure_seed_variety.py", "THRESHOLDS"),
            ("spikes/hand_orientation_crosscheck.py", "QUANTISATION_CM"),
        },
    ),
    (
        "coordinate-convention", EXCLUDE,
        "A world axis or a unit direction vector. It says which way is up in a "
        "coordinate system, not anything about a person, and every one of "
        "these is a unit vector on an axis.",
        {
            ("spikes/movement_engine.py", "WORLD_UP"),
            ("spikes/multi_camera_fit.py", "WORLD_UP"),
            ("spikes/hand_orientation.py", "WORLD_UP"),
            ("spikes/poc_engine.py", "MHR_WORLD_UP"),
            ("spikes/hand_orientation_crosscheck.py", "UP"),
            ("spikes/spike_i_camera_placement.py", "UP"),
            ("spikes/test_export_tactics_clip.py", "UP"),
            ("spikes/test_export_tactics_clip.py", "FORWARD"),
        },
    ),
    (
        "unit-conversion", EXCLUDE,
        "Degrees per radian. Sourced outside this project and identical for "
        "every body.",
        {
            ("spikes/opensim_crosscheck.py", "DEGREES_PER_RADIAN"),
            ("spikes/video_flick_requirement.py", "DEGREES_PER_RADIAN"),
        },
    ),
    (
        "presentation", EXCLUDE,
        "A pixel size, a camera placement for a render, a light, or a panel "
        "layout. It changes the picture and not the claim.",
        {
            ("blender_glb_render.py", "RESOLUTION"),
            ("spikes/export_blender_job.py", "VIEWS"),
            ("spikes/export_blender_job.py", "VIEW_RESOLUTION"),
            ("spikes/export_blender_job.py", "VIEW_TARGET"),
            ("spikes/render_figure.py", "BALL"),
            ("spikes/render_figure.py", "FIGURE"),
            ("spikes/render_figure.py", "LIGHT"),
            ("spikes/render_figure.py", "SHEET"),
            ("scripts/compare_lift_against_view.py", "size"),
        },
    ),
    (
        "video-pipeline", EXCLUDE,
        "A file pairing, a search window, a board size or a section boundary "
        "inside the footage pipeline. It changes how a recording is READ, "
        "never what the engine claims a body did.",
        {
            ("spikes/video_keypoints.py", "PAIRS"),
            ("spikes/video_keypoints.py", "ATHLETE"),
            ("spikes/video_keypoints.py", "USABLE_TO"),
            ("spikes/video_section_cuts.py", "PAIR1_SECTIONS"),
            ("spikes/video_calibration.py", "DEFAULT_BOARD"),
            ("spikes/video_event_ledger.py", "SEARCH_STEP_SECONDS"),
            ("spikes/video_event_ledger.py", "TOLERANCE_SECONDS"),
            ("spikes/video_flick_requirement.py", "SCATTER_WINDOWS"),
            ("spikes/spike_h_roundtrip.py", "NOISE_LEVELS_PX"),
        },
    ),
    (
        "test-fixture", EXCLUDE,
        "A structure built to make a test or a spike run: an input case, an "
        "identity matrix, a synthetic frame, a default argument. It decides "
        "how hard we look, never what we claim to have found.",
        {
            ("spikes/test_ball_track.py", "VALID"),
            ("spikes/test_technique.py", "VALID"),
            ("spikes/test_elbow_pole.py", "OBLIQUE_DIRECTIONS"),
            ("spikes/test_grip.py", "HAND"),
            ("spikes/test_isb_angles.py", "IDENTITY"),
            ("spikes/test_possession.py", "CARRY"),
            ("spikes/test_reference_curves.py", "DRILL"),
            ("spikes/test_video_measures.py", "POSE"),
            ("spikes/test_video_ball_in_frame.py", "WINDOWS"),
            ("spikes/test_video_calibration.py", "SIZE"),
            ("spikes/test_video_calibration.py", "TRUE_DISTORTION"),
            ("spikes/test_video_calibration.py", "TRUE_FOCAL"),
            ("spikes/test_video_calibration.py", "TRUE_PRINCIPAL"),
            ("spikes/test_video_ledger_reading_step.py", "PERIOD"),
            ("spikes/test_archive_receipts.py", "STAMP"),
            ("spikes/test_archive_receipts.py", "OTHER"),
            ("spikes/spike_h_roundtrip.py", "FRAME"),
            ("spikes/spike_i_camera_placement.py", "FRAME"),
            ("spikes/verify_capture_pipeline.py", "FRAME"),
            # READ 2026-09-09 out of not-yet-read. THUMB is a captured report
            # handed to the reader under test. REST is a constructed point:
            # 1.427681 sits one metre above a number close to, and NOT equal
            # to, girdle_agreement.REST_TORSO_M = 0.427689. A synthetic value
            # that resembles a measured one is still synthetic.
            ("tests/test_report_axis_calibration.py", "THUMB"),
            ("tests/test_girdle_agreement.py", "REST"),
        },
    ),
]


def sites() -> tuple[list[tuple[str, int, str, int]], list[str]]:
    """Every module-level structure holding numbers, and the files not read."""
    found: list[tuple[str, int, str, int]] = []
    unread: list[str] = []
    for path in sorted(ROOT.rglob("*.py")):
        if any(part in {".git", ".pixi", "__pycache__"} for part in path.parts):
            continue
        relative = path.relative_to(ROOT).as_posix()
        try:
            tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        except (SyntaxError, UnicodeDecodeError):
            unread.append(relative)
            continue
        for node in tree.body:
            if isinstance(node, ast.Assign):
                names = [t.id for t in node.targets if isinstance(t, ast.Name)]
                value = node.value
            elif isinstance(node, ast.AnnAssign) and isinstance(node.target, ast.Name):
                names = [node.target.id]
                value = node.value
            else:
                continue
            if value is None or not names or literal(value) is not None:
                continue
            numbers = numbers_in(value, names[0])
            if numbers:
                found.append((relative, node.lineno, names[0], len(numbers)))
    return found, unread


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--show", choices=[INCLUDE, EXCLUDE, CONTESTED])
    args = parser.parse_args()

    found, unread = sites()
    print(f"tip:         {tip()}")
    print(f"interpreter: python {platform.python_version()}")
    print()

    verdicts = []
    unmatched = []
    multiple = []
    for relative, line, name, count in found:
        key = (relative, name)
        hit = [rule for rule in RULES if key in rule[3]]
        if not hit:
            unmatched.append((relative, line, name, count))
        elif len(hit) > 1:
            multiple.append(((relative, line, name), [r[0] for r in hit]))
        else:
            verdicts.append((relative, line, name, count, hit[0][0], hit[0][1]))

    literals = {INCLUDE: 0, EXCLUDE: 0, CONTESTED: 0}
    site_counts = {INCLUDE: 0, EXCLUDE: 0, CONTESTED: 0}
    for _, _, _, count, _, decision in verdicts:
        literals[decision] += count
        site_counts[decision] += 1

    print(f"assignment sites: {len(found)}   distinct names: "
          f"{len({(f, n) for f, _, n, _ in found})}   literals: "
          f"{sum(c for _, _, _, c in found)}")
    print("(compare_lift_against_view.py assigns `size` twice at module level, "
          "so the two differ by one.)")
    print()
    for rule_id, decision, _reason, members in RULES:
        got = sum(1 for v in verdicts if v[4] == rule_id)
        held = sum(v[3] for v in verdicts if v[4] == rule_id)
        print(f"  {decision:9s}  {got:3d} sites {held:5d} numbers  {rule_id}")
    print()
    for decision in (INCLUDE, CONTESTED, EXCLUDE):
        print(f"  {decision:9s}  {site_counts[decision]:3d} sites "
              f"{literals[decision]:5d} numbers")

    if args.show:
        print()
        for relative, line, name, count, rule_id, decision in sorted(verdicts):
            if decision == args.show:
                print(f"  {rule_id:20s} {relative}:{line}  {name}  ({count})")

    failed = False
    if unmatched:
        print()
        print(f"{len(unmatched)} SITE(S) MATCH NO RULE. A2 cannot account for them")
        print("and no reason has been written for leaving them out. File each one,")
        print("including into not-yet-read, which is a decision and not an omission:")
        for relative, line, name, count in unmatched:
            print(f"    {relative}:{line}  {name}  ({count} numbers)")
        failed = True
    if multiple:
        print()
        print(f"{len(multiple)} SITE(S) MATCH MORE THAN ONE RULE:")
        for (relative, line, name), names in multiple:
            print(f"    {relative}:{line}  {name}  ->  {', '.join(names)}")
        failed = True
    if unread:
        print()
        print(f"THE COUNTS ARE A LOWER BOUND. Files not read: {', '.join(unread)}")
        failed = True
    return 2 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
