"""Report whether the athlete can reach the ball, frame by frame. No solving.

This is the first step of the possession model, and it is deliberately the
smallest one that can fail honestly. It answers one question per frame: is the
ball inside this athlete's reachable span? Nothing is posed, nothing is solved,
and no hand is moved toward anything.

That matters, because the answer has to be a property of the ball and the body
rather than a property of the solver. If a solve produced the answer, a solver
that stretched an arm would report success, and the engine would go on claiming
the athlete caught a ball she could not have caught.

The reachable span
------------------

A hand meets a ball at its surface, not at its centre, so the test is between
the shoulder and the nearest point of the ball:

    reachable when   near <= distance to the ball surface <= far

``far`` is the arm at full stretch, shoulder to elbow to wrist, plus the offset
from the wrist to the middle of the palm. ``near`` is the same arm folded to the
elbow limit. Both are measured on the athlete, not typed in.

The test is slightly conservative on purpose. The shoulder is taken where the
trunk holds it, so the extra few centimetres a shoulder blade contributes during
a high reach are not counted, and a ball right on the boundary reads as out of
reach rather than in it. A drill should not depend on that margin.

    pixi run python ball_reach.py
    pixi run python ball_reach.py netball_two_hand_snatch_pull_in
"""

from __future__ import annotations

import json
import math
import sys
from dataclasses import dataclass
from pathlib import Path

import numpy as np

from ball_track import BallTrack, ball_path, has_ball, load_ball, stance_frame

SPIKE_DIR = Path(__file__).resolve().parent
OUTPUT = SPIKE_DIR / "poc-output" / "library"

# The elbow does not fold past this, so the hand cannot come closer to the
# shoulder than the arm folded this far. Same source as the anatomy check in
# build_library, so the two agree about what a person can do.
ELBOW_FLEXION_LIMIT_DEGREES = 150.0
# The ball rests against the middle of the palm, not against the knuckle, so
# the reach past the wrist is half the way to the first knuckle.
PALM_CENTRE_FRACTION = 0.5


@dataclass(frozen=True)
class ReachEnvelope:
    """How far a palm can get from its own shoulder, in centimetres."""

    near_cm: float
    far_cm: float

    def holds(self, surface_distance_cm: float, diameter_cm: float) -> bool:
        """Can a palm touch a sphere whose nearest surface is this far away?"""
        return (
            surface_distance_cm <= self.far_cm
            and surface_distance_cm + diameter_cm >= self.near_cm
        )


def reach_envelope(
    upper_cm: float,
    fore_cm: float,
    palm_cm: float,
    elbow_flexion_limit_degrees: float = ELBOW_FLEXION_LIMIT_DEGREES,
) -> ReachEnvelope:
    """Return the palm's reachable shell around the shoulder.

    The far edge is the straight arm. The near edge is the arm folded to the
    elbow limit, with the palm turned back toward the shoulder.
    """
    palm_centre = palm_cm * PALM_CENTRE_FRACTION
    far = upper_cm + fore_cm + palm_centre
    # The angle between the upper arm and the forearm at full flexion. Flexion
    # is measured from straight, so the included angle is its complement.
    included = math.radians(180.0 - elbow_flexion_limit_degrees)
    folded = math.sqrt(
        upper_cm * upper_cm
        + fore_cm * fore_cm
        - 2.0 * upper_cm * fore_cm * math.cos(included)
    )
    return ReachEnvelope(near_cm=max(0.0, folded - palm_centre), far_cm=far)


@dataclass(frozen=True)
class HandReach:
    side: str
    centre_distance_cm: float
    surface_distance_cm: float
    # How much reach is left over. Negative means the ball is that far too far.
    margin_cm: float
    reachable: bool


def hand_reach(
    side: str,
    shoulder: np.ndarray,
    ball_centre_cm: np.ndarray,
    radius_cm: float,
    envelope: ReachEnvelope,
) -> HandReach:
    centre = float(np.linalg.norm(np.asarray(ball_centre_cm) - np.asarray(shoulder)))
    surface = centre - radius_cm
    return HandReach(
        side=side,
        centre_distance_cm=centre,
        surface_distance_cm=surface,
        margin_cm=envelope.far_cm - surface,
        reachable=envelope.holds(surface, 2.0 * radius_cm),
    )


def verdict(hands: dict[str, HandReach]) -> str:
    reached = sorted(side for side, hand in hands.items() if hand.reachable)
    if len(reached) == 2:
        return "both"
    if not reached:
        return "neither"
    return "left only" if reached[0] == "l" else "right only"


def first_reachable_phase(rows: list[dict]) -> float | None:
    for row in rows:
        if row["verdict"] != "neither":
            return row["phase"]
    return None


