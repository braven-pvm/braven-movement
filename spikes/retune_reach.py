"""Pull every movement back to a reach an honest shoulder can deliver.

The library was authored while the shoulder girdle could slide up to 28 cm
forward to help the hand reach its target. A clavicle allows a few centimetres,
not that, so the engine now holds the shoulder. The keys that were written
against the old behaviour ask for more reach than the arm has.

This scales the reach in each movement until the hands actually arrive. It tunes
against reachability, which is anatomy, and never against the coaching bands,
which are the manual's business.

    pixi run python retune_reach.py [--apply]
"""

from __future__ import annotations

import copy
import json
import sys
from pathlib import Path

SPIKE_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(SPIKE_DIR))

from motion_track import load_motion  # noqa: E402
from movement_engine import library, load_character, motion_path, solve  # noqa: E402

# A hand that lands this close has arrived. Anything more and the pose is not
# the pose the key asked for.
ACCEPTABLE_MISS_CM = 1.2
# Reach is scaled toward the chest. Below this the movement is not the same
# movement any more and a person should look at it.
LOWEST_SCALE = 0.55


def solve_with_scale(character, path: Path, scale: float) -> float:
    """Return the worst hand miss when this movement's reach is scaled."""
    data = json.loads(path.read_text(encoding="utf-8"))
    scaled = copy.deepcopy(data)
    for key in scaled["keys"]:
        for field in ("across", "up", "ahead"):
            if field in key:
                key[field] = key[field] * scale
        for side in ("left", "right"):
            if side in key:
                for field in ("across", "up", "ahead"):
                    if field in key[side]:
                        key[side][field] = key[side][field] * scale

    temporary = path.with_suffix(".scaled.tmp.json")
    temporary.write_text(json.dumps(scaled), encoding="utf-8")
    try:
        track = load_motion(temporary)
        result = solve(character, track)
        return max(result["misses"])
    finally:
        temporary.unlink(missing_ok=True)


def find_scale(character, path: Path) -> tuple[float, float]:
    """Return the largest reach scale whose hands still arrive."""
    miss = solve_with_scale(character, path, 1.0)
    if miss <= ACCEPTABLE_MISS_CM:
        return 1.0, miss

    low, high = LOWEST_SCALE, 1.0
    best = LOWEST_SCALE
    best_miss = solve_with_scale(character, path, LOWEST_SCALE)
    for _ in range(6):
        middle = (low + high) / 2.0
        middle_miss = solve_with_scale(character, path, middle)
        if middle_miss <= ACCEPTABLE_MISS_CM:
            best, best_miss = middle, middle_miss
            low = middle
        else:
            high = middle
    return best, best_miss


def apply_scale(path: Path, scale: float) -> None:
    data = json.loads(path.read_text(encoding="utf-8"))
    for key in data["keys"]:
        for field in ("across", "up", "ahead"):
            if field in key:
                key[field] = round(key[field] * scale, 4)
        for side in ("left", "right"):
            if side in key:
                for field in ("across", "up", "ahead"):
                    if field in key[side]:
                        key[side][field] = round(key[side][field] * scale, 4)
    data["notes"] = data.get("notes", "") + (
        f" Reach scaled by {scale:.3f} so the hands arrive without the shoulder "
        "girdle sliding forward to help."
    )
    path.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")


def main() -> int:
    apply = "--apply" in sys.argv
    character = load_character()

    print(f"{'movement':<40} {'scale':>7} {'miss after':>12}")
    changes = []
    for movement_id in library():
        path = motion_path(movement_id)
        scale, miss = find_scale(character, path)
        print(f"{movement_id:<40} {scale:7.3f} {miss:9.2f} cm")
        if scale < 1.0:
            changes.append((path, scale))

    if not changes:
        print("\nevery movement already reaches with an honest shoulder")
        return 0
    if apply:
        for path, scale in changes:
            apply_scale(path, scale)
        print(f"\napplied to {len(changes)} movements")
    else:
        print(f"\n{len(changes)} movements need scaling. Re-run with --apply.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
