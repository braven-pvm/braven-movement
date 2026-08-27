"""Solve one frame with the hands on the ball, and measure what happened.

Milestone 2 of the possession model. The hands are no longer authored. The ball
is placed by its own trajectory, the grip decides where on the ball each palm
belongs, and the solver is asked to put the hands there.

Everything the old solver did below the hands is kept exactly: the trunk hold,
the foot pins, the scapular rhythm, the elbow pole, the joint limits at 200.
What is replaced is the pair of wrist position targets and the knuckle
direction, and nothing else.

    pixi run python contact_solve.py
    pixi run python contact_solve.py netball_two_hand_snatch_pull_in
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
import pymomentum.solver2 as solver2

SPIKE_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(SPIKE_DIR))

from ball_track import ball_path, has_ball, load_ball, stance_frame  # noqa: E402
from grip import (  # noqa: E402
    contacts,
    grip_targets,
    measure_hand,
    palm_skin,
    reconstruct,
)
from motion_track import arm_length, load_motion  # noqa: E402
from movement_engine import (  # noqa: E402
    FOOT_WEIGHT,
    LIMIT_WEIGHT,
    SCAPULA_WEIGHT,
    TRUNK_WEIGHT,
    WORLD_UP,
    enabled_parameters,
    joint_positions,
    library,
    load_character,
    motion_path,
    scapula_targets,
    foot_targets,
    trunk_frame,
)
from finger_wrap import (  # noqa: E402
    enable_curl,
    wrap_constraints,
    wrap_report,
)
from athlete import minmax_limits  # noqa: E402,F401
from technique import has_technique, load_technique, technique_path  # noqa: E402

OUTPUT = SPIKE_DIR / "poc-output" / "library"

# The wrist and the middle knuckle carry where the palm is. The index and
# little knuckles carry how it is rolled. The thumb is the most distal and the
# least certain, so it is only a tie breaker.
CONTACT_WEIGHT = {
    "wrist": 6.0,
    "middle1": 6.0,
    "index1": 3.0,
    "pinky1": 3.0,
    "thumb1": 1.0,
}
# Forearm pronation seeds, in radians, spanning the limit range.
#
# One solve from the rest pose is not enough. The hand has to roll a long way
# from rest to face a ball, Gauss-Newton is local, and from rest it rolled the
# wrong way round and jammed against the pronation limit with the palm facing
# away. Solving from several starting twists and keeping the best costs about
# 20 ms and removes the failure entirely.
TWIST_SEEDS = (-2.0, -1.0, 0.0, 1.0)
# The elbow pole, stronger than the movement solver's 0.35.
#
# The possession model folds the arm much further than hand keys ever did,
# because the ball comes all the way to the chest, and a folded arm has two
# answers: elbow up or elbow down. At 0.35 the solver sat in the elbow up
# answer and dropped out of it, swinging the shoulder 58 degrees in one frame
# and leaving the palm 13 cm off the ball. Swept across the whole library, 0.8
# brings the worst palm gap to 0.05 cm. Higher starts to overpower the grip
# again: 1.5 puts it back to 9.8 cm.
CONTACT_POLE_WEIGHT = 0.8
# Where the elbow is pushed, in centimetres, on the reference athlete.
#
# The movement solver's 5 out and 11 down tucked the elbows into the ribs: the
# shoulders are 38.6 cm apart and the elbows came out 17.5 cm apart, 12 cm
# inboard of each shoulder. The manual's own photographs show them out and up.
# Swept across the library, 16 out and 6 down opens them to 27.3 cm and also
# quietens the two drills that were already rough, from 36 to 21.
#
# It does not reach the 38.6 cm the photographs show. Pushing the pole further,
# or up rather than down, gets the width but costs the movement: at 22 out and
# 6 up the elbows are 45 cm apart and the worst spike on a clean drill goes
# from 2.1 to 11.3. A point target on the elbow is a tie breaker, and the right
# instrument for holding the elbows up is a term on the upper arm's
# orientation, which is engine work rather than a constant.
ELBOW_POLE_OUT_CM = 16.0
ELBOW_POLE_DOWN_CM = 6.0
# Where the upper arm points, as a direction rather than as a place.
#
# The pole above is a point target on the elbow, and a point target cannot hold
# an upper arm up. It pulls the elbow's position while the reach pulls the hand,
# so the two argue and the elbow settles wherever the heavier weight puts it.
# Swept across the library it opened the elbows to 27.3 cm against the 38.6 cm
# the manual's photographs show, and pushing it further bought the width by
# wrecking the movement: at 22 out and 6 up the worst spike on a clean drill
# went from 2.1 to 11.3.
#
# An aim term asks only for a direction, so it shapes the arm without arguing
# about where the hand has to be. These are the components of that direction in
# the trunk frame: out to the athlete's side, and down.
UPPER_ARM_AIM_OUT = 0.55
UPPER_ARM_AIM_DOWN = 0.84
UPPER_ARM_AIM_WEIGHT = 2.0
# The upper arm's own axis, in the shoulder's local frame, pointing at the
# elbow. Measured on the rest skeleton as (1, -0.0018, 0) on the left and its
# mirror on the right, so plus or minus X to four decimal places.
# `test_upper_arm_axis_is_local_x` guards this against a model change.
UPPER_ARM_LOCAL_AXIS = (1.0, 0.0, 0.0)
# The arm the pole offsets were measured on. Everything absolute in this file
# is relative to this body and has to be scaled to any other.
REFERENCE_ARM_CM = 52.68
# The fingertips are frozen straight, so a flat hand cannot wrap a sphere. This
# is how far the tips are allowed to be off the surface before it is reported.
TIP_TOLERANCE_CM = 6.0


def solver_options() -> solver2.GaussNewtonSolverOptions:
    options = solver2.GaussNewtonSolverOptions()
    options.do_line_search = True
    options.max_iterations = 30
    options.min_iterations = 4
    return options


def contact_constraints(
    character,
    index: dict[str, int],
    placed,
    shapes: dict,
    ball_centre_cm,
    radius_cm: float,
    spread_degrees: float,
    sides: tuple[str, ...],
) -> tuple[solver2.PositionErrorFunction, dict]:
    """Return the position errors that put these hands on this ball.

    ``ball_centre_cm`` may be one position or one per hand. A drill where the
    second hand joins later needs the second: the hand that has the ball is on
    the ball, and the one still coming is shaped around the point it is moving
    toward. Leaving that hand unconstrained instead let the free arm wander,
    and it snapped 114 degrees at the elbow on the frame it joined.

    The grip geometry always uses every hand the drill will end up putting on
    the ball, so a hand does not change where on the ball it belongs at the
    moment the other one arrives.
    """
    shoulders = np.mean([placed.shoulders[side] for side in ("l", "r")], axis=0)
    if not isinstance(ball_centre_cm, dict):
        ball_centre_cm = {side: ball_centre_cm for side in sides}

    found = {}
    for side in sides:
        centre = np.asarray(ball_centre_cm[side], dtype=np.float64)
        found[side] = contacts(
            ball_centre=centre,
            radius_cm=radius_cm,
            toward_catcher=shoulders - centre,
            up=np.asarray(WORLD_UP, dtype=np.float64),
            spread_degrees=spread_degrees,
            sides=sides,
        )[side]
    targets = grip_targets(shapes, found)

    error = solver2.PositionErrorFunction(character, weight=1.0)
    for joint, target in targets.items():
        weight = CONTACT_WEIGHT[joint.split("_", 1)[1]]
        error.add_constraint(
            index[joint],
            target=np.asarray(target, dtype=np.float32),
            offset=np.zeros(3, dtype=np.float32),
            weight=weight,
        )
    return error, found


def trunk_constraints(
    character, index: dict[str, int], placed, hand_targets: dict
) -> solver2.PositionErrorFunction:
    """Hold the trunk exactly as the movement solver does."""
    error = solver2.PositionErrorFunction(character, weight=1.0)
    scapula = scapula_targets(placed, hand_targets)
    for joint, target, weight in (
        ("root", placed.root, TRUNK_WEIGHT),
        ("c_spine3", placed.chest, TRUNK_WEIGHT),
        ("c_neck", placed.neck, TRUNK_WEIGHT * 0.6),
        ("l_uparm", scapula.get("l", placed.shoulders["l"]), SCAPULA_WEIGHT),
        ("r_uparm", scapula.get("r", placed.shoulders["r"]), SCAPULA_WEIGHT),
    ):
        error.add_constraint(
            index[joint],
            target=np.asarray(target, dtype=np.float32),
            offset=np.zeros(3, dtype=np.float32),
            weight=weight,
        )
    return error


def foot_constraints(
    character, index: dict[str, int], targets: dict
) -> solver2.PositionErrorFunction:
    """Pin the feet where the movement puts them.

    This used to pin them at their rest position and never read the movement,
    so under the possession model a drill that runs and jumps kept both feet
    on the spot. It takes the targets now, from the same function the movement
    solver uses.
    """
    error = solver2.PositionErrorFunction(character, weight=1.0)
    for joint, target in targets.items():
        error.add_constraint(
            index[joint],
            target=np.asarray(target, dtype=np.float32),
            offset=np.zeros(3, dtype=np.float32),
            weight=FOOT_WEIGHT,
        )
    return error


def elbow_poles(
    character,
    index: dict[str, int],
    placed,
    targets: dict,
    reach_cm: float,
    sides: tuple[str, ...],
) -> solver2.PositionErrorFunction:
    """The same tie breaker the movement solver uses, aimed at the palm."""
    error = solver2.PositionErrorFunction(character, weight=1.0)
    for side in sides:
        sign = 1.0 if side == "l" else -1.0
        shoulder = placed.shoulders[side]
        hand = np.asarray(targets[f"{side}_wrist"], dtype=np.float64)
        midpoint = (shoulder + hand) / 2.0
        span = float(np.linalg.norm(hand - shoulder))
        slack = max(0.0, min(1.0, 1.0 - span / max(reach_cm, 1e-6)))
        if slack <= 0.0:
            continue
        # Down and out relative to the athlete, not to the world. On the
        # only drill in the library with a large authored turn, a world aligned
        # pole pushes the elbow across her body instead of away from it.
        # Scaled by the athlete's own arm. These were absolute centimetres
        # measured on the reference body, so on a shorter arm the same pole was
        # a proportionally harder pull and the elbow came out at a different
        # angle for the same movement.
        pole = midpoint + slack * (reach_cm / REFERENCE_ARM_CM) * (
            placed.rotation
            @ np.array([sign * ELBOW_POLE_OUT_CM, -ELBOW_POLE_DOWN_CM, 0.0])
        )
        error.add_constraint(
            index[f"{side}_lowarm"],
            target=np.asarray(pole, dtype=np.float32),
            offset=np.zeros(3, dtype=np.float32),
            weight=CONTACT_POLE_WEIGHT * slack,
        )
    return error


def upper_arm_aim(
    character,
    index: dict[str, int],
    placed,
    targets: dict,
    reach_cm: float,
    sides: tuple[str, ...],
    width: float = 1.0,
):
    """Ask each upper arm to point out and down, without moving the hand.

    This is the instrument the elbow pole could not be. The pole says "the
    elbow belongs here" and the grip says "the hand belongs there", and one of
    them loses. This says "the upper arm points this way" and leaves the
    forearm to reach, which is how a person holds a ball away from their chest.

    It is deliberately not faded out as the arm straightens, which is the one
    thing that made the first attempt useless. The pole fades because a point
    target argues with the reach, so near full extension it has to yield. This
    does not argue with the reach, and at contact the arms sit at 0.69 to 0.90
    of full extension across the library, so a fade would switch the term off
    at precisely the moment the manual's photographs show the elbows widest.
    """
    error = solver2.AimDirErrorFunction(character, weight=1.0)
    for side in sides:
        sign = 1.0 if side == "l" else -1.0
        shoulder = placed.shoulders[side]
        # `width` is the technique's own, so a chest catch can fold the
        # elbows in where a snatch spreads them.
        wanted = np.array(
            [sign * UPPER_ARM_AIM_OUT * width, -UPPER_ARM_AIM_DOWN, 0.0]
        )
        wanted = wanted / float(np.linalg.norm(wanted))
        # Out and down in the athlete's frame, not the world's, so a drill that
        # turns keeps its elbows beside her rather than beside the court.
        target = shoulder + reach_cm * (placed.rotation @ wanted)
        error.add_constraint(
            local_point=np.zeros(3, dtype=np.float32),
            local_dir=np.asarray(
                [sign * axis for axis in UPPER_ARM_LOCAL_AXIS],
                dtype=np.float32,
            ),
            global_target=np.asarray(target, dtype=np.float32),
            parent=index[f"{side}_uparm"],
            weight=UPPER_ARM_AIM_WEIGHT,
        )
    return error


def contact_miss(points: np.ndarray, index: dict[str, int], targets: dict) -> float:
    """The worst distance from a carried joint to where the grip asked for it."""
    return max(
        float(np.linalg.norm(points[index[joint]] - target))
        for joint, target in targets.items()
    )


def seeds(character, rest: np.ndarray, start: np.ndarray | None):
    """Yield starting poses for the contact solve, best guess first."""
    if start is not None:
        yield np.asarray(start, dtype=np.float32)
    names = list(character.parameter_transform.names)
    twists = [
        names.index(name)
        for name in (f"{side}_lowarm_twist" for side in ("l", "r"))
        if name in names
    ]
    for value in TWIST_SEEDS:
        seed = rest.copy()
        for number in twists:
            seed[number] = value
        yield seed


def close_fingers(
    character,
    index: dict[str, int],
    posed: np.ndarray,
    ball_centre_cm: np.ndarray,
    radius_cm: float,
    sides: tuple[str, ...],
) -> np.ndarray:
    """Curl the fingers onto the ball, moving nothing above the wrist.

    Only the curl parameters of the participating hands are enabled, so the arm
    cannot move to help. Every other drill in the library keeps all 104 finger
    parameters frozen, exactly as before.
    """
    function = solver2.SkeletonSolverFunction(
        character,
        [
            wrap_constraints(character, index, ball_centre_cm, radius_cm, sides),
            solver2.LimitErrorFunction(character, weight=LIMIT_WEIGHT),
        ],
    )
    solver = solver2.GaussNewtonSolver(function, solver_options())
    frozen = np.zeros(character.parameter_transform.size, dtype=bool)
    solver.set_enabled_parameters(enable_curl(character, frozen, sides))
    closed = np.asarray(
        solver.solve(np.asarray(posed, dtype=np.float32).reshape(-1, 1)),
        dtype=np.float32,
    ).reshape(-1)
    return closed if np.all(np.isfinite(closed)) else posed


def solve_contact(
    character,
    track,
    ball,
    method,
    phase: float,
    start: np.ndarray | None = None,
    ball_centre_cm: np.ndarray | None = None,
) -> dict:
    """Solve one frame with the hands on the ball. No hand keys are read."""
    names = list(character.skeleton.joint_names)
    index = {name: number for number, name in enumerate(names)}
    count = character.parameter_transform.size
    rest = np.zeros(count, dtype=np.float32)
    rest_positions = joint_positions(character, rest)
    reach_cm = arm_length(rest_positions, index)
    shapes = {side: measure_hand(rest_positions, index, side) for side in ("l", "r")}

    placed = trunk_frame(track, phase, rest_positions, index, reach_cm)
    if ball_centre_cm is None:
        frame0 = trunk_frame(track, 0.0, rest_positions, index, reach_cm)
        anchor = stance_frame(frame0.chest, reach_cm, track.turn_at(0.0))
        ball_centre_cm = anchor.place(ball.offset_at(phase))
    radius_cm = ball.radius_cm_for(reach_cm)

    contact_error, found = contact_constraints(
        character, index, placed, shapes, ball_centre_cm, radius_cm,
        method.spread_degrees, method.sides,
    )
    targets = grip_targets(shapes, found)
    function = solver2.SkeletonSolverFunction(
        character,
        [
            contact_error,
            trunk_constraints(
                character, index, placed,
                {side: targets[f"{side}_wrist"] for side in method.sides},
            ),
            foot_constraints(
                character,
                index,
                foot_targets(track, phase, placed, rest_positions, index, reach_cm),
            ),
            elbow_poles(character, index, placed, targets, reach_cm, method.sides),
            upper_arm_aim(
                character, index, placed, targets, reach_cm, method.sides,
                method.elbow_width,
            ),
            solver2.LimitErrorFunction(character, weight=LIMIT_WEIGHT),
        ],
    )
    solver = solver2.GaussNewtonSolver(function, solver_options())
    solver.set_enabled_parameters(enabled_parameters(character))

    def run(seed: np.ndarray) -> tuple[float, np.ndarray]:
        answer = np.asarray(
            solver.solve(np.asarray(seed, dtype=np.float32).reshape(-1, 1)),
            dtype=np.float32,
        ).reshape(-1)
        # A first solve from a cold seed lands far from the answer, and the
        # second one is what converges.
        answer = np.asarray(
            solver.solve(answer.reshape(-1, 1)), dtype=np.float32
        ).reshape(-1)
        if not np.all(np.isfinite(answer)):
            return float("inf"), answer
        return contact_miss(joint_positions(character, answer), index, targets), answer

    best_miss, solved = float("inf"), None
    for seed in seeds(character, rest, start):
        miss, answer = run(seed)
        if miss < best_miss:
            best_miss, solved = miss, answer
    if solved is None:
        raise RuntimeError("the contact solve produced a pose that is not finite")

    # Then close the fingers, with the arm held exactly where it landed.
    #
    # Solving the arm and the fingers together does not work. The fingers reach
    # the ball by dragging the whole hand round it, and the grip came out 83
    # degrees wide when 90 was asked for, with the thumbs 19 cm apart instead of
    # 6. Where the hand is, is the palm's decision. The fingers only close
    # around whatever is already there.
    solved = close_fingers(
        character, index, solved, ball_centre_cm, radius_cm, method.sides
    )

    return {
        "parameters": solved,
        "contactMissCm": best_miss,
        "points": joint_positions(character, solved),
        "index": index,
        "shapes": shapes,
        "contacts": found,
        "ballCentreCm": np.asarray(ball_centre_cm, dtype=np.float64),
        "radiusCm": radius_cm,
        "targets": targets,
        "sides": method.sides,
    }


def measure_contact(result: dict) -> dict:
    """Report what the hands actually did, read back from the solved pose."""
    points = result["points"]
    index = result["index"]
    centre = result["ballCentreCm"]
    radius = result["radiusCm"]
    placed = {name: points[number] for name, number in index.items()}

    def gap(position) -> float:
        return float(np.linalg.norm(np.asarray(position) - centre)) - radius

    hands = {}
    normals = {}
    for side in result["sides"]:
        shape = result["shapes"][side]
        origin, axes = reconstruct(placed, shape)
        skin = palm_skin(origin, axes)
        normals[side] = axes[1]
        tips = {
            name: gap(origin + local @ axes) for name, local in shape.tips.items()
        }
        hands[side] = {
            "palmSkinGapCm": round(gap(skin), 3),
            "wristGapCm": round(gap(points[index[f"{side}_wrist"]]), 2),
            "thumbBaseGapCm": round(gap(points[index[f"{side}_thumb1"]]), 2),
            "fingertipGapCm": {name: round(value, 2) for name, value in tips.items()},
            "worstFingertipGapCm": round(max(tips.values()), 2),
            "targetMissCm": {
                name.split("_", 1)[1]: round(
                    float(np.linalg.norm(points[index[name]] - target)), 2
                )
                for name, target in result["targets"].items()
                if name.startswith(side + "_")
            },
        }

    report = {
        "ballCentreCm": [round(float(v), 2) for v in centre],
        "wrap": wrap_report(points, index, centre, radius, result["sides"]),
        "ballRadiusCm": round(radius, 2),
        "hands": hands,
        "worstPalmSkinGapCm": round(
            max(abs(hand["palmSkinGapCm"]) for hand in hands.values()), 3
        ),
        "ballInsideAWrist": any(hand["wristGapCm"] < 0.0 for hand in hands.values()),
    }
    if len(normals) == 2:
        cosine = float(np.dot(normals["l"], normals["r"]))
        report["palmSpreadDegrees"] = round(
            np.degrees(np.arccos(max(-1.0, min(1.0, cosine)))), 2
        )
        report["thumbTipSeparationCm"] = round(
            float(
                np.linalg.norm(
                    points[index["l_thumb3"]] - points[index["r_thumb3"]]
                )
            ),
            2,
        )
    return report


# How close a parameter has to sit to its own limit before the drill is
# described as having run out of that joint. Two percent of the range.
PINNED_FRACTION = 0.02
# The engine should say when a grip is not the one that was asked for. Anything
# further than this and the achieved spread is reported as unreachable.
SPREAD_TOLERANCE_DEGREES = 3.0


def pinned_parameters(character, parameters: np.ndarray) -> list[str]:
    """Return the joints that have run out of movement in this pose.

    When a drill cannot be performed, this is the answer a coach wants: not
    that the solver did badly, but which joint reached the end of its range.
    """
    names = list(character.parameter_transform.names)
    found = []
    for name, (low, high) in minmax_limits(character).items():
        span = high - low
        if span <= 1e-6:
            continue
        value = float(parameters[names.index(name)])
        if value - low < PINNED_FRACTION * span:
            found.append(f"{name} at its lower limit")
        elif high - value < PINNED_FRACTION * span:
            found.append(f"{name} at its upper limit")
    return sorted(found)


def joint_limit_error(character, parameters: np.ndarray) -> float:
    """The model's own limit error for this pose. Zero means inside every limit."""
    function = solver2.SkeletonSolverFunction(
        character, [solver2.LimitErrorFunction(character, weight=1.0)]
    )
    return float(function.get_error(np.asarray(parameters, dtype=np.float32)))