def report(character, movement_id: str) -> dict:
    """Place the ball on every frame and report the reach. Nothing is solved."""
    from motion_track import arm_length, load_motion
    from movement_engine import joint_positions, motion_path, trunk_frame

    track = load_motion(motion_path(movement_id))
    ball = load_ball(ball_path(movement_id))
    if ball.movement_id != movement_id:
        raise ValueError(
            f"{movement_id}: the ball file names movement {ball.movement_id}"
        )

    names = list(character.skeleton.joint_names)
    index = {name: position for position, name in enumerate(names)}
    rest = np.zeros(character.parameter_transform.size, dtype=np.float32)
    rest_positions = joint_positions(character, rest)
    reach_cm = arm_length(rest_positions, index)

    def segment(first: str, second: str) -> float:
        return float(
            np.linalg.norm(rest_positions[index[first]] - rest_positions[index[second]])
        )

    envelope = reach_envelope(
        upper_cm=segment("l_uparm", "l_lowarm"),
        fore_cm=segment("l_lowarm", "l_wrist"),
        palm_cm=segment("l_wrist", "l_middle1"),
    )

    # The stance frame is taken once, at phase 0, and then left alone. That is
    # what stops the ball following the athlete.
    start = trunk_frame(track, 0.0, rest_positions, index, reach_cm)
    frame = stance_frame(start.chest, reach_cm, track.turn_at(0.0))
    radius_cm = ball.radius_cm_for(reach_cm)

    rows: list[dict] = []
    for number in range(track.frames):
        phase = number / (track.frames - 1)
        placed = trunk_frame(track, phase, rest_positions, index, reach_cm)
        centre = frame.place(ball.offset_at(phase))
        hands = {
            side: hand_reach(side, placed.shoulders[side], centre, radius_cm, envelope)
            for side in ("l", "r")
        }
        rows.append(
            {
                "frame": number,
                "phase": round(phase, 4),
                "state": ball.state_at(phase),
                "ballCm": [round(float(value), 2) for value in centre],
                # Where the trunk holds each shoulder. Every distance below is
                # measured from here, so anything that draws the reach has to
                # draw it from here too.
                "shouldersCm": [
                    [round(float(value), 2) for value in placed.shoulders[side]]
                    for side in ("l", "r")
                ],
                "left": {
                    "surfaceDistanceCm": round(hands["l"].surface_distance_cm, 2),
                    "marginCm": round(hands["l"].margin_cm, 2),
                    "reachable": hands["l"].reachable,
                },
                "right": {
                    "surfaceDistanceCm": round(hands["r"].surface_distance_cm, 2),
                    "marginCm": round(hands["r"].margin_cm, 2),
                    "reachable": hands["r"].reachable,
                },
                "verdict": verdict(hands),
            }
        )

    entered = first_reachable_phase(rows)
    unreachable = [row for row in rows if row["verdict"] == "neither"]
    after_arrival = [row for row in rows if row["phase"] >= ball.arrival_phase]
    return {
        "movementId": movement_id,
        "releasePhase": ball.release_phase,
        "arrivalPhase": ball.arrival_phase,
        "ballRadiusCm": round(radius_cm, 2),
        "armLengthCm": round(reach_cm, 2),
        "reach": {
            "nearCm": round(envelope.near_cm, 2),
            "farCm": round(envelope.far_cm, 2),
            "note": (
                "palm to shoulder, measured on this athlete. The shoulder is "
                "taken where the trunk holds it, so scapular travel is not "
                "counted and the far edge is conservative."
            ),
        },
        "startsOutOfReach": bool(rows and rows[0]["verdict"] == "neither"),
        "framesOutOfReach": len(unreachable),
        "entersReachAtPhase": entered,
        "reachableFromArrival": bool(
            after_arrival and all(row["verdict"] != "neither" for row in after_arrival)
        ),
        "frames": rows,
    }


def _print(result: dict) -> None:
    print(f"\n{result['movementId']}")
    print(
        f"  ball radius {result['ballRadiusCm']} cm on a {result['armLengthCm']} cm "
        f"arm, released at phase {result['releasePhase']}, arrives at "
        f"{result['arrivalPhase']}"
    )
    print(
        f"  palm reaches {result['reach']['nearCm']} to {result['reach']['farCm']} cm "
        "from the shoulder"
    )
    print(
        "\n  frame phase  state    ball x      y      z    "
        "left margin  right margin  in reach"
    )
    for row in result["frames"]:
        x, y, z = row["ballCm"]
        print(
            f"  {row['frame']:5d} {row['phase']:5.3f}  {row['state']:<7s} "
            f"{x:7.1f} {y:6.1f} {z:6.1f}  "
            f"{row['left']['marginCm']:9.1f}    {row['right']['marginCm']:9.1f}   "
            f"{row['verdict']}"
        )
    entered = result["entersReachAtPhase"]
    print(
        f"\n  out of reach for {result['framesOutOfReach']} of "
        f"{len(result['frames'])} frames"
    )
    print(
        "  enters reach at phase "
        + ("never" if entered is None else f"{entered:.3f}")
        + f", arrival is at phase {result['arrivalPhase']:.3f}"
    )


def main(argv: list[str]) -> int:
    from movement_engine import library, load_character

    wanted = argv[1:] or [name for name in library() if has_ball(name)]
    missing = [name for name in wanted if not has_ball(name)]
    for name in missing:
        print(f"{name}: no {ball_path(name).name}, not migrated yet")
    wanted = [name for name in wanted if has_ball(name)]
    if not wanted:
        print("no ball trajectories found")
        return 1

    character = load_character()
    OUTPUT.mkdir(parents=True, exist_ok=True)
    failed = 0
    for movement_id in wanted:
        result = report(character, movement_id)
        _print(result)
        (OUTPUT / f"{movement_id}.reach.json").write_text(
            json.dumps(result, indent=2) + "\n", encoding="utf-8"
        )
        # Milestone 1 of the possession model asks for exactly this: the ball is
        # out of reach early in the flight and in reach from arrival onward.
        ok = result["startsOutOfReach"] and result["reachableFromArrival"]
        print(f"  milestone 1: {'passed' if ok else 'FAILED'}")
        if not ok:
            failed += 1
            if not result["startsOutOfReach"]:
                print("    the ball is already in reach on the first frame")
            if not result["reachableFromArrival"]:
                print("    the ball is out of reach at or after arrival")
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
