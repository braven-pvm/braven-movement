"""What retiming the carry moves in the GRADED window.

    cd spikes
    pixi run --frozen -- python -B ../scripts/sweep_carry_timing.py

STEP 2's SECOND HALF. Marius ruled the release timing mechanical because a
retiming moves the arm inside the frames Erin's checkpoints measure. **That is
the claim this measures.**

WHAT IT VARIES, AND WHY IT AUTHORS NOTHING. Each pass's technique file carries
an `afterContact` path. The LAST key is the release. The one before it is where
the ball is still being driven. Moving that key LATER compresses the same travel
into fewer frames before the release, which is what "the hand accelerates into
the release" means in the numbers this engine already has.

    chest_pass          drive @ 0.62 -> release @ 0.80
    overhead_pass       step  @ 0.58 -> release @ 0.80
    bounce_pass         drive @ 0.62 -> release @ 0.80
    one_hand_high_pass  step  @ 0.55 -> release @ 0.80

**So this sweeps ONE EXISTING NUMBER per drill and creates nothing.** No path is
authored. `spikes/movements/` is copied to a temporary directory and patched
there, and the shipped value sits inside the swept range rather than at its end.

WHAT IT KNOWS THAT THE FILES SAY. `netball_chest_pass`'s `step` key carries a
coaching cue in its own note: "SHE STEPS AND THE BALL DOES NOT MOVE ... the
manual's 'Keep hands where they were with catch, don't pull ball back' ... NOTHING
GRADES IT". **This sweep does not touch the step key on the chest pass for that
reason** — it moves the key AFTER it. A retune that accelerated the whole carry
would delete a manual cue that no instrument would catch.

AND THE FILE ALREADY CARRIES A RELATED MUTATION. `pullBackMeasureNote` records
that moving the step key 13.2 cm moved every graded measure by at most 5.1
degrees, which is the threshold this repository calls meaningless. **That is
about POSITION. This is about TIMING, and they are different questions.**
"""
import json
import shutil
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SPIKES = ROOT / "spikes"
if str(SPIKES) not in sys.path:
    sys.path.insert(0, str(SPIKES))

DRILLS = (
    "netball_chest_pass",
    "netball_overhead_pass",
    "netball_bounce_pass",
    "netball_one_hand_high_pass",
)
# A fraction of the gap from the shipped key to the release key. 0.0 is the
# shipped build. NEGATIVE moves the key EARLIER, so the shipped value sits
# inside the sweep rather than at its end.
SHIFTS = (-0.25, 0.0, 0.25, 0.5, 0.75)
# The null this sweep measures for itself, from phases the change cannot reach.
# Filled at run time; not a constant.


def patched_movements(into: Path) -> Path:
    target = into / "movements"
    shutil.copytree(SPIKES / "movements", target)
    return target


def shift_key(directory: Path, movement_id: str, fraction: float) -> tuple:
    """Move the key before the release, by a fraction of the gap to it."""
    path = directory / f"{movement_id}.technique.json"
    data = json.loads(path.read_text(encoding="utf-8"))
    keys = data["afterContact"]
    release = keys[-1]
    moving = keys[-2]
    was = float(moving["atPhase"])
    gap = float(release["atPhase"]) - was
    now = was + fraction * gap
    moving["atPhase"] = round(now, 6)
    if fraction != 0.0 and abs(now - was) < 1e-9:
        raise SystemExit(f"{movement_id}: the shift did not change the phase")
    path.write_text(json.dumps(data, indent=2), encoding="utf-8")
    return moving["name"], was, now


