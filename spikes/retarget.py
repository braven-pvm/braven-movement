"""Run the whole library on bodies of different sizes, and report what breaks.

Every offset in this repository is written in arm lengths so that a movement
authored on one athlete carries to another. Nothing has ever checked it. The
library has only ever been solved on the one body the model ships with, and a
coach's squad is not one body.

This runs all of it on five: the reference, a 152 cm junior, a 190 cm senior,
and two players of the same height whose reach differs by a tenth either way.
The last pair is the one that matters, because they differ in exactly the
quantity everything is written in.

What a correct retarget looks like:

- the palms still finish on the ball surface, which is an absolute distance and
  must not grow with the athlete
- no finger goes into the ball
- every measured angle sits close to the reference athlete's, because the same
  movement performed by a bigger person is the same movement
- no joint goes outside its own range
- nothing snaps

An angle is the right thing to compare. Distances are supposed to change with
the body; angles are not, and they are also what the coaching layer grades.

    pixi run python retarget.py
    pixi run python retarget.py netball_two_hand_snatch_pull_in
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np

SPIKE_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(SPIKE_DIR))

from athlete import squad  # noqa: E402
from ball_track import has_ball  # noqa: E402
from check_joint_limits import TOLERANCE_DEGREES, overshoots  # noqa: E402
from athlete import minmax_limits  # noqa: E402
from finger_wrap import wrap_report  # noqa: E402
from grip import palm_skin, reconstruct  # noqa: E402
from isb_angles import AAOS_LIMITS  # noqa: E402
from movement_engine import SolveError, library, load_character  # noqa: E402
from possession_solve import solve_movement, spike_report, step_report  # noqa: E402
from proof import anatomy_violations  # noqa: E402
from technique import has_technique, load_technique, technique_path  # noqa: E402

OUTPUT = SPIKE_DIR / "poc-output" / "library"

# How far a retargeted athlete's measured angles may sit from the reference
# athlete's before the movement counts as having changed rather than scaled.
#
# Five degrees, the same threshold the coaching layer uses for the smallest
# angle worth reporting. Below it the two bodies are performing a movement no
# goniometer could tell apart.
ANGLE_TOLERANCE_DEGREES = 5.0
# The palm sits on the ball surface. That is an absolute distance and must not
# grow with the athlete.
PALM_TOLERANCE_CM = 1.0


def angles(measurements: list[dict]) -> dict[str, list[float]]:
    return {
        key: [frame[key] for frame in measurements]
        for key, value in measurements[0].items()
        if key.endswith("Degrees") and isinstance(value, (int, float))
    }


def examine(character, movement_id: str, athlete, limits: dict) -> dict:
    result = solve_movement(character, movement_id, None, athlete.identity)
    held = result["possession"]
    number = held.contact_frame
    points = result["points"][number]
    index = result["index"]
    centre = held.frames[number].centre
    radius = result["radiusCm"]
    placed = {name: points[position] for name, position in index.items()}

    palms = []
    for side in result["technique"].sides:
        origin, axes = reconstruct(placed, result["shapes"][side])
        palms.append(
            abs(float(np.linalg.norm(palm_skin(origin, axes) - centre)) - radius)
        )
    wrap = wrap_report(points, index, centre, radius, result["technique"].sides)
    worst_limit = max(
        max(overshoots(character, pose, limits).values(), default=0.0)
        for pose in result["motion"]
    )
    return {
        "athlete": athlete.name,
        "heightCm": round(athlete.height_cm, 1),
        "armCm": round(athlete.arm_cm, 2),
        "contactFrame": number,
        "worstPalmSkinGapCm": round(max(palms), 3),
        "deepestFingerInsideBallCm": wrap["deepestFingerInsideBallCm"],
        "worstJointOvershootDegrees": round(worst_limit, 3),
        "worstStepDegrees": round(max(step_report(result["measurements"]).values()), 2),
        "spike": spike_report(result["measurements"])["worstNeighbourRatio"],
        "anatomyViolations": len(anatomy_violations(result["measurements"])),
        "angles": angles(result["measurements"]),
    }


def compare(runs: list[dict]) -> list[dict]:
    """Score every body against the reference, which is what was authored."""
    # Taken before the loop, because the loop drops each run's angle series
    # once it has been scored and the reference is usually scored first.
    reference = next(run for run in runs if run["athlete"] == "reference")["angles"]
    for run in runs:
        worst, where = 0.0, None
        for key, series in run["angles"].items():
            base = reference[key]
            if len(base) != len(series):
                worst, where = float("inf"), f"{key} has a different frame count"
                break
            gap = max(abs(a - b) for a, b in zip(base, series))
            if gap > worst:
                worst, where = gap, key
        run["worstAngleDriftDegrees"] = round(worst, 2)
        run["driftsMostOn"] = where
        run["checks"] = {
            "palms on the surface": run["worstPalmSkinGapCm"] <= PALM_TOLERANCE_CM,
            "no finger inside the ball": run["deepestFingerInsideBallCm"] <= 1.0,
            "anatomy clean": run["anatomyViolations"] == 0,
            "joint limits clean": (
                run["worstJointOvershootDegrees"] <= TOLERANCE_DEGREES
            ),
            "same movement as the reference": worst <= ANGLE_TOLERANCE_DEGREES,
        }
        run["retargets"] = all(run["checks"].values())
        del run["angles"]
    return runs


def main(argv: list[str]) -> int:
    wanted = argv[1:] or [
        name
        for name in library()
        if has_ball(name)
        and has_technique(name)
        and load_technique(technique_path(name)).possession_ready
    ]
    character = load_character()
    limits = minmax_limits(character)
    people = squad(character)

    print("the squad")
    for athlete in people:
        print("  " + athlete.describe())

    report = {}
    failed = 0
    for movement_id in wanted:
        runs = []
        for athlete in people:
            try:
                runs.append(examine(character, movement_id, athlete, limits))
            except SolveError as error:
                runs.append(
                    {
                        "athlete": athlete.name,
                        "heightCm": round(athlete.height_cm, 1),
                        "error": str(error),
                        "retargets": False,
                        "angles": {},
                        "checks": {},
                    }
                )
        solved = [run for run in runs if "error" not in run]
        runs = compare(solved) + [run for run in runs if "error" in run]
        report[movement_id] = runs

        print(f"\n{movement_id}")
        print(
            "  athlete       height    arm   palm gap   finger in   "
            "angle drift   limits   spike"
        )
        for run in runs:
            if "error" in run:
                print(f"  {run['athlete']:<12s} NOT SOLVED: {run['error'][:60]}")
                failed += 1
                continue
            mark = "" if run["retargets"] else "   <- "
            if not run["retargets"]:
                failed += 1
                mark += ", ".join(
                    name for name, ok in run["checks"].items() if not ok
                )
            print(
                f"  {run['athlete']:<12s} {run['heightCm']:6.1f} {run['armCm']:6.2f} "
                f"{run['worstPalmSkinGapCm']:10.3f} "
                f"{run['deepestFingerInsideBallCm']:+11.2f} "
                f"{run['worstAngleDriftDegrees']:13.2f} "
                f"{run['worstJointOvershootDegrees']:8.3f} "
                f"{run['spike']:7.2f}{mark}"
            )
        drift = [r for r in runs if "error" not in r and r["driftsMostOn"]]
        if drift:
            worst = max(drift, key=lambda r: r["worstAngleDriftDegrees"])
            if worst["worstAngleDriftDegrees"] > ANGLE_TOLERANCE_DEGREES:
                print(
                    f"     drifts most on {worst['driftsMostOn']}, "
                    f"{worst['worstAngleDriftDegrees']:.1f} degrees on "
                    f"{worst['athlete']}"
                )

    OUTPUT.mkdir(parents=True, exist_ok=True)
    (OUTPUT / "retarget.json").write_text(
        json.dumps(report, indent=2) + "\n", encoding="utf-8"
    )
    print(
        f"\n{failed} of {sum(len(v) for v in report.values())} body and drill "
        "pairings do not retarget"
    )
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
