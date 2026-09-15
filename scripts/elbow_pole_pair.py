"""The two `deflect_high` jobs for the elbow-pole pair, and what differs.

    cd spikes
    pixi run --frozen -- python -B ../scripts/elbow_pole_pair.py --out <directory>

WHAT THIS PRODUCES. Two Blender jobs for `netball_deflect_high`, one solved at
the engine's own `ELBOW_POLE_ANGLE_DEGREES` and one at the candidate a coach is
being asked to consider. Each job records what it was solved with, in its own
`solveParameters` mapping. The rendering lane renders both and the pair is
verifiable rather than trusted.

**NOTHING UNDER `spikes/movements/` IS WRITTEN.** The library is copied to a
temporary directory and the candidate is set THERE, exactly as the sweeps do.
`ELBOW_POLE_ANGLE_DEGREES` in the repository stays at its shipped value.

**THIS RENDERS A CANDIDATE, NOT A CHANGE.** 37.3 is the value a coach is being
asked about. It is in no file in the library.

## WHY THIS SCRIPT DIFFS THE TWO JOBS ITSELF

The rendering lane refuses to call two pictures a pair unless **every OTHER
parameter is equal**, because a pair whose second parameter also moved shows a
difference the caption attributes to the first. That is a check at the CONSUMER.

**This checks at the PRODUCER, so a bad pair never travels.** A pair handed over
as differing in one parameter, and differing in two, would put a false caption
under a coach's picture, and **the caption is the whole artefact.**

## WHAT THE PAIR ANSWERS, AND WHAT IT DOES NOT

`elbowAngleDegrees` is a PER-TECHNIQUE override, and **0 of 12 technique files
set it today**. These two solves would be the library's first use of it.

**So this pair answers the per-drill question only.** Setting the engine's
default would move all twelve drills; setting a per-drill override moves one.
**The two are different questions with different costs, and this script does not
answer either on the coach's behalf.**
"""
import argparse
import json
import shutil
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SPIKES = ROOT / "spikes"
if str(SPIKES) not in sys.path:
    sys.path.insert(0, str(SPIKES))

MOVEMENT = "netball_deflect_high"
# The value a coach is being ASKED about. It is in no file in the library.
CANDIDATE = 37.3


def library(into: Path) -> Path:
    target = into / "movements"
    shutil.copytree(SPIKES / "movements", target)
    return target


def set_candidate(movements: Path, angle: float) -> None:
    """Put the candidate in the COPY's grip block, and prove it landed."""
    path = movements / f"{MOVEMENT}.technique.json"
    data = json.loads(path.read_text(encoding="utf-8"))
    before = data["grip"].get("elbowAngleDegrees")
    if before is not None:
        raise SystemExit(
            f"REFUSED: {MOVEMENT} already sets elbowAngleDegrees to {before}. "
            "This script assumes the shipped library sets none, and that "
            "assumption is now false."
        )
    data["grip"]["elbowAngleDegrees"] = angle
    path.write_text(json.dumps(data, indent=2), encoding="utf-8")
    again = json.loads(path.read_text(encoding="utf-8"))
    if again["grip"].get("elbowAngleDegrees") != angle:
        raise SystemExit("REFUSED: the candidate did not land in the copy")


def differences(one: dict, two: dict, trail: str = "") -> list[str]:
    """Every leaf that differs between two jobs, by path."""
    found: list[str] = []
    if isinstance(one, dict) and isinstance(two, dict):
        for key in sorted(set(one) | set(two)):
            if key not in one:
                found.append(f"{trail}/{key}: only in the second")
            elif key not in two:
                found.append(f"{trail}/{key}: only in the first")
            else:
                found += differences(one[key], two[key], f"{trail}/{key}")
    elif isinstance(one, list) and isinstance(two, list):
        if len(one) != len(two):
            found.append(f"{trail}: {len(one)} against {len(two)} entries")
        else:
            for number, (a, b) in enumerate(zip(one, two)):
                found += differences(a, b, f"{trail}[{number}]")
    elif one != two:
        found.append(f"{trail}: {one!r} against {two!r}")
    return found


def solve(movements: Path, character) -> dict:
    import ball_track
    import movement_engine
    import technique
    from export_blender_job import build

    for module in (ball_track, movement_engine, technique):
        module.MOVEMENT_DIR = movements
    if ball_track.MOVEMENT_DIR != movements:
        raise SystemExit("REFUSED: the redirect did not take")
    return build(character, MOVEMENT)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", type=Path, required=True)
    arguments = parser.parse_args()

    from contact_solve import ELBOW_POLE_ANGLE_DEGREES
    from movement_engine import load_character

    shipped = float(ELBOW_POLE_ANGLE_DEGREES)
    if shipped == CANDIDATE:
        raise SystemExit(
            "REFUSED: the shipped value and the candidate are the same, so "
            "this pair would differ in nothing at all"
        )

    character = load_character()
    jobs = {}
    for label, angle in (("shipped", None), ("candidate", CANDIDATE)):
        workspace = Path(tempfile.mkdtemp(prefix=f"braven-pole-{label}-"))
        try:
            movements = library(workspace)
            if angle is not None:
                set_candidate(movements, angle)
            jobs[label] = solve(movements, character)
        finally:
            shutil.rmtree(workspace, ignore_errors=True)

    print(f"    the engine's shipped value: {shipped}")
    print(f"    the candidate:              {CANDIDATE}")
    print()
    for label, job in jobs.items():
        print(f"    {label:10s} solveParameters {job['solveParameters']}")
    print()

    found = differences(jobs["shipped"], jobs["candidate"])
    parameter = "/solveParameters/ELBOW_POLE_ANGLE_DEGREES"
    others = [line for line in found if not line.startswith(parameter)]

    print(f"    THE TWO JOBS DIFFER IN {len(found)} LEAF VALUES")
    print(f"    {len(found) - len(others)} of them are the parameter itself")
    print()
    if others:
        print("    EVERYTHING ELSE THAT DIFFERS, which is the pose the")
        print("    parameter moved, and is what the pair is FOR:")
        for line in others[:40]:
            print(f"      {line}")
        if len(others) > 40:
            print(f"      ... and {len(others) - 40} more")
    print()
    if not any(line.startswith(parameter) for line in found):
        raise SystemExit(
            "REFUSED: the two jobs do not differ in the parameter at all. "
            "Either the override did not reach the solve or the two solves "
            "are the same. A pair that differs in nothing is not a pair."
        )

    arguments.out.mkdir(parents=True, exist_ok=True)
    for label, job in jobs.items():
        target = arguments.out / f"{MOVEMENT}.{label}.job.json"
        target.write_text(json.dumps(job, indent=2), encoding="utf-8")
        print(f"    written  {target}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
