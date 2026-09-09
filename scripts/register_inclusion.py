"""The inclusion test for the movement-parameter register, applied to every
module-level numeric constant in the tree.

    python scripts/register_inclusion.py
    python scripts/register_inclusion.py --show INCLUDE
    python scripts/register_inclusion.py --json verdicts.json

THE TEST, IN ONE SENTENCE. A number belongs in the register if changing it
changes what the engine CLAIMS A HUMAN BODY DID, or SHOULD DO.

WHY THE EXCLUSIONS ARE THE PART THAT MATTERS. A register that quietly drops a
number is worse than one that never had it, because a reader takes the absence
for a decision that was made. So every constant lands in EXACTLY ONE rule, each
rule carries a reason written for somebody who disagrees with it, and the run
FAILS if any constant matches no rule or more than one.

    exit 0  every constant matched exactly one rule
    exit 2  at least one constant matched none, or more than one

THE RULES ARE ORDERED FOR READING, NOT FOR PRECEDENCE. First-match-wins would
hide an overlap between two rules, and an overlap is a disagreement between two
reasons that a reader should be shown rather than spared. So a constant
matching two rules is a failure of this file, not a resolved case.

WHAT THIS FILE IS NOT. It is not the register and it holds no sources. It says
only which numbers the register must account for. A constant marked INCLUDE
here has not been examined; it has been admitted.

THE HARDEST CALL IN THIS FILE IS THE SOLVER WEIGHTS, and it is marked as
contested rather than settled. Refer to CONTESTED below.
"""

from __future__ import annotations

import argparse
import json
import platform
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from register_survey_constants import constants_in, tip  # noqa: E402

import ast  # noqa: E402

INCLUDE = "INCLUDE"
EXCLUDE = "EXCLUDE"
CONTESTED = "CONTESTED"

