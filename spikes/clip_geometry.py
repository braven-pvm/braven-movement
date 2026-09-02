"""The geometry a technique clip is measured with, and nothing else.

Split out of `export_tactics_clip.py` so that the conventions can be tested
where the solver cannot run. Every function here is arithmetic on joint
positions: no character, no solve, and nothing that needs pymomentum, which is
conda-forge only and is why pixi exists in this repository.

That is not tidiness. The one class of defect this file guards against — a
reading that is right in the plane of the run and wrong out of it — is invisible
in every viewer, survives a clip loading and playing correctly, and was found by
an instrument rather than by an eye. A guard nothing runs is not a guard, and
before this split nothing ran these tests except a person with a 4.5 GB asset
directory on their machine.

Refer to `docs/TACTICS_CLIP_CONTRACT.md`, section 8, for what each number means.
"""

from __future__ import annotations

import numpy as np

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
    # The first `pass`, and the first moment that is not a contact or a
    # landing. `chest-pass` is in Tactics' own RELEASE_KINDS; `release` is the
    # frame the hands come off the ball, which the technique file declares and
    # the possession model derives independently. The exporter prints the
    # difference between the two, as it does for every other clip.
    "netball_chest_pass": ("pass", "chest-pass", "release"),
    # The second `pass`. `overhead-pass` is NOT in Tactics' RELEASE_KINDS today,
    # which lists chest-pass, shoulder-pass, lob and bounce-pass, so no board can
    # select this clip yet. It is exported anyway: the engine may hold a
    # technique the board cannot ask for, and the reconciliation between the
    # manual's pass family and that vocabulary is on the coach agenda. Refer to
    # docs/TACTICS_CLIP_CONTRACT.md section 3 and docs/LOB_AUTHORING_BRIEF.md.
    "netball_overhead_pass": ("pass", "overhead-pass", "release"),
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


def bend_of(start, middle, end) -> float:
    """How far a joint is folded, in three dimensions.

    The angle between the two segments, which is what an elbow flexion angle and
    a knee flexion angle are. It needs no plane at all, and that is the point.

    This is deliberately NOT the difference of two swings. `swing_of` reads a
    segment in the plane of forward and up and throws the sideways part away, so
    the difference between two such readings equals the true joint angle only
    while the limb stays in that plane. A high deflect puts the arm overhead and
    out; a hooks catch puts it behind the body. Measured against the engine's own
    ISB flexion on every phase of every drill, the difference of swings was wrong
    by up to 52.7 degrees and this is wrong by 0.0.

    A magnitude, never a direction. A knee folds the heel backwards and an elbow
    brings the hand forwards, and which way is anatomy rather than anything in
    this file, so the direction belongs where the pose is put on a rig.
    """
    a = np.asarray(middle, dtype=np.float64) - np.asarray(start, dtype=np.float64)
    b = np.asarray(end, dtype=np.float64) - np.asarray(middle, dtype=np.float64)
    a = a / np.linalg.norm(a)
    b = b / np.linalg.norm(b)
    return float(np.arccos(np.clip(np.dot(a, b), -1.0, 1.0)))


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
        # Two planar readings and one spatial one, and the split is not
        # arbitrary. The consumer applies `upper` and `out` as rotations about
        # two axes, so a reading in each of those planes is exactly what it
        # wants. It applies `lower` as a bend at the joint, so that one has to be
        # the true angle. Refer to `bend_of`.
        return {
            "upper": swing_of(a, b, forward, up),
            "lower": bend_of(a, b, c),
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

