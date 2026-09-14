"""Population B of the movement-parameter register: the library's graded bands.

THIS IS A SURVEY AND NOT THE REGISTER. It reports, for every graded checkpoint
in the library, the band it holds and WHAT LANGUAGE its `why` uses about where
that band came from. It does not decide whether a row is sourced. That is a
judgment, it is made by a person reading the row, and it lives in the register's
sidecar.

    python scripts/register_survey_bands.py
    python scripts/register_survey_bands.py --json rows.json

A RATIONALE IS NOT A SOURCE, AND THIS IS WHY THE SURVEY EXISTS. Every graded
checkpoint in the library carries a non-empty `why`. Most of them are correct
coaching and none the worse for it:

    "A locked arm cannot redirect a ball. A collapsed one cannot control it."

That sentence justifies that a bound should EXIST. It derives neither 20.0 nor
100.0. A reader would call these files unusually well documented and would be
right about the prose and wrong about the numbers. The register keeps the two
in separate columns for that reason, and merging them is how this stayed
invisible. The keyword pass below is TRIAGE that says which rows a person must
read. It is not a verdict, and no count it prints is a count of sourced rows.

THE MEASURE UNION IS CROSS-CHECKED, NOT TRUSTED. This survey walks the phases
to get one row per checkpoint, which it needs. `MovementDefinition` already
answers the narrower question of which measures a drill grades, so the two are
compared per drill and a disagreement stops the run. Two instruments that agree
prove more than either alone, and the walk is the one more likely to be wrong.

    exit 0  every drill read, and the two measure sets agree everywhere
    exit 2  at least one drill disagreed
"""

from __future__ import annotations

import argparse
import json
import platform
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MOVEMENTS = ROOT / "spikes" / "movements"
sys.path.insert(0, str(ROOT / "spikes"))

import movement_definition  # noqa: E402

# THE LANGUAGE A `why` USES ABOUT ITS OWN NUMBER. Each pattern marks a row for
# a person to read. None of them establishes a source.
MARKERS = {
    "provisional": re.compile(r"\bPROVISIONAL\b"),
    "transferred": re.compile(r"\bTRANSFERRED\b", re.I),
    "from another band": re.compile(r"taken from|copied from|same band as|inherits", re.I),
    "quotes the manual": re.compile(r"manual|page \d+", re.I),
    "measured": re.compile(r"\bmeasured\b|receipt|solved|build [0-9a-f]{7}", re.I),
    "anatomy": re.compile(r"anatomy|range of motion", re.I),
    "coach": re.compile(r"\bcoach\b|Erin", re.I),
}

# A ROW WITH NO CITATION SIGNAL AT ALL. Not one digit, not one quotation mark,
# not one file reference. A `why` like that cannot be pointing at anything.
DIGIT = re.compile(r"\d")
QUOTE = re.compile("['\"‘’“”]")
REFERENCE = re.compile(r"\.json|\.py|\.md|netball_")


def tip() -> str:
    """The commit every count below was taken on, read from git and not typed."""
    found = subprocess.run(
        ["git", "-C", str(ROOT), "rev-parse", "HEAD"],
        capture_output=True, text=True, check=False,
    )
    if found.returncode != 0:
        return f"UNKNOWN (git exited {found.returncode})"
    dirty = subprocess.run(
        ["git", "-C", str(ROOT), "status", "--porcelain"],
        capture_output=True, text=True, check=False,
    )
    mark = "" if dirty.stdout.strip() == "" else " (WORKING TREE DIRTY)"
    return found.stdout.strip()[:40] + mark


def drill_files() -> list[Path]:
    """The definitions only. The .ball, .motion and .technique files are siblings."""
    return sorted(
        path for path in MOVEMENTS.glob("*.json")
        if not any(part in path.name for part in (".ball.", ".motion.", ".technique."))
    )


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--json", type=Path, help="write the rows to this file")
    args = parser.parse_args()

    rows: list[dict[str, object]] = []
    disagreed: list[str] = []

    for path in drill_files():
        definition = json.loads(path.read_text(encoding="utf-8"))
        drill = path.stem
        walked: set[str] = set()
        for phase in definition.get("phases", []):
            for checkpoint in phase.get("checkpoints", []):
                if "measure" not in checkpoint:
                    continue
                why = checkpoint.get("why", "") or ""
                walked.add(checkpoint["measure"])
                rows.append({
                    "drill": drill,
                    "phase": phase.get("name"),
                    "measure": checkpoint["measure"],
                    "minimumDegrees": checkpoint.get("minimumDegrees"),
                    "maximumDegrees": checkpoint.get("maximumDegrees"),
                    "wasBand": checkpoint.get("wasBand"),
                    "cue": checkpoint.get("cue"),
                    "why": why,
                    "markers": [key for key, pattern in MARKERS.items() if pattern.search(why)],
                    "hasDigit": bool(DIGIT.search(why)),
                    "hasQuote": bool(QUOTE.search(why)),
                    "hasReference": bool(REFERENCE.search(why)),
                })
        # THE CROSS-CHECK. The engine's own answer, from the definition alone.
        stated = movement_definition.load(path).graded_measures()
        if stated != walked:
            disagreed.append(
                f"{drill}: this survey walked {sorted(walked)}, "
                f"graded_measures() returned {sorted(stated)}"
            )

    print(f"tip:         {tip()}")
    print(f"interpreter: python {platform.python_version()}")
    print()
    print(f"drill definitions read: {len(drill_files())}")
    print(f"graded checkpoints:     {len(rows)}")
    union = movement_definition.union_of_graded(
        movement_definition.load(path) for path in drill_files()
    )
    print(f"distinct graded measures (union_of_graded): {len(union)}")
    for measure in sorted(union):
        print(f"    {measure}")
    print()

    empty = [r for r in rows if not str(r["why"]).strip()]
    print(f"checkpoints with an EMPTY why: {len(empty)}")
    for row in empty:
        print(f"    {row['drill']} / {row['phase']} / {row['measure']}")
    print()

    changed = [r for r in rows if r["wasBand"] is not None]
    print(f"checkpoints carrying wasBand (a band already changed once): {len(changed)}")
    print()

    print("rows whose `why` uses each kind of language (a row may use several):")
    for key in MARKERS:
        print(f"  {sum(1 for r in rows if key in r['markers']):4d}  {key}")
    print()

    unmarked = [r for r in rows if not r["markers"]]
    silent = [r for r in unmarked
              if not (r["hasDigit"] or r["hasQuote"] or r["hasReference"])]
    print(f"rows matching no marker: {len(unmarked)}")
    print("rows with NO citation signal of any kind, meaning no digit, no")
    print(f"quotation mark and no file reference anywhere in the why: {len(silent)}")
    print()
    print("THOSE ROWS ARE NOT PROVED UNSOURCED BY THIS SURVEY. They are the rows")
    print("a person must read. Read them. Do not quote this count as a finding.")
    for row in silent:
        print(f"    {row['drill'][8:]:30s} {str(row['phase'])[:12]:12s} "
              f"{row['measure'][:26]:26s} "
              f"{row['minimumDegrees']:>6}-{row['maximumDegrees']:<6}")

    if args.json:
        args.json.write_text(json.dumps(rows, indent=1, ensure_ascii=False), encoding="utf-8")
        print(f"\nrows written to {args.json}")

    if disagreed:
        print()
        print("THE TWO MEASURE SETS DISAGREE. The survey's walk and the engine's")
        print("own graded_measures() do not match, so neither may be quoted:")
        for line in disagreed:
            print(f"    {line}")
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
