"""Does the ball move during the carry, and in which frame of reference.

    cd spikes
    pixi run --frozen -- python -B ../scripts/carry_path.py

WHY THIS EXISTS. The release-timing unit rests on where the pre-release hand
speed comes from. Two readings were offered and they disagree:

  - "the hand follows the AUTHORED CARRY PATH in the drill's .ball.json keys"
  - "the wrist is constrained to a STATIONARY authored point for the whole
    carry"

Both are testable and this measures them. Two quantities per frame:

  authored   `ball.offset_at(phase)`, THE ENGINE'S OWN offset, in arm lengths.
             This is the quantity the question is about.
  world      the ball centre's own displacement, in centimetres.

A SHOULDER-MIDPOINT PROXY WAS TRIED FIRST AND IT IS WRONG. It reported the ball
moving 0.28 cm per frame relative to the body and appeared to refute a
body-fixed offset. It does not: the engine places the carried ball in the
ATHLETE'S frame, which is anchored at the chest and carries her orientation,
and the shoulder midpoint is a different origin that moves differently when the
trunk turns. One phrase, two origins, which is the fault this ledger records
most often. The offset is read from the engine here instead.

Nothing here writes to `spikes/movements/`. Gate 4 is untouched.
"""
import sys
from pathlib import Path

SPIKES = Path(__file__).resolve().parents[1] / "spikes"
if str(SPIKES) not in sys.path:
    sys.path.insert(0, str(SPIKES))

import numpy as np  # noqa: E402
from ball_track import ball_path, load_ball  # noqa: E402
from movement_engine import load_character  # noqa: E402
from possession_solve import solve_movement  # noqa: E402

PASSES = (
    "netball_chest_pass",
    "netball_overhead_pass",
    "netball_bounce_pass",
    "netball_one_hand_high_pass",
)
CARRY_FRAMES_SHOWN = 6


def authored_offsets(movement_id: str, phases) -> list:
    """The engine's own authored offset at each phase, not a rebuild of it."""
    ball = load_ball(ball_path(movement_id))
    return [ball.offset_at(phase) for phase in phases]


def main() -> int:
    character = load_character()
    print("    THE BALL DURING THE CARRY, cm per frame")
    print()
    print(f"    {'drill':22s} {'held':>5s} {'world mean':>11s} "
          f"{'world max':>10s} {'authored offsets seen':>23s}")
    for movement_id in PASSES:
        result = solve_movement(character, movement_id)
        index, points = result["index"], result["points"]
        frames = result["possession"].frames
        held = [n for n, frame in enumerate(frames) if frame.holding]
        world = []
        for earlier, later in zip(held, held[1:]):
            if later != earlier + 1:
                continue
            one = np.asarray(frames[earlier].centre, dtype=float)
            two = np.asarray(frames[later].centre, dtype=float)
            world.append(float(np.linalg.norm(two - one)))
        offsets = authored_offsets(
            movement_id, [frames[n].phase for n in held]
        )
        distinct = {
            (round(o.across, 6), round(o.up, 6), round(o.ahead, 6))
            for o in offsets
        }
        print(f"    {movement_id.replace('netball_', ''):22s} {len(held):5d} "
              f"{np.mean(world):11.4f} {max(world):10.4f} "
              f"{len(distinct):23d}")

    print()
    print("    THE LAST CARRY FRAMES OF THE CHEST PASS, so the pattern is")
    print("    visible rather than summarised")
    print()
    result = solve_movement(character, PASSES[0])
    index, points = result["index"], result["points"]
    frames = result["possession"].frames
    held = [n for n, frame in enumerate(frames) if frame.holding]
    ball = load_ball(ball_path(PASSES[0]))
    print(f"    {'frame':>6s} {'ball world x/y/z':>28s} "
          f"{'the AUTHORED offset':>27s}")
    for number in held[-CARRY_FRAMES_SHOWN:]:
        centre = np.asarray(frames[number].centre, dtype=float)
        o = ball.offset_at(frames[number].phase)
        print(f"    {number:6d} "
              f"{centre[0]:9.3f}{centre[1]:9.3f}{centre[2]:9.3f}   "
              f"{o.across:9.4f}{o.up:9.4f}{o.ahead:9.4f}")
    print()
    print("    ONE AUTHORED OFFSET, HELD FOR EVERY CARRY FRAME, WHILE THE BALL")
    print("    MOVES IN THE WORLD. So the ball is pinned to the athlete and")
    print("    every centimetre it travels before the release is HER motion.")
    print("    There is no authored carry path to retime: there is one triple.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
