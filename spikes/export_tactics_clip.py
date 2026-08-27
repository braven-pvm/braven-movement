"""Write a solved movement as a technique clip Braven Tactics can play.

Braven Tactics is the court planning application. A coach choreographs a play
there, and every player is drawn by a pure function of the playhead. This is the
boundary between the two products, and it is the same shape as the Blender
boundary in `export_blender_job.py`: one file per movement, and the consuming
side never needs the solver.

The contract is `docs/TACTICS_CLIP_CONTRACT.md`. Read that first. What follows
is the part of it that is arithmetic.

Why a pose and not a bone track
-------------------------------
Tactics describes a body with fifteen numbers a frame: how far each limb is
swung, how far it is carried away from the midline, how far each lower joint is
bent, the lean, the shoulder twist and the rise off the floor. That description
names no skeleton at all, which is why it can be drawn on a bought character
and on a stack of cylinders without either knowing about the other.

So the retarget happens here, once, and it is a measurement rather than a
transfer. Every number below is read off the solved joint positions with the
same geometry Tactics uses to read a motion capture file. Nothing new runs at
play time.

What this loses, and why that is honest
---------------------------------------
The pose carries no wrist, no forearm roll and no fingers. Tactics stops at the
wrist by contract, so a grip cannot cross this boundary and must not pretend to.
The graded angles stay in the movement report, and the clip declares the
assessment rather than carrying the geometry that earned it.

Axes. MHR is Y up, centimetres, and the athlete's left is positive X. Her front
is positive Z. Refer to `athlete_frame`, which asserts both.

    pixi run python export_tactics_clip.py
    pixi run python export_tactics_clip.py netball_two_hand_snatch_pull_in
    pixi run python export_tactics_clip.py --all
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
from movement_engine import definition_path, library, load_character  # noqa: E402
from possession_solve import solve_movement  # noqa: E402
from technique import has_technique, load_technique, technique_path  # noqa: E402

OUTPUT = SPIKE_DIR / "poc-output"

SCHEMA_VERSION = 1

# Which movement class each drill belongs to, what the technique is called, and
# which coaching phase is the moment the movement is about.
#
# The class names are Tactics' own event vocabulary, from `ACTOR_EVENT_TYPES`
# and `RELEASE_KINDS` in its `src/contract/vocabulary.ts`. They are not invented
# here. A movement whose class is not in that vocabulary cannot be played by a
# board, because no event would ever select it.
#
# The moment is named rather than derived. A board stamps an event at the
# instant it happens and lines the clip up on that instant, so a clip that named
# the wrong moment would play its follow-through before the ball arrived. The
# possession model derives the frame the ball is taken on, which is the answer
# for a catch and is not the answer for a landing: she takes the ball in flight
# and lands a third of a second later.
CLASSES = {
    "netball_two_hand_snatch_pull_in": ("catch", "two-hand-snatch", "contact"),
    "netball_two_hand_snatch_straight_back": ("catch", "two-hand-snatch-back", "contact"),
    "netball_two_hand_catch_chest": ("catch", "two-hand-chest", "contact"),
    "netball_one_hand_snatch_to_other_hand": ("catch", "one-hand-snatch", "contact"),
    "netball_hooks_jump_pull_in": ("catch", "hooks-jump", "contact"),
    "netball_hooks_outside_hand": ("catch", "hooks-outside-hand", "contact"),
    "netball_deflect_high": ("block", "deflect-high", "contact"),
    "netball_double_foot_landing": ("land", "double-foot", "land"),
}

# Above this much root travel, a clip is not in place and the consumer must
# reconcile the travel against its own player track. Two millimetres is solver
# noise on a movement coached with the feet still.
IN_PLACE_METRES = 0.02

# Below this, the movement is in place and the clip is played on the play clock
# rather than against metres run. A third of the way from the floor to the hips
# is about half a pace, which is the same test Tactics' own bake applies.
TRAVELS_FRACTION = 0.35


def athlete_frame(points, index) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Up, forward and lateral, in the athlete's own terms.

    Stated rather than measured, and then asserted. Tactics reads these off the
    capture because a capture does not say which way it faces. The engine does
    say: MHR is Y up and the athlete's left is positive X, which makes her front
    positive Z. Measuring the direction of travel on a movement whose feet do
    not move would read three hundredths of a centimetre of solver noise as a
    heading, which is the trap Tactics' own bake documents.

    Returns up, forward, and the lateral axis as the cross product of the two,
    which is how Tactics builds it. That axis points at the athlete's left here.
    The caller compares it against the shoulders rather than trusting a sign.
    """
    left_shoulder = np.asarray(points[index["l_uparm"]], dtype=np.float64)
    right_shoulder = np.asarray(points[index["r_uparm"]], dtype=np.float64)
    if left_shoulder[0] <= right_shoulder[0]:
        raise ValueError(
            "the athlete's left is not positive X. MHR puts l_uparm at about "
            f"x +17.6 and this solve has {left_shoulder[0]:.2f}. Refer to "
            "gotcha 2 in docs/HANDOFF_RENDERING.md."
        )
    hip = np.asarray(points[index["root"]], dtype=np.float64)
    ankle = np.asarray(points[index["l_foot"]], dtype=np.float64)
    if hip[1] <= ankle[1]:
        raise ValueError("the pelvis is not above the ankle. MHR is Y up.")

    up = np.array([0.0, 1.0, 0.0])
    forward = np.array([0.0, 0.0, 1.0])
    return up, forward, np.cross(up, forward)


