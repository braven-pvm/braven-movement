"""Draw the proof: one technique, four arrival points, nothing else changed.

The numbers in proof.py are the authority. This exists because the claim being
made is a claim about movement, and a table cannot show whether a catch looks
like a catch.

Every panel is the same athlete, the same motion file and the same technique
file. The only difference between them is where the passer put the ball.

    pixi run python export_proof_viewer.py
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np

SPIKE_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(SPIKE_DIR))

from ball_track import ball_variants  # noqa: E402
from movement_engine import load_character  # noqa: E402
from possession_solve import solve_movement, spike_report, step_report  # noqa: E402
from render_contact_sheet import BONES  # noqa: E402

OUTPUT = SPIKE_DIR / "poc-output"
TEMPLATE = SPIKE_DIR / "proof_viewer_template.html"
DEFAULT = "netball_two_hand_snatch_pull_in"

# The hand is drawn as well as the arm, because the grip is the whole point.
HAND_BONES = [
    (f"{side}_wrist", f"{side}_{finger}1")
    for side in ("l", "r")
    for finger in ("index", "middle", "ring", "pinky", "thumb")
] + [
    (f"{side}_{finger}{segment}", f"{side}_{finger}{segment + 1}")
    for side in ("l", "r")
    for finger in ("index", "middle", "ring", "pinky", "thumb")
    for segment in (1, 2)
]
# Every third frame. Ninety-eight frames of a full skeleton is more data than a
# page needs, and the movement reads the same at 20 frames per second.
KEEP_EVERY = 3


def collect(character, movement_id: str, variant: str | None) -> dict:
    result = solve_movement(character, movement_id, variant)
    index = result["index"]
    held = result["possession"]
    bones = [pair for pair in BONES + HAND_BONES if all(n in index for n in pair)]
    drawn = sorted({name for bone in bones for name in bone})

    keep = sorted(
        {0, held.contact_frame, len(held.frames) - 1}
        | set(range(0, len(held.frames), KEEP_EVERY))
    )
    frames = []
    for number in keep:
        points = result["points"][number]
        frame = held.frames[number]
        frames.append(
            {
                "n": number,
                "j": {
                    name: [round(float(v), 1) for v in points[index[name]]]
                    for name in drawn
                },
                "b": [round(float(v), 1) for v in frame.centre],
                "s": frame.state,
                "c": number >= held.contact_frame,
            }
        )

    steps = step_report(result["measurements"])
    return {
        "variant": variant or "central",
        "frames": frames,
        "contactFrame": held.contact_frame,
        "turnedByDegrees": result["turnedByDegrees"],
        "catchHeightCm": round(float(held.frames[held.contact_frame].centre[1]), 1),
        "fastestDegreesPerSecond": round(
            max(steps.values()) * result["track"].frames_per_second
        ),
        "spike": spike_report(result["measurements"])["worstNeighbourRatio"],
        "elbowAtContact": round(
            result["measurements"][held.contact_frame]["leftElbowFlexionDegrees"], 1
        ),
    }


def main(argv: list[str]) -> int:
    movement_id = argv[1] if len(argv) > 1 else DEFAULT
    variants = ball_variants(movement_id)
    if len(variants) < 2:
        print(f"{movement_id} has only one ball trajectory")
        return 1

    character = load_character()
    runs = [collect(character, movement_id, variant) for variant in variants]
    bones = [
        list(pair)
        for pair in BONES + HAND_BONES
        if all(n in runs[0]["frames"][0]["j"] for n in pair)
    ]
    payload = {
        "movementId": movement_id,
        "bones": bones,
        "ballRadiusCm": 11.0,
        "runs": runs,
    }
    page = TEMPLATE.read_text(encoding="utf-8").replace(
        "__DATA__", json.dumps(payload)
    )
    OUTPUT.mkdir(parents=True, exist_ok=True)
    path = OUTPUT / f"{movement_id}.proof.html"
    path.write_text(page, encoding="utf-8")
    print(f"{path}  ({path.stat().st_size // 1024} KB)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
