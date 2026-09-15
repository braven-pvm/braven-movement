"""How big the hand must be, and how fast the camera, before a wrist flick can
be measured at all.

THE REQUIREMENT RESTS ON A MEASURED FLOOR AND ON NOTHING ELSE. On 2026-09-02
the still-arm noise of the wrist angle was measured on this footage, on the two
stretches the frame strips prove she is standing still: a median of 40, a 90th
percentile of 104 and a MAXIMUM of 197 degrees per second, on a 30 px
wrist-to-knuckle lever. That reading, and the fact that the floor scales with
the lever, is the whole derivation. Refer to "Instruction: put enough pixels on
the hands to measure a wrist" in `docs/VIDEO_CAPTURE_FINDINGS.md`.

WHAT THIS FILE REPLACES, AND WHY. On 2026-09-08 the same requirement was
derived a second way, from a landmark scatter of `e = 3.0 px`. That `e` was
WRONG: it came from taking the RANGE of the angle over a 29-frame window,
max minus min, and spending it in a formula that wants a one-sigma scatter. It
inflated `e` by about four. The window was not still either — the forearm grows
39 per cent in pixels inside it, because she is raising the arm. Every figure
built on that `e` is withdrawn. The scatter is still REPORTED below, measured
properly and named as a RANGE, and it derives nothing.

THE SCATTER IS AN OBSERVATION, NOT AN INPUT. `scatter_rows()` needs the
keypoint files, so it is absent on a machine that does not carry them, and the
requirement must not depend on it. `requirement()` never calls it, and a test
proves that by making the scatter raise and asking for the requirement anyway.

A THIRD REQUIREMENT IS NOT ABOUT PIXELS AT ALL: a movement needs SAMPLES. Four
across the flick is 40 fps for 100 ms and 80 fps for 50 ms. Both cameras of
2026-08-28 ran at 30.

    pixi run --frozen python -B video_flick_requirement.py
"""

from __future__ import annotations

import math
import statistics
import sys
from pathlib import Path
from typing import NamedTuple

import video_hand_speed as speed

SPIKE_DIR = Path(__file__).resolve().parent
FINDINGS = SPIKE_DIR.parent / "docs" / "VIDEO_CAPTURE_FINDINGS.md"

DEGREES_PER_RADIAN = 180.0 / math.pi


class Floor(NamedTuple):
    """The 2026-09-02 reading. Every field was MEASURED on this footage."""

    leverPixels: float
    median: float
    p90: float
    maximum: float


MEASURED_FLOOR = Floor(30.0, 40.0, 104.0, 197.0)

# How many times a flick must clear the floor before it is called measurable.
MARGIN = 3.0
# How many samples a movement needs before a rise and a fall can be seen.
SAMPLES_WANTED = 4
# What the recordings of 2026-08-28 were shot at.
SHOT_AT_FPS = 30.0


class Flick(NamedTuple):
    """A flick nobody has measured. Both fields are ASSUMPTIONS and are said
    to be: the whole point of the requirement is that this cannot be read off
    the footage that exists."""

    degrees: float
    milliseconds: float


ASSUMED = (Flick(25.0, 100.0), Flick(15.0, 50.0))


class Window(NamedTuple):
    """A stretch of frames the scatter is measured on, and what it is."""

    view: str
    setId: str
    start: int
    end: int
    what: str


SCATTER_WINDOWS = (
    Window("side", "0.2", 37, 52,
           "the searched null: the one window this pack proves still, by its "
           "own search rather than by eye"),
    Window("side", "0.2", 560, 588,
           "the window the withdrawn derivation called still, in which the "
           "forearm grows by more than a third"),
)


def flick_rate(flick: Flick) -> float:
    """Degrees per second, which is what the measured floor is in."""
    return flick.degrees / (flick.milliseconds / 1000.0)


def floor_at(lever_pixels: float, against: str = "maximum") -> float:
    """The measured floor carried to another lever.

    The floor scales with the lever because the angle noise does: the same
    landmark error subtends a smaller angle across a longer arm.
    """
    measured = getattr(MEASURED_FLOOR, against)
    return measured * MEASURED_FLOOR.leverPixels / lever_pixels


def lever_for(flick: Flick, against: str = "maximum",
              margin: float = MARGIN) -> float:
    """The lever at which this flick clears the measured floor `margin` times.

    Solved from `floor_at`, so it cannot drift from it.
    """
    measured = getattr(MEASURED_FLOOR, against)
    return (margin * measured * MEASURED_FLOOR.leverPixels) / flick_rate(flick)


def frames_per_second_for(flick: Flick,
                          samples: float = SAMPLES_WANTED) -> float:
    """Pixels are not enough: a brief movement needs samples in it."""
    return samples * 1000.0 / flick.milliseconds


def requirement(flick: Flick) -> dict:
    """What a shoot must deliver for this flick. The published lever is the
    one taken against the MAXIMUM, which is the conservative choice: the
    median and the 90th are carried beside it so a reader can see the price
    of that choice rather than take it on trust."""
    return {
        "flick": flick,
        "leverAgainstMaximum": lever_for(flick, "maximum"),
        "leverAgainstP90": lever_for(flick, "p90"),
        "leverAgainstMedian": lever_for(flick, "median"),
        "framesPerSecond": frames_per_second_for(flick),
    }


