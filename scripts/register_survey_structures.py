"""Population A2 of the movement-parameter register: numbers inside structures.

    python scripts/register_survey_structures.py
    python scripts/register_survey_structures.py --name AAOS_LIMITS
    python scripts/register_survey_structures.py --json rows.json

WHY THIS FILE EXISTS. `register_survey_constants.py` reads population A1: a
module-level assignment whose value IS a number. It cannot see a number inside
a dictionary, a list, a tuple or a call, so it never offered those numbers to
the inclusion test at all.

**The row that proved it was `AAOS_LIMITS`.** The register had already recorded
`"elbow.flexion": RangeLimit(0.0, 150.0, "AAOS")` as an open question, because
`build_library.py` checks every drill in the library against it and "AAOS" is
four letters with no edition, no page and no population. That constant sits at
`spikes/isb_angles.py:240` inside a dictionary of calls, and the A1 extractor
walked straight past it.

Saying "252 constants, a lower bound" while citing a five-constant gap
understated the gap by two orders of magnitude. A1 and A2 are therefore
declared as SEPARATE POPULATIONS with separate coverage, and the register's
header says so, because a reader must never have to infer coverage.

WHAT A ROW HOLDS. Each number gets a PATH that addresses it inside its
structure, so a row can be found again and argued with:

    isb_angles.py:241  AAOS_LIMITS['elbow.flexion'] -> RangeLimit(arg 1) = 150.0

MOST OF THESE WILL BE EXCLUDED ON SIGHT AND THAT IS FINE. Test fixtures and
pixel geometry are the bulk of them. The finding is not that they belong in the
register. It is that the inclusion test was never OFFERED them, and a number
nobody was asked about is not a number anybody decided to leave out.

WHAT THIS FILE DELIBERATELY DOES NOT COUNT, so a reader can disagree with the
boundary rather than discover it. It descends into a dictionary, a list, a
tuple, a set, a call's arguments, and both sides of an operator. It does NOT
descend into a call's own FUNCTION, a subscript, a comparison or a
comprehension. That boundary excludes 28 sites, and every one of them is an
incidental number in an expression rather than an authored value:
`Path(__file__).resolve().parents[1]` and `.split(' ', 1)` are the whole of it.

A FIRST DRAFT OF THIS FILE REPORTED 105 SITES AND 737 LITERALS. That count came
from a scratchpad probe that walked every node, so it counted those path
indices. This file counts 78 sites and 702 literals. The difference is 28 sites
of incidental numbers, plus two real tables the probe found and the first
version of this file then missed, because they hold their numbers on the KEY
side of a dictionary. Both numbers are recorded here rather than the later one
replacing the earlier silently.

    exit 0  every file was read
    exit 2  at least one file was not read; the count is a lower bound
"""

from __future__ import annotations

import argparse
import ast
import json
import platform
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from register_survey_constants import literal, tip  # noqa: E402


