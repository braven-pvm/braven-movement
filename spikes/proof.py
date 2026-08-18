"""One technique, several arrival points. This is what proves or kills the model.

Milestone 4 of the possession model. The claim being tested is that the hands
are solved rather than authored, and there is only one way to test it: put the
ball somewhere else and change nothing about the athlete.

Every run below uses the same technique file and the same motion file. The only
thing that differs is where the passer put the ball. If the athlete cannot adapt
to that, the inversion has bought nothing and the design says so itself.

A run counts as a plausible catch when all of this holds:

- she reaches it, so there is a contact frame at all
- both palms finish on the ball surface
- no finger is inside the ball
- every measured angle stays inside its clinical range
- the model's own joint limits stay clean
- nothing snaps, meaning no frame's step is more than three times the steps
  either side of it, judged only on steps large enough to be clinically real

The last of those was written twice, and the first version was wrong. It
compared each run against the central pass and failed anything rougher by more
than a quarter. That measures which arrival point is easiest rather than which
is plausible: a wide ball is taken faster than a central one by a real athlete
too. What the check is for is a spike, so it now looks for one.

    pixi run python proof.py
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np

SPIKE_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(SPIKE_DIR))

from ball_track import ball_variants, load_ball, ball_path  # noqa: E402
from contact_solve import joint_limit_error  # noqa: E402
from finger_wrap import wrap_report  # noqa: E402
from grip import palm_skin, reconstruct  # noqa: E402
from isb_angles import AAOS_LIMITS  # noqa: E402
from movement_engine import SolveError, load_character  # noqa: E402
from possession_solve import (  # noqa: E402
    solve_movement,
    spike_report,
    step_report,
)

OUTPUT = SPIKE_DIR / "poc-output" / "library"
DEFAULT = "netball_two_hand_snatch_pull_in"

RANGE_KEYS = (
    ("ElbowFlexionDegrees", "elbow.flexion"),
    ("ShoulderElevationDegrees", "shoulder.elevation"),
    ("KneeFlexionDegrees", "knee.flexion"),
)
# How far a single frame's step may exceed the steps either side of it before
# the movement counts as jumping at that frame.
#
# This replaced a check that compared each run against the central pass. That
# one measured which arrival point is easiest, not which is plausible, and it
# failed a wide catch for being faster than a central one, which a real athlete
# is too. A snap is a spike against its own neighbours.
SNAP_RATIO = 3.0


def anatomy_violations(measurements: list[dict]) -> list[str]:
    found = []
    for number, frame in enumerate(measurements):
        for prefix in ("left", "right"):
            for suffix, key in RANGE_KEYS:
                value = frame[f"{prefix}{suffix}"]
                limit = AAOS_LIMITS[key]
                if value < limit.minimum_degrees or value > limit.maximum_degrees:
                    found.append(
                        f"frame {number}: {prefix} {key} is {value:.1f} degrees"
                    )
    return found


def examine(character, movement_id: str, variant: str | None) -> dict:
    result = solve_movement(character, movement_id, variant)
    held = result["possession"]
    number = held.contact_frame
    points = result["points"][number]
    index = result["index"]
    centre = held.frames[number].centre
    radius = result["radiusCm"]
    placed = {name: points[position] for name, position in index.items()}

    palms = {}
    for side in result["technique"].sides:
        origin, axes = reconstruct(placed, result["shapes"][side])
        palms[side] = round(
            float(np.linalg.norm(palm_skin(origin, axes) - centre)) - radius, 3
        )
    wrap = wrap_report(points, index, centre, radius, result["technique"].sides)
    steps = step_report(result["measurements"])
    spikes = spike_report(result["measurements"])
    ball = load_ball(ball_path(movement_id, variant))
    arrival = ball.keys[-1].offset

    return {
        "variant": variant or "central",
        "arrival": {
            "across": arrival.across,
            "up": arrival.up,
            "ahead": arrival.ahead,
        },
        "catchHeightCm": round(float(centre[1]), 1),
        "contactFrame": number,
        "contactPhase": round(held.frames[number].phase, 4),
        "worstPalmSkinGapCm": round(max(abs(value) for value in palms.values()), 3),
        "palmSkinGapCm": palms,
        "deepestFingerInsideBallCm": wrap["deepestFingerInsideBallCm"],
        "worstFingertipGapCm": wrap["worstFingertipGapCm"],
        "ballStepAtHandoverCm": round(held.ball_step_at(number), 2),
        "biggestBallStepCm": round(held.biggest_ball_step_cm(), 2),
        "worstStepBetweenFramesDegrees": round(max(steps.values()), 2),
        "fastestDegreesPerSecond": round(
            max(steps.values()) * result["track"].frames_per_second, 0
        ),
        "spike": spikes,
        "turnedByDegrees": result["turnedByDegrees"],
        "jointLimitError": round(
            max(
                joint_limit_error(character, result["motion"][n])
                for n in range(len(result["motion"]))
            ),
            5,
        ),
        "anatomyViolations": anatomy_violations(result["measurements"]),
    }


def judge(runs: list[dict]) -> list[dict]:
    """Score every run on its own terms."""
    for run in runs:
        run["checks"] = {
            "she reaches it": run["contactFrame"] is not None,
            "palms on the surface": run["worstPalmSkinGapCm"] <= 1.0,
            "no finger inside the ball": run["deepestFingerInsideBallCm"] <= 1.0,
            "anatomy clean": not run["anatomyViolations"],
            "joint limits clean": run["jointLimitError"] <= 0.1,
            "nothing snaps": run["spike"]["worstNeighbourRatio"] <= SNAP_RATIO,
        }
        run["plausible"] = all(run["checks"].values())
    return runs


def main(argv: list[str]) -> int:
    movement_id = argv[1] if len(argv) > 1 else DEFAULT
    variants = ball_variants(movement_id)
    if len(variants) < 2:
        print(
            f"{movement_id} has {len(variants)} ball trajectory. The proof needs "
            "the same technique against several."
        )
        return 1

    character = load_character()
    runs = []
    for variant in variants:
        try:
            runs.append(examine(character, movement_id, variant))
        except SolveError as error:
            runs.append(
                {
                    "variant": variant or "central",
                    "contactFrame": None,
                    "plausible": False,
                    "error": str(error),
                }
            )
    runs = judge([run for run in runs if run.get("contactFrame") is not None]) + [
        run for run in runs if run.get("contactFrame") is None
    ]

    print(f"\n{movement_id}: one technique, {len(runs)} arrival points\n")
    print(
        "variant   arrival across/up/ahead   catch cm   turn   frame   palm gap   "
        "finger in   fastest deg/s   spike"
    )
    for run in runs:
        if run.get("contactFrame") is None:
            print(f"{run['variant']:<9s} NOT CAUGHT: {run.get('error', '')}")
            continue
        arrival = run["arrival"]
        print(
            f"{run['variant']:<9s} "
            f"{arrival['across']:6.2f} {arrival['up']:5.2f} {arrival['ahead']:6.2f}   "
            f"{run['catchHeightCm']:8.1f}  {run['turnedByDegrees']:5.1f}  "
            f"{run['contactFrame']:6d}   "
            f"{run['worstPalmSkinGapCm']:+8.2f}   "
            f"{run['deepestFingerInsideBallCm']:+9.2f}   "
            f"{run['fastestDegreesPerSecond']:13.0f}   "
            f"{run['spike']['worstNeighbourRatio']:5.2f}"
        )

    print()
    for run in runs:
        marks = " ".join(
            ("ok" if passed else "FAIL") + " " + name
            for name, passed in run.get("checks", {}).items()
            if not passed
        )
        print(
            f"  {run['variant']:<9s} "
            + ("plausible catch" if run.get("plausible") else f"NOT PLAUSIBLE: {marks}")
        )

    OUTPUT.mkdir(parents=True, exist_ok=True)
    (OUTPUT / f"{movement_id}.proof.json").write_text(
        json.dumps({"movementId": movement_id, "runs": runs}, indent=2) + "\n",
        encoding="utf-8",
    )
    passed = sum(1 for run in runs if run.get("plausible"))
    print(
        f"\n{passed} of {len(runs)} arrival points produce a plausible catch, "
        "with no hand authoring anywhere."
    )
    return 0 if passed == len(runs) else 1


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
