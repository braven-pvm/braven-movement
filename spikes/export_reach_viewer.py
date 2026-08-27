"""Draw the reach report, so the numbers can be checked by eye.

The report in ``ball_reach.py`` is the authority. This only draws it, and it
draws the one thing the table cannot show: where the ball is relative to what
the athlete can actually touch.

The dashed arc is exact rather than indicative. It is the set of ball centres
the palm could reach, sliced through the plane the ball is flying in, so the
ball centre being inside the arc means reachable and outside means not. Slicing
matters: the shoulder sits 17.6 cm to the side of the ball's line, and drawing
the full arm length as a flat circle would overstate the reach by 3 cm.

The athlete is the existing solve of the existing hand keys. She is not
reaching for this ball, and she is not meant to be yet. Watching her miss it is
the point of the milestone.

Her drawn shoulder and the centre of the arc are not the same point. The arc is
centred where the trunk holds the shoulder, which is what the report measures
from, and the solver moves the shoulder a few centimetres from there during a
reach. Drawing the arc around the solved shoulder instead made the picture
disagree with its own table by 6 cm.

    pixi run python export_reach_viewer.py
"""

from __future__ import annotations

import json
import math
import sys
from pathlib import Path

import numpy as np

SPIKE_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(SPIKE_DIR))

from ball_reach import reach_envelope, report  # noqa: E402
from ball_track import ball_path, has_ball, load_ball, stance_frame  # noqa: E402
from motion_track import arm_length, load_motion  # noqa: E402
from movement_engine import (  # noqa: E402
    joint_positions,
    load_character,
    motion_path,
    solve,
)
from render_contact_sheet import BONES  # noqa: E402

OUTPUT = SPIKE_DIR / "poc-output"
DEFAULT = "netball_two_hand_snatch_pull_in"


def collect(character, movement_id: str) -> dict:
    track = load_motion(motion_path(movement_id))
    ball = load_ball(ball_path(movement_id))
    result = solve(character, track)
    index = result["index"]
    reach = report(character, movement_id)

    rest = np.zeros(character.parameter_transform.size, dtype=np.float32)
    rest_positions = joint_positions(character, rest)
    reach_cm = arm_length(rest_positions, index)
    radius_cm = ball.radius_cm_for(reach_cm)

    def segment(first: str, second: str) -> float:
        return float(
            np.linalg.norm(rest_positions[index[first]] - rest_positions[index[second]])
        )

    envelope = reach_envelope(
        upper_cm=segment("l_uparm", "l_lowarm"),
        fore_cm=segment("l_lowarm", "l_wrist"),
        palm_cm=segment("l_wrist", "l_middle1"),
    )

    drawn = sorted({name for bone in BONES for name in bone if name in index})
    frames = []
    for number, points in enumerate(result["points"]):
        row = reach["frames"][number]
        ball_cm = row["ballCm"]
        frames.append(
            {
                "joints": {
                    name: [round(float(value), 1) for value in points[index[name]]]
                    for name in drawn
                },
                "ball": ball_cm,
                # The shoulders the report measured from, not the ones the
                # solver produced. Drawing the arc around the solved shoulder
                # put it 6 cm from where the number came from, so the picture
                # and the table disagreed.
                "shoulders": row["shouldersCm"],
                "state": row["state"],
                # The nearer hand. Reaching a ball takes one hand, not two.
                "margin": max(row["left"]["marginCm"], row["right"]["marginCm"]),
                "verdict": row["verdict"],
            }
        )

    return {
        "movementId": movement_id,
        "frames": frames,
        "bones": [list(bone) for bone in BONES if all(n in index for n in bone)],
        "ballRadiusCm": round(radius_cm, 2),
        "farCm": round(envelope.far_cm, 2),
        "releasePhase": ball.release_phase,
        "arrivalPhase": ball.arrival_phase,
        "framesPerSecond": track.frames_per_second,
        "reach": reach["reach"],
        "entersReachAtPhase": reach["entersReachAtPhase"],
        "framesOutOfReach": reach["framesOutOfReach"],
    }


TEMPLATE = SPIKE_DIR / "reach_viewer_template.html"


def main(argv: list[str]) -> int:
    wanted = argv[1:] or [DEFAULT]
    missing = [name for name in wanted if not has_ball(name)]
    for name in missing:
        print(f"{name}: no ball trajectory yet")
    wanted = [name for name in wanted if has_ball(name)]
    if not wanted:
        return 1

    character = load_character()
    OUTPUT.mkdir(parents=True, exist_ok=True)
    for movement_id in wanted:
        payload = collect(character, movement_id)
        page = TEMPLATE.read_text(encoding="utf-8").replace(
            "__DATA__", json.dumps(payload)
        )
        path = OUTPUT / f"{movement_id}.reach.html"
        path.write_text(page, encoding="utf-8")
        print(f"{movement_id} -> {path}  ({path.stat().st_size // 1024} KB)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
