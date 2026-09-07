"""The instruments behind every figure the `ballHeightCm` ledger row quotes.

    pixi run --frozen -- python -B sweep_ball_height.py           the sweep
    pixi run --frozen -- python -B sweep_ball_height.py --fine    across the basin
    pixi run --frozen -- python -B sweep_ball_height.py --wrist   ball against wrist

GATE 4 IS NOT TOUCHED. `spikes/movements/` is copied to a temporary directory
and the module constants are pointed at the copy, so the tracked tree is
unchanged before, during and after. Check it with
`git status --porcelain -- spikes/movements` after a run.

EVERY HEIGHT HERE IS ABOVE THE COURT, y = 0, which is the zero `ballHeightCm`
uses. The rest `l_foot` ANKLE sits 7.3886 cm above that and is the zero the
three foot heights use. An earlier draft of the ledger quoted the
follow-through pair from the ankle zero, inside the very row whose subject is
that two zeros must not be confused, so this file prints the zero it used.

WHAT THE SWEEP SHOWED, on ad7e65d. Coarse, 7 points at 0.12 torso lengths on
the lift carry's `up`, read at the graded lift frame 33:

    up      ballHeightCm   step    body joint step
    1.42    199.95                 -
    1.30    193.64        -6.31    25.38  r_lowarm
    1.18    187.32        -6.32     6.45  r_wrist_twist
    1.06    181.04        -6.28     6.29  r_wrist_twist
    0.94    174.78        -6.26     6.17  r_wrist_twist
    0.82    168.55        -6.23     6.38  r_lowarm
    0.70    162.35        -6.20     7.29  r_lowarm

37.60 cm of travel, monotone, the steps agreeing to 0.12 cm. So a checkpoint on
this measure can fail. BUT ONE BODY STEP IS FOUR TIMES THE OTHERS AND IT SITS
AT THE SHIPPED VALUE, so the coarse sweep alone would have published a basin.

Fine, 10 points at 0.02, locates it between `up` 1.42 and 1.40:

    up      ballHeightCm   step    lift shoulder   body joint step
    1.44    200.98        -1.04    160.44           4.55
    1.42    199.95        -1.03    159.60           4.78   <- shipped
    1.40    198.91        -1.04    139.26          19.03  r_lowarm
    1.38    197.88        -1.03    135.52           1.88

THE MEASURE DOES NOT SEE IT. `ballHeightCm` steps -1.04 across the boundary,
the same as every other step. The SUBSTITUTE does: at the lift frame
`rightShoulderElevationDegrees` falls 20.34 degrees there, against 0.84 to 3.74
elsewhere, and the elbow reverses sign. The ball goes where it is told whatever
configuration the arm finds to hold it, and an arm measure does not.

NOTHING SHIPPED FAILS BECAUSE OF IT. The lift's graded elbow reads 60.56 and
54.07 across the boundary, inside its 20 to 85 band. The release checkpoints
barely move under this lever -- and "barely" is measured, not assumed, which is
why the release columns are printed here. Refer to the ledger row.
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
from movement_engine import joint_positions, load_character
from possession_solve import solve_movement

MOVEMENT_ID = "netball_one_hand_high_pass"
LIFT_FRAME = 33
RELEASE_FRAME = 76
SHIPPED_UP = 1.42

FINE = "--fine" in sys.argv
WRIST = "--wrist" in sys.argv

# The digits re-wrap the ball at every arm angle, so the largest-moving joint is
# almost always a finger and says nothing about the body finding another
# solution. The discontinuity statistic is therefore the largest step among the
# NON-digit joints, and both are available here.
DIGITS = ("thumb", "index", "middle", "ring", "pinky")


def redirected():
    """Point the movement loaders at a copy and return it.

    EVERY MODULE THAT HOLDS ITS OWN BINDING MUST BE SET, and `technique` is the
    one that matters most here, because the lever this file sweeps lives in the
    technique file. `technique.py` does `from ball_track import MOVEMENT_DIR`,
    which binds the VALUE at import, so setting `ball_track.MOVEMENT_DIR` does
    not reach it. A draft of this file missed that and every sweep point came
    back identical -- an instrument reporting that its own lever does nothing.
    `flat_sweep_is_a_broken_instrument` below refuses to let that be a result.
    """
    source = Path(movement_engine.MOVEMENT_DIR)
    copy = Path(tempfile.mkdtemp(prefix="height-sweep-")) / "movements"
    shutil.copytree(source, copy)
    for module in (movement_engine, ball_track, technique):
        if hasattr(module, "MOVEMENT_DIR"):
            module.MOVEMENT_DIR = copy
    return source, copy


def body_step(result, points, previous):
    """The largest move of a non-digit joint, and its name."""
    moved = np.linalg.norm(points - previous, axis=1)
    names = {joint: name for name, joint in result["index"].items()}
    body = [
        joint for joint in range(len(moved))
        if not any(digit in names.get(joint, "") for digit in DIGITS)
    ]
    where = body[int(np.argmax(moved[body]))]
    return float(moved[where]), names[where]


def sweep(character, copy) -> None:
    points_swept = (
        [round(1.46 - 0.02 * n, 4) for n in range(10)] if FINE
        else [round(SHIPPED_UP - 0.12 * n, 4) for n in range(7)]
    )
    spacing = 0.02 if FINE else 0.12
    path = copy / f"{MOVEMENT_ID}.technique.json"
    original = json.loads(path.read_text(encoding="utf-8"))

    print(f"    lever: the lift carry's `up` on {MOVEMENT_ID}")
    print(f"    spacing {spacing} torso lengths, {len(points_swept)} points, "
          f"shipped value {SHIPPED_UP}")
    print(f"    ball height read at frame {LIFT_FRAME}, the graded lift phase;"
          f" release columns at frame {RELEASE_FRAME}")
    print()
    print(f"    {'up':>6s} {'ballHeightCm':>13s} {'step':>7s} "
          f"{'lift shldr':>11s} {'rel shldr':>10s} {'rel elbow':>10s} "
          f"{'body joint step':>16s}")

    previous_height, previous_points, readings = None, None, []
    for up in points_swept:
        data = json.loads(json.dumps(original))
        for key in data["afterContact"]:
            if key["name"] == "lift":
                key["up"] = up
        path.write_text(json.dumps(data, indent=2), encoding="utf-8")

        result = solve_movement(character, MOVEMENT_ID)
        lift = result["measurements"][LIFT_FRAME]
        release = result["measurements"][RELEASE_FRAME]
        height = float(lift["ballHeightCm"])
        points = result["points"][LIFT_FRAME]

        step = "" if previous_height is None else f"{height - previous_height:7.2f}"
        joint = ""
        if previous_points is not None:
            distance, name = body_step(result, points, previous_points)
            joint = f"{distance:9.2f}  {name}"
        print(f"    {up:6.2f} {height:13.2f} {step:>7s} "
              f"{float(lift['rightShoulderElevationDegrees']):11.2f} "
              f"{float(release['rightShoulderElevationDegrees']):10.2f} "
              f"{float(release['rightElbowFlexionDegrees']):10.2f} {joint}")
        readings.append(height)
        previous_height, previous_points = height, points

    path.write_text(json.dumps(original, indent=2), encoding="utf-8")

    # AN INSTRUMENT THAT REPORTS NO MOVEMENT HAS NOT MEASURED NO MOVEMENT.
    # It has usually failed to reach what it was pointed at. A flat sweep here
    # means the redirect missed a module, not that the lever is inert.
    span = max(readings) - min(readings)
    if span < 1.0:
        raise SystemExit(
            f"    REFUSED: the ball height moved {span:.4f} cm across "
            f"{len(readings)} points. The lever is not reaching the solve; "
            "check that every module holding its own MOVEMENT_DIR was set."
        )
    print()
    print(f"    the ball height moved {span:.2f} cm across the sweep")


def wrist(character) -> None:
    """The ball against the wrist, the peaks, and the follow-through pair.

    Every figure the ledger quotes for "there is no wrist height", measured
    here so the table is not a number without an instrument.
    """
    print("    ball centre minus the HOLDING wrist, over the frames she holds")
    print(f"    {'drill':32s} {'frames':>6s} {'lowest':>16s} {'highest':>16s} "
          f"{'spread':>7s}")
    for movement_id in (
        "netball_one_hand_high_pass",
        "netball_overhead_pass",
        "netball_chest_pass",
    ):
        result = solve_movement(character, movement_id)
        index, points = result["index"], result["points"]
        offsets = []
        for number, frame in enumerate(result["possession"].frames):
            if not (frame.holding and frame.sides):
                continue
            side = sorted(frame.sides)[0] if len(frame.sides) == 1 else "l"
            wrist_y = float(points[number][index[f"{side}_wrist"]][1])
            offsets.append((float(frame.centre[1]) - wrist_y, number))
        low, high = min(offsets), max(offsets)
        print(f"    {movement_id:32s} {len(offsets):6d} "
              f"{low[0]:8.2f} (f{low[1]:<3d}) {high[0]:8.2f} (f{high[1]:<3d}) "
              f"{high[0] - low[0]:7.2f}")

    print()
    print("    the peaks, and the follow-through, ABOVE THE COURT")
    for movement_id in ("netball_one_hand_high_pass", "netball_overhead_pass"):
        result = solve_movement(character, movement_id)
        index, points = result["index"], result["points"]
        frames = result["possession"].frames
        balls = [float(f.centre[1]) for f in frames]
        wrists = [float(p[index["r_wrist"]][1]) for p in points]
        print(f"    {movement_id}: ball peaks {max(balls):.2f} at frame "
              f"{balls.index(max(balls))}, right wrist peaks {max(wrists):.2f} "
              f"at frame {wrists.index(max(wrists))}")

    result = solve_movement(character, "netball_overhead_pass")
    index, points = result["index"], result["points"]
    last = len(points) - 1
    ball = float(result["possession"].frames[last].centre[1])
    hand = float(points[last][index["r_wrist"]][1])
    print(f"    netball_overhead_pass follow_through, frame {last}: "
          f"ball {ball:.2f}, right wrist {hand:.2f}, "
          f"ball {hand - ball:.2f} cm BELOW the hand")


def main() -> int:
    source, copy = redirected()
    character = load_character()
    rest = joint_positions(
        character, solve_movement(character, MOVEMENT_ID)["identity"]
    )
    index = solve_movement(character, MOVEMENT_ID)["index"]
    print(f"    the court is y = 0; the rest l_foot ANKLE sits "
          f"{float(rest[index['l_foot']][1]):.4f} cm above it")
    print()
    if WRIST:
        wrist(character)
    else:
        sweep(character, copy)
    shutil.rmtree(copy.parent, ignore_errors=True)
    print()
    print(f"    the copy is deleted; {source} was never opened for writing")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
