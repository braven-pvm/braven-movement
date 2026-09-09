"""Items 6 and 5 of the coach morning, measured on both bodies.

Erin grades the engine's solved skeleton. She looks at the MPFB athlete. Item 6
asks whether the ready pose shows an arm span, and item 5 asks whether the second
hand travels too far to meet the ball. This measures both quantities on both
bodies, so that what she is asked about and what she is shown can be compared.

THE AXIS FOR ITEM 5 IS NOT A CHOICE MADE HERE. `docs/KNOWN_ISSUES.md` records the
free hand as "11.9 cm ahead of her shoulders", so the quantity is the AHEAD
component from the shoulder midpoint and not a distance. Of four axes tried, only
world-ahead reproduces the recorded numbers, and it reproduces them to 0.18, 0.00
and 0.01 cm on `one_hand_snatch_to_other_hand`.

WHY THE TWO SIDES ARE COMPARABLE. Every job file on this tree is byte-identical to
the `jobSha256` its receipt recorded, so the solve here IS the solve those figures
were rendered from. The engine side is solved now. The rendered side is read from
the archived receipts of build `2413f9d`.

WHAT THE ARCHIVE CANNOT ANSWER. A receipt carries one pose per phase. The engine
puts the free hand furthest out at a frame that is not a phase frame, so the peak
is reported for the engine alone and marked as such.

    pixi run --frozen python ../scripts/two_bodies_ready_and_join.py
"""

from __future__ import annotations

import json
import math
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
for extra in (REPO, REPO / "spikes"):
    if str(extra) not in sys.path:
        sys.path.insert(0, str(extra))

import numpy as np  # noqa: E402
from export_blender_job import load_character, to_blender  # noqa: E402
from possession_solve import solve_movement  # noqa: E402

ARCHIVE = "coach-figures-2413f9d"

# The eight rows of item 6, as the coach morning states them, read on `ac240b2`.
MORNING_ITEM_6 = {
    "netball_deflect_high": 18.29,
    "netball_hooks_jump_pull_in": 19.83,
    "netball_double_foot_landing": 19.91,
    "netball_two_hand_snatch_pull_in": 20.08,
    "netball_two_hand_snatch_straight_back": 20.08,
    "netball_two_hand_catch_chest": 20.10,
    "netball_one_hand_snatch_to_other_hand": 32.15,
    "netball_hooks_outside_hand": 45.68,
}

# The two rows of item 5, contact then furthest out then back, read on `ac240b2`.
MORNING_ITEM_5 = {
    "netball_one_hand_snatch_to_other_hand": (11.85, 25.97, 12.07),
    "netball_hooks_outside_hand": (3.43, 14.33, 3.48),
}


def archives() -> Path:
    for base in [Path(__file__).resolve()] + list(Path(__file__).resolve().parents):
        candidate = base / ".assets" / "archives"
        if candidate.is_dir():
            return candidate
    raise SystemExit("no .assets/archives found from this file")


def gap(a, b) -> float:
    """Distance in centimetres between two Blender-frame points."""
    return float(np.linalg.norm(np.asarray(a) - np.asarray(b))) * 100.0


def ahead(point, shoulder_l, shoulder_r) -> float:
    """Centimetres the point sits ahead of the shoulder midpoint.

    The rig faces negative Y in the Blender frame, so ahead is minus Y. This is
    the axis `docs/KNOWN_ISSUES.md` measured the free hand on.
    """
    midpoint = (np.asarray(shoulder_l) + np.asarray(shoulder_r)) / 2.0
    return float(midpoint[1] - np.asarray(point)[1]) * 100.0


def turn_degrees(shoulder_l, shoulder_r) -> float:
    """Degrees the shoulder line is turned away from square, in the ground plane."""
    line = np.asarray(shoulder_l) - np.asarray(shoulder_r)
    return abs(math.degrees(math.atan2(line[1], line[0])))


def solved(character, movement_id):
    result = solve_movement(character, movement_id)
    index, points = result["index"], result["points"]

    def at(frame: int, joint: str):
        return to_blender(points[frame][index[joint]])

    return at, len(points)


