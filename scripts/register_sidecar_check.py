"""The sidecar must not name a row that no extractor produced.

    python scripts/register_sidecar_check.py

WHY THIS EXISTS. `scripts/register_sidecar.json` carries the judgment columns:
a source, a scope, a frame, a unit's evidence. None of them can be computed and
all of them are written by a person.

**A SIDECAR ENTRY FOR A CONSTANT THAT DOES NOT EXIST IS POPULATION C INSIDE THE
REGISTER ITSELF.** A name reasoned about, carrying a source and a scope and a
dependants list, denoting nothing. That is the exact defect this lane was
chartered to find, and a register that contained one would have no standing to
report it in anybody else's work.

It is not a hypothetical. This lane's charter named `wristToDegrees` and
`fingerToDegrees` as constants in the release model. They are two names in a
paragraph. The same mistake in this file would be worse, because the register
is where a reader would go to check.

    exit 0  every sidecar id resolves to a row an extractor produces
    exit 2  at least one does not

WHAT IT CAN AND CANNOT CHECK, stated so a reader can weigh it. A1, A2 and C ids
are checked against their extractors. **B ids are checked by a WEAKER test**:
the key name must occur in the library file the id names, or in any movement
file when the id names no file. Population B has no extractor keyed the way
these rows are keyed, and pretending otherwise would be a check that passes
without looking.
"""

from __future__ import annotations

import ast
import json
import platform
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from register_survey_constants import constants_in, literal, tip  # noqa: E402
from register_survey_structures import numbers_in  # noqa: E402

SIDECAR = ROOT / "scripts" / "register_sidecar.json"
MOVEMENTS = ROOT / "spikes" / "movements"


def a1_rows() -> set[str]:
    found: set[str] = set()
    for path in sorted(ROOT.rglob("*.py")):
        if any(p in {".git", ".pixi", "__pycache__"} for p in path.parts):
            continue
        try:
            tree = ast.parse(path.read_text(encoding="utf-8"))
        except (SyntaxError, UnicodeDecodeError):
            continue
        relative = path.relative_to(ROOT).as_posix()
        for _line, name, _value in constants_in(tree):
            found.add(f"{relative}:{name}")
    return found


def a2_rows() -> set[str]:
    found: set[str] = set()
    for path in sorted(ROOT.rglob("*.py")):
        if any(p in {".git", ".pixi", "__pycache__"} for p in path.parts):
            continue
        try:
            tree = ast.parse(path.read_text(encoding="utf-8"))
        except (SyntaxError, UnicodeDecodeError):
            continue
        relative = path.relative_to(ROOT).as_posix()
        for node in tree.body:
            if isinstance(node, ast.Assign):
                names = [t.id for t in node.targets if isinstance(t, ast.Name)]
                value = node.value
            elif isinstance(node, ast.AnnAssign) and isinstance(node.target, ast.Name):
                names = [node.target.id]
                value = node.value
            else:
                continue
            if value is None or not names or literal(value) is not None:
                continue
            if numbers_in(value, names[0]):
                found.add(f"{relative}:{names[0]}")
    return found


def library_text() -> str:
    return "\n".join(
        path.read_text(encoding="utf-8", errors="replace")
        for path in sorted(MOVEMENTS.glob("*.json"))
    )


def main() -> int:
    sidecar = json.loads(SIDECAR.read_text(encoding="utf-8"))
    print(f"tip:         {tip()}")
    print(f"interpreter: python {platform.python_version()}")
    print()

    a1, a2 = a1_rows(), a2_rows()
    library = library_text()
    docs = ROOT / "docs"

    checked = 0
    unresolved: list[tuple[str, str]] = []
    weak = 0
    for key in sidecar:
        if key.startswith("_"):
            continue
        checked += 1
        try:
            population, rest = key.split(" ", 1)
        except ValueError:
            unresolved.append((key, "the id has no population prefix"))
            continue
        if population == "A1":
            if rest not in a1:
                unresolved.append((key, "no A1 constant of that file and name"))
        elif population == "A2":
            if rest not in a2:
                unresolved.append((key, "no A2 structure of that file and name"))
        elif population == "C":
            document, _, name = rest.partition(":")
            page = docs / document
            if not page.exists():
                unresolved.append((key, f"{document} is not in docs/"))
            elif f"`{name}`" not in page.read_text(encoding="utf-8", errors="replace"):
                unresolved.append((key, f"{document} does not name `{name}`"))
        elif population == "B":
            weak += 1
            name = rest.split(":")[-1].split("@")[0]
            if name not in library:
                unresolved.append((key, f"no movement file mentions {name!r}"))
        else:
            unresolved.append((key, f"unknown population {population!r}"))

    print(f"sidecar rows checked: {checked}")
    print(f"  A1 constants known to the extractor: {len(a1)}")
    print(f"  A2 structures known to the extractor: {len(a2)}")
    print(f"  of the rows checked, {weak} used the WEAKER population B test")
    print()

    if unresolved:
        print(f"{len(unresolved)} SIDECAR ROW(S) NAME NOTHING AN EXTRACTOR PRODUCES.")
        print("A sidecar entry for a row that does not exist is population C")
        print("inside the register itself: a name carrying a source and denoting")
        print("nothing. Fix the id, or delete the row:")
        for key, why in unresolved:
            print(f"    {key}")
            print(f"        {why}")
        return 2

    print("Every sidecar id resolves to a row an extractor produces.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