def published_lever() -> float:
    """The one number a shoot is planned around: the strictest lever over
    every assumed flick, against the measured maximum. Never an average."""
    return max(requirement(f)["leverAgainstMaximum"] for f in ASSUMED)


# --- the scatter, which is reported and spent on nothing ------------------


def angle_and_lever(frame: dict, index: dict,
                    side: str = speed.NEAR_ARM) -> tuple | None:
    """The forearm-to-hand angle and the hand lever, in degrees and pixels."""
    elbow = speed.image_point(frame, index, f"{side}_elbow")[:2]
    wrist = speed.image_point(frame, index, f"{side}_wrist")[:2]
    hand = speed.hand_centre(frame, index, speed.image_point, side)[:2]
    forearm = (wrist[0] - elbow[0], wrist[1] - elbow[1])
    lever = (hand[0] - wrist[0], hand[1] - wrist[1])
    a, b = math.hypot(*forearm), math.hypot(*lever)
    if a == 0 or b == 0:
        return None
    dot = forearm[0] * lever[0] + forearm[1] * lever[1]
    cos = max(-1.0, min(1.0, dot / (a * b)))
    return math.degrees(math.acos(cos)), b, a


def scatter_rows(windows=SCATTER_WINDOWS) -> list[dict]:
    """The per-frame scatter of the angle, per window, MEASURED.

    Two implied landmark errors are reported, from the angle's own spread and
    from the spread of the frame-to-frame difference. They are reported as a
    RANGE across the windows, and the range is the honest form: this footage
    does not hold one number.
    """
    rows = []
    for window in windows:
        d, index = speed.load(window.view, window.setId)
        angles, levers, forearms = [], [], []
        for n in range(window.start, window.end + 1):
            frame = d["frames"][n]
            if not frame["detected"]:
                continue
            found = angle_and_lever(frame, index)
            if found is None:
                continue
            angles.append(found[0])
            levers.append(found[1])
            forearms.append(found[2])
        if len(angles) < 3:
            raise SystemExit(f"window {window.start}-{window.end} has too few "
                             "detected frames to measure a scatter")
        steps = [b - a for a, b in zip(angles, angles[1:])]
        lever = statistics.fmean(levers)
        rows.append({
            "window": window,
            "frames": len(angles),
            "leverMean": lever,
            "forearmGrowth": max(forearms) / min(forearms) - 1.0,
            "angleRange": max(angles) - min(angles),
            "angleSd": statistics.stdev(angles),
            "stepSd": statistics.stdev(steps),
            "eFromAngle": statistics.stdev(angles) * lever
                          / (DEGREES_PER_RADIAN * math.sqrt(2)),
            "eFromStep": statistics.stdev(steps) * lever
                         / (2 * DEGREES_PER_RADIAN),
        })
    return rows


def scatter_range(rows: list[dict] | None = None) -> tuple[float, float]:
    """The landmark error this footage supports, AS A RANGE. It is reported
    and it derives nothing."""
    rows = scatter_rows() if rows is None else rows
    every = [r[k] for r in rows for k in ("eFromAngle", "eFromStep")]
    return min(every), max(every)


def main(argv: list[str]) -> int:
    print("THE REQUIREMENT, from the 2026-09-02 measured floor: "
          f"{MEASURED_FLOOR.maximum:.0f} deg/s maximum "
          f"(p90 {MEASURED_FLOOR.p90:.0f}, median {MEASURED_FLOOR.median:.0f}) "
          f"on a {MEASURED_FLOOR.leverPixels:.0f} px lever")
    print()
    print(f"{'flick':>18s} {'rate':>9s} {'vs max':>8s} {'vs p90':>8s} "
          f"{'vs median':>10s} {'fps':>5s}")
    for flick in ASSUMED:
        r = requirement(flick)
        print(f"{flick.degrees:6.0f} deg {flick.milliseconds:5.0f} ms "
              f"{flick_rate(flick):7.0f}/s {r['leverAgainstMaximum']:8.1f} "
              f"{r['leverAgainstP90']:8.1f} {r['leverAgainstMedian']:10.1f} "
              f"{r['framesPerSecond']:5.0f}")
    print()
    print(f"PUBLISHED: a lever of at least {published_lever():.0f} px, against "
          "the measured MAXIMUM, which is")
    print("the conservative choice. The hundred pixels asked for on "
          "2026-09-02 sits above it and stands.")
    print()
    print("THE SCATTER, REPORTED AND SPENT ON NOTHING:")
    try:
        rows = scatter_rows()
    except SystemExit as refusal:
        print(f"  not measurable here: {refusal}")
        return 0
    for r in rows:
        w = r["window"]
        print(f"  {w.view} {w.setId} {w.start}-{w.end}, {r['frames']} frames, "
              f"lever {r['leverMean']:.1f} px, forearm "
              f"{r['forearmGrowth'] * 100:+.0f}%")
        print(f"    angle range {r['angleRange']:.1f} deg, sd "
              f"{r['angleSd']:.2f} deg, step sd {r['stepSd']:.2f} deg")
        print(f"    implied landmark error {r['eFromAngle']:.2f} px from the "
              f"angle, {r['eFromStep']:.2f} px from the step")
        print(f"    {w.what}")
    low, high = scatter_range(rows)
    print(f"  RANGE: {low:.2f} to {high:.2f} px. Not one number, and not an "
          "input to anything above.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
