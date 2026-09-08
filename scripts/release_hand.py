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
from clip_geometry import athlete_frame, read_ball  # noqa: E402
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
# The frames after release, over which the paper reads what the hand does next.
FOLLOW_FRAMES = 4
# The arm the video lane converted the clip's arm-length channel with, metres.
ATHLETE_ARM_M = 0.77
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


def wrist_angle(pose, index, side: str) -> float:
    return angle_at(pose[index[f"{side}_lowarm"]], pose[index[f"{side}_wrist"]],
                    pose[index[f"{side}_middle1"]])


def finger_angle(pose, index, side: str) -> float:
    return angle_at(pose[index[f"{side}_wrist"]], pose[index[f"{side}_middle1"]],
                    pose[index[f"{side}_middle3"]])


def hand_travel(character) -> None:
    """How far the wrist and the finger actually travel, on all four passes.

    FOR THE CONTRACT LANE'S SIXTH QUESTION. A hand channel has to be sized by
    what the hand does, and section 1 measured only the chest pass. Reported as
    the first value, the last value and the span, because a span alone cannot
    say whether the hand opened or closed.
    """
    print()
    print("    WRIST AND FINGER TRAVEL, all four passes, from the solve")
    print(f"    {'drill':22s} {'side':4s} "
          f"{'wrist, last 8 held frames':>30s} "
          f"{'wrist, 4 frames after':>30s} "
          f"{'finger, before -> at release':>30s}")
    for movement_id in PASSES:
        result = solve_movement(character, movement_id)
        index, points = result["index"], result["points"]
        release = release_frame(result)
        side = working_side(result, release)
        last = len(points) - 1

        held = [wrist_angle(points[n], index, side)
                for n in range(max(0, release - CONTACT_FRAMES), release)]
        after = [wrist_angle(points[n], index, side)
                 for n in range(release, min(last, release + FOLLOW_FRAMES) + 1)]
        before_finger = finger_angle(points[release - 1], index, side)
        at_finger = finger_angle(points[release], index, side)

        print(f"    {movement_id.replace('netball_', ''):22s} {side:4s} "
              f"{held[0]:8.2f} to {held[-1]:7.2f} span {max(held) - min(held):5.2f}  "
              f"{after[0]:8.2f} to {after[-1]:7.2f} span {max(after) - min(after):5.2f}  "
              f"{before_finger:9.2f} to {at_finger:8.2f} "
              f"span {abs(at_finger - before_finger):5.2f}")
    print()
    print("    A span is a MAXIMUM MINUS A MINIMUM inside the window, so it can")
    print("    exceed the first-to-last difference when the angle turns around.")


def clip_units(character) -> None:
    """Why this lane's metres and the video lane's are not the same metres.

    The clip does not carry the ball in metres. `clip_geometry.read_ball`
    carries it FROM THE SHOULDER MIDPOINT AND IN ARM LENGTHS, and it recomputes
    the divisor every frame from that frame's own left arm. So one ball has
    three speeds and they are not interchangeable:

      world      the ball centre's own displacement.
      shoulder   the same ball measured from the moving shoulder midpoint,
                 which is the quantity the clip channel actually carries.
      athlete    that channel converted with a HUMAN arm of 0.77 m, which is
                 what the video lane published.

    This prints all three so the two lanes' figures can be compared as the same
    quantity or not at all.
    """
    result = solve_movement(character, CLOSE_UP)
    index, points = result["index"], result["points"]
    frames = result["possession"].frames
    rate = float(result["track"].frames_per_second)
    release = release_frame(result)
    axes = athlete_frame(points[0], index)

    def arm_cm(n: int) -> float:
        pose = points[n]
        shoulder, elbow = pose[index["l_uparm"]], pose[index["l_lowarm"]]
        return float(np.linalg.norm(elbow - shoulder)) + float(
            np.linalg.norm(pose[index["l_wrist"]] - elbow))

    offsets = [
        np.asarray(read_ball(points[n], index, frames[n], axes)[:3], dtype=float)
        for n in range(len(points))
    ]

    print()
    print(f"    THE SAME BALL IN THREE UNITS, {CLOSE_UP}, release at {release}")
    print(f"    {'step':>9s} {'arm cm':>7s} {'world m/s':>10s} "
          f"{'shoulder m/s':>13s} {'arm len/s':>10s} {'x 0.77 m':>9s}")
    for n in range(release - 1, min(len(points) - 1, release + 2)):
        world = float(np.linalg.norm(
            np.asarray(frames[n + 1].centre) - np.asarray(frames[n].centre))) * rate
        channel = float(np.linalg.norm(offsets[n + 1] - offsets[n])) * rate
        shoulder = channel * arm_cm(n + 1) / 100.0
        print(f"    {n:4d}->{n + 1:<4d} {arm_cm(n):7.2f} {world / 100:10.2f} "
              f"{shoulder:13.2f} {channel:10.3f} {channel * ATHLETE_ARM_M:9.2f}")
    print()
    print(f"    the engine's own arm at release: {arm_cm(release):.2f} cm, so a")
    print(f"    channel converted with {ATHLETE_ARM_M} m is inflated by "
          f"{ATHLETE_ARM_M / (arm_cm(release) / 100.0):.3f}x")


