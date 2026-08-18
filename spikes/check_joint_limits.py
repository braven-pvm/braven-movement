"""Ask the model whether any solved pose breaks its own joint limits.

The solver carries a LimitErrorFunction, but it is a soft term. A hand target
that pulls hard enough will simply pay the penalty and bend a joint past where a
person bends. Nothing until now checked whether that was happening, and the
coaching layer only inspects three joints at four phases.

This checks every joint on every frame of every movement, using the limits that
ship with the athlete rather than any number of mine.

    pixi run python check_joint_limits.py
"""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pymomentum.solver2 as solver2

SPIKE_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(SPIKE_DIR))

from motion_track import load_motion  # noqa: E402
from movement_engine import (  # noqa: E402
    library,
    load_character,
    motion_path,
    solve,
)

# The limit term reports squared error. Anything above this is a joint being
# held outside its range rather than numerical noise.
TOLERANCE = 1e-6


def main() -> int:
    character = load_character()
    limit = solver2.LimitErrorFunction(character, weight=1.0)

    print(f"{'movement':<40} {'worst frame':>12} {'frames over':>12}")
    worst_overall = 0.0
    offenders = []
    for movement_id in library():
        track = load_motion(motion_path(movement_id))
        result = solve(character, track)

        errors = []
        for parameters in result["motion"]:
            value = float(
                limit.get_error(np.asarray(parameters, dtype=np.float32).reshape(-1))
            )
            errors.append(value)

        worst = max(errors)
        over = sum(1 for value in errors if value > TOLERANCE)
        worst_overall = max(worst_overall, worst)
        if over:
            offenders.append((movement_id, worst, over, len(errors)))
        print(f"{movement_id:<40} {worst:12.6f} {over:6d} of {len(errors):<5d}")

    print()
    if not offenders:
        print("PASS no solved pose breaks a joint limit anywhere in the library")
        return 0
    print("Joint limits are being exceeded:")
    for movement_id, worst, over, total in offenders:
        print(f"  {movement_id}: {over} of {total} frames, worst {worst:.6f}")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
