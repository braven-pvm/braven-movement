"""Every drill as a skeletal animation, for the coach grading pack.

The pack shows a coach a figure at each coaching phase. A still cannot show
whether a catch looks like a catch, and the phases it grades are moments in a
movement rather than poses in their own right. This writes the movement.

One file, keyed by movement, every solved frame. The pack embeds it at build
time and reads it from this lane's worktree, so it is derived output and is not
committed, like the renders. Provenance travels inside the file instead:
`generatedFrom` records the commit that produced it, and says so honestly when
the tree was dirty, because a commit hash recorded against uncommitted code is
a receipt for something that was never in the repository.

    pixi run python export_coach_animations.py
    pixi run python export_coach_animations.py netball_two_hand_snatch_pull_in
"""

from __future__ import annotations

import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

SPIKE_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(SPIKE_DIR))

from athlete import reference  # noqa: E402
from ball_track import has_ball  # noqa: E402
from movement_definition import load as load_definition  # noqa: E402
from movement_engine import definition_path, library, load_character  # noqa: E402
from possession_solve import solve_movement  # noqa: E402
from render_contact_sheet import BONES  # noqa: E402
from technique import has_technique, load_technique, technique_path  # noqa: E402

OUTPUT = SPIKE_DIR / "poc-output" / "coach"

# The hand is drawn as well as the arm, because the grip is the whole point.
# Taken from export_proof_viewer, which draws the same skeleton.
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


def provenance() -> dict:
    """Which solve produced this, and whether that can be trusted."""

    def git(*arguments: str) -> str | None:
        try:
            done = subprocess.run(
                ["git", *arguments],
                cwd=SPIKE_DIR,
                capture_output=True,
                text=True,
                check=False,
            )
        except OSError:
            return None
        return done.stdout.strip() if done.returncode == 0 else None

    commit = git("rev-parse", "HEAD")
    dirty = git("status", "--porcelain")
    return {
        "commit": commit,
        # A commit hash recorded against a modified tree names code that was
        # never committed. Saying so is the difference between a receipt and a
        # decoration.
        "treeWasClean": None if dirty is None else dirty == "",
        "utcTimestamp": datetime.now(timezone.utc).isoformat(timespec="seconds"),
    }


def animation(character, movement_id: str) -> dict:
    """One drill, every solved frame, in centimetres."""
    result = solve_movement(character, movement_id)
    definition = load_definition(definition_path(movement_id))
    index = result["index"]
    held = result["possession"]
    points = result["points"]
    total = len(points)

    bones = [pair for pair in BONES + HAND_BONES if all(n in index for n in pair)]
    drawn = sorted({name for bone in bones for name in bone})

    frames = []
    for number in range(total):
        frame = held.frames[number]
        frames.append(
            {
                "n": number,
                "j": {
                    name: [round(float(v), 1) for v in points[number][index[name]]]
                    for name in drawn
                },
                "b": [round(float(v), 1) for v in frame.centre],
                # Whether she has the ball on this frame, not whether contact
                # has happened. A drill that releases stops holding again.
                "c": bool(frame.holding),
            }
        )

    return {
        "movementId": movement_id,
        "skill": definition.skill,
        "bones": bones,
        "ballRadiusCm": round(float(result["radiusCm"]), 2),
        "heightCm": round(reference(character).height_cm, 1),
        "fps": float(result["track"].frames_per_second),
        "frames": frames,
        "phases": [
            {
                "name": phase.name,
                "frame": max(0, min(total - 1, round(phase.at_phase * (total - 1)))),
            }
            for phase in definition.phases
        ],
        "contactFrame": held.contact_frame,
    }


def main(argv: list[str]) -> int:
    wanted = argv[1:] or [
        name
        for name in library()
        if has_ball(name)
        and has_technique(name)
        and load_technique(technique_path(name)).possession_ready
    ]
    character = load_character()

    drills = {}
    for movement_id in wanted:
        drills[movement_id] = animation(character, movement_id)
        item = drills[movement_id]
        print(
            f"  {movement_id:42s} {len(item['frames']):3d} frames  "
            f"{len(item['bones']):3d} bones  {len(item['phases'])} phases"
        )

    payload = {
        "schemaVersion": 1,
        "generatedFrom": provenance(),
        "unitsNote": "joint and ball positions are centimetres, Y up",
        "movements": drills,
    }
    OUTPUT.mkdir(parents=True, exist_ok=True)
    path = OUTPUT / "animations.json"
    path.write_text(json.dumps(payload) + "\n", encoding="utf-8")
    where = payload["generatedFrom"]
    clean = where["treeWasClean"]
    print(
        f"\n{len(drills)} movements -> {path} "
        f"({path.stat().st_size // 1024} KB)"
    )
    print(
        f"from {where['commit']}"
        + ("" if clean else "  WITH A MODIFIED TREE, so the commit is not the code")
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