# A rule is (id, verdict, reason, {(file, name), ...}).
#
# THE MEMBERS ARE LISTED BY NAME AND NOT MATCHED BY PATTERN. A pattern is a
# claim about a list that nobody can check without re-running it, and this file
# exists to be argued with. Listing them costs lines and makes every call
# visible in a diff when a constant is added, moved or renamed.
RULES: list[tuple[str, str, str, set[tuple[str, str]]]] = [
    (
        "anthropometry", INCLUDE,
        "A length or proportion of a human body. Changing it changes the body "
        "the engine claims to be describing, and every angle measured on it.",
        {
            ("spikes/contact_solve.py", "REFERENCE_ARM_CM"),
            ("spikes/contact_solve.py", "UPPER_ARM_FRACTION"),
            ("spikes/opensim_crosscheck.py", "HUMERUS_LENGTH_M"),
            ("spikes/opensim_crosscheck.py", "FOREARM_LENGTH_M"),
            ("spikes/opensim_crosscheck.py", "EPICONDYLE_OFFSET_M"),
            ("spikes/opensim_crosscheck.py", "STYLOID_OFFSET_M"),
            ("spikes/video_hand_speed.py", "ATHLETE_HEIGHT_METRES"),
            ("spikes/video_hand_speed.py", "ATHLETE_ARM_METRES"),
            ("spikes/video_hand_speed.py", "NOSE_TO_HEEL_FRACTION"),
            ("spikes/test_ball_reach.py", "UPPER_CM"),
            ("spikes/test_ball_reach.py", "FORE_CM"),
            ("spikes/test_ball_reach.py", "PALM_CM"),
            ("spikes/test_elbow_pole.py", "REFERENCE_CM"),
            ("spikes/test_elbow_pole.py", "MEASURED_CM"),
            ("spikes/test_elbow_pole.py", "ONE_HANDED_GAP_CM"),
            ("spikes/test_authored_launch.py", "ARM_CM"),
            ("girdle_agreement.py", "REST_TORSO_M"),
            ("scripts/landmark_comparison.py", "MY_TORSO_CM"),
            ("scripts/clavicle_divisor_probe.py", "ENGINE_TORSO_CM"),
            ("scripts/clavicle_divisor_probe.py", "ENGINE_CLAVICLE_CM"),
            ("blender_glb_render.py", "TARGET_HEIGHT"),
            ("spikes/grip.py", "PALM_SKIN_CM"),
            ("spikes/finger_wrap.py", "FINGER_SKIN_CM"),
        },
    ),
    (
        "range-of-motion", INCLUDE,
        "A limit on how far a joint or a hand may go. It is a claim about what "
        "a human being can do, and a coach or a clinical source can rule on it. "
        "THE PAIR MOST LIKELY TO LOOK INCONSISTENT FROM OUTSIDE IS "
        "technique.MINIMUM_SPREAD_DEGREES here against "
        "contact_solve.SPREAD_TOLERANCE_DEGREES under numerical-tolerance. "
        "Both are about the hand spread. ONE BOUNDS WHAT A HAND CAN DO. THE "
        "OTHER BOUNDS AGREEMENT BETWEEN TWO COMPUTATIONS OF IT. That is the "
        "whole of the difference and it is the reason the split holds.",
        {
            ("spikes/ball_reach.py", "ELBOW_FLEXION_LIMIT_DEGREES"),
            ("spikes/technique.py", "MINIMUM_SPREAD_DEGREES"),
            ("spikes/technique.py", "MAXIMUM_SPREAD_DEGREES"),
            ("spikes/motion_track.py", "MAXIMUM_TURN_DEGREES"),
            ("blender_mpfb_reference_catch.py", "KNUCKLE_SEARCH_CEILING_DEGREES"),
        },
    ),
    (
        "authored-technique", INCLUDE,
        "A number that decides where a body part or the ball is placed during a "
        "drill. It is the engine's statement of how the movement is performed.",
        {
            ("spikes/contact_solve.py", "ELBOW_POLE_ANGLE_DEGREES"),
            ("spikes/contact_solve.py", "UPPER_ARM_AIM_OUT"),
            ("spikes/contact_solve.py", "UPPER_ARM_AIM_DOWN"),
            ("spikes/author_flight.py", "DEFAULT_SPEED_CM"),
            ("spikes/author_flight.py", "DEFAULT_PASSER_AHEAD"),
            ("spikes/author_flight.py", "DEFAULT_RELEASE_HEIGHT_CM"),
            ("spikes/author_flight.py", "DEFAULT_ARRIVAL_PHASE"),
            ("spikes/possession.py", "READY_FRACTION"),
            ("spikes/possession.py", "CONTACT_FRACTION"),
            ("spikes/possession.py", "FOLLOW_THROUGH_SECONDS"),
            ("spikes/possession.py", "TURN_DEADBAND_DEGREES"),
            ("spikes/movement_engine.py", "SCAPULA_START_DEGREES"),
            ("spikes/movement_engine.py", "SCAPULA_RATIO"),
            ("spikes/movement_engine.py", "SCAPULA_MAX_DEGREES"),
            ("spikes/movement_engine.py", "SHOULDER_LINE_FULL_AT_DEGREES"),
            ("spikes/movement_engine.py", "ELBOW_POLE_DOWN_CM"),
            ("spikes/movement_engine.py", "ELBOW_POLE_OUT_CM"),
            ("spikes/movement_engine.py", "HAND_LIFT"),
            ("spikes/ball_reach.py", "PALM_CENTRE_FRACTION"),
            ("spikes/smplx_retarget.py", "LEAN"),
            ("spikes/sweep_ball_height.py", "SHIPPED_UP"),
            ("spikes/clip_geometry.py", "IN_PLACE_METRES"),
            ("spikes/clip_geometry.py", "TRAVELS_FRACTION"),
        },
    ),
    (
        "grading-floor", INCLUDE,
        "A number that decides whether a coach's band is allowed to exist, or "
        "whether a difference is reported to her. It sets what the engine is "
        "willing to say about a body, so it is a claim about measurability.",
        {
            ("spikes/movement_definition.py", "MINIMUM_MEANINGFUL_BAND_DEGREES"),
            ("spikes/movement_definition.py", "MINIMUM_MEANINGFUL_BAND_CENTIMETRES"),
            ("spikes/snap_report.py", "MINIMUM_MEANINGFUL_BAND_DEGREES"),
            ("spikes/snap_report.py", "SNAP_FLOOR_DEGREES"),
            ("spikes/test_band_floor.py", "LANDMARK_NOISE_MM"),
            ("spikes/test_band_floor.py", "LANDMARKS_IN_A_LENGTH"),
            ("spikes/clip_gap_read.py", "NOTABLE_DEGREES"),
            ("spikes/verify_tactics_clip.py", "THRESHOLD_DEGREES"),
        },
    ),
    (
        "object-in-the-hand", INCLUDE,
        "The ball's own size. It is not a body, but every hand position and "
        "every clearance is measured against it, so a coach can dispute it and "
        "a change moves the hands.",
        {
            ("spikes/author_flight.py", "SIZE_FIVE_RADIUS_CM"),
            ("spikes/ball_track.py", "SIZE_FIVE_NETBALL_RADIUS_CM"),
            ("spikes/export_mesh_viewer.py", "BALL_RADIUS_CM"),
            ("scripts/ball_anchor_verdict.py", "RADIUS"),
        },
    ),
    (
        "solver-weight", CONTESTED,
        "A relative weight in the solver's objective. It is NOT a statement "
        "about a body, and no coach can rule on it. But changing one changes "
        "the pose the engine reports, so it changes what the engine claims a "
        "body did. THIS CALL IS NOT SETTLED and it is the one place this file "
        "expects to be argued with. Held out of the register for now on the "
        "ground that a register a coach cannot read is a different document.",
        {
            ("spikes/movement_engine.py", "FOOT_WEIGHT"),
            ("spikes/movement_engine.py", "LIMIT_WEIGHT"),
            ("spikes/movement_engine.py", "HAND_WEIGHT"),
            ("spikes/movement_engine.py", "TRUNK_WEIGHT"),
            ("spikes/movement_engine.py", "SHOULDER_LINE_WEIGHT"),
            ("spikes/movement_engine.py", "SHOULDER_BASE_WEIGHT"),
            ("spikes/movement_engine.py", "SCAPULA_WEIGHT"),
            ("spikes/movement_engine.py", "FOOTWORK_SHOULDER_WEIGHT"),
            ("spikes/movement_engine.py", "ELBOW_POLE_WEIGHT"),
            ("spikes/contact_solve.py", "CONTACT_POLE_WEIGHT"),
            ("spikes/contact_solve.py", "UPPER_ARM_AIM_WEIGHT"),
            ("spikes/possession_solve.py", "CONTINUITY_WEIGHT"),
            ("spikes/finger_wrap.py", "TIP_WEIGHT"),
            ("spikes/finger_wrap.py", "MIDDLE_WEIGHT"),
            ("spikes/finger_wrap.py", "THUMB_WEIGHT"),
            ("spikes/smplx_retarget.py", "BODY_WEIGHT"),
        },
    ),
    (
        "planted-threshold", CONTESTED,
        "PLANTED_CM decides when a foot counts as planted. That is either a "
        "claim about a body, because a coach can say how still a planted foot "
        "is, or a numerical tolerance on a position the solver already "
        "reports. RULED CONTESTED 2026-09-09 rather than decided: a row on the "
        "line filed as decided is worse than a row filed as contested.",
        {
            ("spikes/movement_engine.py", "PLANTED_CM"),
        },
    ),
    (
        "physical-constant", EXCLUDE,
        "Gravity and unit conversions. Sourced outside this project, identical "
        "for every body, and nothing a coach or a shoot could change.",
        {
            ("spikes/author_flight.py", "GRAVITY_CM"),
            ("spikes/ball_track.py", "GRAVITY_CM"),
            ("spikes/possession.py", "GRAVITY_CM"),
            ("spikes/test_return_pass.py", "GRAVITY_CM"),
            ("spikes/smplx_retarget.py", "METRES_TO_CM"),
            ("spikes/poc_engine.py", "CENTIMETRES_PER_METRE"),
        },
    ),
    (
        "numerical-tolerance", EXCLUDE,
        "An epsilon, a rounding step or an agreement threshold between two "
        "computations of the SAME quantity. Changing it changes whether two "
        "numbers are called equal, never what either number says about a body.",
        {
            ("spikes/isb_angles.py", "_EPSILON"),
            ("spikes/segment_measures.py", "_EPSILON"),
            ("spikes/movement_engine.py", "ZERO_WIDTH_RADIANS"),
            ("girdle_agreement.py", "ROUNDING_M"),
            ("girdle_agreement.py", "TOLERANCE_M"),
            ("girdle_agreement.py", "REACH_TOLERANCE_MM"),
            ("spikes/athlete.py", "TOLERANCE_CM"),
            ("spikes/check_joint_limits.py", "TOLERANCE_DEGREES"),
            ("spikes/hand_orientation_crosscheck.py", "RECEIPT_ROUNDING_DEGREES"),
            ("spikes/test_open_hand.py", "OPEN_TOLERANCE"),
            ("spikes/test_hand_mirror.py", "MIRROR_TOLERANCE_CM"),
            ("spikes/test_job_shoulders.py", "ROUNDING_TORSOS"),
            ("spikes/test_job_shoulders.py", "COMPOSED_TORSOS"),
            ("spikes/test_job_shoulders.py", "LOOKS_ABSOLUTE_TORSOS"),
            ("spikes/retarget.py", "CONTACT_TOLERANCE_FRAMES"),
            ("spikes/retarget.py", "PALM_TOLERANCE_CM"),
            ("spikes/retarget.py", "SNAP_RATIO"),
            ("spikes/proof.py", "SNAP_RATIO"),
            ("spikes/test_snap_report.py", "SNAP_RATIO"),
            ("spikes/snap_report.py", "SNAP_WINDOW"),
            ("spikes/retune_reach.py", "ACCEPTABLE_MISS_CM"),
            ("spikes/retune_reach.py", "LOWEST_SCALE"),
            ("spikes/contact_solve.py", "TIP_TOLERANCE_CM"),
            ("spikes/contact_solve.py", "PINNED_FRACTION"),
            ("spikes/contact_solve.py", "SPREAD_TOLERANCE_DEGREES"),
            ("blender_mpfb_reference_catch.py", "CONTACT_CLEARANCE_M"),
            ("blender_mpfb_reference_catch.py", "CONTACT_TOLERANCE_M"),
            ("blender_mpfb_reference_catch.py", "FINGER_AIM"),
            ("blender_mpfb_reference_catch.py", "KNUCKLE_ITERATIONS"),
            ("blender_mpfb_reference_catch.py", "FLEXION_MEASURE_FLOOR_DEGREES"),
            ("finger_curl.py", "MIN_AXIS_SHARE"),
            ("scripts/report_clearance.py", "CONTACT_MM"),
            ("scripts/ball_anchor_verdict.py", "THRESHOLD"),
            ("scripts/ball_anchor_verdict.py", "IN_FLIGHT_CM"),
            ("scripts/before_after_sheet.py", "BAND"),
            ("scripts/before_after_sheet.py", "MOVED"),
            ("scripts/fan_mirror_check.py", "SYMMETRIC_DEGREES"),
            ("scripts/fan_mirror_check.py", "GIRDLE_TRAVEL_M"),
            ("spikes/test_waiting_hand.py", "STANCE_TOLERANCE_DEGREES"),
            ("spikes/test_waiting_hand.py", "KNEE_GAP_SOLVED_DEGREES"),
            ("spikes/test_cold_start.py", "STILL_CM"),
            ("spikes/test_cold_start.py", "THRESHOLD_DEGREES"),
            ("spikes/test_cold_start.py", "WINDOW"),
            ("spikes/test_hand_mirror.py", "OPEN_FAN_FLOOR_CM"),
        },
    ),
    (
        "video-pipeline", EXCLUDE,
        "A threshold, sample rate, window or visibility floor inside the "
        "footage pipeline. Changing one changes how an event is DETECTED in a "
        "recording, never what the engine claims a body did. The measurements "
        "these produce are in scope; the detector's own settings are not.",
        {
            ("spikes/video_clap_evidence.py", name) for name in (
                "BAND_HERTZ", "BLOCK_SECONDS", "FLOOR_SECONDS", "FLOOR_GUARD_BLOCKS",
                "ATTACK_RATIO", "SEPARATION_SECONDS", "SPIKE_RISE", "TOGETHER_WIDTHS",
                "WRIST_VISIBILITY", "BODY_VISIBILITY",
            )
        } | {
            ("spikes/video_phase_align.py", name) for name in (
                "SMOOTHING_SAMPLES", "PEAK_PROMINENCE_DEGREES", "PEAK_SEPARATION_SECONDS",
                "MINIMUM_PEAK_TO_NOISE", "CATCH_LOOKBACK_SECONDS", "PULL_IN_ONSET_RISE_SHARE",
                "ONSET_FLATNESS_RATIO", "MAX_LEAD_SECONDS", "FEATURELESS_TOLERANCE_DEGREES",
                "WARP_BAND_SHARE",
            )
        } | {
            ("spikes/video_event_ledger.py", name) for name in (
                "ANCHOR_GAP_SECONDS", "NULL_TRIALS", "NULL_SEED", "NULL_PERCENTILE",
                "SEARCH_SECONDS", "ANCHOR_FRAME_STEP",
            )
        } | {
            ("spikes/video_calibration.py", name) for name in (
                "STATIC_TRANSLATION_TOLERANCE_METRES", "STATIC_ROTATION_TOLERANCE_DEGREES",
                "MINIMUM_SEPARATION_DEGREES", "DEFAULT_EVERY", "HELD_OUT_SHARE",
                "MINIMUM_HELD_OUT",
            )
        } | {
            ("spikes/video_keypoints.py", "PTS_TOLERANCE_SECONDS"),
            ("spikes/video_keypoints.py", "SYNC_UNCERTAINTY_SECONDS"),
            ("spikes/video_keypoints.py", "CONSTANT_RATE_TOLERANCE_SECONDS"),
            ("spikes/video_motion_sync.py", "WIDTH"),
            ("spikes/video_motion_sync.py", "GRID_RATE"),
            ("spikes/video_motion_sync.py", "GUARD_SECONDS"),
            ("spikes/video_ball_in_frame.py", "WINDOW_TOLERANCE_SECONDS"),
            ("spikes/video_ball_in_frame.py", "NARROW_MARGIN_FRAMES"),
            ("spikes/video_lift_3d.py", "VISIBLE_ENOUGH"),
            ("spikes/video_hand_speed.py", "NULL_MIN_VISIBILITY"),
            ("spikes/video_flick_requirement.py", "MARGIN"),
            ("spikes/video_flick_requirement.py", "SAMPLES_WANTED"),
            ("spikes/video_flick_requirement.py", "SHOT_AT_FPS"),
            ("spikes/video_dry_run.py", "MEANINGFUL_DEGREES"),
            ("spikes/video_dry_run.py", "MINIMUM_SEPARATION_DEGREES"),
            ("spikes/video_dry_run.py", "FAST_HAND_METRES_PER_SECOND"),
            ("spikes/video_dry_run.py", "RELEASE_RAMP_SECONDS"),
            ("spikes/video_dry_run.py", "RELEASE_RAMP_SAMPLES"),
            ("spikes/video_dry_run.py", "RELEASE_FRAME_RATE"),
            ("spikes/video_dry_run.py", "ADDRESSABLE_KEYFRAME_SECONDS"),
            ("spikes/multi_camera_fit.py", "MINIMUM_SEPARATION_DEGREES"),
            ("spikes/multi_camera_fit.py", "MEANINGFUL_DEGREES"),
            ("spikes/multi_camera_fit.py", "UNCERTAINTY_MARGIN"),
            ("spikes/multi_camera_fit.py", "UNCERTAINTY_SAMPLES"),
            ("spikes/spike_i_camera_placement.py", "DISTANCE_CM"),
            ("spikes/spike_i_camera_placement.py", "DETECTOR_NOISE_PX"),
            ("spikes/verify_capture_pipeline.py", "DETECTOR_NOISE_PX"),
            ("spikes/fit_from_photo.py", "MINIMUM_VISIBILITY"),
            ("scripts/video_sync_sheet.py", "WINDOW_HALF_S"),
            ("scripts/video_sync_sheet.py", "WINDOW_FRAMES"),
            ("scripts/keypoint_overlay.py", "SEEN"),
            ("scripts/keypoint_overlay.py", "GLIMPSED"),
            ("spikes/test_video_calibration.py", "TRUE_SEPARATION_DEGREES"),
            ("spikes/test_video_calibration.py", "NOISE_PIXELS"),
            ("spikes/test_video_calibration.py", "VIEWS"),
            ("spikes/test_video_clap_evidence.py", "RATE"),
            ("spikes/test_video_phase_align.py", "FRAMES"),
            ("spikes/test_video_phase_align.py", "CONTACT_PHASE"),
        },
    ),
    (
        "presentation", EXCLUDE,
        "A pixel size, image quality, panel count or frame rate for something "
        "a person looks at. It changes the picture and not the claim. A figure "
        "too small to read is a real fault and it is not this register's.",
        {
            ("spikes/video_anchor_sheets.py", name) for name in (
                "SHEET_STEP", "SHEET_HALF", "TILE_HEIGHT", "LABEL_SIZE",
                "TILE_LABEL_BAND", "TILE_MARGIN_DB", "MEASURED_MIN_TILE_MARGIN_DB",
            )
        } | {
            ("spikes/video_section_cuts.py", name) for name in (
                "OUTPUT_FPS", "PROOF_INSTANTS", "PROOF_TILE_WIDTH", "POSTER_QUALITY",
                "RELATIVE_MARGIN_DB", "MEASURED_MIN_MARGIN_DB",
            )
        } | {
            ("spikes/render_contact_sheet.py", "PANELS"),
            ("spikes/render_contact_sheet.py", "PANEL_WIDTH"),
            ("spikes/render_contact_sheet.py", "PANEL_HEIGHT"),
            ("spikes/export_manual_page.py", "FIGURE_WIDTH"),
            ("spikes/export_manual_page.py", "FIGURE_QUALITY"),
            ("spikes/export_viewer_data.py", "VIEW_WIDTH"),
            ("spikes/export_viewer_data.py", "VIEW_HEIGHT"),
            ("spikes/export_figure_check.py", "VERTEX_SCALE"),
            ("spikes/export_proof_viewer.py", "KEEP_EVERY"),
            ("spikes/render_figure.py", "AMBIENT"),
            ("spikes/render_photo_fit.py", "PANEL"),
            ("scripts/keypoint_overlay.py", "JOINT_RADIUS"),
            ("spikes/test_video_anchor_sheets.py", "TILE_HEIGHT_FOR_TESTS"),
        },
    ),
    (
        "format-and-model", EXCLUDE,
        "A schema version, a level of detail, or a fact about a third-party "
        "body model's file format. Not authored by this project as a claim "
        "about people, and not a thing a coach or a shoot could change.",
        {
            ("spikes/clip_geometry.py", "SCHEMA_VERSION"),
            ("spikes/reference_curves.py", "SCHEMA_VERSION"),
            ("movement_contract.py", "JOB_VERSION"),
            ("spikes/movement_engine.py", "LEVEL_OF_DETAIL"),
            ("spikes/poc_engine.py", "LEVEL_OF_DETAIL"),
            ("spikes/spike_a_mhr_ik.py", "LEVEL_OF_DETAIL"),
            ("spikes/export_mesh_viewer.py", "VIEWER_LOD"),
            ("spikes/smplx_body.py", "VERTICES"),
            ("spikes/smplx_body.py", "JOINTS"),
            ("spikes/smplx_body.py", "SHAPE_COEFFICIENTS"),
        },
    ),
    (
        "test-fixture", EXCLUDE,
        "A seed, a sample count, a repeat count or a frame index that exists "
        "to make a test or a sweep run. It decides how hard we look, never "
        "what we claim to have found.",
        {
            ("spikes/test_band_floor.py", "SAMPLES"),
            ("spikes/test_band_floor.py", "SEED"),
            ("spikes/spike_h_roundtrip.py", "SAMPLES"),
            ("spikes/spike_h_roundtrip.py", "SEED"),
            ("spikes/spike_i_camera_placement.py", "SAMPLES"),
            ("spikes/spike_i_camera_placement.py", "SEED"),
            ("spikes/verify_capture_pipeline.py", "SEED"),
            ("spikes/spike_a_mhr_ik.py", "SOLVE_REPEATS"),
            ("spikes/athlete.py", "MAXIMUM_PASSES"),
            ("spikes/author_flight.py", "DEFAULT_KEYS"),
            ("spikes/test_job_shoulders.py", "COVERED_AT_LEAST"),
            ("spikes/test_possession.py", "FRAMES"),
            # RULED 2026-09-09: moved here from anthropometry. 50.0 is a round
            # number and the reference athlete's arm is 52.68, so this is a
            # fixture and not a body. test_authored_launch.ARM_CM = 52.7 STAYS
            # in anthropometry, because it is a rounding of the real value.
            ("spikes/test_possession.py", "ARM_CM"),
            ("spikes/test_authored_launch.py", "SECONDS_PER_PHASE"),
            ("spikes/sweep_ball_height.py", "LIFT_FRAME"),
            ("spikes/sweep_ball_height.py", "RELEASE_FRAME"),
        },
    ),
]


