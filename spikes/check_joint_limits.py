"""Ask the model whether any solved pose breaks its own joint limits.

The solver carries a LimitErrorFunction, but it is a soft term. A hand target
that pulls hard enough will simply pay the penalty and bend a joint past where a
person bends. Nothing until now checked whether that was happening, and the
coaching layer only inspects three joints at four phases.

This checks every joint on every frame of every movement, using the limits that
ship with the athlete rather than any number of mine, and it checks the poses
the library actually produces: the possession model where a drill is migrated,
hand keys where it is not.

It reports the overshoot in degrees rather than the solver's squared error. The
squared error was unreadable, and it made a two hundredth of a degree look the
same as six degrees. What a person wants to know is how far past the limit a
joint went, and the answer across the library is under a tenth of a degree.

    pixi run python check_joint_limits.py
"""

from __future__ import annotations

import math
import sys
from pathlib import Path

import numpy as np

SPIKE_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(SPIKE_DIR))

from ball_track import has_ball  # noqa: E402
from athlete import minmax_limits  # noqa: E402
from motion_track import load_motion  # noqa: E402
from movement_engine import (  # noqa: E402
    library,
    load_character,
    motion_path,
    solve,
)
from possession_solve import solve_movement  # noqa: E402
from technique import has_technique, load_technique, technique_path  # noqa: E402

# How far past its own limit a joint may sit before it counts as a violation.
#
# The limit term is soft, so a joint pressed against its limit settles a hair
# past it and always will. Demanding zero from a soft constraint is not a check,
# it is a tautology, so the question is what overshoot is too small to mean
# anything. A quarter of a degree is a twentieth of the 5 degrees the coaching
# layer already treats as the smallest angle worth reporting, and a tenth of
# the best a goniometer resolves.
#
# It is not a number chosen to pass. At the old limit weight of 200 this check
# fails at 4.1 degrees on every drill in the library.
TOLERANCE_DEGREES = 0.25


def overshoots(character, parameters: np.ndarray, limits: dict) -> dict[str, float]:
    """Return every joint outside its range, and by how many degrees.

    Scale parameters are left out. They are lengths, not angles, so reporting
    one of them in degrees is a category error, and a body outside the model's
    size range is a different fault from a pose outside a joint's range. That
    is what athlete.supported_heights is for.
    """
    names = list(character.parameter_transform.names)
    found: dict[str, float] = {}
    for name, (low, high) in limits.items():
        if name.startswith("scale_"):
            continue
        value = float(parameters[names.index(name)])
        past = max(low - value, value - high, 0.0)
        if past > 0.0:
            found[name] = math.degrees(past)
    return found


def poses(character, movement_id: str) -> np.ndarray:
    """The motion the library builds for this movement, however it builds it."""
    migrated = (
        has_ball(movement_id)
        and has_technique(movement_id)
        and load_technique(technique_path(movement_id)).possession_ready
    )
    if migrated:
        return solve_movement(character, movement_id)["motion"]
    return solve(character, load_motion(motion_path(movement_id)))["motion"]


def main() -> int:
    character = load_character()
    limits = minmax_limits(character)

    print(f"{'movement':<40} {'worst degrees':>14} {'joint':>22}")
    offenders = []
    for movement_id in library():
        motion = poses(character, movement_id)
        worst, where, frames_over = 0.0, "-", 0
        for parameters in motion:
            found = overshoots(character, parameters, limits)
            past = max(found.values(), default=0.0)
            if past > TOLERANCE_DEGREES:
                frames_over += 1
            if past > worst:
                worst = past
                where = max(found, key=found.get)
        if frames_over:
            offenders.append((movement_id, worst, where, frames_over, len(motion)))
        print(f"{movement_id:<40} {worst:14.4f} {where:>22}")

    print()
    if not offenders:
        print(
            "PASS no solved pose puts a joint more than "
            f"{TOLERANCE_DEGREES} degrees past its own limit, anywhere in the "
            "library"
        )
        return 0
    print("Joint limits are being exceeded:")
    for movement_id, worst, where, over, total in offenders:
        print(
            f"  {movement_id}: {over} of {total} frames, worst {worst:.3f} "
            f"degrees on {where}"
        )
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