def main() -> int:
    workspace = Path(tempfile.mkdtemp(prefix="braven-carry-sweep-"))
    try:
        movements = patched_movements(workspace)
        import ball_track
        import movement_engine
        import numpy as np
        import technique
        from movement_definition import load as load_definition
        from movement_engine import load_character
        from possession_solve import solve_movement

        for module in (ball_track, movement_engine, technique):
            module.MOVEMENT_DIR = movements
        if ball_track.MOVEMENT_DIR != movements:
            raise SystemExit("the redirect did not take")
        print(f"    patched copy: {movements}")
        print(f"    spikes/movements/ is untouched")
        print()

        character = load_character()
        readings: dict = {}
        moved_keys: dict = {}
        seams: dict = {}

        def seam_of(result) -> tuple:
            """The release seam: the step in hand speed the ease-out makes.

            `docs/KNOWN_ISSUES.md` names this the seam and measures it two ways:
            the wrist's speed multiplying at the release frame, and the shoulder
            elevation stepping there. Both are taken.

            THE HYPOTHESIS THIS TESTS. The ease-out begins at FULL SPEED, which
            is right only if the incoming speed matches it. Today it does not,
            and the mismatch is the seam. If an accelerating carry supplies that
            speed, the seam should shrink WITHOUT the easing changing.
            """
            frames = result["possession"].frames
            index, points = result["index"], result["points"]
            rate = float(result["track"].frames_per_second)
            release = min(n for n, f in enumerate(frames) if not f.holding)
            sides = frames[release - 1].sides
            side = sorted(sides)[0] if len(sides) == 1 else "l"
            joint = index[f"{side}_wrist"]

            def speed(n: int) -> float:
                step = points[n][joint] - points[n - 1][joint]
                return float(np.linalg.norm(step)) * rate

            into = speed(release)
            after = speed(release + 1)
            shoulder = result["measurements"]
            elevation = f"{'left' if side == 'l' else 'right'}ShoulderElevationDegrees"
            step = abs(
                float(shoulder[release + 1].get(elevation, 0.0))
                - float(shoulder[release].get(elevation, 0.0))
            )
            return into, after, after / into, step
        for shift in SHIFTS:
            shutil.rmtree(movements)
            patched_movements(workspace)
            for movement_id in DRILLS:
                moved_keys[movement_id] = shift_key(movements, movement_id, shift)
            for movement_id in DRILLS:
                result = solve_movement(character, movement_id)
                definition = load_definition(movements / f"{movement_id}.json")
                receipt = definition.assess(result["measurements"]).to_receipt()
                for phase, rows in receipt["phases"].items():
                    for row in rows:
                        key = (movement_id, phase, row["measure"])
                        readings.setdefault(key, {})[shift] = row["measured"]
                seams[(movement_id, shift)] = seam_of(result)

        print("    THE KEY THAT MOVED, per drill")
        for movement_id in DRILLS:
            name, was, _ = moved_keys[movement_id]
            print(f"    {movement_id.replace('netball_', ''):22s} "
                  f"{name:14s} shipped at {was:4.2f}, release at 0.80")
        print()
        print("    WHAT MOVES IN THE GRADED WINDOW, against the shipped build")
        print()
        header = f"    {'drill / phase / measure':52s} {'shipped':>8s}"
        for shift in SHIFTS:
            if shift != 0.0:
                header += f" {shift:+10.2f}"
        print(header)

        worst = 0.0
        unreachable = 0.0
        for key in sorted(readings):
            movement_id, phase, measure = key
            values = readings[key]
            base = values.get(0.0)
            if base is None:
                continue
            line = (
                f"    {movement_id.replace('netball_', '') + '/' + phase + '/' + measure:52s} "
                f"{base:8.2f}"
            )
            moved = False
            for shift in SHIFTS:
                if shift == 0.0:
                    continue
                delta = values.get(shift, base) - base
                worst = max(worst, abs(delta))
                # A phase at or before the moved key cannot be reached by a
                # change that happens after it. Those rows are this sweep's
                # own null.
                if phase in ("ready", "step"):
                    unreachable = max(unreachable, abs(delta))
                if abs(delta) >= 0.01:
                    moved = True
                line += f" {delta:+10.2f}"
            if moved:
                print(line)

        print()
        print("    THE RELEASE SEAM, against the same shifts")
        print("    does an accelerating carry close what the ease-out opens?")
        print()
        print(f"    {'drill':22s} {'shift':>7s} {'into cm/s':>10s} "
              f"{'after cm/s':>11s} {'step':>7s} {'elevation deg':>14s}")
        for movement_id in DRILLS:
            for shift in SHIFTS:
                into, after, ratio, elevation = seams[(movement_id, shift)]
                mark = "  <- shipped" if shift == 0.0 else ""
                print(f"    {movement_id.replace('netball_', ''):22s} "
                      f"{shift:+7.2f} {into:10.1f} {after:11.1f} "
                      f"{ratio:6.1f}x {elevation:14.2f}{mark}")
            print()

        print(f"    the largest move anywhere: {worst:.2f}")
        print(f"    the largest move in a phase the change CANNOT reach: "
              f"{unreachable:.2f}")
        print("    the second is this sweep's own null, measured on its own")
        print("    drills, in its own units, with no effect present.")
        if worst < 0.01:
            raise SystemExit(
                "REFUSED: nothing moved anywhere. A sweep that cannot move "
                "anything is more likely to be disconnected than to be "
                "evidence. Check the redirect before reporting no effect."
            )
        return 0
    finally:
        shutil.rmtree(workspace, ignore_errors=True)


if __name__ == "__main__":
    raise SystemExit(main())
