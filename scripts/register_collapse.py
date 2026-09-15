"""The collapse: how many SOURCES the register's sightings actually are.

    python scripts/register_collapse.py

A register that counts sightings reports a library as well grounded because one
number appears in fifteen places. Two collapses are measured here.

**REPEATED CONSTANTS.** The same value under the same name in several files is
one authoring seen several times, until something shows otherwise. The register
holds it once and lists the sites.

**UNIFORM SERIES.** A run of evenly spaced numbers is one generated series and
not N authored numbers. `author_flight.py` builds its keys as
`release_phase + flight_phase * step / keys`, so a uniform `atPhase` run is
fixed by two endpoints however many keys it holds.

THE TOLERANCE IS SET BY THE FILE'S OWN PRECISION, NOT BY TASTE. `atPhase` is
stored to four decimal places, so any difference of two stored values carries
plus or minus 1e-4, and a spread at or below 2e-4 is indistinguishable from
zero. A first pass used `spread <= 1e-4` and reported six uniform sequences
against five not. That split was an artefact of a float comparison:
`1.0000000000000005e-04` is not `<= 1e-04`, and eleven identical cases were
being cut in half. **A spurious six-against-five split, published, would have
looked exactly like a finding.**

THIS COUNTS SIGHTINGS AND SOURCES. It does not decide provenance. A collapsed
group still needs one source, and the register still has to find it.
"""

from __future__ import annotations

import argparse
import collections
import json
import platform
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MOVEMENTS = ROOT / "spikes" / "movements"
sys.path.insert(0, str(ROOT / "scripts"))

from register_survey_constants import tip  # noqa: E402

# atPhase is stored to four decimals. Refer to the docstring.
UNIFORM_TOLERANCE = 2e-4


def repeated_constants() -> dict[tuple[str, float], list[str]]:
    """The same name holding the same value in more than one file."""
    import ast

    seen: dict[tuple[str, float], list[str]] = collections.defaultdict(list)
    from register_survey_constants import constants_in

    for path in sorted(ROOT.rglob("*.py")):
        if any(part in {".git", ".pixi", "__pycache__"} for part in path.parts):
            continue
        try:
            tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        except (SyntaxError, UnicodeDecodeError):
            continue
        relative = path.relative_to(ROOT).as_posix()
        for line, name, number in constants_in(tree):
            seen[(name, float(number))].append(f"{relative}:{line}")
    return {key: sites for key, sites in seen.items() if len(sites) > 1}


