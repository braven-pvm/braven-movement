"""Solve a whole movement with the ball as the reason the athlete moves.

Milestone 3 of the possession model. Nothing about the hands is read from the
motion file any more. The ball flies on its own trajectory, the athlete holds
her hands out toward it while it is out of reach, she takes it on the first
frame it comes inside that distance, and after that she carries it where the
technique says.

Everything below the hands still comes from the motion file, unchanged: the hip
drop, the trunk turn, the foot placement, the root travel.

    pixi run python possession_solve.py
    pixi run python possession_solve.py netball_two_hand_snatch_pull_in
"""

from __future__ import annotations

import json
import sys
import time
from pathlib import Path

import numpy as np
import pymomentum.solver2 as solver2

SPIKE_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(SPIKE_DIR))

from ball_reach import reach_envelope  # noqa: E402
from ball_track import ball_path, has_ball, load_ball, stance_frame  # noqa: E402
from contact_solve import (  # noqa: E402
    close_fingers,
    contact_constraints,
    contact_miss,
    elbow_poles,
    upper_arm_aim,
    foot_constraints,
    measure_contact,
    pinned_parameters,
    seeds,
    solver_options,
    trunk_constraints,
)
from finger_wrap import curl_parameters, spread_fingers  # noqa: E402
from grip import grip_targets, measure_hand  # noqa: E402
from motion_track import (  # noqa: E402
    MAXIMUM_TURN_DEGREES,
    arm_length,
    load_motion,
    torso_length,
)
from movement_engine import (  # noqa: E402
    LIMIT_WEIGHT,
    SolveError,
    definition_path,
    enabled_parameters,
    foot_targets,
    joint_positions,
    library,
    load_character,
    measure_frame,
    motion_path,
    trunk_frame,
)
from snap_report import spike_report  # noqa: E402, F401
from movement_definition import (  # noqa: E402
    MINIMUM_MEANINGFUL_BAND_DEGREES,
    load as load_definition,
)
from possession import (  # noqa: E402
    READY_FRACTION,
    resolve,
    turn_profile,
    turn_toward,
)
from technique import has_technique, load_technique, technique_path  # noqa: E402

OUTPUT = SPIKE_DIR / "poc-output" / "library"

# A weak pull toward the REST POSE, and the same one the movement solver uses.
#
# The name is wrong and is left alone here deliberately, so that this commit
# changes no behaviour. `ModelParametersErrorFunction` penalises the difference
# between the current parameters and a TARGET, and nothing below ever calls
# `set_target_parameters`, so the target is zero: the rest pose. Every other
# use of this class in the repository names the variable `prior`, which is what
# it is.
#
# FRAME-TO-FRAME CONTINUITY IN THIS SOLVER COMES FROM THE SEED. Each frame is
# solved starting from the previous frame's answer, and nothing in the
# objective prefers the previous pose. That distinction matters when reading a
# snap: a term pulling toward rest cannot carry a bad pose forward, and cannot
# oppose a correct term frame by frame. The seed does both.
#
# Refer to "The term named continuity is a pull toward the rest pose" in
# docs/KNOWN_ISSUES.md before explaining any discontinuity by this term.
CONTINUITY_WEIGHT = 0.02


def athlete_frames(
    track, rest_positions, index, reach_cm, torso_cm, phases, turns=None
):
    """The trunk, per frame, and the athlete's own frame that goes with it."""
    if turns is None:
        turns = [track.turn_at(phase) for phase in phases]
    placed = [
        trunk_frame(track, phase, rest_positions, index, reach_cm, turn)
        for phase, turn in zip(phases, turns)
    ]
    frames = [
        stance_frame(one.chest, reach_cm, turn) for one, turn in zip(placed, turns)
    ]
    # The same frames scaled by the torso, for the ball she is already holding.
    carried = [
        stance_frame(one.chest, torso_cm, turn) for one, turn in zip(placed, turns)
    ]
    shoulders = [
        (one.shoulders["l"] + one.shoulders["r"]) / 2.0 for one in placed
    ]
    return placed, frames, carried, shoulders


