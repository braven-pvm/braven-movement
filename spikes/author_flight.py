"""Turn "the passer stands there and passes to here" into a ball file.

A flight is a parabola, not a shape, so authoring one by hand means typing
numbers that are nearly right and never checking. This solves the pass instead:
given where the passer stands, how hard she throws, and where in the worker's
arm span the ball should arrive, it works out the launch that joins the two
under gravity, samples the arc at a few keys, and reports how far the
interpolated ball strays from the real one.

That last number is the point of doing it this way. Two keys cost 2.0 cm and
five cost 0.18 cm, which is how the key count was chosen rather than guessed.

    pixi run python author_flight.py netball_two_hand_snatch_pull_in high \\
        --across 0.0 --up 0.80 --ahead 0.45
"""

from __future__ import annotations

import argparse
import json
import math
import sys
from pathlib import Path

import numpy as np

SPIKE_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(SPIKE_DIR))

from ball_track import (  # noqa: E402
    MOVEMENT_DIR,
    BallOffset,
    ball_path,
    solve_launch,
)
from motion_track import _sample, arm_length, load_motion  # noqa: E402

GRAVITY_CM = 981.0
# A drill feed. A game pass is faster, and the flight gets shorter with it.
DEFAULT_SPEED_CM = 600.0
DEFAULT_PASSER_AHEAD = 4.0
DEFAULT_RELEASE_HEIGHT_CM = 135.0
DEFAULT_ARRIVAL_PHASE = 0.55
DEFAULT_KEYS = 5
SIZE_FIVE_RADIUS_CM = 11.0


def sample_flight(
    release: np.ndarray,
    velocity: np.ndarray,
    seconds: float,
    at: float,
) -> np.ndarray:
    return np.array(
        [
            release[0] + velocity[0] * at,
            release[1] + velocity[1] * at - 0.5 * GRAVITY_CM * at * at,
            release[2] + velocity[2] * at,
        ]
    )


def spline_error_cm(
    phases: list[float],
    offsets: list[BallOffset],
    release_phase: float,
    arrival_phase: float,
    frames: int,
    arm_cm: float,
    truth,
) -> float:
    """How far the interpolated ball strays from the real arc, at worst."""
    worst = 0.0
    for frame in range(frames):
        phase = frame / (frames - 1)
        if not release_phase <= phase <= arrival_phase:
            continue
        want = truth(phase)
        got = np.array(
            [
                _sample([o.across for o in offsets], phase, phases),
                _sample([o.up for o in offsets], phase, phases),
                _sample([o.ahead for o in offsets], phase, phases),
            ]
        )
        worst = max(worst, float(np.linalg.norm(got - want)) * arm_cm)
    return worst