def load_rows() -> tuple[list[dict[str, object]], list[str]]:
    """The constants, and the files this interpreter could not read.

    The second value is not decoration. A file that was not read contributes no
    constants, and an unread file is indistinguishable from a file with none.
    """
    rows: list[dict[str, object]] = []
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
        for line, name, number in constants_in(tree):
            rows.append({"file": relative, "line": line, "name": name, "value": number})
    return rows, unread


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--show", choices=[INCLUDE, EXCLUDE, CONTESTED],
                        help="list the constants with this verdict")
    parser.add_argument("--json", type=Path, help="write the verdicts to this file")
    args = parser.parse_args()

    rows, unread = load_rows()
    print(f"tip:         {tip()}")
    print(f"interpreter: python {platform.python_version()}")
    print()

    verdicts: list[dict[str, object]] = []
    unmatched: list[dict[str, object]] = []
    multiple: list[tuple[dict[str, object], list[str]]] = []

    for row in rows:
        key = (row["file"], row["name"])
        hit = [rule for rule in RULES if key in rule[3]]
        if not hit:
            unmatched.append(row)
            continue
        if len(hit) > 1:
            multiple.append((row, [rule[0] for rule in hit]))
            continue
        rule = hit[0]
        verdicts.append({**row, "rule": rule[0], "verdict": rule[1], "reason": rule[2]})

    counts = {INCLUDE: 0, EXCLUDE: 0, CONTESTED: 0}
    for verdict in verdicts:
        counts[str(verdict["verdict"])] += 1

    print(f"constants read: {len(rows)}"
          + (f"   A LOWER BOUND: {len(unread)} file(s) unread: {', '.join(unread)}"
             if unread else ""))
    print()
    for rule_id, decision, _reason, members in RULES:
        got = sum(1 for v in verdicts if v["rule"] == rule_id)
        print(f"  {decision:9s}  {got:4d}  {rule_id}"
              + ("" if got == len(members) else f"   (rule lists {len(members)})"))
    print()
    print(f"  INCLUDE   {counts[INCLUDE]}")
    print(f"  CONTESTED {counts[CONTESTED]}")
    print(f"  EXCLUDE   {counts[EXCLUDE]}")
    print(f"  TOTAL     {sum(counts.values())} of {len(rows)} read")

    if args.show:
        print()
        for verdict in sorted(verdicts, key=lambda v: (v["rule"], v["file"], v["name"])):
            if verdict["verdict"] == args.show:
                print(f"  {verdict['rule']:22s} {verdict['file']}:{verdict['line']} "
                      f"{verdict['name']} = {verdict['value']}")

    if args.json:
        args.json.write_text(json.dumps(verdicts, indent=1), encoding="utf-8")
        print(f"\nverdicts written to {args.json}")

    failed = False
    if unmatched:
        print()
        print(f"{len(unmatched)} CONSTANT(S) MATCH NO RULE. The register cannot")
        print("account for them and no reason has been written for leaving them out:")
        for row in unmatched:
            print(f"    {row['file']}:{row['line']}  {row['name']} = {row['value']}")
        failed = True
    if multiple:
        print()
        print(f"{len(multiple)} CONSTANT(S) MATCH MORE THAN ONE RULE. Two reasons")
        print("disagree about the same number and a reader must be shown which:")
        for row, names in multiple:
            print(f"    {row['file']}:{row['line']}  {row['name']}  ->  {', '.join(names)}")
        failed = True
    return 2 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
