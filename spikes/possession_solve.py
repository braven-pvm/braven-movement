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
    elbow_poles,
    foot_constraints,
    measure_contact,
    pinned_parameters,
    solver_options,
    trunk_constraints,
)
from grip import grip_targets, measure_hand  # noqa: E402
from motion_track import MAXIMUM_TURN_DEGREES, arm_length, load_motion  # noqa: E402
from movement_engine import (  # noqa: E402
    LIMIT_WEIGHT,
    SolveError,
    definition_path,
    enabled_parameters,
    joint_positions,
    library,
    load_character,
    measure_frame,
    motion_path,
    trunk_frame,
)
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

# The same continuity term the movement solver uses, for the same reason: a
# frame solved in isolation can pick a different arm configuration from its
# neighbour and the movement snaps between them.
CONTINUITY_WEIGHT = 0.02


def athlete_frames(track, rest_positions, index, reach_cm, phases, turns=None):
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
    shoulders = [
        (one.shoulders["l"] + one.shoulders["r"]) / 2.0 for one in placed
    ]
    return placed, frames, shoulders


def solve_movement(character, movement_id: str, variant: str | None = None) -> dict:
    """Solve every frame of a movement against its ball. No hand keys are read.

    The variant selects which ball. The technique never changes with it, which
    is the whole claim being tested: one technique, any arrival point.
    """
    track = load_motion(motion_path(movement_id))
    ball = load_ball(ball_path(movement_id, variant))
    method = load_technique(technique_path(movement_id))

    names = list(character.skeleton.joint_names)
    index = {name: number for number, name in enumerate(names)}
    count = character.parameter_transform.size
    rest = np.zeros(count, dtype=np.float32)
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
    placed, frames, shoulders = athlete_frames(
        track, rest_positions, index, reach_cm, phases, authored
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
            placed, frames, shoulders = athlete_frames(
                track, rest_positions, index, reach_cm, phases, turns
            )

    held = resolve(
        phases=phases,
        ball=ball,
        stance=stance,
        athlete_frames=frames,
        shoulder_mids=shoulders,
        after_contact=method.after_contact,
        reach_limit_cm=envelope.far_cm + radius_cm,
        arm_length_cm=reach_cm,
    )
    if not held.caught:
        raise SolveError(
            f"{movement_id}: the ball never comes inside the athlete's reach, so "
            "there is no catch to solve. That is a dropped ball, not a defect."
        )

    enabled = enabled_parameters(character)
    started = time.perf_counter()
    motion = np.zeros((track.frames, count), dtype=np.float32)
    points_per_frame: list[np.ndarray] = []
    measurements: list[dict] = []
    previous = rest.copy()

    for frame in held.frames:
        number, phase = frame.number, frame.phase
        contact_error, found = contact_constraints(
            character, index, placed[number], shapes, frame.presented,
            radius_cm, method.spread_degrees, method.sides,
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
                    {side: targets[f"{side}_wrist"] for side in method.sides},
                ),
                foot_constraints(character, index, rest_positions),
                elbow_poles(
                    character, index, placed[number], targets, reach_cm, method.sides
                ),
                continuity,
                solver2.LimitErrorFunction(character, weight=LIMIT_WEIGHT),
            ],
        )
        solver = solver2.GaussNewtonSolver(function, solver_options())
        solver.set_enabled_parameters(enabled)
        solved = np.asarray(
            solver.solve(previous.reshape(-1, 1)), dtype=np.float32
        ).reshape(-1)
        if number == 0:
            solved = np.asarray(
                solver.solve(solved.reshape(-1, 1)), dtype=np.float32
            ).reshape(-1)
        if not np.all(np.isfinite(solved)):
            solved = previous.copy()

        # The fingers close on the ball only once she has it. Before that they
        # stay open, which is what a hand waiting to receive actually does.
        if frame.holding:
            solved = close_fingers(
                character, index, solved, frame.centre, radius_cm, method.sides
            )
        motion[number] = solved
        previous = solved

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
            "sides": result["technique"].sides,
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


def spike_report(measurements: list[dict]) -> dict:
    """Find frames where a measured angle jumps against its own neighbours.

    A snap is a local spike, not a fast movement. Comparing the largest step in
    a run against the largest step in an easier run measures which run is
    easier, which is a different question and the wrong one: a wide ball is
    taken faster than a central one by a real athlete too.

    So each step is judged against the two either side of it. Anything more
    than three times its neighbours is a frame the movement jumps at.
    """
    worst_ratio = 0.0
    worst_where = None
    for key, value in measurements[0].items():
        if not key.endswith("Degrees") or not isinstance(value, (int, float)):
            continue
        series = [frame[key] for frame in measurements]
        steps = [abs(series[i + 1] - series[i]) for i in range(len(series) - 1)]
        for number in range(1, len(steps) - 1):
            neighbours = (steps[number - 1] + steps[number + 1]) / 2.0
            # A step of a fraction of a degree is noise, not a movement, and
            # dividing by it produces enormous ratios that mean nothing.
            if steps[number] < MINIMUM_MEANINGFUL_BAND_DEGREES or neighbours < 0.2:
                continue
            ratio = steps[number] / neighbours
            if ratio > worst_ratio:
                worst_ratio = ratio
                worst_where = {"measure": key, "frame": number + 1,
                               "stepDegrees": round(steps[number], 2)}
    return {
        "worstNeighbourRatio": round(worst_ratio, 2),
        "at": worst_where,
    }


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
