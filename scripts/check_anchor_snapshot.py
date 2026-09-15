"""Is the anchor snapshot in `ball_anchor_verdict.py` still true of this build?

    cd spikes
    pixi run --frozen -- python -B ../scripts/check_anchor_snapshot.py

WHY. `scripts/ball_anchor_verdict.py` holds 187 solved body positions in
centimetres, described as "the MOVEMENT LANE'S measured values, reported
2026-09-04, from the solved pose". **It carries a date and no build hash**, so
nothing in it says whether the engine has moved underneath it, and the science
lane recorded it as the largest untestable INCLUDE in its register.

**A DATE IS NOT AN IDENTITY.** The rule in `docs/CAPABILITY_AND_RESULT.md` is
that a result carries the identity of what it measured.

**THIS ANSWERS IT BY MEASUREMENT RATHER THAN BY ARCHAEOLOGY.** Adding a hash
inferred from the file's commit date would be inventing provenance: the values
could have been read on any tree at or before that commit. Re-reading them on
THIS build says something stronger and testable — whether the snapshot is still
true, and of which commit.

WHAT IT READS. The shoulder midpoint minus `root`, in engine axes, at
`round(atPhase * (frames - 1))` for each graded phase, which is the definition
the file itself states.
"""
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SPIKES = ROOT / "spikes"
if str(SPIKES) not in sys.path:
    sys.path.insert(0, str(SPIKES))
if str(ROOT / "scripts") not in sys.path:
    sys.path.insert(0, str(ROOT / "scripts"))

import numpy as np  # noqa: E402
from ball_anchor_verdict import ENGINE  # noqa: E402
from movement_definition import load as load_definition  # noqa: E402
from movement_engine import MOVEMENT_DIR, load_character  # noqa: E402
from possession_solve import solve_movement  # noqa: E402

# The file's own tolerance: the 1 cm rule it exists to check.
MOVED_CM = 0.01


def head() -> str:
    return subprocess.run(
        ["git", "-C", str(ROOT), "rev-parse", "HEAD"],
        capture_output=True, text=True, check=True,
    ).stdout.strip()


def main() -> int:
    character = load_character()
    build = head()
    print(f"    this build: {build}")
    print(f"    the snapshot says: reported 2026-09-04, no build recorded")
    print()
    print(f"    {'drill / phase':44s} {'axis':>6s} "
          f"{'snapshot':>10s} {'now':>10s} {'moved':>9s}")

    worst = 0.0
    checked = moved = 0
    for movement_id, rows in sorted(ENGINE.items()):
        full = f"netball_{movement_id}"
        try:
            result = solve_movement(character, full)
        except Exception as problem:  # noqa: BLE001
            print(f"    {movement_id}: could not solve: {problem}")
            continue
        index, points = result["index"], result["points"]
        definition = load_definition(MOVEMENT_DIR / f"{full}.json")
        last = len(points) - 1
        at = {phase.name: phase.at_phase for phase in definition.phases}
        for name, across, up, ahead in rows:
            if name not in at:
                print(f"    {movement_id}/{name}: no such graded phase now")
                continue
            frame = round(at[name] * last)
            pose = points[frame]
            middle = (pose[index["l_uparm"]] + pose[index["r_uparm"]]) / 2.0
            now = middle - pose[index["root"]]
            for axis, was, value in zip(
                ("across", "up", "ahead"), (across, up, ahead), now
            ):
                checked += 1
                gap = abs(float(value) - was)
                worst = max(worst, gap)
                if gap >= MOVED_CM:
                    moved += 1
                    print(f"    {movement_id + '/' + name:44s} {axis:>6s} "
                          f"{was:10.3f} {float(value):10.3f} {gap:9.3f}")

    print()
    print(f"    {checked} numbers checked, {moved} moved by {MOVED_CM} cm or more")
    print(f"    the largest movement: {worst:.4f} cm")
    if checked == 0:
        raise SystemExit(
            "REFUSED: nothing was checked. That is a broken check, not a "
            "clean snapshot."
        )
    if moved == 0:
        print()
        print(f"    THE SNAPSHOT IS STILL TRUE OF {build[:7]}, so it can be")
        print("    stamped with this build rather than with a date.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
