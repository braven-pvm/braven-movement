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
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

import numpy as np

SPIKE_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(SPIKE_DIR))

from ball_track import has_ball  # noqa: E402
from movement_definition import load as load_definition  # noqa: E402
from movement_engine import definition_path, library, load_character  # noqa: E402
from possession_solve import solve_movement  # noqa: E402
from technique import has_technique, load_technique, technique_path  # noqa: E402

OUTPUT = SPIKE_DIR / "poc-output" / "video"

# The measures a two-camera lift can plausibly recover. Elbow flexion is the
# one deliverable (d) asks for; the others are here because they cost nothing
# extra and a shoot finding may turn on which of them survive the video.
WANTED = (
    "leftElbowFlexionDegrees",
    "rightElbowFlexionDegrees",
    "leftShoulderElevationDegrees",
    "rightShoulderElevationDegrees",
    "trunkLeanDegrees",
)


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
    found = {}
    for movement_id in drills():
        result = solve_movement(character, movement_id)
        definition = load_definition(definition_path(movement_id))
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
            "curves": {measure: curve(result, measure) for measure in WANTED},
        }
        elbow = [v for v in found[movement_id]["curves"]["leftElbowFlexionDegrees"] if v is not None]
        print(
            f"  {movement_id[8:44]:36s} {frames:4d} frames   "
            f"left elbow {min(elbow):6.1f} to {max(elbow):6.1f} deg   "
            f"contact at phase "
            f"{found[movement_id]['landmarks']['contactPhase']}"
        )

    OUTPUT.mkdir(parents=True, exist_ok=True)
    where = OUTPUT / "reference-curves.json"
    commit = subprocess.run(["git", "rev-parse", "HEAD"], capture_output=True,
                            text=True, cwd=SPIKE_DIR).stdout.strip()
    dirty = subprocess.run(["git", "status", "--porcelain"], capture_output=True,
                           text=True, cwd=SPIKE_DIR).stdout.strip()
    where.write_text(
        json.dumps(
            {
                "generatedFrom": {
                    "commit": commit,
                    "treeWasClean": not dirty,
                    "utcTimestamp": datetime.now(timezone.utc).isoformat(
                        timespec="seconds"
                    ),
                },
                "note": (
                    "Engine curves for comparison against video. Phase runs 0 to 1 "
                    "across each movement, so a clip of a different duration can be "
                    "laid over these. Angles are the engine's own definitions, taken "
                    "from the same measurements build_library grades."
                ),
                "measures": list(WANTED),
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
