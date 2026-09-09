"""A screen for multi-solution drills: how much a figure moves between builds.

    python -B scripts/spread_screen.py

THE IDEA IS THE CONTENT LANE'S. It noticed that `hooks_outside_hand`, the known
two-solution drill, reads 3.58 cm apart across three independent readings, while
`one_hand_snatch_to_other_hand` reads 0.18 cm apart across the same three.
**The stable drill is stable everywhere; the two-solution drill is different
every time anyone looks.** So the SPREAD of a figure across readings is a cheap
detector, and it needs no solver and no sweep.

A FIRST VERSION OF THIS SCRIPT SCREENED THE PROSE IN `docs/` AND IT WAS INVALID.
It paired every number on a line with every measure name on that line, so a
table row reading `| leftElbowFlexionDegrees | 49.85 | 47.66 | -2.19 |` became
three readings of one measure with a spread of 52. **Two values and a DELTA are
three different quantities, and prose does not say which is which.** Its top four
hits were all that artefact, including one manufactured from this lane's own
table. It is replaced rather than tuned, because the fault was the source and
not the threshold.

**The content lane's version worked because a person knew the three numbers were
the same quantity.** That knowledge is not in the text, so the screen has to read
something that carries it. This reads the archived RENDER RECEIPTS, where a
field name means one thing.

WHAT IT COMPARES. Two archived builds under `.assets/archives/`, per drill, per
phase, per numeric field. **The builds differ by real changes, so a spread is
expected and is not itself a defect.** The screen is COMPARATIVE: on the same
field, which drills move much more than the others.

**A HIT IS A CANDIDATE AND NOT A FINDING.** A drill may move because it has two
solutions, or because a real change between the builds touched it. The screen
says where to look.
"""
import json
import statistics
import sys
from collections import defaultdict
from pathlib import Path

ARCHIVES = Path("F:/Repositories/braven-movement/.assets/archives")
BUILDS = ("coach-figures-aa3f244", "coach-figures-2413f9d")
# Fields whose value is a measurement rather than a count, a flag or an id.
SKIP = {"frame", "verticesInside", "atPhase"}


def leaves(node, trail=()) -> dict:
    out = {}
    if isinstance(node, dict):
        for key, value in node.items():
            out.update(leaves(value, trail + (key,)))
    elif isinstance(node, list):
        for number, value in enumerate(node):
            out.update(leaves(value, trail + (str(number),)))
    elif isinstance(node, (int, float)) and not isinstance(node, bool):
        if trail and trail[-1] not in SKIP:
            out["/".join(trail)] = float(node)
    return out


def build_readings(build: str) -> dict:
    directory = ARCHIVES / build
    readings = {}
    for path in sorted(directory.glob("*.render.json")):
        data = json.loads(path.read_text(encoding="utf-8"))
        drill = data.get("movementId", path.name)
        for phase in data.get("phases", []):
            name = phase.get("name", "?")
            for field, value in leaves(phase).items():
                readings[(drill, name, field)] = value
    return readings


def main() -> int:
    if not ARCHIVES.exists():
        raise SystemExit(f"REFUSED: no archives at {ARCHIVES}")
    first, second = (build_readings(b) for b in BUILDS)
    shared = set(first) & set(second)
    if not shared:
        raise SystemExit(
            "REFUSED: the two builds share no drill, phase and field. "
            "That is a broken screen, not a stable library."
        )
    print(f"    {BUILDS[0]}  {len(first)} readings")
    print(f"    {BUILDS[1]}  {len(second)} readings")
    print(f"    shared: {len(shared)}")
    print()

    # Per FIELD, how far each drill moved between the two builds. Comparing
    # drills against each other on one field is the whole point: an absolute
    # movement means nothing, because the builds genuinely differ.
    by_field: dict = defaultdict(dict)
    for drill, phase, field in shared:
        key = (drill, phase, field)
        moved = abs(second[key] - first[key])
        by_field[field].setdefault(drill, []).append(moved)

    rows = []
    for field, drills in by_field.items():
        if len(drills) < 4:
            continue
        worst = {d: max(v) for d, v in drills.items()}
        values = sorted(worst.values())
        middle = statistics.median(values)
        if middle <= 0.0:
            continue
        for drill, value in worst.items():
            if value > 0.0:
                rows.append((value / middle, value, middle, drill, field))
    rows.sort(reverse=True)

    print("    THE SPREAD SCREEN, per field, drills against each other")
    print("    'times median' is this drill's movement over the median drill's")
    print()
    # THE BEST ROW PER DRILL. A first version printed the top twenty rows and
    # all twenty were `hooks_outside_hand`, the drill already known to have two
    # solutions. That is a good positive control and a useless report: the
    # question is which OTHER drills light up, and one drill was hiding them.
    print(f"    {'x median':>9s} {'moved':>10s} {'median':>9s}  "
          f"{'drill':30s} field")
    seen = set()
    for ratio, value, middle, drill, field in rows:
        if drill in seen:
            continue
        seen.add(drill)
        print(f"    {ratio:9.1f} {value:10.3f} {middle:9.3f}  "
              f"{drill.replace('netball_', ''):30s} {field}")

    print()
    print("    A RATIO OVER A NEAR-ZERO MEDIAN IS NOT EVIDENCE. Read the")
    print("    'moved' column beside it: `ballCentreM/0` rows score in the")
    print("    hundreds on movements of 0.001 to 0.021, which is a small")
    print("    number divided by a smaller one and means nothing.")
    print()
    print("    AND THESE TWO BUILDS SPAN PR #46, THE HAND MIRROR FIX, so hand")
    print("    fields were CHANGED DELIBERATELY between them. That confound")
    print("    strengthens the top row rather than explaining it away: one")
    print("    common change moved one drill two hundred times further than")
    print("    its peers on the same field.")
    print()
    print("    A HIT IS A CANDIDATE. The two builds differ by real changes, so")
    print("    a drill can move because something changed it. What the screen")
    print("    says is which drills move much more than their peers on the")
    print("    SAME field, which is the shape a second solution makes.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
