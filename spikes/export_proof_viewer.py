"""Draw the library, or the proof, side by side.

With no arguments it draws every drill the library builds, each one solved by
the ball. With a movement id it draws that drill against every pass it has,
which is the proof: one technique, several arrival points, nothing else changed.
With "squad" and a movement id it draws one drill performed by five bodies.

The numbers in build_library.py and proof.py are the authority. This exists
because the claims being made are claims about movement, and a table cannot
show whether a catch looks like a catch.

    pixi run python export_proof_viewer.py
    pixi run python export_proof_viewer.py netball_two_hand_snatch_pull_in
    pixi run python export_proof_viewer.py squad netball_two_hand_snatch_pull_in
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np

SPIKE_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(SPIKE_DIR))

from athlete import squad  # noqa: E402
from ball_track import ball_variants, has_ball  # noqa: E402
from movement_definition import load as load_definition  # noqa: E402
from movement_engine import (  # noqa: E402
    definition_path,
    library,
    load_character,
)
from technique import (  # noqa: E402
    has_technique,
    load_technique,
    technique_path,
)
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


def collect(
    character, movement_id: str, variant: str | None, athlete=None
) -> dict:
    result = solve_movement(
        character, movement_id, variant, None if athlete is None else athlete.identity
    )
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
        "heightCm": None if athlete is None else round(athlete.height_cm, 1),
        "armCm": None if athlete is None else round(athlete.arm_cm, 2),
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
    character = load_character()
    if len(argv) > 2 and argv[1] == "squad":
        movement_id = argv[2]
        runs = []
        for athlete in squad(character):
            run = collect(character, movement_id, None, athlete)
            run["variant"] = athlete.name
            runs.append(run)
        title = "Five Bodies, One Drill"
        heading = "The same drill, five bodies"
        lede = (
            "One drill, one technique file, five athletes: the reference, the "
            "shortest and tallest this model will make, and two of the same "
            "height whose reach differs by a tenth either way. <b>Nothing was "
            "re-authored for any of them</b>. Watch the ball: it arrives at each "
            "athlete's own arm span and finishes at her own chest, and her "
            "joints do whatever her proportions require, which is the point."
        )
    elif len(argv) > 1:
        movement_id = argv[1]
        variants = ball_variants(movement_id)
        if len(variants) < 2:
            print(f"{movement_id} has only one ball trajectory")
            return 1
        runs = [collect(character, movement_id, variant) for variant in variants]
        title = "Four Balls, One Technique"
        heading = "Four balls, one technique"
        lede = (
            "Same athlete, same movement file, same technique file. The only "
            "thing that differs between these four is where the passer put the "
            "ball. <b>Nothing about the hands is authored anywhere</b>: the "
            "grip decides where on the ball each palm belongs and the solver "
            "puts the hands there. Watch the wide catch, where she turns to "
            "the ball rather than reaching across for it."
        )
    else:
        movement_id = "library"
        runs = []
        for name in library():
            if not (has_ball(name) and has_technique(name)):
                continue
            if not load_technique(technique_path(name)).possession_ready:
                continue
            run = collect(character, name, None)
            run["variant"] = load_definition(definition_path(name)).skill
            runs.append(run)
        title = "The Ball Moves Her"
        heading = "The ball moves her"
        lede = (
            "Every netball drill in the library, each one driven by the ball "
            "rather than by an authored hand path. <b>Nothing about the hands "
            "is written down anywhere</b>: the pass is a real parabola, the "
            "grip decides where on the ball each palm belongs, and the solver "
            "puts the hands there. The ball is pale while it is in flight and "
            "solid once she has it."
        )
    bones = [
        list(pair)
        for pair in BONES + HAND_BONES
        if all(n in runs[0]["frames"][0]["j"] for n in pair)
    ]
    payload = {
        "movementId": movement_id,
        "bones": bones,
        "ballRadiusCm": 11.0,
        "sharedScale": bool(len(argv) > 2 and argv[1] == "squad"),
        "heading": heading,
        "lede": lede,
        "runs": runs,
    }
    page = (
        TEMPLATE.read_text(encoding="utf-8")
        .replace("__TITLE__", title)
        .replace("__DATA__", json.dumps(payload))
    )
    OUTPUT.mkdir(parents=True, exist_ok=True)
    stem = movement_id if "squad" not in argv else f"{movement_id}.squad"
    path = OUTPUT / f"{stem}.proof.html"
    path.write_text(page, encoding="utf-8")
    print(f"{path}  ({path.stat().st_size // 1024} KB)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