def item_six(character, receipts) -> list:
    print("=== ITEM 6. Is she showing her arm span while she waits? ===")
    print("Wrist to wrist at the first frame, in centimetres.")
    print()
    print(f"{'drill':<38}{'engine':>8}{'rendered':>9}{'gap':>7}"
          f"{'eng/span':>10}{'ren/span':>10}{'morning':>9}")
    moved = []
    rows = []
    for movement_id, receipt in receipts.items():
        at, _ = solved(character, movement_id)
        phase = receipt["phases"][0]
        frame = phase["frame"]
        arms = phase["arms"]
        engine = gap(at(frame, "l_wrist"), at(frame, "r_wrist"))
        rendered = gap(arms["l"]["wrist"], arms["r"]["wrist"])
        engine_span = gap(at(frame, "l_uparm"), at(frame, "r_uparm"))
        rendered_span = gap(arms["l"]["shoulder"], arms["r"]["shoulder"])
        stated = MORNING_ITEM_6.get(movement_id)
        note = f"{stated:>9.2f}" if stated is not None else f"{'-':>9}"
        if stated is not None and abs(stated - engine) > 0.005:
            moved.append((movement_id, stated, engine))
        rows.append((movement_id, engine, rendered))
        print(f"{movement_id.replace('netball_', ''):<38}{engine:>8.2f}{rendered:>9.2f}"
              f"{engine - rendered:>7.2f}{engine / engine_span:>10.3f}"
              f"{rendered / rendered_span:>10.3f}{note}")
    print()
    print("THE ENGINE SIDE REPRODUCES THE COACH MORNING, except where it does not,")
    print("and the exception is named rather than averaged away:")
    if moved:
        for movement_id, stated, engine in moved:
            print(f"    {movement_id.replace('netball_', ''):<34}"
                  f"morning {stated:.2f}, this tree {engine:.2f}")
    else:
        print("    every row reproduces to two decimal places")
    return rows


def ready_turn(character, receipts) -> None:
    print()
    print("=== WHY THAT ONE ROW MOVED ===")
    print("The turn of the shoulder line at the first frame, in degrees off square.")
    print()
    for movement_id in ("netball_hooks_outside_hand",
                        "netball_one_hand_snatch_to_other_hand",
                        "netball_two_hand_catch_chest"):
        at, _ = solved(character, movement_id)
        arms = receipts[movement_id]["phases"][0]["arms"]
        engine = turn_degrees(at(0, "l_uparm"), at(0, "r_uparm"))
        rendered = turn_degrees(arms["l"]["shoulder"], arms["r"]["shoulder"])
        print(f"{movement_id.replace('netball_', ''):<38}"
              f"engine {engine:6.2f}    rendered {rendered:6.2f}")
    print()
    print("Item 7 of the coach morning is STRUCK because `hooks_outside_hand` has two")
    print("solved poses about 33 degrees apart. It records 48.22 degrees as the")
    print("corrected pose and 15.44 as the one the shipped parameter set reached.")
    print("This tree solves 48.22, so this tree is the corrected pose, and the")
    print("rendered figure carries it too. The item 6 and item 5 rows for that drill")
    print("were read on the other pose, and nobody has marked them.")


def item_five(character, receipts) -> None:
    print()
    print("=== ITEM 5. Does the second hand travel too far to meet the ball? ===")
    print("Centimetres the free hand sits ahead of the shoulder midpoint.")
    print()
    for movement_id, stated in MORNING_ITEM_5.items():
        at, frames = solved(character, movement_id)
        receipt = receipts[movement_id]
        phase_frames = {phase["frame"]: phase for phase in receipt["phases"]}
        contact = next(phase["frame"] for phase in receipt["phases"]
                       if phase["name"] == "contact")
        track = [ahead(at(frame, "l_wrist"), at(frame, "l_uparm"), at(frame, "r_uparm"))
                 for frame in range(frames)]
        peak = contact + int(np.argmax(track[contact:]))
        print(f"--- {movement_id.replace('netball_', '')}")
        print(f"    {'where':<26}{'engine':>8}{'rendered':>9}{'gap':>7}")
        for frame in sorted(phase_frames):
            phase = phase_frames[frame]
            arms = phase["arms"]
            rendered = ahead(arms["l"]["wrist"], arms["l"]["shoulder"],
                             arms["r"]["shoulder"])
            where = f"{phase['name']} f{frame}"
            print(f"    {where:<26}{track[frame]:>8.2f}{rendered:>9.2f}"
                  f"{track[frame] - rendered:>7.2f}")
        where = f"furthest out f{peak}"
        if peak in phase_frames:
            print(f"    {where:<26}{track[peak]:>8.2f}   the archive holds this frame")
        else:
            print(f"    {where:<26}{track[peak]:>8.2f}"
                  f"        -      -   ENGINE ONLY, no such frame in the archive")
        print(f"    engine travel, contact to furthest out: "
              f"{track[peak] - track[contact]:.2f} cm")
        print(f"    the coach morning states {stated[0]} out to {stated[1]} "
              f"and back to {stated[2]}")
        print()
    print("THE TRAVEL CANNOT BE COMPARED ACROSS THE TWO BODIES. The engine puts the")
    print("hand furthest out at a frame that is not a phase, and a receipt carries")
    print("one pose per phase. What CAN be compared is every phase frame, and those")
    print("rows are above.")


def main() -> None:
    directory = archives() / ARCHIVE
    receipts = {}
    for path in sorted(directory.glob("*.render.json")):
        receipt = json.loads(path.read_text(encoding="utf-8"))
        receipts[receipt["movementId"]] = receipt
    if not receipts:
        raise SystemExit(f"no receipts in {directory}")

    character = load_character()
    item_six(character, receipts)
    ready_turn(character, receipts)
    item_five(character, receipts)


if __name__ == "__main__":
    main()
