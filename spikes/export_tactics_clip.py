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
from clip_geometry import (  # noqa: E402
    CLASSES,
    moment_against,
    moment_frame,
    IN_PLACE_METRES,
    SCHEMA_VERSION,
    TRAVELS_FRACTION,
    athlete_frame,
    chest_joint,
    read_ball,
    read_frame,
    rest_median,
    unwrap,
)
from movement_definition import load as load_definition  # noqa: E402
from movement_engine import definition_path, library, load_character  # noqa: E402
from possession_solve import solve_movement  # noqa: E402
from technique import has_technique, load_technique, technique_path  # noqa: E402

OUTPUT = SPIKE_DIR / "poc-output"


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
    # THE MODEL'S ANSWER FOR THE OTHER KIND OF MOMENT. A clip whose declared
    # moment is a RELEASE — which the pass family needs, and which the clip
    # contract's vocabulary already lists — must be checked against when the
    # ball actually leaves, not against when she caught it. Comparing a
    # release clip's `hit` against `contactFrame` compares two different
    # questions and would agree only by accident.
    #
    # Both are emitted, each named for what it is, and neither stands in for
    # the other. A consumer compares like with like: `contact` moments against
    # `contactFrame`, `release` moments against `releaseFrame`. None where the
    # drill never lets go, which is every catch that ends holding the ball.
    released = next(
        (frame.number for frame in result["possession"].frames
         if frame.state == "released"),
        None,
    )
    release_frame = None if released is None else int(released)

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
        "releaseFrame": release_frame,
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
        # THIS LINE CARRIED THE OLD RULE ONE FILE LONGER THAN THE VERIFIER.
        # It divided `contactFrame` for every clip, so on the same `--all` run
        # where the verifier printed "-0.00 s vs releaseFrame" it printed
        # "the ball is taken -1.27 s from the release phase" for both passes.
        # It now reads the same `moment_frame` the verifier does, and says
        # which frame it used, so the two cannot disagree again.
        against = moment_against(clip)
        gap = moment_frame(clip) / max(1, len(clip["frames"])) - clip["hit"]
        if abs(gap) > 0.02:
            print(
                f"   note: the {clip['hitPhase']} phase is "
                f"{gap * clip['seconds']:+.2f} s from {against}"
            )
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