def solve_movement(
    character,
    movement_id: str,
    variant: str | None = None,
    identity: np.ndarray | None = None,
) -> dict:
    """Solve every frame of a movement against its ball. No hand keys are read.

    The variant selects which ball. The technique never changes with it, which
    is the whole claim being tested: one technique, any arrival point.

    ``identity`` is the athlete's size. Everything the drill says is in arm
    lengths, so a different body should produce the same movement at its own
    scale, and that is the other claim being tested.
    """
    track = load_motion(motion_path(movement_id))
    ball = load_ball(ball_path(movement_id, variant))
    method = load_technique(technique_path(movement_id))

    names = list(character.skeleton.joint_names)
    index = {name: number for number, name in enumerate(names)}
    count = character.parameter_transform.size
    rest = (
        np.zeros(count, dtype=np.float32)
        if identity is None
        else np.asarray(identity, dtype=np.float32).copy()
    )
    # The hand is open before it is anything else.
    rest = spread_fingers(character, rest, method.every_side)
    rest_positions = joint_positions(character, rest)
    reach_cm = arm_length(rest_positions, index)
    radius_cm = ball.radius_cm_for(reach_cm)
    shapes = {side: measure_hand(rest_positions, index, side) for side in ("l", "r")}

    def segment(first: str, second: str) -> float:
        return float(
            np.linalg.norm(rest_positions[index[first]] - rest_positions[index[second]])
        )

    envelope = reach_envelope(
        upper_cm=segment("l_uparm", "l_lowarm"),
        fore_cm=segment("l_lowarm", "l_wrist"),
        palm_cm=segment("l_wrist", "l_middle1"),
    )

    phases = [number / (track.frames - 1) for number in range(track.frames)]
    authored = [track.turn_at(phase) for phase in phases]
    torso_cm = torso_length(rest_positions, index)
    placed, frames, carried, shoulders = athlete_frames(
        track, rest_positions, index, reach_cm, torso_cm, phases, authored
    )
    stance = stance_frame(placed[0].chest, reach_cm, track.turn_at(0.0))

    # A wide ball is taken by turning to it, not by reaching across. The turn
    # comes from where the ball arrives, which is known without solving, so
    # nothing here depends on the pose it produces.
    turns = authored
    turned_by = 0.0
    if method.turn_to_ball:
        turned_by = turn_toward(ball.keys[-1].offset, MAXIMUM_TURN_DEGREES)
        if turned_by:
            turns = turn_profile(
                phases, ball.release_phase, ball.arrival_phase, turned_by, authored
            )
            placed, frames, carried, shoulders = athlete_frames(
                track, rest_positions, index, reach_cm, torso_cm, phases, turns
            )

    held = resolve(
        phases=phases,
        ball=ball,
        stance=stance,
        athlete_frames=frames,
        shoulder_mids=shoulders,
        shoulder_places=[one.shoulders for one in placed],
        after_contact=method.after_contact,
        reach_limit_cm=envelope.far_cm + radius_cm,
        arm_length_cm=reach_cm,
        carry_frames=carried,
        torso_length_cm=torso_cm,
        ready_offset=method.ready,
        release_phase=method.release_phase,
        sides_at=method.sides_at,
        seconds_per_phase=(track.frames - 1) / track.frames_per_second,
    )
    if not held.caught:
        raise SolveError(
            f"{movement_id}: the ball never comes inside the athlete's reach, so "
            "there is no catch to solve. That is a dropped ball, not a defect."
        )

    # When the free hand starts closing on the ball, and how long it takes.
    joining_from = None
    joining_span = 0.0
    if method.second_hand_phase is not None:
        joining_from = held.frames[held.contact_frame].phase
        joining_span = method.second_hand_phase - joining_from

    enabled = enabled_parameters(character)
    started = time.perf_counter()
    motion = np.zeros((track.frames, count), dtype=np.float32)
    points_per_frame: list[np.ndarray] = []
    measurements: list[dict] = []

    def solve_one(frame, seed, cold: bool):
        """Solve one frame from one seed.

        The seed is the only thing that differs between the two sweeps below.
        The targets, the error terms and the weights are rebuilt identically
        each time, so a frame cannot change because it was reached second."""
        number, phase = frame.number, frame.phase
        # Every hand the drill uses is shaped on every frame. A hand that is
        # not on the ball is shaped around the point it is moving toward, which
        # before contact is what she is presenting at and between contact and
        # the second hand joining is a point closing on the ball.
        sides = method.every_side
        # sides_at knows about the release and the second hand, not about
        # contact, so a hand only counts as on the ball once she has it.
        on_ball = frame.sides if frame.holding else ()
        centres = {}
        for side in sides:
            if side in on_ball:
                centres[side] = frame.centre
            elif joining_from is None:
                centres[side] = frame.presented
            elif not frame.holding:
                # The free hand of a one hand drill waits. Only the hand that
                # is taking the ball goes out to meet it.
                #
                # This line used to send BOTH hands to `waiting`, because the
                # test above it asks only whether she is holding the ball yet
                # and never which hand is doing the catching. So on the two
                # drills that join a second hand, the CATCHING hand waited too
                # and then arrived on the ball in a single frame: the wrist sat
                # 39.5 cm from the ball centre on the frame before contact and
                # 15.2 cm on the frame of it, a 19.9 cm step, and the upper arm
                # swung 48.1 degrees following it. That was the largest step in
                # the library. Every drill without a second hand takes the
                # branch above and steps 1.7 to 4.2 cm.
                #
                # The comment was right and the code did not do what it said.
                centres[side] = (
                    frame.presented if side in method.sides else frame.waiting
                )
            else:
                # The same squared ramp the catching hand uses. Easing this
                # one in at both ends with a smoothstep was tried and made no
                # difference, so what is left on the outside hand hooks drill
                # is the free arm changing configuration as it comes round her,
                # not the shape of the ramp.
                travel = min(
                    1.0,
                    max(0.0, (phase - joining_from) / max(joining_span, 1e-9)),
                ) ** 2
                centres[side] = (
                    frame.waiting + (frame.centre - frame.waiting) * travel
                )

        contact_error, found = contact_constraints(
            character, index, placed[number], shapes, centres,
            radius_cm, method.spread_degrees, sides,
        )
        targets = grip_targets(shapes, found)
        continuity = solver2.ModelParametersErrorFunction(character)
        continuity.weight = CONTINUITY_WEIGHT
        function = solver2.SkeletonSolverFunction(
            character,
            [
                contact_error,
                trunk_constraints(
                    character, index, placed[number],
                    {side: targets[f"{side}_wrist"] for side in sides},
                ),
                foot_constraints(
                    character,
                    index,
                    foot_targets(
                        track, phase, placed[number], rest_positions, index,
                        reach_cm,
                    ),
                ),
                elbow_poles(
                    character, index, placed[number], targets, reach_cm, sides,
                    method.elbow_angle_degrees,
                ),
                upper_arm_aim(
                    character, index, placed[number], targets, reach_cm, sides
                ),
                continuity,
                solver2.LimitErrorFunction(character, weight=LIMIT_WEIGHT),
            ],
        )
        solver = solver2.GaussNewtonSolver(function, solver_options())
        solver.set_enabled_parameters(enabled)

        def run(seed: np.ndarray) -> np.ndarray:
            answer = np.asarray(
                solver.solve(np.asarray(seed, dtype=np.float32).reshape(-1, 1)),
                dtype=np.float32,
            ).reshape(-1)
            return np.asarray(
                solver.solve(answer.reshape(-1, 1)), dtype=np.float32
            ).reshape(-1)

        if cold:
            # The first frame is a cold start: there is no previous pose and the
            # rest pose has the arms by the sides. Solving it once from rest
            # left the athlete in a different arm configuration from frame one,
            # and the elbow moved 33 degrees over the first few frames while the
            # target barely moved. Every later frame continues from its
            # neighbour and needs none of this.
            # `start`, not `seed`: this loop used to rebind the parameter, so
            # the fallback below copied the last twist seed rather than the
            # pose the caller asked to start from. It needs every seed to come
            # back non-finite to reach, so no drill has ever taken it, and a
            # branch that is wrong only when everything else has failed is the
            # worst place to be wrong.
            best, solved = float("inf"), None
            for start in seeds(character, rest, None):
                answer = run(start)
                if not np.all(np.isfinite(answer)):
                    continue
                miss = contact_miss(
                    joint_positions(character, answer), index, targets
                )
                if miss < best:
                    best, solved = miss, answer
            if solved is None:
                solved = seed.copy()
        else:
            # The same two passes frame zero uses on each of its seeds, rather
            # than one. A single Gauss-Newton solve from the previous pose is
            # usually enough and on frame 12 of the outside-hand hooks it was
            # not: the wrists ended 24.1 and 32.5 cm from the points they were
            # asked for, against about 15.5 cm on every neighbouring frame, and
            # the whole athlete moved with it — the root 13.5 cm, both feet
            # about 50, the left shoulder elevation 19.4 to 114.8 degrees and
            # back. That frame then seeded the next, and the right wrist never
            # recovered: its miss sat at 22.7 cm for the rest of the drill
            # instead of returning to 15.2.
            #
            # It is an unconverged frame and not a second valid pose, which is
            # what the residual says. Frame zero already solves twice, so this
            # removes a special case rather than adding one.
            solved = run(seed)
        if not np.all(np.isfinite(solved)):
            solved = seed.copy()

        # The fingers close on the ball only once she has it. Before that they
        # stay open, which is what a hand waiting to receive actually does.
        if frame.holding and frame.sides:
            solved = close_fingers(
                character, index, solved, frame.centre, radius_cm, frame.sides
            )
        return solved

    # ---- the forward sweep ---------------------------------------------
    answers: dict[int, np.ndarray] = {}
    previous = rest.copy()
    for frame in held.frames:
        previous = solve_one(frame, previous, cold=(frame.number == 0))
        answers[frame.number] = previous

    # ---- the backward sweep ----------------------------------------------
    # Frame zero is the only frame the forward sweep solves without a
    # neighbour to start from, so an under-determined joint resolves there
    # however the rest pose leaves it, and the drill then steps into line.
    # On the outside-hand hooks the right knee opened at 34.1 degrees against
    # the 47 the drill settles at, held it for six frames and stepped 9.6,
    # with both feet reading 0.00 cm off the floor and the pelvis inside
    # 0.02 cm throughout. A planted foot and a fixed pelvis do not determine a
    # knee, so nothing pulled it back.
    #
    # The LAST frame is solved from a neighbour, so the drill is walked back
    # from it and every earlier frame is re-solved from its successor. Frame
    # zero then starts from frame one exactly as frame one started from frame
    # zero, and no frame in the kept answer is a cold start. The forward sweep
    # is still what finds the drill; this is what removes its seam.
    backward = list(held.frames)[::-1]
    previous = answers[backward[0].number]
    for frame in backward[1:]:
        previous = solve_one(frame, previous, cold=False)
        answers[frame.number] = previous

    # ---- the fingers open again on every frame she is not holding ---------
    # `close_fingers` runs inside the solve and its result becomes the next
    # frame's SEED. While the only sweep ran forward that was harmless: every
    # frame after contact is holding anyway. The backward sweep seeds each
    # frame from its SUCCESSOR, so the curl from the end of the drill
    # propagated back through every pre-contact frame. The curl parameters are
    # frozen in the main solve, so a seeded curl passes straight through to the
    # answer untouched.
    #
    # Measured on e1b2ca8: at frame zero, where she is not holding, 20 of the
    # 30 curl parameters were non-zero and the largest was 1.570 radians. That
    # is a hand closed to a fist while she waits to receive. (The first write-up
    # of this said 32, from an ad-hoc list of finger parameters ending in _rz
    # rather than the set curl_parameters actually returns. The denominator
    # here is that set, 15 per hand.) Before the
    # backward sweep the same frame read 0 of 32.
    #
    # NOTHING IN THE LIBRARY MEASURES A FINGER, so 311 tests, two independent
    # reviews and the manual clip gate all passed over it. It was found by
    # asking why frame zero's fingers did not match the pose the solve starts
    # from.
    #
    # THE CONDITION IS PER SIDE, and a frame-level version of it is not
    # enough. `close_fingers` curls only the hands in `frame.sides`. A first
    # version of this reset skipped every HOLDING frame, so a hand that is off
    # the ball on a frame where the OTHER hand holds it fell into neither
    # branch: not curled, and not reset. It kept whatever the seed had, which
    # from the backward sweep is the fist of the joined phase.
    #
    # That is one hand fisted for 15 frames on the outside-hand hooks, 46 to
    # 60, and 12 on the one-hand snatch, 47 to 58 — about two tenths of a
    # second each, exactly while she takes the ball one-handed and the other
    # hand waits to join. It sat identically on the build before this reset, so
    # no consequence diff could show it, and a frame-level test cannot see it
    # either: SOME finger on that frame is legitimately curled.
    #
    # Written per side, the condition is the exact negation of the one that
    # applies the curl, so the two cannot drift apart.
    #
    # `names` earlier in this function is the JOINT names. The curl is
    # addressed by PARAMETER name, and the two lists differ in both length and
    # order.
    parameter_names = list(character.parameter_transform.names)
    curl_at = {
        side: [
            parameter_names.index(name)
            for name in curl_parameters(character, (side,))
        ]
        for side in method.every_side
    }
    for frame in held.frames:
        for side, where in curl_at.items():
            if not (frame.holding and side in frame.sides):
                answers[frame.number][where] = rest[where]

    for frame in held.frames:
        number, phase = frame.number, frame.phase
        solved = answers[number]
        motion[number] = solved

        points = joint_positions(character, solved)
        points_per_frame.append(points)
        entry = measure_frame(points, index, phase)
        entry["trunkTurnDegrees"] = round(track.turn_at(phase), 2)
        ground = float(rest_positions[index["l_foot"]][1])
        left_up = float(points[index["l_foot"]][1]) - ground
        right_up = float(points[index["r_foot"]][1]) - ground
        entry["leftFootHeightCm"] = round(left_up, 2)
        entry["rightFootHeightCm"] = round(right_up, 2)
        entry["footHeightGapCm"] = round(abs(left_up - right_up), 2)
        entry["ballState"] = frame.state
        entry["holdingTheBall"] = frame.holding
        entry["handsOnTheBall"] = len(frame.sides)
        measurements.append(entry)

    seconds = time.perf_counter() - started
    return {
        "movementId": movement_id,
        "variant": variant,
        "track": track,
        "ball": ball,
        "technique": method,
        "index": index,
        "motion": motion,
        "points": points_per_frame,
        "measurements": measurements,
        "possession": held,
        "shapes": shapes,
        "radiusCm": radius_cm,
        "armLengthCm": reach_cm,
        "identity": rest,
        "secondsPerFrame": seconds / track.frames,
        "turnedByDegrees": round(turned_by, 2),
        "turns": turns,
    }


