"""What the authored 600 implies, at the only distance the manual states.

    cd spikes
    pixi run --frozen -- python -B ../scripts/launch_provenance.py

STEP 1 OF THE RELEASE-TIMING UNIT. This does not change the constant and it
does not propose a value. It reports what `author_flight.DEFAULT_SPEED_CM`
produces, using the engine's own `ball_track.solve_launch` rather than a
rebuild of the ballistics, because a rebuilt parabola is a second
implementation that can drift.

TWO THINGS ABOUT THE CONSTANT THAT ARE EASY TO GET WRONG:

  1. 600 IS A HORIZONTAL SPEED, not a launch speed. `solve_launch` takes the
     horizontal component and derives the vertical from the span and the rise.
     The launch speed is always larger, and how much larger depends on the span.
  2. THE SPAN IS THE ENGINE'S `DEFAULT_PASSER_AHEAD`, 4.0 m. The manual states
     one distance for a passing drill and it is 5 to 7 m, in 37 places.

Nothing here reads `spikes/movements/`. Gate 4 is untouched.
"""
import sys
from pathlib import Path

SPIKES = Path(__file__).resolve().parents[1] / "spikes"
if str(SPIKES) not in sys.path:
    sys.path.insert(0, str(SPIKES))

import numpy as np  # noqa: E402
from author_flight import (  # noqa: E402
    DEFAULT_PASSER_AHEAD,
    DEFAULT_RELEASE_HEIGHT_CM,
    DEFAULT_SPEED_CM,
)
from ball_track import GRAVITY_CM, solve_launch  # noqa: E402

# The only distance the coaches manual states for a passing drill, in metres.
MANUAL_SPANS_M = (5.0, 6.0, 7.0)
# Released and caught at the same height, which is the flattest a pass can be
# and therefore the KINDEST case for the constant.
LEVEL_RISE_CM = 0.0


def launch(span_m: float, horizontal_cm: float, rise_cm: float):
    release = np.array([0.0, DEFAULT_RELEASE_HEIGHT_CM, 0.0])
    catch = np.array([span_m * 100.0, DEFAULT_RELEASE_HEIGHT_CM + rise_cm, 0.0])
    seconds, velocity = solve_launch(release, catch, horizontal_cm)
    speed = float(np.linalg.norm(velocity))
    angle = float(np.degrees(np.arctan2(velocity[1], horizontal_cm)))
    apex = float(velocity[1] ** 2 / (2.0 * GRAVITY_CM)) if velocity[1] > 0 else 0.0
    return seconds, float(velocity[1]), speed, angle, apex


def main() -> int:
    print(f"    DEFAULT_SPEED_CM      {DEFAULT_SPEED_CM:g} cm/s HORIZONTAL")
    print(f"    DEFAULT_PASSER_AHEAD  {DEFAULT_PASSER_AHEAD:g} m")
    print(f"    DEFAULT_RELEASE_HEIGHT_CM {DEFAULT_RELEASE_HEIGHT_CM:g} cm")
    print()
    print("    THE AUTHORED SPEED AT THE AUTHORED SPAN, AND AT THE MANUAL'S")
    print("    level release and catch, which is the flattest and kindest case")
    print()
    print(f"    {'span':>6s} {'flight s':>9s} {'vertical':>9s} {'launch':>8s} "
          f"{'angle':>7s} {'apex above release':>19s}")
    for span in (DEFAULT_PASSER_AHEAD,) + MANUAL_SPANS_M:
        seconds, vertical, speed, angle, apex = launch(
            span, DEFAULT_SPEED_CM, LEVEL_RISE_CM
        )
        mark = "  <- the engine's own" if span == DEFAULT_PASSER_AHEAD else ""
        print(f"    {span:5.1f}m {seconds:9.3f} {vertical:8.1f}  {speed:7.1f} "
              f"{angle:6.1f}d {apex:15.1f} cm{mark}")
    print()
    print("    A LEVEL PASS'S APEX DEPENDS ONLY ON ITS FLIGHT TIME, because the")
    print("    vertical must cancel gravity exactly: apex = g * t * t / 8. So a")
    print("    flatter pass over the same span is a FASTER pass, and the")
    print("    horizontal speed is the only lever.")
    print()
    print(f"    {'span':>6s} {'apex 20cm':>18s} {'apex 40cm':>18s} "
          f"{'apex 80cm':>18s}")
    for span in MANUAL_SPANS_M:
        row = []
        for apex_cm in (20.0, 40.0, 80.0):
            seconds = float(np.sqrt(8.0 * apex_cm / GRAVITY_CM))
            row.append(span * 100.0 / seconds)
        print(f"    {span:5.1f}m " + " ".join(
            f"{value:11.0f} cm/s" for value in row))
    print()
    # COMPUTED, NOT WRITTEN OUT. A first version of this script stated 1049
    # here while the table above it computed 1051, which is the fault of prose
    # contradicting its own figure that this lane has now made three times.
    # NAMED, because "600" in this function would mean SIX METRES IN
    # CENTIMETRES and the constant beside it is also 600. One number with two
    # meanings is the fault this repository keeps recording.
    example_span_m, example_apex_cm = 6.0, 40.0
    seconds = float(np.sqrt(8.0 * example_apex_cm / GRAVITY_CM))
    needed = example_span_m * 100.0 / seconds
    print(f"    Read the table above as: to throw {example_span_m:g} m and rise "
          f"no more than {example_apex_cm:g} cm above")
    print(f"    the release, the ball must leave at {needed:.0f} cm/s "
          f"horizontally, which is")
    print(f"    {needed / DEFAULT_SPEED_CM:.2f} times the authored constant.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
