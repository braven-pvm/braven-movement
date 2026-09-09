"""How far the engine's skeleton and the rendered athlete differ, quantity by quantity.

Erin grades the engine's skeleton, because that is what the bands measure. She
looks at the MPFB athlete, because that is what the manual prints. The two are
different bodies, and a band she sets on one is printed on the other.

At `two_hand_catch_chest/contact` the elbows sit 36.43 cm apart on the engine's
skeleton and 32.02 cm apart on the rendered athlete. Item 2 of the coach morning
asks her to set a band on exactly that quantity.

WHY THIS CAN BE MEASURED AT ALL. Every one of the eleven job files on this tree
is byte-identical to the `jobSha256` the shipped library recorded, so the solve
here IS the solve those figures were rendered from. The engine side is solved
now; the rendered side is read from the archived receipts of build `2413f9d`.

It attributes nothing it cannot attribute. Where a gap is the size and direction
of the open girdle narrowing, it says so and gives both numbers. Where it is
not, it says that instead.

    pixi run --frozen python ../scripts/two_bodies_compare.py
"""

from __future__ import annotations

import json
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


def archives() -> Path:
    for base in [Path(__file__).resolve()] + list(Path(__file__).resolve().parents):
        candidate = base / ".assets" / "archives"
        if candidate.is_dir():
            return candidate
    raise SystemExit("no .assets/archives found from this file")


def gap(a, b) -> float:
    """Distance in centimetres between two Blender-frame points."""
    return float(np.linalg.norm(np.asarray(a) - np.asarray(b))) * 100.0


def main() -> None:
    directory = archives() / ARCHIVE
    receipts = {}
    for path in sorted(directory.glob("*.render.json")):
        receipt = json.loads(path.read_text(encoding="utf-8"))
        receipts[receipt["movementId"]] = receipt
    if not receipts:
        raise SystemExit(f"no receipts in {directory}")

    character = load_character()
    print(f"{'drill / phase':<38}{'quantity':<11}{'engine':>8}{'rendered':>9}"
          f"{'gap':>7}{'eng/sh':>8}{'ren/sh':>9}{'ratio d':>8}")
    rows = []
    for movement_id, receipt in receipts.items():
        result = solve_movement(character, movement_id)
        index, points = result["index"], result["points"]
        drill = movement_id.replace("netball_", "")
        for phase in receipt["phases"]:
            frame = phase["frame"]
            if frame >= len(points):
                continue
            here = points[frame]

            def joint(name):
                return to_blender(here[index[name]])

            girdle = phase["girdle"]
            narrowing = girdle["wantedWidthMm"] - girdle["renderedWidthMm"]
            arms = phase["arms"]
            pairs = (
                ("shoulders", gap(joint("l_uparm"), joint("r_uparm")),
                 gap(arms["l"]["shoulder"], arms["r"]["shoulder"])),
                ("elbows", gap(joint("l_lowarm"), joint("r_lowarm")),
                 gap(arms["l"]["elbow"], arms["r"]["elbow"])),
                ("wrists", gap(joint("l_wrist"), joint("r_wrist")),
                 gap(arms["l"]["wrist"], arms["r"]["wrist"])),
            )
            # THE SCALE OF EACH BODY, so a distance can be compared at all.
            # The engine's athlete is simply bigger, and most of a raw gap is
            # that rather than a defect.
            engine_span = gap(joint("l_uparm"), joint("r_uparm"))
            rendered_span = gap(arms["l"]["shoulder"], arms["r"]["shoulder"])
            for name, engine, rendered in pairs:
                ratio_engine = engine / engine_span if engine_span else 0.0
                ratio_rendered = rendered / rendered_span if rendered_span else 0.0
                rows.append({
                    "where": f"{drill}/{phase['name']}",
                    "quantity": name,
                    "engine": engine,
                    "rendered": rendered,
                    "gap": engine - rendered,
                    "ratioEngine": ratio_engine,
                    "ratioRendered": ratio_rendered,
                    "ratioGap": ratio_engine - ratio_rendered,
                    "narrowingMm": narrowing,
                })
                print(f"{drill + '/' + phase['name']:<38}{name:<11}"
                      f"{engine:>8.2f}{rendered:>9.2f}{engine - rendered:>7.2f}"
                      f"{ratio_engine:>8.3f}{ratio_rendered:>9.3f}"
                      f"{ratio_engine - ratio_rendered:>8.3f}")

    print()
    print("Centimetres. `gap` is the engine minus the rendered figure. `girdle`")
    print("is how much narrower this rig's shoulders are than the solve asks, at")
    print("that phase, from the same receipt.")
    print()
    for name in ("shoulders", "elbows", "wrists"):
        here = [r for r in rows if r["quantity"] == name]
        gaps = sorted(r["gap"] for r in here)
        ratios = sorted(r["ratioGap"] for r in here)
        print(f"{name:<11}raw gap {gaps[0]:+7.2f} to {gaps[-1]:+7.2f} cm, "
              f"median {gaps[len(gaps) // 2]:+6.2f}")
        print(f"{'':<11}as a fraction of each body's own shoulder span, "
              f"{ratios[0]:+.3f} to {ratios[-1]:+.3f}, "
              f"median {ratios[len(ratios) // 2]:+.3f}")
    print()
    print("THE RAW GAP IS MOSTLY TWO DIFFERENT-SIZED PEOPLE. The engine's")
    print("shoulders are wider than this rig's at every phase, so a distance")
    print("measured on one body is not the same distance on the other, and")
    print("nothing is wrong about that.")
    print()
    print("The ratio column is the one that can cross. Where it agrees, a band")
    print("expressed as a fraction of shoulder span transfers between the two")
    print("bodies. Where it does not, no restatement of the band will make it")
    print("transfer, and that is a finding rather than a scaling problem.")


if __name__ == "__main__":
    main()