def swing_of(start, end, forward, up) -> float:
    """How far a segment is swung from hanging straight down, in radians.

    Positive is forward. This is the inverse of the rotation Tactics applies to
    a bone, so a clip written here and played there is the same body.
    """
    direction = np.asarray(end, dtype=np.float64) - np.asarray(start, dtype=np.float64)
    direction = direction / np.linalg.norm(direction)
    return float(np.arctan2(np.dot(direction, forward), -np.dot(direction, up)))


def out_of(start, end, lateral, side: int) -> float:
    """How far a segment is carried away from the midline, in radians.

    Positive is outward on both sides, so the caller says which side the limb is
    on and the sign is not carried in the number. Without this axis everything a
    person does sideways is thrown away, and a two hand snatch is largely
    sideways: the hands separate to take the ball and close on it.
    """
    direction = np.asarray(end, dtype=np.float64) - np.asarray(start, dtype=np.float64)
    direction = direction / np.linalg.norm(direction)
    return float(np.arcsin(np.clip(np.dot(direction, lateral) * side, -1.0, 1.0)))


def shortest(angle: float) -> float:
    """The same angle, brought into minus pi to pi."""
    return float(np.arctan2(np.sin(angle), np.cos(angle)))


def across(start, end, forward, lateral, up) -> float:
    """The yaw of a line drawn across the body, about the up axis.

    The shoulders and the hips, for the twist between them.
    """
    direction = np.asarray(end, dtype=np.float64) - np.asarray(start, dtype=np.float64)
    direction = direction - up * np.dot(direction, up)
    direction = direction / np.linalg.norm(direction)
    return float(np.arctan2(np.dot(direction, forward), np.dot(direction, lateral)))


def chest_joint(index) -> str:
    """The top of the spine chain, for the lean.

    Tactics reads the trunk as a direction from the hips to the chest rather
    than as anybody's idea of a local axis, so this needs the highest spine
    joint and not a named one.
    """
    for name in ("c_spine3", "c_spine2", "c_spine1", "c_spine0"):
        if name in index:
            return name
    raise KeyError("no spine joint in the solved skeleton")


LIMBS = {
    "legL": ("l_upleg", "l_lowleg", "l_foot"),
    "legR": ("r_upleg", "r_lowleg", "r_foot"),
    "armL": ("l_uparm", "l_lowarm", "l_wrist"),
    "armR": ("r_uparm", "r_lowarm", "r_wrist"),
}


