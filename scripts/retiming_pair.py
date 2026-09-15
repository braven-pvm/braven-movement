"""Two jobs for one drill, before and after the release retiming.

    cd spikes
    pixi run --frozen -- python -B ../scripts/retiming_pair.py --out <directory>

WHAT THIS IS FOR. Marius ruled the release timing mechanical on 2026-09-08 and
asked to see it. This produces the two jobs a render pair is made from: the
shipped build, and the same drill with the ball driven later into the release.

**NOTHING UNDER `spikes/movements/` IS WRITTEN.** The library is copied to a
temporary directory and the key is moved THERE, exactly as the sweeps do. This
is a PICTURE of a candidate, not a change to the library, and the 48 numbers a
real retiming would touch are gate 4 and unruled.

## WHAT IS VARIED, AND IT IS ONE EXISTING NUMBER

Each pass's technique file carries an `afterContact` path. The last key is the
release. **Moving the key before it LATER compresses the same travel into fewer
frames before the release**, which is what "the hand accelerates into the
release" means in the numbers the engine already has.

    chest_pass    drive @ 0.62 -> release @ 0.80
    bounce_pass   drive @ 0.62 -> release @ 0.80

Shifted by +0.75 of the gap, which is the point in the swept range that moved
the graded elbow furthest: **22.02 degrees on the bounce pass and 14.95 on the
chest, monotonically, against a measured solver noise floor of 6.00.**

## WHAT NOTHING CHECKS, AND IT GOES ON THE CAPTION

**A job records `solveParameters` and its posed phases. It does NOT record the
technique's `afterContact` keys.** So these two jobs carry IDENTICAL
`solveParameters` and differ only in pose values, and
`render_receipt.refuse_unverifiable_pair` has no parameter to name.

**The pair machinery verifies solver CONSTANTS. A retiming is an authored KEY,
and the job is silent about those.** So this pair is produced honestly and
verified by nothing, and the caption written beside it says so.
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

# The bounce pass first: it is the bigger effect, 22.02 against 14.95.
DRILLS = ("netball_bounce_pass", "netball_chest_pass")
# A fraction of the gap from the shipped key to the release key.
SHIFT = 0.75


def library(into: Path) -> Path:
    target = into / "movements"
    shutil.copytree(SPIKES / "movements", target)
    return target


def retime(movements: Path, movement_id: str, fraction: float) -> tuple:
    """Move the key before the release later, and prove it landed."""
    path = movements / f"{movement_id}.technique.json"
    data = json.loads(path.read_text(encoding="utf-8"))
    keys = data["afterContact"]
    release, moving = keys[-1], keys[-2]
    was = float(moving["atPhase"])
    now = was + fraction * (float(release["atPhase"]) - was)
    moving["atPhase"] = round(now, 6)
    path.write_text(json.dumps(data, indent=2), encoding="utf-8")
    again = json.loads(path.read_text(encoding="utf-8"))
    if again["afterContact"][-2]["atPhase"] != round(now, 6):
        raise SystemExit(f"REFUSED: {movement_id}: the shift did not land")
    return moving["name"], was, round(now, 6)


def differences(one, two, trail: str = "") -> list[str]:
    found: list[str] = []
    if isinstance(one, dict) and isinstance(two, dict):
        for key in sorted(set(one) | set(two)):
            if key not in one or key not in two:
                found.append(f"{trail}/{key}: only in one")
            else:
                found += differences(one[key], two[key], f"{trail}/{key}")
    elif isinstance(one, list) and isinstance(two, list):
        if len(one) != len(two):
            found.append(f"{trail}: {len(one)} against {len(two)}")
        else:
            for number, (a, b) in enumerate(zip(one, two)):
                found += differences(a, b, f"{trail}[{number}]")
    elif one != two:
        found.append(f"{trail}: {one!r} against {two!r}")
    return found


def solve(movements: Path, character, movement_id: str) -> dict:
    import ball_track
    import movement_engine
    import technique
    from export_blender_job import build

    for module in (ball_track, movement_engine, technique):
        module.MOVEMENT_DIR = movements
    if ball_track.MOVEMENT_DIR != movements:
        raise SystemExit("REFUSED: the redirect did not take")
    return build(character, movement_id)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--drills", nargs="*", default=list(DRILLS))
    arguments = parser.parse_args()

    from movement_engine import load_character

    character = load_character()
    arguments.out.mkdir(parents=True, exist_ok=True)
    caption: list[str] = []

    for movement_id in arguments.drills:
        jobs = {}
        moved = None
        for label, fraction in (("shipped", None), ("retimed", SHIFT)):
            workspace = Path(tempfile.mkdtemp(prefix=f"braven-retime-{label}-"))
            try:
                movements = library(workspace)
                if fraction is not None:
                    moved = retime(movements, movement_id, fraction)
                jobs[label] = solve(movements, character, movement_id)
            finally:
                shutil.rmtree(workspace, ignore_errors=True)

        name, was, now = moved
        found = differences(jobs["shipped"], jobs["retimed"])
        short = movement_id.replace("netball_", "")
        print(f"    {short}: key '{name}' moved {was} -> {now}, "
              f"release at 0.80")
        print(f"      the two jobs differ in {len(found)} leaf values")
        same = [
            line for line in found if line.startswith("/solveParameters")
        ]
        print(f"      of which in solveParameters: {len(same)}  "
              f"<- ZERO is expected and is the point")
        if not found:
            raise SystemExit(
                f"REFUSED: {movement_id}: the two jobs are identical. A pair "
                "that differs in nothing is not a pair."
            )
        for label, job in jobs.items():
            target = arguments.out / f"{movement_id}.{label}.job.json"
            target.write_text(json.dumps(job, indent=2), encoding="utf-8")
            print(f"      written {target.name}")
        caption.append(
            f"| `{short}` | `{name}` {was} -> {now} | {len(found)} | "
            f"{len(same)} |"
        )

    (arguments.out / "CAPTION.md").write_text(
        "# The release retiming, before and after\n\n"
        "Produced by `scripts/retiming_pair.py`. **Nothing under "
        "`spikes/movements/` was written**: the library was copied and the key "
        "moved in the copy. This is a picture of a candidate and not a change.\n\n"
        "## What was varied\n\n"
        "One existing number per drill: the phase of the `afterContact` key "
        "BEFORE the release, moved 75 per cent of the way to it. That "
        "compresses the same ball travel into fewer frames before the "
        "release, which is what an accelerating carry means in the numbers "
        "this engine already has.\n\n"
        "| drill | key moved | leaf values differing | of them in `solveParameters` |\n"
        "|---|---|---|---|\n" + "\n".join(caption) + "\n\n"
        "## WHAT NOTHING CHECKS, AND IT IS NOT A SMALL CAVEAT\n\n"
        "**This pair is verified by nothing.** A job records "
        "`solveParameters` and its posed phases, and it does NOT record the "
        "technique's `afterContact` keys. So both jobs carry IDENTICAL "
        "`solveParameters`, and `render_receipt.refuse_unverifiable_pair` has "
        "no parameter to name.\n\n"
        "**The pair machinery built on 2026-09-09 verifies solver CONSTANTS. "
        "A retiming is an authored KEY, and the job is silent about those.** "
        "So a reader must take on trust that these two jobs differ only in "
        "the retiming. **The producer diffed them and the count is above; "
        "nothing downstream can confirm it.**\n\n"
        "## The number under the picture\n\n"
        "Measured separately by `scripts/sweep_carry_timing.py`, as a sweep "
        "with the shipped value inside it: at this shift the graded drive "
        "elbow moves **22.02 degrees on the bounce pass and 14.95 on the "
        "chest**, monotonically in the shift, against a solver noise floor of "
        "**6.00 degrees** measured in phases the change cannot reach.\n",
        encoding="utf-8",
    )
    print(f"    written {arguments.out / 'CAPTION.md'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
