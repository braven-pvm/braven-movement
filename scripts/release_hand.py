"""Every figure in section 1 of `docs/RELEASE_HAND_PAPER.md`.

    cd spikes
    pixi run --frozen -- python -B ../scripts/release_hand.py

WHAT IT MEASURES, and the convention for each, because an angle without its
convention is not a number:

  wrist   the angle elbow-wrist-knuckle. 180 is a straight line from the elbow
          through the wrist to the middle knuckle; less is flexion.
  finger  the angle wrist-knuckle-tip at the middle finger. 180 is a straight
          finger; less is a wrapped one.
  speed   the wrist joint's own speed in centimetres per second, from the frame
          step and the track's own frame rate.

IT READS THE SOLVE AND NOT A RECEIPT, because the receipt carries neither of
these angles: they are the measures the paper proposes and do not exist yet.

NOTHING UNDER `spikes/movements/` IS OPENED FOR WRITING. This script only
solves and reads.
"""
import sys
from pathlib import Path

SPIKES = Path(__file__).resolve().parents[1] / "spikes"
if str(SPIKES) not in sys.path:
    sys.path.insert(0, str(SPIKES))

import numpy as np  # noqa: E402
from movement_definition import load  # noqa: E402
from movement_engine import MOVEMENT_DIR, load_character  # noqa: E402
from possession_solve import solve_movement  # noqa: E402

CLOSE_UP = "netball_chest_pass"
PASSES = (
    "netball_chest_pass",
    "netball_overhead_pass",
    "netball_bounce_pass",
    "netball_one_hand_high_pass",
)
# The last frames of contact, over which the paper reads the hand's speed.
CONTACT_FRAMES = 8
DIGITS = ("_thumb", "_index", "_middle", "_ring", "_pinky")


def angle_at(first, middle, last) -> float:
    one, two = first - middle, last - middle
    cosine = float(np.dot(one, two) / (np.linalg.norm(one) * np.linalg.norm(two)))
    return float(np.degrees(np.arccos(np.clip(cosine, -1.0, 1.0))))


def working_side(result, release: int) -> str:
    """The hand that held the ball last. Not assumed to be the left."""
    sides = result["possession"].frames[release - 1].sides
    return sorted(sides)[0] if len(sides) == 1 else "l"


def release_frame(result) -> int:
    frames = result["possession"].frames
    return min(n for n, frame in enumerate(frames) if not frame.holding)


def close_up(character) -> None:
    result = solve_movement(character, CLOSE_UP)
    index, points = result["index"], result["points"]
    frames = result["possession"].frames
    rate = float(result["track"].frames_per_second)
    radius = float(result["radiusCm"])
    release = release_frame(result)
    side = working_side(result, release)
    definition = load(MOVEMENT_DIR / f"{CLOSE_UP}.json")
    last = len(points) - 1
    named = {round(p.at_phase * last): p.name for p in definition.phases}

    print(f"    {CLOSE_UP}: {len(points)} frames at {rate:g} fps, ball radius "
          f"{radius:g} cm, releases at frame {release}, working hand {side!r}")
    print(f"    phases: " + ", ".join(
        f"{name} {frame}" for frame, name in sorted(named.items())))
    print()
    print(f"    {'f':>3s} {'phase':9s} {'state':9s} {'wrist':>7s} "
          f"{'finger':>7s} {'cm/s':>7s} {'nearest digit to the centre':>29s}")

    previous = None
    for number, pose in enumerate(points):
        wrist = pose[index[f"{side}_wrist"]]
        speed = (
            0.0 if previous is None
            else float(np.linalg.norm(wrist - previous)) * rate
        )
        previous = wrist
        if not release - CONTACT_FRAMES <= number <= release + 2:
            continue
        digits = {
            name: float(np.linalg.norm(np.asarray(frames[number].centre) - pose[joint]))
            for name, joint in index.items()
            if name.startswith(side + "_")
            and any(digit in name for digit in DIGITS)
        }
        nearest = min(digits, key=digits.get)
        inside = " INSIDE" if digits[nearest] < radius else ""
        print(f"    {number:3d} {named.get(number, ''):9s} "
              f"{frames[number].state:9s} "
              f"{angle_at(pose[index[f'{side}_lowarm']], wrist, pose[index[f'{side}_middle1']]):7.2f} "
              f"{angle_at(wrist, pose[index[f'{side}_middle1']], pose[index[f'{side}_middle3']]):7.2f} "
              f"{speed:7.1f}   {nearest:16s} {digits[nearest]:6.2f}{inside}")


def hand_against_ball(character) -> None:
    print()
    print(f"    THE HAND AGAINST THE BALL IT RELEASES, over the last "
          f"{CONTACT_FRAMES} contact frames")
    print(f"    {'drill':32s} {'release':>7s} {'hand cm/s':>18s} "
          f"{'ball cm/s':>10s} {'ratio':>7s}   "
          f"the same wrist in the athlete's units")
    for movement_id in PASSES:
        result = solve_movement(character, movement_id)
        index, points = result["index"], result["points"]
        frames = result["possession"].frames
        rate = float(result["track"].frames_per_second)
        release = release_frame(result)
        side = working_side(result, release)
        joint = index[f"{side}_wrist"]
        hand = [
            float(np.linalg.norm(points[n][joint] - points[n - 1][joint])) * rate
            for n in range(release - CONTACT_FRAMES, release)
        ]
        ball = [
            float(np.linalg.norm(
                np.asarray(frames[n].centre) - np.asarray(frames[n - 1].centre)
            )) * rate
            for n in range(release + 1, release + 4)
        ]
        flight = sum(ball) / len(ball)
        print(f"    {movement_id.replace('netball_', ''):32s} {release:7d} "
              f"{min(hand):7.1f} to {max(hand):6.1f} {flight:10.1f} "
              f"{flight / max(hand):6.1f}x   "
              f"wrist {min(hand) / 100:.2f} to {max(hand) / 100:.2f} m/s")
    print()
    print("    The ball's speed is AUTHORED (author_flight.DEFAULT_SPEED_CM),")
    print("    not imparted, so the ratio is not a defect in the hand: it is a")
    print("    statement that the two are not connected.")


def main() -> int:
    character = load_character()
    close_up(character)
    hand_against_ball(character)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