def read_frame(points, index, axes, sides, chest) -> dict:
    """One frame of the solve, as the body Tactics describes."""
    up, forward, lateral = axes
    at = lambda name: np.asarray(points[index[name]], dtype=np.float64)  # noqa: E731

    hips = at("root")

    def limb(name: str) -> dict:
        upper_joint, lower_joint, end_joint = LIMBS[name]
        a, b, c = at(upper_joint), at(lower_joint), at(end_joint)
        upper = swing_of(a, b, forward, up)
        whole = swing_of(b, c, forward, up)
        return {
            "upper": upper,
            # A magnitude. A knee folds one way and an elbow the other, and
            # which way is anatomy rather than anything in this file, so the
            # direction belongs where the pose is put on a rig.
            "lower": abs(shortest(whole - upper)),
            "out": out_of(a, b, lateral, sides[name]),
        }

    spine = at(chest) - hips
    spine = spine / np.linalg.norm(spine)

    return {
        # The lowest ankle, in the athlete's own units for now. Re-seated on the
        # floor and converted once the whole clip is known.
        "bob": float(min(np.dot(at("l_foot"), up), np.dot(at("r_foot"), up))),
        "lean": float(np.arctan2(np.dot(spine, forward), np.dot(spine, up))),
        "twist": shortest(
            across(at("l_uparm"), at("r_uparm"), forward, lateral, up)
            - across(at("l_upleg"), at("r_upleg"), forward, lateral, up)
        ),
        "leg": {"left": limb("legL"), "right": limb("legR")},
        "arm": {"left": limb("armL"), "right": limb("armR")},
    }


def read_ball(points, index, held, axes) -> list:
    """Where the ball is, from the shoulder midpoint, in arm lengths.

    A separate channel from the pose, and separate on purpose. The pose is fifteen
    numbers in a fixed order and inserting a sixteenth would silently change
    every clip already written. This rides alongside it, the same length, and a
    consumer that does not read it loses nothing.

    In arm lengths rather than metres, which is the same unit discipline the
    Blender boundary uses: the athlete this was solved on is not the size of the
    body it will be drawn on, and an absolute offset measured on one lands in the
    wrong place on the other. The ball's own size is absolute, because a netball
    is a netball, and it is declared once for the clip.

    Why it exists: Braven Tactics carries a ball at one fixed point in front of
    the chest for as long as a player holds it, so a catch has no gather. Her
    hands are solved onto that point, which overrides the arms of any technique
    laid over it. This is what a consumer needs in order to move the ball
    instead. Refer to section 12 of docs/TACTICS_CLIP_CONTRACT.md.
    """
    up, forward, lateral = axes
    at = lambda name: np.asarray(points[index[name]], dtype=np.float64)  # noqa: E731

    shoulders = (at("l_uparm") + at("r_uparm")) / 2.0
    elbow = at("l_lowarm")
    arm = float(
        np.linalg.norm(elbow - at("l_uparm")) + np.linalg.norm(at("l_wrist") - elbow)
    )
    offset = (np.asarray(held.centre, dtype=np.float64) - shoulders) / arm
    return [
        round(float(np.dot(offset, forward)), 4),
        round(float(np.dot(offset, up)), 4),
        round(float(np.dot(offset, lateral)), 4),
        1 if held.holding else 0,
    ]


def rest_median(values: list[float]) -> float:
    ordered = sorted(values)
    return ordered[len(ordered) >> 1] if ordered else 0.0


def unwrap(frames: list[dict]) -> None:
    """Let a limb angle keep counting past half a turn.

    `swing_of` is an arctangent and lands in the half open turn from minus pi to
    pi. An arm swung past vertical therefore steps from +154 degrees to -103 in
    one frame, and the player interpolates between the frames it is given, so
    ten degrees of arm becomes two hundred and fifty seven degrees of windmill.
    Nothing downstream minds an angle past a half turn.
    """
    for part in ("leg", "arm"):
        for side in ("left", "right"):
            for i in range(1, len(frames)):
                previous = frames[i - 1][part][side]["upper"]
                frames[i][part][side]["upper"] = previous + shortest(
                    frames[i][part][side]["upper"] - previous
                )