def author(
    movement_id: str,
    variant: str | None,
    catch: BallOffset,
    passer_ahead: float = DEFAULT_PASSER_AHEAD,
    passer_across: float = 0.0,
    release_height_cm: float = DEFAULT_RELEASE_HEIGHT_CM,
    speed_cm: float = DEFAULT_SPEED_CM,
    arrival_phase: float = DEFAULT_ARRIVAL_PHASE,
    keys: int = DEFAULT_KEYS,
    radius_cm: float = SIZE_FIVE_RADIUS_CM,
    chest_cm: np.ndarray | None = None,
    arm_cm_override: float | None = None,
    note: str = "",
) -> dict:
    """Return a ball file for one pass, as a dictionary ready to write."""
    track = load_motion(MOVEMENT_DIR / f"{movement_id}.motion.json")
    chest, arrival_chest, arm_cm = stance_of(movement_id, arrival_phase)
    if chest_cm is not None:
        chest = np.asarray(chest_cm, dtype=np.float64)
    if arm_cm_override is not None:
        arm_cm = arm_cm_override

    # The catch point is given relative to where the athlete is when she takes
    # the ball, not to where she started. On a drill that runs and jumps those
    # are half a metre apart, and an author means the first.
    catch_world = arrival_chest + np.array(
        [catch.across * arm_cm, catch.up * arm_cm, catch.ahead * arm_cm]
    )
    release_world = np.array(
        [
            chest[0] + passer_across * arm_cm,
            release_height_cm,
            chest[2] + passer_ahead * arm_cm,
        ]
    )
    seconds, velocity = solve_launch(release_world, catch_world, speed_cm)
    flight_phase = seconds * track.frames_per_second / (track.frames - 1)
    release_phase = arrival_phase - flight_phase
    if release_phase <= 0.0:
        raise ValueError(
            f"the flight takes {flight_phase:.3f} of the movement, so a pass "
            f"arriving at {arrival_phase} would have to leave before it starts"
        )

    def truth(phase: float) -> np.ndarray:
        at = (phase - release_phase) * (track.frames - 1) / track.frames_per_second
        world = sample_flight(release_world, velocity, seconds, max(0.0, at))
        return (world - chest) / arm_cm

    phases = [
        release_phase + flight_phase * step / keys for step in range(keys + 1)
    ]
    offsets = [BallOffset(*truth(phase)) for phase in phases]
    error = spline_error_cm(
        phases, offsets, release_phase, arrival_phase, track.frames, arm_cm, truth
    )

    names = ["release"] + [f"flight{n}" for n in range(1, keys)] + ["arrival"]
    peak_seconds = max(0.0, min(seconds, velocity[1] / GRAVITY_CM))
    peak = sample_flight(release_world, velocity, seconds, peak_seconds)

    return {
        "movementId": movement_id,
        "variant": variant,
        "source": "authored by author_flight.py from a passer position and a "
        "catch point in the arm span",
        "notes": note
        or "Where the ball is, and when. Positions are given in the athlete's "
        "stance frame, in fractions of her own arm length. The frame is "
        "anchored at her chest as she stands at phase 0 and does not move with "
        "her. Only the flight is authored, from release to arrival.",
        "radiusCm": round(radius_cm, 2),
        "radiusFraction": round(radius_cm / arm_cm, 4),
        "release": {"atPhase": round(release_phase, 4)},
        "arrival": {"atPhase": round(arrival_phase, 4)},
        "flight": {
            "method": "real parabola under gravity, sampled at keys",
            "passerAheadCm": round(passer_ahead * arm_cm, 1),
            "releaseHeightCm": round(release_height_cm, 1),
            "launchSpeedMetresPerSecond": round(
                float(np.linalg.norm(velocity)) / 100.0, 2
            ),
            "launchAngleDegrees": round(
                math.degrees(
                    math.atan2(
                        velocity[1],
                        math.hypot(velocity[0], velocity[2]),
                    )
                ),
                1,
            ),
            "flightSeconds": round(seconds, 3),
            "peakHeightCm": round(float(peak[1]), 1),
            "catchHeightCm": round(float(catch_world[1]), 1),
            "splineErrorCm": round(error, 3),
        },
        "keys": [
            {
                "atPhase": round(phase, 4),
                "name": name,
                "across": round(offset.across, 4),
                "up": round(offset.up, 4),
                "ahead": round(offset.ahead, 4),
            }
            for phase, name, offset in zip(phases, names, offsets)
        ],
    }


def stance_of(
    movement_id: str, arrival_phase: float = 0.0
) -> tuple[np.ndarray, np.ndarray, float]:
    """The chest at the start, the chest when the ball arrives, and the reach."""
    from movement_engine import joint_positions, load_character, trunk_frame

    character = load_character()
    names = list(character.skeleton.joint_names)
    index = {name: number for number, name in enumerate(names)}
    rest = np.zeros(character.parameter_transform.size, dtype=np.float32)
    points = joint_positions(character, rest)
    arm_cm = arm_length(points, index)
    track = load_motion(MOVEMENT_DIR / f"{movement_id}.motion.json")
    return (
        trunk_frame(track, 0.0, points, index, arm_cm).chest,
        trunk_frame(track, arrival_phase, points, index, arm_cm).chest,
        arm_cm,
    )


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("movement_id")
    parser.add_argument("variant", nargs="?", default=None)
    parser.add_argument("--across", type=float, required=True)
    parser.add_argument("--up", type=float, required=True)
    parser.add_argument("--ahead", type=float, required=True)
    parser.add_argument("--passer-ahead", type=float, default=DEFAULT_PASSER_AHEAD)
    parser.add_argument("--passer-across", type=float, default=0.0)
    parser.add_argument(
        "--release-height", type=float, default=DEFAULT_RELEASE_HEIGHT_CM
    )
    parser.add_argument("--speed", type=float, default=DEFAULT_SPEED_CM)
    parser.add_argument("--arrival", type=float, default=DEFAULT_ARRIVAL_PHASE)
    parser.add_argument("--keys", type=int, default=DEFAULT_KEYS)
    parser.add_argument("--note", default="")
    arguments = parser.parse_args(argv[1:])

    payload = author(
        movement_id=arguments.movement_id,
        variant=arguments.variant,
        catch=BallOffset(arguments.across, arguments.up, arguments.ahead),
        passer_ahead=arguments.passer_ahead,
        passer_across=arguments.passer_across,
        release_height_cm=arguments.release_height,
        speed_cm=arguments.speed,
        arrival_phase=arguments.arrival,
        keys=arguments.keys,
        note=arguments.note,
    )
    path = ball_path(arguments.movement_id, arguments.variant)
    path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    flight = payload["flight"]
    print(
        f"{path.name}: {flight['launchSpeedMetresPerSecond']} m/s at "
        f"{flight['launchAngleDegrees']} degrees, {flight['flightSeconds']} s, "
        f"peak {flight['peakHeightCm']} cm, catch {flight['catchHeightCm']} cm, "
        f"spline error {flight['splineErrorCm']} cm"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
