"""Names kept for the spikes written before the library existed.

The solve moved to movement_engine, which takes any movement instead of one
hard-coded catch. The earlier spikes ask for a single catch, so this binds the
old names to the pull-in drill and re-exports the rest. Nothing is duplicated
here, so the two cannot drift.

New work should import movement_engine directly.
"""

from __future__ import annotations

from motion_track import load_motion
from movement_engine import (  # noqa: F401 - re-exported for the older spikes
    ASSET_FOLDER,
    ELBOW_POLE_DOWN_CM,
    ELBOW_POLE_OUT_CM,
    ELBOW_POLE_WEIGHT,
    FOOT_WEIGHT,
    FORBIDDEN,
    LEVEL_OF_DETAIL,
    MOVEMENT_DIR,
    TRUNK_WEIGHT,
    WANTED,
    WORLD_UP,
    SolveError,
    enabled_parameters,
    joint_positions,
    load_character,
    measure_frame,
    motion_path,
    solve,
)

DEFAULT_MOVEMENT = "netball_two_hand_snatch_pull_in"
MOTION_PATH = motion_path(DEFAULT_MOVEMENT)

_TRACK = load_motion(MOTION_PATH)
FRAME_COUNT = _TRACK.frames
FRAMES_PER_SECOND = _TRACK.frames_per_second
CONTACT_PHASE = _TRACK.contact_phase()


def solve_catch(character) -> dict:
    """Solve the pull-in drill, the movement these spikes were written against."""
    return solve(character, _TRACK)