def build(character, movement_id: str) -> dict:
    if movement_id not in CLASSES:
        raise KeyError(
            f"{movement_id} has no movement class. Add one to CLASSES, using a "
            "name from Tactics' own event vocabulary."
        )
    movement_class, technique_name, moment = CLASSES[movement_id]

    definition = load_definition(definition_path(movement_id))
    result = solve_movement(character, movement_id)
    index = result["index"]
    points = result["points"]
    count = len(points)
    fps = float(result["track"].frames_per_second)

    axes = athlete_frame(points[0], index)
    up, _, lateral = axes
    chest = chest_joint(index)

    # Which side of the body each limb is on, measured rather than assumed. The
    # lateral axis is a cross product of two axes the engine supplies, so one
    # dot product against the shoulders settles it and no sign is guessed.
    left_shoulder = np.asarray(points[0][index["l_uparm"]], dtype=np.float64)
    right_shoulder = np.asarray(points[0][index["r_uparm"]], dtype=np.float64)
    right_side = 1 if np.dot(right_shoulder - left_shoulder, lateral) >= 0 else -1
    sides = {
        "armR": right_side,
        "armL": -right_side,
        "legR": right_side,
        "legL": -right_side,
    }

    frames = [read_frame(points[i], index, axes, sides, chest) for i in range(count)]
    ball = [
        read_ball(points[i], index, result["possession"].frames[i], axes)
        for i in range(count)
    ]

    # How far she travels over the ground, and whether that is travel at all.
    hips = np.stack([np.asarray(points[i][index["root"]]) for i in range(count)])
    along = hips - np.outer(hips @ up, up)
    travel_cm = float(np.sum(np.linalg.norm(np.diff(along, axis=0), axis=1)))
    stance_cm = float(np.dot(hips[0], up) - min(f["bob"] for f in frames))
    travels = travel_cm > stance_cm * TRAVELS_FRACTION

    # Rise and fall about the lowest point the movement reaches, in metres,
    # which is what `Pose.bob` means. A constant offset in the ankle joint
    # cancels here, so it does not matter that an ankle is not a sole.
    floor = min(frame["bob"] for frame in frames)
    for frame in frames:
        frame["bob"] = (frame["bob"] - floor) / 100.0

    # Sideways is measured from this athlete's own neutral, not from her
    # midline. Every body has a resting splay and the drawn figure already
    # carries its own, so an absolute angle stacks the two and puts every player
    # in a straddle with her arms held out.
    for part in ("leg", "arm"):
        for side in ("left", "right"):
            rest = rest_median([frame[part][side]["out"] for frame in frames])
            for frame in frames:
                frame[part][side]["out"] -= rest

    unwrap(frames)

    # The grading, carried with the clip.
    #
    # `docs/REQUIREMENTS.md` R2 asks that every figure states whether its
    # movement met every coaching checkpoint. A clip is a figure that moves, so
    # it carries the same statement. A consumer that shows a technique to a
    # coach can then say which one it is showing, and a technique that failed
    # its own definition can be excluded rather than quietly drawn.
    measurements = result["measurements"]
    assessment = definition.assess(measurements)

    phases = []
    for phase in definition.phases:
        frame = max(0, min(count - 1, round(phase.at_phase * (count - 1))))
        checkpoints = []
        for checkpoint in phase.checkpoints:
            measured = float(measurements[frame][checkpoint.measure])
            checkpoints.append(
                {
                    "measure": checkpoint.measure,
                    "measuredDegrees": round(measured, 2),
                    "minimumDegrees": checkpoint.minimum_degrees,
                    "maximumDegrees": checkpoint.maximum_degrees,
                    "verdict": checkpoint.assess(measured).verdict,
                    "cue": checkpoint.cue,
                }
            )
        phases.append(
            {
                "name": phase.name,
                "at": round(frame / max(1, count), 4),
                "frame": frame,
                "cues": [checkpoint.cue for checkpoint in phase.checkpoints],
                "checkpoints": checkpoints,
            }
        )

    # The moment the clip is about, declared rather than guessed.
    #
    # Tactics derives this from the busiest frame of the legs, which is right
    # for a kick and wrong for everything a netballer does with her hands: this
    # movement is coached with the feet still, so the busiest leg frame is
    # solver noise. The coaching definition already names the moment.
    named = [phase for phase in phases if phase["name"] == moment]
    if not named:
        raise KeyError(
            f"{movement_id} has no phase named {moment!r}, so the clip cannot "
            "say which instant it is about. Refer to CLASSES."
        )
    hit_frame = named[0]["frame"]

    # And the possession model's own answer, so the two can be compared rather
    # than one quietly standing in for the other. They agree on a catch. On a
    # landing they must not: she takes the ball in flight and lands later.
    contact_frame = int(result["possession"].contact_frame)

    return {
        "schemaVersion": SCHEMA_VERSION,
        "clipId": f"{movement_class}.{definition.sport}.{technique_name}",
        "class": movement_class,
        "sport": definition.sport,
        "technique": technique_name,
        "movementId": movement_id,
        "skill": definition.skill,
        "source": definition.source if hasattr(definition, "source") else None,
        # Whether this technique met every coaching checkpoint it was graded
        # against. A consumer may refuse to draw a technique that did not.
        "graded": bool(assessment.correct),
        # Metres of ground one loop covers, and zero for anything that is not a
        # locomotion cycle. Tactics reads this to decide which clock plays the
        # clip: a stride is periodic in distance and a one-shot action is not.
        # Every clip this file writes is a one-shot action, so every one of them
        # declares zero, and the travel it did make is reported separately.
        "stride": 0,
        "seconds": round(count / fps, 3),
        "hit": round(hit_frame / max(1, count), 3),
        "hitPhase": moment,
        # Whether she stays where she is, and how far she goes if she does not.
        # The consumer owns the player's own track, so travel that crosses this
        # boundary must be reconciled there rather than added to it.
        "inPlace": bool(travel_cm / 100.0 <= IN_PLACE_METRES),
        "rootTravelM": round(travel_cm / 100.0, 4),
        "travelsUnderItsOwnPower": bool(travels),
        "framesPerSecond": fps,
        "contactFrame": contact_frame,
        "phases": phases,
        # The ball's own size is absolute. A netball is a netball on every body.
        "ballRadiusM": round(float(result["radiusCm"]) / 100.0, 4),
        # One entry per frame: forward, up and lateral from the shoulder midpoint
        # in arm lengths, then whether she has it. Refer to `read_ball`.
        "ball": ball,
        "frames": [
            [
                round(f["bob"], 3),
                round(f["lean"], 3),
                round(f["twist"], 3),
                round(f["leg"]["left"]["upper"], 3),
                round(f["leg"]["left"]["lower"], 3),
                round(f["leg"]["right"]["upper"], 3),
                round(f["leg"]["right"]["lower"], 3),
                round(f["arm"]["left"]["upper"], 3),
                round(f["arm"]["left"]["lower"], 3),
                round(f["arm"]["right"]["upper"], 3),
                round(f["arm"]["right"]["lower"], 3),
                round(f["leg"]["left"]["out"], 3),
                round(f["leg"]["right"]["out"], 3),
                round(f["arm"]["left"]["out"], 3),
                round(f["arm"]["right"]["out"], 3),
            ]
            for f in frames
        ],
    }