def contact_report(character, result: dict) -> dict:
    """Measure the grip on the frame the athlete takes the ball."""
    held = result["possession"]
    number = held.contact_frame
    frame = held.frames[number]
    measured = measure_contact(
        {
            "points": result["points"][number],
            "index": result["index"],
            "shapes": result["shapes"],
            "sides": frame.sides or result["technique"].sides,
            "ballCentreCm": frame.centre,
            "radiusCm": result["radiusCm"],
            "targets": {},
        }
    )
    measured["frame"] = number
    measured["atPhase"] = round(frame.phase, 4)
    return measured


def step_report(measurements: list[dict]) -> dict:
    """The largest change in any measured angle between two frames."""
    keys = [
        key
        for key in measurements[0]
        if key.endswith("Degrees") and isinstance(measurements[0][key], (int, float))
    ]
    worst = {}
    for key in keys:
        series = [frame[key] for frame in measurements]
        steps = [abs(series[i + 1] - series[i]) for i in range(len(series) - 1)]
        worst[key] = round(max(steps), 2) if steps else 0.0
    return worst


def build(character, movement_id: str, variant: str | None = None) -> dict:
    result = solve_movement(character, movement_id, variant)
    held = result["possession"]
    measurements = result["measurements"]
    definition = load_definition(definition_path(movement_id))
    assessment = definition.assess(measurements)

    report = {
        "movementId": movement_id,
        "variant": variant,
        "skill": definition.skill,
        "possession": {
            "contactFrame": held.contact_frame,
            "contactPhase": round(held.frames[held.contact_frame].phase, 4),
            "arrivalPhase": result["ball"].arrival_phase,
            "readyFraction": READY_FRACTION,
            "turnedByDegrees": result["turnedByDegrees"],
            "biggestBallStepCm": round(held.biggest_ball_step_cm(), 2),
            "ballStepAtHandoverCm": round(
                held.ball_step_at(held.contact_frame), 2
            ),
            "states": [frame.state for frame in held.frames],
        },
        "contact": contact_report(character, result),
        "largestStepBetweenFramesDegrees": step_report(measurements),
        "ranOutOf": [
            name
            for number in range(len(result["motion"]))
            for name in pinned_parameters(character, result["motion"][number])
            if any(k in name for k in ("uparm", "lowarm", "elbow", "wrist"))
        ],
        "secondsPerFrame": round(result["secondsPerFrame"], 4),
        "coaching": assessment.to_receipt(),
        "measurement": {"perFrame": measurements},
    }
    report["ranOutOf"] = sorted(set(report["ranOutOf"]))
    OUTPUT.mkdir(parents=True, exist_ok=True)
    stem = movement_id if variant is None else f"{movement_id}.{variant}"
    (OUTPUT / f"{stem}.possession.json").write_text(
        json.dumps(report, indent=2) + "\n", encoding="utf-8"
    )
    return report


