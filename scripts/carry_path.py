"""Where the ball goes during the carry, read from the engine's own carry path.

    cd spikes
    pixi run --frozen -- python -B ../scripts/carry_path.py

WHY THIS EXISTS, AND WHAT IT GOT WRONG FIRST. The release-timing unit rests on
where the pre-release hand motion comes from. An earlier version of this script
measured `ball.offset_at(phase)`, found it constant, and reported that **the
carry has no path**. That was published and it is wrong.

`ball.offset_at` is the BALL file's FLIGHT offset. The carry does not use it.
`possession.carry_path` builds the carried offsets from the TECHNIQUE file's
`afterContact` keys, passed in at `possession_solve.py:198` as
`after_contact=method.after_contact`. **Every drill authors one, and the four
passes author four keys each.**

Two failures produced that error and both are recorded here rather than in a
commit message alone:

  1. I read an engine value, but the WRONG engine value. It happened to be
     constant, which agreed with the story I had been given.
  2. A first version measured the ball against the SHOULDER MIDPOINT and found
     it moving 0.28 cm per frame relative to her body. **That was detecting the
     real carry path.** I dismissed it as a wrong-origin artefact and replaced
     it with the wrong quantity. I talked myself out of the correct result.

So this reads `carry_path` and `sample_offsets` from `possession` itself, and
the technique through `load_technique`. Nothing is rebuilt.

Nothing here writes to `spikes/movements/`. Gate 4 is untouched.
"""
import sys
from pathlib import Path

SPIKES = Path(__file__).resolve().parents[1] / "spikes"
if str(SPIKES) not in sys.path:
    sys.path.insert(0, str(SPIKES))

import numpy as np  # noqa: E402
from motion_track import arm_length  # noqa: E402
from movement_engine import joint_positions, load_character  # noqa: E402
from possession import carry_path, sample_offsets  # noqa: E402
from possession_solve import solve_movement  # noqa: E402
from technique import load_technique, technique_path  # noqa: E402

PASSES = (
    "netball_chest_pass",
    "netball_overhead_pass",
    "netball_bounce_pass",
    "netball_one_hand_high_pass",
)


def rest_arm_cm(character) -> float:
    index = {
        name: position
        for position, name in enumerate(character.skeleton.joint_names)
    }
    rest = np.zeros(character.parameter_transform.size, dtype=np.float32)
    return float(arm_length(joint_positions(character, rest), index))


def main() -> int:
    character = load_character()
    arm_cm = rest_arm_cm(character)
    print(f"    the rest arm: {arm_cm:.2f} cm, so an arm length is that many cm")
    print()
    print("    THE AUTHORED CARRY PATH, from each technique file's afterContact")
    print()
    for movement_id in PASSES:
        method = load_technique(technique_path(movement_id))
        print(f"    {movement_id.replace('netball_', '')}")
        for key in method.after_contact:
            print(f"        {key.name:12s} at phase {key.at_phase:4.2f}   "
                  f"across {key.offset.across:7.4f}  up {key.offset.up:7.4f}  "
                  f"ahead {key.offset.ahead:7.4f}")

    print()
    print("    HOW FAR THE BALL TRAVELS RELATIVE TO HER, THROUGH THE CARRY")
    print("    read from possession.sample_offsets on the engine's own path")
    print()
    print(f"    {'drill':22s} {'held':>5s} {'in-body cm':>11s} "
          f"{'world cm':>9s} {'in-body share':>14s}")
    for movement_id in PASSES:
        result = solve_movement(character, movement_id)
        frames = result["possession"].frames
        method = load_technique(technique_path(movement_id))
        held = [n for n, frame in enumerate(frames) if frame.holding]
        contact_phase = frames[held[0]].phase
        phases, offsets = carry_path(
            contact_phase,
            sample_offsets(
                [contact_phase],
                [method.after_contact[0].offset],
                contact_phase,
            ),
            method.after_contact,
        )
        in_body = 0.0
        world = 0.0
        for earlier, later in zip(held, held[1:]):
            if later != earlier + 1:
                continue
            one = sample_offsets(phases, offsets, frames[earlier].phase)
            two = sample_offsets(phases, offsets, frames[later].phase)
            step = np.array([
                two.across - one.across, two.up - one.up, two.ahead - one.ahead
            ]) * arm_cm
            in_body += float(np.linalg.norm(step))
            world += float(np.linalg.norm(
                np.asarray(frames[later].centre) - np.asarray(frames[earlier].centre)
            ))
        print(f"    {movement_id.replace('netball_', ''):22s} {len(held):5d} "
              f"{in_body:11.2f} {world:9.2f} {in_body / world:13.0%}")

    print()
    print("    THE IN-BODY COLUMN IS THE AUTHORED PATH AND IT IS MOST OF THE")
    print("    TRAVEL. The ball is NOT pinned to her, and an earlier version of")
    print("    this script said it was. A retiming is a retune of these keys,")
    print("    not the creation of a path that does not exist.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