def main(argv: list[str]) -> int:
    wanted = [value for value in argv[1:] if not value.startswith("--")]
    if "--all" in argv[1:]:
        wanted = [
            name
            for name in library()
            if name in CLASSES
            and has_ball(name)
            and has_technique(name)
            and load_technique(technique_path(name)).possession_ready
        ]
    if not wanted:
        wanted = ["netball_two_hand_snatch_pull_in"]

    # Loading the character reads a 4.5 GB asset directory, so it is read once
    # however many movements are asked for.
    character = load_character()
    OUTPUT.mkdir(parents=True, exist_ok=True)
    for movement_id in wanted:
        clip = build(character, movement_id)
        path = OUTPUT / f"{movement_id}.clip.json"
        path.write_text(json.dumps(clip, indent=2), encoding="utf-8")
        print(
            f"{clip['clipId']}: {len(clip['frames'])} frames, "
            f"{clip['seconds']:.2f} s, travel {clip['rootTravelM']:.3f} m, "
            f"hit on {clip['hitPhase']} at {clip['hit'] * 100:.0f}% -> {path.name}"
        )
        for phase in clip["phases"]:
            mark = " <- hit" if phase["name"] == clip["hitPhase"] else ""
            print(
                f"   {phase['name']:12s} frame {phase['frame']:3d} "
                f"at {phase['at']:.3f}{mark}"
            )
        # Said out loud rather than left in the file, because a landing whose
        # ball arrives a third of a second before the feet is a real difference
        # and not a fault to smooth over.
        if abs(clip["contactFrame"] - clip["phases"][0]["frame"]) >= 0:
            gap = clip["contactFrame"] / max(1, len(clip["frames"])) - clip["hit"]
            if abs(gap) > 0.02:
                print(
                    f"   note: the ball is taken {gap * clip['seconds']:+.2f} s "
                    f"from the {clip['hitPhase']} phase"
                )
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
