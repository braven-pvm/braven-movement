"""Write the solved movement as a job the Blender generator can pose.

The engine solves the movement and Blender owns the athlete and the picture.
This is the boundary between them, and it is the one docs/ARCHITECTURE.md
already describes: the consuming side receives geometry and images, and never
needs the solver.

Nothing absolute crosses the boundary except the ball, because a netball is a
netball. Everything else is a fraction of a bone the receiving body has too:
reach in arm lengths, stance in leg lengths, ball offset in arm lengths. The
MPFB athlete is not the same size or shape as MHR's, and a world coordinate
measured on one body lands in the wrong place on the other. This is the same
unit discipline the rest of the engine uses.

Axes. MHR is Y up, centimetres, and the athlete's left is positive X. Blender
is Z up, metres, and this athlete faces negative Y. Refer to `to_blender`.

    pixi run python export_blender_job.py
    pixi run python export_blender_job.py netball_two_hand_snatch_pull_in
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np

SPIKE_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(SPIKE_DIR))

from ball_track import has_ball  # noqa: E402
from movement_definition import load as load_definition  # noqa: E402
from athlete import minmax_limits  # noqa: E402
from movement_engine import (  # noqa: E402
    definition_path,
    joint_positions,
    library,
    load_character,
)
from possession_solve import solve_movement  # noqa: E402
from technique import has_technique, load_technique, technique_path  # noqa: E402

OUTPUT = SPIKE_DIR / "poc-output"

# The camera positions a manual page wants. The athlete faces negative Y, so a
# front camera stands there.
#
# Blender fits the sensor to the longer side of the image, and these are taller
# than they are wide, so 36 mm covers the height. A 50 mm lens then sees 39.6
# degrees vertically, which is 2.3 m of athlete at 3.2 m away. An 85 mm lens at
# the same distance saw 1.35 m and cut her off at the thigh.
VIEWS = {
    "front": {"locationM": [0.0, -3.20, 1.10], "lensMm": 50.0},
    "quarter": {"locationM": [2.20, -2.35, 1.20], "lensMm": 50.0},
    "side": {"locationM": [3.20, -0.15, 1.10], "lensMm": 50.0},
}
VIEW_RESOLUTION = [1080, 1350]
VIEW_TARGET = [0.0, -0.15, 0.95]

# Carried over from config/reference_catch.v1.json, which measured them against
# a photograph of a real athlete.
#
# These are a calibration of one authored pose, not anatomical limits, and
# fingerBaseDeviation was being used on the receiving side to bound knuckle
# FLEXION. Deviation and flexion are different axes: this model licenses plus
# or minus 45.8 of deviation and up to 90 of flexion, so a deviation-sized
# number was capping a flexion axis and the fingers stopped 26 to 35 mm short
# of the ball. fingerBaseFlexionDegrees below is the replacement. This block is
# left exactly as it was, because deviation still means deviation.
ANATOMY_LIMITS = {
    "forearmRoll": 75.0,
    "wristBend": 45.0,
    "fingerJointBend": 25.0,
    "fingerBaseDeviation": 40.0,
}

FINGERS = ("index", "middle", "ring", "pinky")


def knuckle_flexion_limits(character) -> dict[str, float]:
    """How far each knuckle bends, measured rather than stated.

    The quantity is the GEOMETRIC bend: the angle between wrist-to-knuckle and
    knuckle-to-phalanx. Not a joint rotation. A rotation only means something
    against the rest pose it was measured in, and the two rigs do not share
    one, so a rotation would be a number whose meaning depends on the body.
    The receiving rig subtracts its own rest offset.

    Derived by driving each knuckle's own curl parameter to its limit and
    measuring what the hand does, because the two do not simply add: the rest
    bend is 18.5 on the index and its rotation limit is 90, and the result is
    90.0 rather than 108.5.

    Pure flexion, with the other two knuckle axes at zero. The full envelope
    with all three axes helping reaches 91 to 103, and the solve does use it -
    the index reaches 96.4 at contact on the one-handed drills. So this is a
    flexion licence and not a hard ceiling on the visible angle.
    """
    names = list(character.parameter_transform.names)
    limits = minmax_limits(character)
    index = {n: i for i, n in enumerate(character.skeleton.joint_names)}
    zero = np.zeros(character.parameter_transform.size, dtype=np.float32)

    def bend(points, a, b, c):
        first = points[index[b]] - points[index[a]]
        second = points[index[c]] - points[index[b]]
        cosine = np.dot(first, second) / (
            np.linalg.norm(first) * np.linalg.norm(second)
        )
        return float(np.degrees(np.arccos(np.clip(cosine, -1.0, 1.0))))

    found: dict[str, float] = {}
    for finger in FINGERS:
        parameter = f"l_{finger}1_rz"
        if parameter not in limits or parameter not in names:
            continue
        posed = zero.copy()
        posed[names.index(parameter)] = limits[parameter][1]
        found[finger] = round(
            bend(
                joint_positions(character, posed),
                "l_wrist",
                f"l_{finger}1",
                f"l_{finger}2",
            ),
            1,
        )
    return found


def to_blender(point) -> np.ndarray:
    """MHR centimetres, Y up, to Blender metres, Z up, facing negative Y."""
    x, y, z = np.asarray(point, dtype=np.float64)
    return np.array([x, -z, y]) / 100.0


def unit(vector) -> np.ndarray:
    vector = np.asarray(vector, dtype=np.float64)
    length = np.linalg.norm(vector)
    if length < 1e-9:
        raise ValueError("cannot take the direction of a zero length vector")
    return vector / length


def _pole(shoulder, elbow, wrist) -> np.ndarray:
    """The direction the elbow leaves the line from the shoulder to the wrist.

    The Blender generator rebuilds the elbow from this and the two bone
    lengths, so only the direction crosses, never the position.
    """
    along = unit(wrist - shoulder)
    offset = (elbow - shoulder) - along * np.dot(elbow - shoulder, along)
    return unit(offset)


def _hand(points, index, side: str) -> dict:
    """The hand frame, built exactly as the Blender generator builds it.

    `hand_basis` in blender_mpfb_reference_catch.py takes the finger direction
    from the wrist to the middle knuckle, and the palm normal from that crossed
    with the knuckle line. Building it the same way here means the two agree
    without anyone having to guess a sign.
    """
    wrist = to_blender(points[index[f"{side}_wrist"]])
    middle = to_blender(points[index[f"{side}_middle1"]])
    little = to_blender(points[index[f"{side}_pinky1"]])
    pointer = to_blender(points[index[f"{side}_index1"]])

    finger = unit(middle - wrist)
    lateral = pointer - little
    lateral = lateral - finger * np.dot(lateral, finger)
    lateral = unit(lateral)
    return {
        "fingerDirection": [round(float(v), 6) for v in finger],
        "palmNormal": [round(float(v), 6) for v in np.cross(finger, lateral)],
    }


def _arm(points, index, side: str) -> dict:
    shoulder = to_blender(points[index[f"{side}_uparm"]])
    elbow = to_blender(points[index[f"{side}_lowarm"]])
    wrist = to_blender(points[index[f"{side}_wrist"]])
    arm = np.linalg.norm(elbow - shoulder) + np.linalg.norm(wrist - elbow)
    reach = wrist - shoulder
    return {
        # Where the hand is, as a direction and a fraction of this athlete's
        # own arm. The receiving athlete multiplies by hers.
        "direction": [round(float(v), 6) for v in unit(reach)],
        "reachFraction": round(float(np.linalg.norm(reach) / arm), 6),
        "pole": [round(float(v), 6) for v in _pole(shoulder, elbow, wrist)],
    }


def _stance(points, index) -> dict:
    """The stance, in leg lengths, measured from the pelvis."""
    pelvis = to_blender(points[index["root"]])
    legs = []
    for side in ("l", "r"):
        hip = to_blender(points[index[f"{side}_upleg"]])
        knee = to_blender(points[index[f"{side}_lowleg"]])
        ankle = to_blender(points[index[f"{side}_foot"]])
        legs.append(np.linalg.norm(knee - hip) + np.linalg.norm(ankle - knee))
    leg = float(np.mean(legs))

    ankles = {}
    for side in ("l", "r"):
        ankle = to_blender(points[index[f"{side}_foot"]])
        ankles[side] = [round(float(v), 6) for v in (ankle - pelvis) / leg]
    return {"ankleFromPelvisInLegs": ankles}


def _grip(points, index, centre, radius: float, arm: float) -> dict:
    """Where each hand meets the ball, measured from the ball.

    A grip cannot cross as a direction from the shoulder. The ball is one
    absolute size on every body, so a narrower pair of shoulders needs the
    hands to open further, not the same amount. Sending shoulder directions
    closed this athlete's grip from 19.0 cm between the wrists to 12.1 and put
    both hands in front of the ball instead of either side of it.

    So the ball is placed first and the hands are placed on it, which is what
    the possession model says happens once she has it.
    """
    grip = {}
    for side in ("l", "r"):
        wrist = to_blender(points[index[f"{side}_wrist"]])
        outward = wrist - centre
        grip[side] = {
            "outward": [round(float(v), 6) for v in unit(outward)],
            "wristFromSurfaceInArms": round(
                float((np.linalg.norm(outward) - radius) / arm), 6
            ),
        }
    return grip


def phase_job(result, index, frame: int) -> dict:
    points = result["points"][frame]
    held = result["possession"].frames[frame]

    shoulders = np.stack(
        [to_blender(points[index[f"{side}_uparm"]]) for side in ("l", "r")]
    ).mean(axis=0)
    shoulder = to_blender(points[index["l_uparm"]])
    elbow = to_blender(points[index["l_lowarm"]])
    arm = (np.linalg.norm(elbow - shoulder)
           + np.linalg.norm(to_blender(points[index["l_wrist"]]) - elbow))
    centre = to_blender(held.centre)
    radius = float(result["radiusCm"]) / 100.0

    job = {
        "frame": int(frame),
        "arms": {side: _arm(points, index, side) for side in ("l", "r")},
        "hands": {side: _hand(points, index, side) for side in ("l", "r")},
        "stance": _stance(points, index),
        "ball": {
            # Absolute in metres, because a netball is a netball. Where it sits
            # is relative, because that depends on the body holding it.
            "radiusM": round(radius, 4),
            "fromShouldersInArms": [
                round(float(v), 6) for v in (centre - shoulders) / arm
            ],
            "holding": bool(held.holding),
        },
    }
    # Before she has it the athlete reaches for the ball, and the arms say
    # where the hands go. After she has it the ball says where they go.
    if held.holding:
        job["grip"] = _grip(points, index, centre, radius, arm)
    return job


def build(character, movement_id: str, every: int = 0) -> dict:
    definition = load_definition(definition_path(movement_id))
    result = solve_movement(character, movement_id)
    index = result["index"]
    frames = len(result["points"])

    phases = []
    for phase in definition.phases:
        frame = max(0, min(frames - 1, round(phase.at_phase * (frames - 1))))
        job = phase_job(result, index, frame)
        job["name"] = phase.name
        phases.append(job)

    # Every frame, for animation. The phases are the pictures a manual page
    # wants and these are the movement between them.
    frames_out = []
    if every > 0:
        for frame in range(0, frames, every):
            frames_out.append(phase_job(result, index, frame))

    return {
        "schemaVersion": 1,
        "movementId": movement_id,
        "skill": definition.skill,
        "sport": definition.sport,
        "anatomyLimitsDegrees": dict(ANATOMY_LIMITS),
        # Additive. A reader that does not know this field keeps working on
        # the block above; a reader that does should prefer it for the
        # knuckle, because the block above has no flexion number in it.
        #
        # GEOMETRIC BEND, per digit: the angle between wrist-to-knuckle and
        # knuckle-to-phalanx. Never the word metacarpal, because neither rig
        # has one. Never a joint rotation, because a rotation only means
        # something against the rest pose it was measured in. Subtract your own
        # rest offset to get your own rotation.
        "fingerBaseFlexionDegrees": knuckle_flexion_limits(character),
        "views": {
            name: {
                "resolutionPx": list(VIEW_RESOLUTION),
                "locationM": list(view["locationM"]),
                "targetM": list(VIEW_TARGET),
                "lensMm": view["lensMm"],
                "sensorWidthMm": 36.0,
            }
            for name, view in VIEWS.items()
        },
        "framesPerSecond": float(result["track"].frames_per_second),
        "frameStep": int(every),
        "phases": phases,
        "frames": frames_out,
    }


def main(argv: list[str]) -> int:
    wanted = [value for value in argv[1:] if not value.startswith("--")]
    every = 0
    for value in argv[1:]:
        if value.startswith("--every="):
            every = int(value.split("=", 1)[1])
    if "--all" in argv[1:]:
        wanted = [
            name
            for name in library()
            if has_ball(name)
            and has_technique(name)
            and load_technique(technique_path(name)).possession_ready
        ]
    if not wanted:
        wanted = ["netball_two_hand_snatch_pull_in"]

    # Loading the character reads a 4.5 GB asset directory, so it is loaded
    # once however many movements are asked for.
    character = load_character()
    OUTPUT.mkdir(parents=True, exist_ok=True)
    for movement_id in wanted:
        job = build(character, movement_id, every)
        path = OUTPUT / f"{movement_id}.job.json"
        path.write_text(json.dumps(job, indent=2), encoding="utf-8")
        print(
            f"{len(job['phases'])} phases, {len(job['frames'])} frames -> {path} "
            f"({path.stat().st_size // 1024} KB)"
        )
        for phase in job["phases"]:
            left, right = phase["arms"]["l"], phase["arms"]["r"]
            print(
                f"   {phase['name']:9s} frame {phase['frame']:3d}  "
                f"reach l {left['reachFraction']:.2f} r {right['reachFraction']:.2f}  "
                f"holding {phase['ball']['holding']}"
            )
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