def across_release(character) -> None:
    """The wrist's speed on BOTH sides of the release, both hands.

    THE CORRECTION THAT PROMPTED THIS. An earlier reading of this paper compared
    the engine's hand with the filmed athlete's using the frames BEFORE release
    only, and concluded the engine's arm is slow. `docs/KNOWN_ISSUES.md` already
    recorded, under "The hands are not already moving", that the wrist multiplies
    its speed in the single frame AFTER release. Both readings are in the same
    solve and the paper had printed the second one without reading it.

    Speed into frame n is |p[n] - p[n-1]| * fps, so the column headed `rel`
    is the last motion while the ball is still held and `rel+1` is the first
    motion after it has gone.
    """
    print()
    print("    THE WRIST ACROSS THE RELEASE, both hands, cm/s")
    print(f"    {'drill':22s} {'side':4s} {'rel-2':>7s} {'rel-1':>7s} "
          f"{'rel':>7s} | {'rel+1':>8s} {'rel+2':>8s} {'rel+3':>8s} "
          f"{'step':>6s} {'peak m/s':>9s}")
    for movement_id in PASSES:
        result = solve_movement(character, movement_id)
        index, points = result["index"], result["points"]
        rate = float(result["track"].frames_per_second)
        release = release_frame(result)
        last = len(points) - 1

        for side in ("l", "r"):
            joint = index[f"{side}_wrist"]

            def speed(n: int) -> float:
                if n <= 0 or n > last:
                    return float("nan")
                step = points[n][joint] - points[n - 1][joint]
                return float(np.linalg.norm(step)) * rate

            held = speed(release)
            after = speed(release + 1)
            # FROM THE RELEASE FRAME, not from the one after it. An earlier
            # version started at release + 1 and reported 3.49 m/s for
            # one_hand_high_pass, whose wrist actually peaks at 5.61 in the
            # release frame itself. The one drill that behaves differently was
            # the one the window excluded.
            peak = max(
                speed(n) for n in range(release, min(last, release + 6) + 1)
            )
            print(f"    {movement_id.replace('netball_', ''):22s} {side:4s} "
                  f"{speed(release - 2):7.1f} {speed(release - 1):7.1f} "
                  f"{held:7.1f} | {after:8.1f} {speed(release + 2):8.1f} "
                  f"{speed(release + 3):8.1f} {after / held:5.1f}x "
                  f"{peak / 100:9.2f}")
    print()
    print("    `step` is the frame after the release over the frame before it.")
    print("    `peak m/s` is the fastest from the release frame through the six after it.")
    print("    THE ATHLETE'S BAND IS 2.5 TO 5.4 m/s ACROSS BOTH SCALES.")


def main() -> int:
    character = load_character()
    close_up(character)
    hand_against_ball(character)
    hand_travel(character)
    across_release(character)
    clip_units(character)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
