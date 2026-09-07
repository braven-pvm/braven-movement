"""A progressive sweep of `ballHeightCm`, on a COPY of the movements directory.

Run it: `pixi run --frozen -- python -B sweep_ball_height.py [--fine]`

WHAT IT SHOWED, on ad7e65d, and the reason it is committed rather than left in
a scratchpad. The coarse sweep, 7 points at 0.12 torso lengths:

    up      ballHeightCm   step    body joint step
    1.42    199.95                 -
    1.30    193.64        -6.31    25.38  r_lowarm
    1.18    187.32        -6.32     6.45  r_wrist_twist
    1.06    181.04        -6.28     6.29  r_wrist_twist
    0.94    174.78        -6.26     6.17  r_wrist_twist
    0.82    168.55        -6.23     6.38  r_lowarm
    0.70    162.35        -6.20     7.29  r_lowarm

37.60 cm of travel, monotone, and the steps agree to 0.12 cm. So a checkpoint
on this measure can fail. But ONE body step is four times the others, at the
SHIPPED value, so the coarse sweep alone would have published a basin.

The fine sweep, 10 points at 0.02, locates it between 1.42 and 1.40:

    up      ballHeightCm   step    lift shoulder   body joint step
    1.44    200.98        -1.04    160.44          4.55
    1.42    199.95        -1.03    159.60          4.78   <- shipped
    1.40    198.91        -1.04    139.26         19.03  r_lowarm
    1.38    197.88        -1.03    135.52          1.88

THE MEASURE DOES NOT SEE IT. `ballHeightCm` steps -1.04 across the boundary,
the same as every other step. The SUBSTITUTE does: at the lift frame
`rightShoulderElevationDegrees` falls 20.34 degrees there, against 0.84 to 3.74
elsewhere, and the elbow reverses sign. The ball goes where it is told whatever
configuration the arm finds to hold it, and an arm measure does not.

NOTHING SHIPPED FAILS BECAUSE OF IT. The lift's graded elbow reads 60.56 and
54.07 across the boundary, inside its 20 to 85 band; the release checkpoints do
not move at all under this lever, 128.48 and 64.63 at every point.

A progressive sweep of `ballHeightCm`, on a COPY of the movements directory.

`spikes/movements/` is gate 4 and is not touched: the whole directory is copied
to a temporary path and the module constants are pointed at the copy, so the
tracked tree is unchanged before, during and after.

THE LEVER is the lift carry's `up` on `netball_one_hand_high_pass`, the key the
drill's own defining cue is about. Five points, spacing stated, each reading
the ball height at the graded lift frame and the largest distance any single
joint moved from the previous point at that frame.
"""
import json
import shutil
import sys
import tempfile
from pathlib import Path

import numpy as np

import ball_track
import movement_engine
import technique
from movement_engine import load_character, joint_positions
from possession_solve import solve_movement

MOVEMENT_ID = "netball_one_hand_high_pass"
LIFT_FRAME = 33
SHIPPED_UP = 1.42
FINE = "--fine" in sys.argv
STEP = 0.02 if FINE else 0.12
POINTS = (
    [round(1.46 - 0.02 * n, 4) for n in range(10)] if FINE
    else [round(SHIPPED_UP - 0.12 * n, 4) for n in range(7)]
)

source = Path(movement_engine.MOVEMENT_DIR)
temporary = Path(tempfile.mkdtemp(prefix="height-sweep-"))
copy = temporary / "movements"
shutil.copytree(source, copy)

for module in (ball_track, movement_engine, technique):
    if hasattr(module, "MOVEMENT_DIR"):
        module.MOVEMENT_DIR = copy
movement_engine.MOVEMENT_DIR = copy
ball_track.MOVEMENT_DIR = copy

path = copy / f"{MOVEMENT_ID}.technique.json"
original = json.loads(path.read_text(encoding="utf-8"))

character = load_character()
print(f"    lever: the lift carry's `up` on {MOVEMENT_ID}")
print(f"    spacing {STEP} torso lengths, {len(POINTS)} points, "
      f"shipped value {SHIPPED_UP}")
print(f"    read at frame {LIFT_FRAME}, the graded lift phase")
print()
print(f"    {'up':>7s} {'ballHeightCm':>13s} {'step':>8s} {'joint step':>11s}")

previous_height = None
previous_points = None
for up in POINTS:
    data = json.loads(json.dumps(original))
    for key in data["afterContact"]:
        if key["name"] == "lift":
            key["up"] = up
    path.write_text(json.dumps(data, indent=2), encoding="utf-8")

    result = solve_movement(character, MOVEMENT_ID)
    row = result["measurements"][LIFT_FRAME]
    height = float(row["ballHeightCm"])
    shoulder = float(row["rightShoulderElevationDegrees"])
    elbow = float(row["rightElbowFlexionDegrees"])
    points = result["points"][LIFT_FRAME]

    move = "" if previous_height is None else f"{height - previous_height:8.2f}"
    joint = ""
    if previous_points is not None:
        moved = np.linalg.norm(points - previous_points, axis=1)
        names = {j: n for n, j in result["index"].items()}
        digits = ("thumb", "index", "middle", "ring", "pinky")
        body = [
            j for j in range(len(moved))
            if not any(d in names.get(j, "") for d in digits)
        ]
        w = int(np.argmax(moved))
        b = body[int(np.argmax(moved[body]))]
        joint = "%8.2f %-12s" % (float(moved[b]), names[b])
    print(f"    {up:7.2f} {height:13.2f} {move:>8s} {shoulder:9.2f} "
          f"{elbow:8.2f} {joint}")
    previous_height, previous_points = height, points

path.write_text(json.dumps(original, indent=2), encoding="utf-8")
shutil.rmtree(temporary, ignore_errors=True)
print()
print(f"    the copy is deleted; {source} was never opened for writing")