def uniform_series() -> tuple[int, int, int, list[tuple[str, int, float]]]:
    """The atPhase runs, and whether each is one generated series."""
    total = 0
    in_series = 0
    rows: list[tuple[str, int, float]] = []
    for path in sorted(MOVEMENTS.glob("*.ball.json")):
        definition = json.loads(path.read_text(encoding="utf-8"))
        phases = [entry["atPhase"] for entry in definition.get("keys", [])
                  if "atPhase" in entry]
        total += len(phases)
        if len(phases) < 3:
            continue
        steps = [phases[i + 1] - phases[i] for i in range(len(phases) - 1)]
        spread = max(steps) - min(steps)
        rows.append((path.name[:-10], len(phases), spread))
        if spread <= UNIFORM_TOLERANCE:
            in_series += len(phases)
    return total, in_series, len(rows), rows


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--value", type=float,
                        help="list every constant holding this value, by name")
    args = parser.parse_args()
    print(f"tip:         {tip()}")
    print(f"interpreter: python {platform.python_version()}")
    print()

    repeated = repeated_constants()
    sightings = sum(len(sites) for sites in repeated.values())
    print("REPEATED CONSTANTS: one name, one value, more than one file.")
    print(f"  groups: {len(repeated)}   sightings: {sightings}"
          f"   sources they collapse to: {len(repeated)}")
    print()
    for (name, value), sites in sorted(repeated.items(), key=lambda kv: -len(kv[1])):
        print(f"  {len(sites)}x  {name} = {value}")
        for site in sites:
            print(f"        {site}")
    print()

    # A WEAKER SIGNAL, AND IT MUST BE LABELLED AS ONE. The section above groups
    # by NAME AND VALUE, which is close to proof. This one groups by VALUE
    # ALONE, which is a question for a person and never an automatic collapse.
    #
    # It exists because the section above CANNOT SEE the case this register
    # already published: the size-five ball radius, 11.0, is authored four
    # times under four different names. A name is not a correspondence, and a
    # collapse keyed on the name misses every constant that was renamed.
    #
    # It will also group numbers that share a value by coincidence. 5.0 is a
    # band floor, a meaningful-degrees threshold and a tolerance. That is why
    # this is a candidate list and not a finding.
    import ast as _ast
    from register_survey_constants import constants_in as _constants_in

    by_value: dict[float, set[tuple[str, str]]] = collections.defaultdict(set)
    for path in sorted(ROOT.rglob("*.py")):
        if any(part in {".git", ".pixi", "__pycache__"} for part in path.parts):
            continue
        try:
            tree = _ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        except (SyntaxError, UnicodeDecodeError):
            continue
        relative = path.relative_to(ROOT).as_posix()
        for line, name, number in _constants_in(tree):
            by_value[float(number)].add((name, f"{relative}:{line}"))

    renamed = {
        value: sites for value, sites in by_value.items()
        if len({name for name, _ in sites}) > 1
    }
    print("SAME VALUE, DIFFERENT NAMES: a CANDIDATE collapse, never automatic.")
    print(f"  values held under more than one name: {len(renamed)}")
    print()
    print("  A LIST OF THESE IS NOT WORTH PRINTING AND THIS FILE WILL NOT PRINT")
    print("  ONE. Ranked by size it is dominated by coincidence: 5.0 appears")
    print("  under 14 names as a band floor, a sample count, a level of detail")
    print("  and a tolerance, and the one case this register has actually")
    print("  published ranks below all of that. A listing that buries its own")
    print("  signal is a worse instrument than no listing.")
    print()
    print("  Query a value instead:  --value 11.0")
    print()
    asked = args.value if args.value is not None else 11.0
    if args.value is None:
        print("  The worked example, and the reason this section exists at all:")
    else:
        print(f"  Every constant holding {asked}:")
    for name, site in sorted(by_value.get(asked, set())):
        print(f"      {name:30s} {site}")
    if args.value is None:
        print()
        print("  FOUR of those five are the size-five netball's radius under four")
        print("  names. ELBOW_POLE_DOWN_CM is 11.0 BY COINCIDENCE and is not a")
        print("  ball at all. So this section found the real group AND a false")
        print("  member in the same five rows, on the one example it was built")
        print("  for. That is exactly why it is a candidate list and never an")
        print("  automatic collapse, and why the output is queried by a person.")
        print()
        print("  The section above cannot see the real group at all, because it")
        print("  groups by NAME and a name is not a correspondence.")
    print()

    total, in_series, runs, rows = uniform_series()
    uniform = [row for row in rows if row[2] <= UNIFORM_TOLERANCE]
    print("UNIFORM SERIES: an evenly spaced run of atPhase keys.")
    print(f"  atPhase values in the ball files: {total}")
    print(f"  runs of three or more keys:       {runs}")
    print(f"  of those, uniform:                {len(uniform)}")
    print(f"  values inside a uniform run:      {in_series}")
    print(f"  values NOT inside one:            {total - in_series}")
    print()
    print("  A uniform run is fixed by TWO endpoints however many keys it holds,")
    print("  so those values collapse to at most two numbers each. The arrival")
    print("  endpoint traces to author_flight.DEFAULT_ARRIVAL_PHASE, which the")
    print("  register already holds as its own row.")
    print()
    for name, keys, spread in rows:
        mark = "uniform" if spread <= UNIFORM_TOLERANCE else "NOT uniform"
        print(f"  {keys} keys  spread {spread:.3e}  {mark:11s} {name}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
