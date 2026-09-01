"""The engine's own angle curves, ready to sit beside a curve read from video.

Deliverable (d) of the video spike puts an elbow flexion curve measured from
real footage next to the engine's curve for the same drill. This writes the
engine half, so that comparison is against a recorded reference rather than
against a solve run at comparison time and never seen again.

It reads what `build_library` already measures. No new angle definition is
invented here: a video curve compared against a differently-defined engine
curve would be the units-across-a-boundary fault this project keeps finding,
wearing a new coat.

Phase, not seconds. A drill filmed at an unknown tempo cannot be compared on a
clock, and every engine curve here runs 0 to 1 over the movement. Matching a
video curve means matching its shape and its phase landmarks, not its duration.

    pixi run python export_reference_curves.py
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np

SPIKE_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(SPIKE_DIR))

from ball_track import has_ball  # noqa: E402
from build_stamp import generated_from  # noqa: E402
from movement_definition import load as load_definition  # noqa: E402
from reference_measures import RECOVERABLE, wanted  # noqa: E402
from movement_engine import definition_path, library, load_character  # noqa: E402
from possession_solve import solve_movement  # noqa: E402
from segment_measures import unit_of  # noqa: E402
from technique import has_technique, load_technique, technique_path  # noqa: E402

OUTPUT = SPIKE_DIR / "poc-output" / "video"

# 1 was the shape with the bare list and no unit anywhere. 2 gives every curve
# a unit and a values list. The number is written into the file so a consumer
# can branch on it rather than sniffing the type of a value.
SCHEMA_VERSION = 2

def drills() -> list[str]:
    return [
        name
        for name in sorted(library())
        if has_ball(name)
        and has_technique(name)
        and load_technique(technique_path(name)).possession_ready
    ]


def curve(result, measure: str) -> list[float | None]:
    return [
        (round(float(frame[measure]), 3) if measure in frame else None)
        for frame in result["measurements"]
    ]


def main(argv: list[str]) -> int:
    character = load_character()
    # The definitions come first, because what gets a curve is derived from
    # them. Reading them inside the loop would mean deciding the measure list
    # from the first drill and applying it to the rest.
    wall = {name: load_definition(definition_path(name)) for name in drills()}
    measures = wanted(list(wall.values()))
    print(f"  {len(measures)} measures: "
          f"{len(set(measures) - set(RECOVERABLE))} graded and newly curved, "
          f"{len(RECOVERABLE)} recoverable")
    found = {}
    for movement_id, definition in wall.items():
        result = solve_movement(character, movement_id)
        frames = len(result["measurements"])
        possession = result["possession"]
        contact = possession.contact_frame
        released = next(
            (n for n, f in enumerate(possession.frames) if f.state == "released"), None
        )
        found[movement_id] = {
            "skill": definition.skill,
            "frames": frames,
            # Phase runs 0 to 1 across the movement, so a video curve of a
            # different duration can still be laid over this one.
            "phase": [round(n / max(frames - 1, 1), 5) for n in range(frames)],
            "landmarks": {
                "contactFrame": contact,
                "contactPhase": (
                    round(contact / max(frames - 1, 1), 4) if contact is not None else None
                ),
                "releaseFrame": released,
                "releasePhase": (
                    round(released / max(frames - 1, 1), 4) if released is not None else None
                ),
                "phases": [
                    {"name": p.name, "atPhase": p.at_phase} for p in definition.phases
                ],
            },
            # EVERY CURVE CARRIES ITS UNIT. `curves[measure]` used to be the
            # list itself, and the file's note called all of it angles. One
            # graded measure is a length, so a file that cannot say which is
            # one bad column away from a video lane reading centimetres as
            # degrees. The unit is read from the engine's own table, never
            # from the measure's name.
            "curves": {
                measure: {
                    "unit": unit_of(measure),
                    "values": curve(result, measure),
                }
                for measure in measures
            },
        }
        elbow = [
            v
            for v in found[movement_id]["curves"]["leftElbowFlexionDegrees"]["values"]
            if v is not None
        ]
        print(
            f"  {movement_id[8:44]:36s} {frames:4d} frames   "
            f"left elbow {min(elbow):6.1f} to {max(elbow):6.1f} deg   "
            f"contact at phase "
            f"{found[movement_id]['landmarks']['contactPhase']}"
        )

    OUTPUT.mkdir(parents=True, exist_ok=True)
    where = OUTPUT / "reference-curves.json"
    where.write_text(
        json.dumps(
            {
                # The shared stamp, not a second copy of it. This file had
                # its own inline version, which is how one shape becomes two
                # that drift.
                # 2 is the shape where every curve is
                # {"unit": ..., "values": [...]}. The unversioned shape that
                # wrote the list directly is 1, named here retrospectively
                # because a reader of an old file has to be able to tell.
                "schemaVersion": SCHEMA_VERSION,
                "generatedFrom": generated_from(),
                "note": (
                    "Engine curves for comparison against video. Phase runs 0 to 1 "
                    "across each movement, so a clip of a different duration can be "
                    "laid over these. Each curve declares its own unit: most are "
                    "the engine's own angle definitions, taken from the same "
                    "measurements build_library grades, and NOT every measure is "
                    "an angle. Read curves[measure][\"values\"] and honour "
                    "curves[measure][\"unit\"]."
                ),
                "measures": list(measures),
                "movements": found,
            },
            indent=1,
        )
        + "\n",
        encoding="utf-8",
    )
    print(f"\nwritten -> {where}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