def main(argv: list[str]) -> int:
    wanted = argv[1:] or [
        name for name in library() if has_ball(name) and has_technique(name)
    ]
    if not wanted:
        print("no movement has both a ball trajectory and a technique yet")
        return 1

    character = load_character()
    OUTPUT.mkdir(parents=True, exist_ok=True)
    failed = 0
    for movement_id in wanted:
        track = load_motion(motion_path(movement_id))
        ball = load_ball(ball_path(movement_id))
        method = load_technique(technique_path(movement_id))
        result = solve_contact(character, track, ball, method, ball.arrival_phase)
        report = measure_contact(result)
        report["movementId"] = movement_id
        report["atPhase"] = ball.arrival_phase
        report["askedSpreadDegrees"] = method.spread_degrees
        report["jointLimitError"] = round(
            joint_limit_error(character, result["parameters"]), 6
        )
        # Only the arm matters here. A pinned ankle is a stance question.
        report["ranOutOf"] = [
            name
            for name in pinned_parameters(character, result["parameters"])
            if any(
                key in name
                for key in ("uparm", "lowarm", "elbow", "wrist", "clavicle")
            )
        ]

        print(f"\n{movement_id}  at phase {ball.arrival_phase}")
        print(f"  ball {report['ballCentreCm']}  radius {report['ballRadiusCm']} cm")
        for side, hand in report["hands"].items():
            print(
                f"  {side}: palm skin {hand['palmSkinGapCm']:+.2f} cm from the "
                f"surface, wrist {hand['wristGapCm']:+.1f}, thumb base "
                f"{hand['thumbBaseGapCm']:+.1f}, target miss "
                + " ".join(
                    f"{k} {v:.1f}" for k, v in hand["targetMissCm"].items()
                )
            )
        wrap = report["wrap"]
        for side, tips in wrap["fingertipGapCm"].items():
            print(
                f"  {side}: fingertips off the surface  "
                + "  ".join(f"{k} {v:+.1f}" for k, v in tips.items())
            )
        if "palmSpreadDegrees" in report:
            print(
                f"  palms {report['palmSpreadDegrees']:.1f} degrees apart, asked "
                f"for {method.spread_degrees:.0f}; thumb tips "
                f"{report['thumbTipSeparationCm']:.1f} cm apart"
            )
        print(f"  joint limit error {report['jointLimitError']}")
        if report["ranOutOf"]:
            print("  ran out of: " + ", ".join(report["ranOutOf"]))

        # The acceptance for milestone 2, checked rather than asserted.
        checks = {
            "palms within 1 cm of the surface": report["worstPalmSkinGapCm"] <= 1.0,
            "ball does not intersect a wrist": not report["ballInsideAWrist"],
            "joint limits clean": report["jointLimitError"] <= 0.1,
        }
        if "palmSpreadDegrees" in report:
            checks["the grip is the one that was asked for"] = (
                abs(report["palmSpreadDegrees"] - method.spread_degrees)
                <= SPREAD_TOLERANCE_DEGREES
            )
        checks["no finger is inside the ball"] = (
            report["wrap"]["deepestFingerInsideBallCm"] <= 1.0
        )
        for name, passed in checks.items():
            print(f"    {'ok  ' if passed else 'FAIL'} {name}")
        report["milestone2"] = all(checks.values())
        if not report["milestone2"]:
            failed += 1
        (OUTPUT / f"{movement_id}.contact.json").write_text(
            json.dumps(report, indent=2) + "\n", encoding="utf-8"
        )
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
