"""Every graded checkpoint of the two retimed drills, against its own band.

    cd spikes
    pixi run --frozen -- python -B ../scripts/retiming_verdicts.py

WHY. Marius ruled the retiming ships. Before the two numbers change, the
question is what a COACH would read afterwards: the graded checkpoint values
and whether any of them leaves its band. A value that crosses a band edge turns
a pose change into a grading change, and that is a different decision.

**THE VALUES ARE MEASURED, NOT DERIVED.** The sweep that produced the 22.02
reported a DIFFERENCE. Adding a difference to a shipped value is a
reconstruction, and a reconstruction is a measurement in this repository's
ledger. So this solves both builds and reads both receipts.

Nothing under `spikes/movements/` is written: the library is copied and the key
moved in the copy.
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

DRILLS = ("netball_bounce_pass", "netball_chest_pass")
# Marius ruled the retiming ships; the orchestrator ruled the SIZE at +0.50,
# because +0.75 takes the bounce pass's drive elbow to 130.29 against a ceiling
# of 130.0 -- a crossing of 0.29 degrees, which is BELOW the 6.00 degree solver
# noise floor and therefore a verdict that would not be stable.
DEFAULT_SHIFT = 0.50


def library(into: Path) -> Path:
    target = into / "movements"
    shutil.copytree(SPIKES / "movements", target)
    return target


def retime(movements: Path, movement_id: str, shift: float) -> tuple:
    path = movements / f"{movement_id}.technique.json"
    data = json.loads(path.read_text(encoding="utf-8"))
    keys = data["afterContact"]
    release, moving = keys[-1], keys[-2]
    was = float(moving["atPhase"])
    now = round(was + shift * (float(release["atPhase"]) - was), 6)
    moving["atPhase"] = now
    path.write_text(json.dumps(data, indent=2), encoding="utf-8")
    if json.loads(path.read_text(encoding="utf-8"))["afterContact"][-2]["atPhase"] != now:
        raise SystemExit(f"REFUSED: {movement_id}: the shift did not land")
    return moving["name"], was, now


def rows(movements: Path, character, movement_id: str) -> dict:
    import ball_track
    import movement_engine
    import technique
    from movement_definition import load as load_definition
    from possession_solve import solve_movement

    for module in (ball_track, movement_engine, technique):
        module.MOVEMENT_DIR = movements
    result = solve_movement(character, movement_id)
    definition = load_definition(movements / f"{movement_id}.json")
    receipt = definition.assess(result["measurements"]).to_receipt()
    found = {}
    for phase, entries in receipt["phases"].items():
        for entry in entries:
            found[(phase, entry["measure"])] = (
                entry["measured"], tuple(entry["band"]), entry["verdict"]
            )
    return found


def report_only(character) -> int:
    """Read the REAL library's graded checkpoints, with no copy and no shift.

    This is what proves a committed tree reproduces the numbers a pack claims.
    A measurement taken on a temporary copy says what a change WOULD do; this
    says what the tree in front of you DOES.
    """
    print(f"    THE LIBRARY AS IT STANDS, no copy and no shift")
    print()
    for movement_id in DRILLS:
        path = SPIKES / "movements" / f"{movement_id}.technique.json"
        keys = json.loads(path.read_text(encoding="utf-8"))["afterContact"]
        moving = keys[-2]
        found = rows(SPIKES / "movements", character, movement_id)
        print(f"    {movement_id.replace('netball_', '')}: "
              f"'{moving['name']}' at {moving['atPhase']}")
        for key in sorted(found):
            value, band, verdict = found[key]
            print(f"      {key[0] + '/' + key[1]:46s} {value:9.2f}  "
                  f"{band[0]:7.1f}-{band[1]:<7.1f}  {verdict}")
        print()
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--shift", type=float, default=DEFAULT_SHIFT)
    parser.add_argument("--report", action="store_true",
                        help="read the real library rather than a shifted copy")
    arguments = parser.parse_args()

    from movement_engine import load_character

    character = load_character()
    if arguments.report:
        return report_only(character)
    crossings = []
    for movement_id in DRILLS:
        builds = {}
        moved = None
        for label, shift in (("shipped", False), ("retimed", True)):
            workspace = Path(tempfile.mkdtemp(prefix=f"braven-verdict-{label}-"))
            try:
                movements = library(workspace)
                if shift:
                    moved = retime(movements, movement_id, arguments.shift)
                builds[label] = rows(movements, character, movement_id)
            finally:
                shutil.rmtree(workspace, ignore_errors=True)

        name, was, now = moved
        short = movement_id.replace("netball_", "")
        print(f"    {short}: '{name}' {was} -> {now}")
        print(f"      {'phase / measure':46s} {'shipped':>9s} {'retimed':>9s} "
              f"{'moved':>8s}  {'band':>16s}  verdicts")
        for key in sorted(builds["shipped"]):
            was_value, band, was_verdict = builds["shipped"][key]
            now_value, _, now_verdict = builds["retimed"].get(key, (None, band, "?"))
            if now_value is None:
                continue
            moved_by = now_value - was_value
            flag = ""
            if was_verdict != now_verdict:
                flag = "   <-- VERDICT CHANGED"
                crossings.append((short, key, was_value, now_value, band,
                                  was_verdict, now_verdict))
            print(f"      {key[0] + '/' + key[1]:46s} {was_value:9.2f} "
                  f"{now_value:9.2f} {moved_by:+8.2f}  "
                  f"{band[0]:7.1f}-{band[1]:<7.1f}  "
                  f"{was_verdict} -> {now_verdict}{flag}")
        print()

    if crossings:
        print("    A CHECKPOINT CHANGED VERDICT. STOP.")
        for short, key, was_value, now_value, band, a, b in crossings:
            print(f"      {short}/{key[0]}/{key[1]}: {was_value:.2f} -> "
                  f"{now_value:.2f}, band {band[0]}-{band[1]}, {a} -> {b}")
        return 1
    print("    NO CHECKPOINT CHANGED ITS VERDICT.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