def numbers_in(node: ast.expr, path: str) -> list[tuple[str, float | int, int]]:
    """Every numeric literal inside a structure, with a path that addresses it.

    A BARE NUMBER AT THE TOP IS NOT A ROW HERE. That is population A1's, and
    counting it in both would report one constant twice, which is the fault
    this register exists to catch.
    """
    found: list[tuple[str, float | int, int]] = []

    def walk(value: ast.expr, where: str) -> None:
        number = literal(value)
        if number is not None:
            found.append((where, number, value.lineno))
            return
        if isinstance(value, ast.Dict):
            for key, item in zip(value.keys, value.values):
                if key is None:
                    walk(item, f"{where}[**]")
                    continue
                label = (repr(key.value) if isinstance(key, ast.Constant)
                         else ast.unparse(key))
                # A NUMERIC KEY IS A ROW. `CORRESPONDENCE = {0: 'root', ...}`
                # and `LANDMARK_TO_JOINT = {0: 'c_head', 11: 'l_uparm', ...}`
                # hold their numbers on the KEY side, and a correspondence
                # table is a claim: it says which landmark is which joint, and
                # a wrong pairing moves every measurement taken from it. A
                # first version of this file read only the value side and
                # missed 29 numbers across those two tables.
                number = literal(key)
                if number is not None:
                    found.append((f"{where}[key {label}]", number, key.lineno))
                walk(item, f"{where}[{label}]")
        elif isinstance(value, (ast.List, ast.Tuple, ast.Set)):
            for index, item in enumerate(value.elts):
                walk(item, f"{where}[{index}]")
        elif isinstance(value, ast.Call):
            name = (ast.unparse(value.func) if not isinstance(value.func, ast.Name)
                    else value.func.id)
            for index, item in enumerate(value.args):
                walk(item, f"{where} -> {name}(arg {index})")
            for keyword in value.keywords:
                walk(keyword.value, f"{where} -> {name}({keyword.arg}=)")
        elif isinstance(value, ast.BinOp):
            walk(value.left, f"{where} (left of an operator)")
            walk(value.right, f"{where} (right of an operator)")

    walk(node, path)
    return found


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--name", help="only this assignment's name")
    parser.add_argument("--json", type=Path, help="write the rows to this file")
    parser.add_argument("--top", type=int, default=15, help="how many sites to list")
    args = parser.parse_args()

    rows: list[dict[str, object]] = []
    sites: list[tuple[str, int, str, int]] = []
    unread: list[tuple[str, str]] = []

    for path in sorted(ROOT.rglob("*.py")):
        if any(part in {".git", ".pixi", "__pycache__"} for part in path.parts):
            continue
        relative = path.relative_to(ROOT).as_posix()
        try:
            tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        except SyntaxError as exc:
            unread.append((relative, f"SyntaxError line {exc.lineno}: {exc.msg}"))
            continue
        except UnicodeDecodeError as exc:
            unread.append((relative, f"UnicodeDecodeError: {exc.reason}"))
            continue
        for node in tree.body:
            if isinstance(node, ast.Assign):
                names = [t.id for t in node.targets if isinstance(t, ast.Name)]
                value = node.value
            elif isinstance(node, ast.AnnAssign) and isinstance(node.target, ast.Name):
                names = [node.target.id]
                value = node.value
            else:
                continue
            if value is None or not names:
                continue
            if literal(value) is not None:
                continue                      # population A1's, not this one
            if args.name and names[0] != args.name:
                continue
            found = numbers_in(value, names[0])
            if not found:
                continue
            sites.append((relative, node.lineno, names[0], len(found)))
            for where, number, line in found:
                rows.append({"file": relative, "line": line, "name": names[0],
                             "path": where, "value": number})

    print(f"tip:         {tip()}")
    print(f"interpreter: python {platform.python_version()}")
    print()
    print(f"module-level structures holding numbers: {len(sites)}")
    print(f"numeric literals inside them:            {len(rows)}")
    print()
    print("THESE WERE NEVER OFFERED TO THE INCLUSION TEST. Most will be excluded")
    print("on sight. A number nobody was asked about is not a number anybody")
    print("decided to leave out, which is the whole of the finding.")
    print()
    for relative, line, name, count in sorted(sites, key=lambda s: -s[3])[:args.top]:
        print(f"  {count:5d}  {relative}:{line}  {name}")

    if args.name:
        print()
        for row in rows:
            print(f"  {row['file']}:{row['line']}  {row['path']} = {row['value']}")

    if args.json:
        args.json.write_text(json.dumps(rows, indent=1), encoding="utf-8")
        print(f"\nrows written to {args.json}")

    if unread:
        print()
        print(f"THE COUNTS ABOVE ARE A LOWER BOUND. {len(unread)} file(s) unread:")
        for relative, why in unread:
            print(f"    {relative}: {why}")
        print("spikes/pixi.toml pins python 3.12. Check the pin before calling a")
        print("file broken.")
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
