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
# of the ball. knuckleLimitsDegrees below is the replacement. This block is
# left exactly as it was, because deviation still means deviation.
ANATOMY_LIMITS = {
    "forearmRoll": 75.0,
    "wristBend": 45.0,
    "fingerJointBend": 25.0,
    "fingerBaseDeviation": 40.0,
}

# The thumb is included. Its knuckle is thumb1, with the same axis naming
# as a finger, and its limits are materially tighter.
DIGITS = ("index", "middle", "ring", "pinky", "thumb")


def knuckle_limits(character) -> dict[str, dict]:
    """What each knuckle is licensed to do, measured rather than stated.

    ROTATIONS about the joint's own axes, per digit, in degrees. A consumer
    must resolve its own rotation into that frame before comparing.

    The quantity matters and the first version of this got it wrong. A POSE
    crosses a body boundary as geometry, because a rotation only means
    something against the rest pose it was measured in and two rigs do not
    share one. A RANGE OF MOTION crosses as a rotation about the anatomical
    axis, because that is an anatomical fact about the joint rather than a
    configuration. This is a range of motion. Exporting it as visible bend
    made it comparable to nothing a consumer computes.

    Visible bend is still reported, clearly labelled, because it is what stops
    someone clipping a legal pose. It is measured by driving the curl axis to
    its limit with the other two at zero, never computed by addition: the
    index rests at 18.5 with a rotation limit of 90 and reaches 90.0 of
    visible bend, not 108.5.
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

    def degrees(parameter: str) -> dict | None:
        if parameter not in limits or parameter not in names:
            return None
        low, high = limits[parameter]
        return {
            "min": round(float(np.degrees(low)), 1),
            "max": round(float(np.degrees(high)), 1),
        }

    found: dict[str, dict] = {}
    for digit in DIGITS:
        curl = f"l_{digit}1_rz"
        flexion = degrees(curl)
        if flexion is None:
            continue
        posed = zero.copy()
        posed[names.index(curl)] = limits[curl][1]
        found[digit] = {
            # About the joint's own curl axis. Resolve into that frame first.
            "flexion": flexion,
            # About the joint's own deviation axis, side to side.
            "deviation": degrees(f"l_{digit}1_ry"),
            # Informational. What the hand visibly does at the flexion limit
            # with the other two axes at zero. Not a ceiling: the solve reaches
            # 96.4 on the index, legally, with the other axes contributing.
            "visibleBendAtFlexionLimit": round(
                bend(
                    joint_positions(character, posed),
                    "l_wrist",
                    f"l_{digit}1",
                    f"l_{digit}2",
                ),
                1,
            ),
        }
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


def blender_arm(points, index, side: str = "l") -> float:
    """The arm length, shoulder to elbow to wrist, IN BLENDER METRES.

    `motion_track.arm_length` is the same span in the rig's centimetres. This
    one divides the metre-valued spans this job sends, so it is measured in the
    frame those spans are measured in. Two names because they are two numbers,
    a hundred apart.

    It was written inline in two places. One of them is the divisor under
    `grip`, which a guard could only rebuild by restating the formula — and a
    guard that restates a formula agrees with itself rather than with the code.
    """
    shoulder = to_blender(points[index[f"{side}_uparm"]])
    elbow = to_blender(points[index[f"{side}_lowarm"]])
    wrist = to_blender(points[index[f"{side}_wrist"]])
    return float(
        np.linalg.norm(elbow - shoulder) + np.linalg.norm(wrist - elbow)
    )


def _arm(points, index, side: str) -> dict:
    shoulder = to_blender(points[index[f"{side}_uparm"]])
    elbow = to_blender(points[index[f"{side}_lowarm"]])
    wrist = to_blender(points[index[f"{side}_wrist"]])
    arm = blender_arm(points, index, side)
    reach = wrist - shoulder
    return {
        # Where the hand is, as a direction and a fraction of this athlete's
        # own arm. The receiving athlete multiplies by hers.
        "direction": [round(float(v), 6) for v in unit(reach)],
        "reachFraction": round(float(np.linalg.norm(reach) / arm), 6),
        "pole": [round(float(v), 6) for v in _pole(shoulder, elbow, wrist)],
    }



def rest_torso(rest_points, index) -> float:
    """The distance from the pelvis to the shoulder midpoint, at REST.

    The unit the shoulder positions cross in, and the counterpart of the leg
    length `_stance` computes: each body derives it from its OWN rest pose, so
    nothing has to be told what it is and the two sides cannot disagree about
    a number neither transmitted.

    IT IS A TORSO LENGTH AND NOT AN ARM LENGTH, which was measured rather than
    assumed. A shoulder-above-pelvis distance is a torso quantity, and the
    first ruling for this field said arm lengths, as everything else in the job
    uses. Four lengths decide it, and each is named with the rig it came from:

        this athlete's arm          52.680 cm    the rendering rig's  48.547
        this athlete's rest torso   49.6456      the rendering rig's  42.7689

    The two ratios are 0.9215 for the arms and 0.8615 for the rest torsos, so
    an arm divisor is 6.5 per cent wrong on a torso span. Sent as arms, this
    athlete's 48.8246 cm shoulder height at `chest_pass/ready` resolves to
    45.00 cm on a rig whose own rest torso is 42.7689 — 2.23 cm out, against a
    rule of 1 cm, on the very phase the field exists to protect. A torso
    divisor gives 0.71 cm in the other direction, which is a girdle slightly
    compressed from rest at neutral on one body reading as slightly compressed
    on the other.

    AN EARLIER VERSION OF THIS DOCSTRING SAID "its shoulder-above-pelvis is
    0.8759" AND THAT NUMBER IS WITHDRAWN. It is 42.7689 / 48.8246: the
    rendering rig's REST torso over this athlete's POSED shoulder height. Two
    rigs, one at rest and one posed, one measured in three axes and one
    vertical — a single label over two quantities, which is the fault this
    whole field exists to fix. The rendering lane does not recognise the
    figure, and is right not to. The 2.23 cm never depended on it.
    """
    pelvis = to_blender(rest_points[index["root"]])
    middle = np.stack(
        [to_blender(rest_points[index[f"{side}_uparm"]]) for side in ("l", "r")]
    ).mean(axis=0)
    return float(np.linalg.norm(middle - pelvis))


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


def _grip(points, index, centre, radius: float, arm: float, sides) -> dict:
    """Where each HOLDING hand meets the ball, measured from the ball.

    A grip cannot cross as a direction from the shoulder. The ball is one
    absolute size on every body, so a narrower pair of shoulders needs the
    hands to open further, not the same amount. Sending shoulder directions
    closed this athlete's grip from 19.0 cm between the wrists to 12.1 and put
    both hands in front of the ball instead of either side of it.

    So the ball is placed first and the hands are placed on it, which is what
    the possession model says happens once she has it.

    Only the hands that are ON the ball. This used to emit both regardless,
    which told the receiving side that a hand still travelling toward the ball
    was gripping it at whatever standoff it happened to have. On a one-handed
    contact that is a lie about the athlete: `sides_at` says one hand, and the
    other is being shaped around the point it is moving toward. Their standoffs
    are not comparable and the second one is not a grip at all. A hand absent
    from this block is placed from `arms`, the same way every hand is before
    contact.
    """
    grip = {}
    for side in sides:
        wrist = to_blender(points[index[f"{side}_wrist"]])
        outward = wrist - centre
        grip[side] = {
            "outward": [round(float(v), 6) for v in unit(outward)],
            "wristFromSurfaceInArms": round(
                float((np.linalg.norm(outward) - radius) / arm), 6
            ),
        }
    return grip


def phase_job(result, index, frame: int, method, rest_points) -> dict:
    points = result["points"][frame]
    held = result["possession"].frames[frame]

    shoulders = np.stack(
        [to_blender(points[index[f"{side}_uparm"]]) for side in ("l", "r")]
    ).mean(axis=0)
    arm = blender_arm(points, index)
    centre = to_blender(held.centre)
    radius = float(result["radiusCm"]) / 100.0
    torso = rest_torso(rest_points, index)

    job = {
        "frame": int(frame),
        "arms": {side: _arm(points, index, side) for side in ("l", "r")},
        "hands": {side: _hand(points, index, side) for side in ("l", "r")},
        "stance": _stance(points, index),
        # THE ANCHOR `fromShouldersInArms` IS MEASURED FROM, which this job did
        # not transmit until 2026-09-04. A consumer was told where the ball sits
        # relative to the shoulder midpoint and never told where that midpoint
        # is, so it had to guess — and the rendering lane's guess was to leave
        # the shoulder girdle at rest, because nothing in the job asked it to
        # move.
        #
        # THE GIRDLE MOVES ON EVERY DRILL, AND A WIDTH RANGE CANNOT SEE IT.
        # The midpoint travels 8.45 cm relative to the pelvis within
        # `netball_overhead_pass`, 5.02 within `netball_deflect_high`, and 1.77
        # on the quietest drill in the library. 31 of the 48 graded phases sit
        # more than a centimetre from the neutral girdle, so the re-render is
        # the whole library and not the loudest few drills.
        #
        # AN EARLIER VERSION OF THIS COMMENT QUOTED A WIDTH RANGE AND SET SEVEN
        # DRILLS ASIDE AT 0.65 TO 1.05 cm. Width is one axis of three.
        # `netball_bounce_pass` moves almost entirely FORE AND AFT — 2.46 to
        # 0.54 cm ahead of the pelvis, with the width barely changing — so on a
        # width check that drill reads as the CLEANEST in the library and
        # ships. That is why this field sends two positions.
        #
        # `_grip` below already knew shoulder width mattered — it records that
        # sending shoulder directions closed this athlete's grip from 19.0 cm
        # between the wrists to 12.1 — and fixed it by placing the ball first
        # and the hands on it. THAT MOVED THE PROBLEM UP A LEVEL RATHER THAN
        # REMOVING IT: the hands became anchored to the ball, and the ball
        # stayed anchored to shoulders nobody sent.
        #
        # A DISPLACEMENT FROM REST, NOT A POSITION, and that took three
        # attempts. Metres failed because every position in this job is
        # normalised and only `radiusM` is absolute. Arm lengths failed
        # because a shoulder-above-pelvis distance is a TORSO quantity and an
        # arm divisor put the rendering rig's neutral 2.23 cm out. And a
        # torso-normalised POSITION failed on all 48 phases, 1.1 to 5.8 cm,
        # including the phases where both girdles are neutral and nothing is
        # wrong — because a divisor SCALES and cannot TRANSLATE, and the two
        # rigs carry a constant offset between where MHR puts `root` and where
        # MPFB puts `pelvis`: +2.46 cm ahead here against −0.26 there.
        #
        # A displacement cancels every constant — landmark convention, neutral
        # posture, build — reads zero at rest by construction, and carries the
        # one thing that was actually missing, which is that this girdle MOVES
        # and the consumer's does not.
        #
        # AND IT IS PELVIS-RELATIVE ON BOTH SIDES OF THE SUBTRACTION. The
        # solved root is never at its rest position — 8.4 cm off at every ready
        # phase and 37 cm at the landing's approach — so a displacement taken
        # from the world would carry the whole body's travel into a field about
        # the shoulder girdle. The guard below caught exactly that: it read
        # 0.6239 torso lengths, 30.97 cm, on `netball_double_foot_landing`
        # frame 0, against the 5.7 to 7.4 cm the girdle actually moves.
        #
        # ADDITIVE. Nothing else in the job changes, so a consumer that ignores
        # this field renders exactly as it did before.
        "shoulderShiftFromRestInTorsos": {
            side: [
                round(float(v), 6)
                for v in (
                    (
                        to_blender(points[index[f"{side}_uparm"]])
                        - to_blender(points[index["root"]])
                    )
                    - (
                        to_blender(rest_points[index[f"{side}_uparm"]])
                        - to_blender(rest_points[index["root"]])
                    )
                )
                / torso
            ]
            for side in ("l", "r")
        },
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
        holding = tuple(method.sides_at(held.phase))
        if holding:
            job["grip"] = _grip(points, index, centre, radius, arm, holding)
    return job


def build(character, movement_id: str, every: int = 0) -> dict:
    definition = load_definition(definition_path(movement_id))
    method = load_technique(technique_path(movement_id))
    result = solve_movement(character, movement_id)
    index = result["index"]
    rest_points = joint_positions(character, result["identity"])
    frames = len(result["points"])

    phases = []
    for phase in definition.phases:
        frame = max(0, min(frames - 1, round(phase.at_phase * (frames - 1))))
        job = phase_job(result, index, frame, method, rest_points)
        job["name"] = phase.name
        phases.append(job)

    # Every frame, for animation. The phases are the pictures a manual page
    # wants and these are the movement between them.
    frames_out = []
    if every > 0:
        for frame in range(0, frames, every):
            frames_out.append(phase_job(result, index, frame, method, rest_points))

    return {
        "schemaVersion": 1,
        "movementId": movement_id,
        "skill": definition.skill,
        "sport": definition.sport,
        "anatomyLimitsDegrees": dict(ANATOMY_LIMITS),
        # Additive. A reader that does not know this field keeps working on
        # the block above; a reader that does should prefer it for the
        # knuckle, because the block above has no flexion number in it and
        # bounds nothing about the thumb at all.
        #
        # ROTATIONS about each knuckle's OWN axes, per digit, including the
        # thumb. Resolve your rotation into that frame before comparing. A
        # scalar bend taken in the plane that points a finger at the ball is
        # not this quantity: off the flexion axis it mixes flexion with
        # deviation, and bounding the mixture by the flexion licence permits
        # a deviation the joint does not have.
        "knuckleLimitsDegrees": knuckle_limits(character),
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