def main(argv: list[str]) -> int:
    wanted = argv[1:] or [
        name for name in library() if has_ball(name) and has_technique(name)
    ]
    if not wanted:
        print("no movement has both a ball trajectory and a technique yet")
        return 1

    character = load_character()
    failed = 0
    for movement_id in wanted:
        try:
            report = build(character, movement_id)
        except SolveError as error:
            print(f"FAIL {movement_id}: {error}")
            failed += 1
            continue

        held = report["possession"]
        contact = report["contact"]
        print(f"\n{report['skill']}  ({movement_id})")
        print(
            f"  contact derived at frame {held['contactFrame']}, phase "
            f"{held['contactPhase']}; the flight was authored to arrive at "
            f"{held['arrivalPhase']}"
        )
        print(
            f"  ball moves at most {held['biggestBallStepCm']} cm between frames, "
            f"and {held['ballStepAtHandoverCm']} cm at the handover"
        )
        for side, hand in contact["hands"].items():
            print(
                f"  {side}: palm skin {hand['palmSkinGapCm']:+.2f} cm from the "
                f"surface, wrist {hand['wristGapCm']:+.1f}"
            )
        steps = report["largestStepBetweenFramesDegrees"]
        worst = sorted(steps.items(), key=lambda pair: -pair[1])[:3]
        print(
            "  largest step between frames: "
            + ", ".join(f"{k} {v:.1f} deg" for k, v in worst)
        )
        print(f"  {report['secondsPerFrame'] * 1000:.1f} ms per frame")
        if report["ranOutOf"]:
            print("  ran out of: " + ", ".join(report["ranOutOf"]))
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
