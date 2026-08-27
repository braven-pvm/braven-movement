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
# Where the elbow sits round the shoulder-to-wrist axis, in degrees. Zero is
# straight down from that axis and ninety is straight out to her side.
#
# This replaces an absolute offset of 16 cm out and 6 cm down. That offset was
# swept against ONE regime — the manual's photographs, which are a snatch AT
# CONTACT, arm at 0.85 to 0.90 of full extension — and then applied everywhere.
# It was also gated by `slack = 1 - span / reach`, so its authority GREW as the
# arm folded. The term was therefore strongest exactly where no photograph was
# taken and silent exactly where the evidence was measured, which is the
# opposite of what the pull-in cue asks for. Measured over 353 holding frames,
# elbow separation and arm extension correlated at -0.865: a 62.9 cm mean in
# the most folded band against 34.8 cm in the most extended, on a 38.6 cm
# reference.
#
# The value is READ, not chosen. It is the angle at which the SOLVED mean elbow
# separation across the library's contact frames is 38.6 cm, which is the
# manual's own figure and the same comparison PR #4 used. Found by bisecting
# the whole solve rather than by placing elbows geometrically: a kinematic
# bisection on the solved shoulders and wrists answered 22.4 degrees, and
# running that through the solver gave 34.1 cm rather than 38.6, because the
# grip, the aim term and the limits move the arm as well. Bisecting the solve
# itself gives 34.6 degrees and 38.58 cm.
#
# RE-READ at 31.3 when the waiting-distance correction landed. That correction
# changes where she stands while she waits, which changes the pose she takes
# the ball from, so the angle that reproduces 38.6 moves with it. This is the
# definition being re-applied, not a number being nudged: the angle is whatever
# puts the solved mean on the manual's figure, and when the solve changes the
# angle has to be read again.
#
# It is deliberately NOT read from the solve's own pole angle in the evidenced
# band. That spreads from -14 to +75 degrees over 16 frames, so its mean would
# be calibrating against noise.
#
# What the folded regime then does is a FINDING, not a target. No evidence says
# how wide the elbows should be with the ball at the chest, so nothing here is
# tuned to make that number anything in particular.
ELBOW_POLE_ANGLE_DEGREES = 31.3
# How much of the arm is upper arm, on this model. Needed to place the elbow on
# the circle it can actually occupy for a given shoulder and wrist, which is
# what lets the pole ask for a direction without arguing about the reach.
# Measured on the rest skeleton and guarded by `test_upper_arm_fraction`.
UPPER_ARM_FRACTION = 0.487473
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
    angle_degrees: float | None = None,
) -> solver2.PositionErrorFunction:
    """Where the elbow sits round the shoulder-to-wrist axis.

    An angle rather than an offset, for one reason that decides everything
    else: rotating the elbow about that axis moves neither the shoulder nor the
    wrist. So this cannot argue with the reach, and the slack gate the old
    offset needed — which had to yield near full extension because a point
    target argues with the hand — is not merely removed, it has nothing left
    to do.

    THE TARGET IS NOT ALWAYS EXACTLY ON THE ELBOW CIRCLE, AND AN EARLIER
    VERSION OF THIS COMMENT SAID IT WAS. `out` and `down` below are each
    projected off the reach axis, but they are never orthogonalised against
    EACH OTHER, so on an oblique reach they are not perpendicular and
    `down * cos + out * sin` is not a unit vector. Measured across a spread of
    reach directions, the target lands up to 10.2 cm off the circle, worst
    where the hand is nearly below the shoulder and `out . down` reaches
    -0.963. On that family the term does argue with the reach a little, which
    is the very thing the paragraph above claims it cannot.

    What survives is the calibration, because 34.6 degrees was bisected
    through the whole solve rather than derived from the geometry, so it
    absorbs whatever the basis actually does. What does NOT survive is the
    stated property. `test_the_target_is_on_the_elbow_circle_where_the_basis_
    is_orthogonal` is the real guard, and its name says how far it reaches:
    it exercises reaches along one axis family, and that is exactly where the
    flaw disappears.

    An orthonormal basis by Gram-Schmidt, and re-reading the angle afterwards,
    is filed as follow-up. It would move figures again, so it waits.

    The geometry also retires the gate's other job for free. As the arm
    straightens, `off` goes to zero and every angle names the same point, so
    the term fades where it should without anything switching it off.
    """
    angle = (
        ELBOW_POLE_ANGLE_DEGREES if angle_degrees is None else float(angle_degrees)
    )
    turn = np.radians(angle)
    upper = UPPER_ARM_FRACTION * reach_cm
    fore = reach_cm - upper
    error = solver2.PositionErrorFunction(character, weight=1.0)
    for side in sides:
        sign = 1.0 if side == "l" else -1.0
        shoulder = np.asarray(placed.shoulders[side], dtype=np.float64)
        hand = np.asarray(targets[f"{side}_wrist"], dtype=np.float64)
        axis = hand - shoulder
        span = float(np.linalg.norm(axis))
        # A straight arm has no elbow circle, and a target beyond her reach has
        # no triangle at all. Both are silence rather than a guess.
        if span < 1e-6 or span >= upper + fore:
            continue
        axis = axis / span
        along = (upper * upper - fore * fore + span * span) / (2.0 * span)
        off_squared = upper * upper - along * along
        if off_squared <= 1e-9:
            continue
        off = float(off_squared ** 0.5)
        # Out and down relative to the athlete, not to the world. On the only
        # drill in the library with a large authored turn, a world aligned pole
        # pushes the elbow across her body instead of away from it.
        out = placed.rotation @ np.array([sign, 0.0, 0.0])
        out = out - np.dot(out, axis) * axis
        down = placed.rotation @ np.array([0.0, -1.0, 0.0])
        down = down - np.dot(down, axis) * axis
        if np.linalg.norm(out) < 1e-6 or np.linalg.norm(down) < 1e-6:
            continue
        out = out / np.linalg.norm(out)
        down = down / np.linalg.norm(down)
        pole = shoulder + axis * along + off * (
            down * np.cos(turn) + out * np.sin(turn)
        )
        error.add_constraint(
            index[f"{side}_lowarm"],
            target=np.asarray(pole, dtype=np.float32),
            offset=np.zeros(3, dtype=np.float32),
            weight=CONTACT_POLE_WEIGHT,
        )
    return error


def upper_arm_aim(
    character,
    index: dict[str, int],
    placed,
    targets: dict,
    reach_cm: float,
    sides: tuple[str, ...],
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
        # No technique dial here any more. `elbowWidth` used to scale this
        # vector, and a weight sweep from 2.0 down to 0.0 moved folded elbow
        # separation by 0.2 cm, so the dial named for the folded case was
        # attached to a term that does not control it. It now sets the pole
        # angle, in degrees. This term keeps the one job it is good at:
        # holding the upper arm up.
        wanted = np.array([sign * UPPER_ARM_AIM_OUT, -UPPER_ARM_AIM_DOWN, 0.0])
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
            elbow_poles(
                character, index, placed, targets, reach_cm, method.sides,
                method.elbow_angle_degrees,
            ),
            upper_arm_aim(
                character, index, placed, targets, reach_cm, method.sides
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
