"""Population A of the movement-parameter register: authored constants in code.

THIS IS A SURVEY AND NOT THE REGISTER. It answers one question only: which
module-level numeric constants exist, and where. It does NOT decide whether a
constant makes a claim about human movement, because that is the inclusion
test, and the inclusion test is a judgment that gets committed separately with
its reasons. A row here is a CANDIDATE.

    python scripts/register_survey_constants.py
    python scripts/register_survey_constants.py --json rows.json

WHY THE AST AND NOT A REGEX. A regex over the text finds a line that LOOKS like
an assignment. The first version of this survey was a regex and reported 233.
The AST reports 252. The difference is not a rounding: a regex cannot see an
annotated assignment, and it happily matches inside a string. A guard on text
is not a guard on code.

WHY IT REFUSES RATHER THAN SKIPS. An extractor that cannot parse a file and
carries on silently UNDERCOUNTS, and an undercount is indistinguishable from an
absence of constants. So a file this interpreter cannot read makes the whole
count incomplete, the run says so, and the exit code is 2.

    exit 0  every file was read; the count is complete
    exit 2  at least one file was not read; the count is a lower bound

THE INTERPRETER IS PART OF THE RESULT. `spikes/pixi.toml` pins python 3.12 and
`.github/workflows/unit-tests.yml` runs 3.11, and at least one tracked file
uses syntax that only 3.12 accepts. A count from this survey means nothing
without the version that produced it, so the version is printed with it.
"""

from __future__ import annotations

import argparse
import ast
import json
import platform
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def tip() -> str:
    """The commit every count below was taken on, read from git and not typed.

    A count without its tip is not reproducible: main moves under a lane
    mid-unit, and it did so during this survey's first run.
    """
    try:
        found = subprocess.run(
            ["git", "-C", str(ROOT), "rev-parse", "HEAD"],
            capture_output=True, text=True, check=False,
        )
    except OSError:
        return "UNKNOWN (git did not run)"
    if found.returncode != 0:
        return f"UNKNOWN (git exited {found.returncode})"
    dirty = subprocess.run(
        ["git", "-C", str(ROOT), "status", "--porcelain"],
        capture_output=True, text=True, check=False,
    )
    mark = "" if dirty.stdout.strip() == "" else " (WORKING TREE DIRTY)"
    return found.stdout.strip()[:40] + mark


def literal(node: ast.expr) -> float | int | None:
    """A bare number, or a negated bare number. Nothing else.

    `RATE = 3 * 4` is deliberately NOT a literal here. It is a computed value
    and its inputs are the thing the register would have to carry, so it is out
    of this survey's scope rather than silently flattened to 12.
    """
    if isinstance(node, ast.Constant) and isinstance(node.value, (int, float)) \
            and not isinstance(node.value, bool):
        return node.value
    if isinstance(node, ast.UnaryOp) and isinstance(node.op, ast.USub) \
            and isinstance(node.operand, ast.Constant) \
            and isinstance(node.operand.value, (int, float)) \
            and not isinstance(node.operand.value, bool):
        return -node.operand.value
    return None


def constants_in(tree: ast.Module) -> list[tuple[int, str, float | int]]:
    """Module level only. A constant inside a function is not authored policy."""
    out: list[tuple[int, str, float | int]] = []
    for node in tree.body:
        if isinstance(node, ast.Assign):
            names = [t.id for t in node.targets if isinstance(t, ast.Name)]
            value = node.value
        elif isinstance(node, ast.AnnAssign) and isinstance(node.target, ast.Name):
            names = [node.target.id]
            value = node.value
        else:
            continue
        if value is None:
            continue
        number = literal(value)
        if number is None:
            continue
        for name in names:
            out.append((node.lineno, name, number))
    return out


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--json", type=Path, help="write the rows to this file")
    args = parser.parse_args()

    rows: list[dict[str, object]] = []
    unread: list[tuple[str, str]] = []

    for path in sorted(ROOT.rglob("*.py")):
        if any(part in {".git", ".pixi", "__pycache__"} for part in path.parts):
            continue
        relative = path.relative_to(ROOT).as_posix()
        try:
            text = path.read_text(encoding="utf-8")
        except UnicodeDecodeError as exc:
            unread.append((relative, f"UnicodeDecodeError: {exc.reason}"))
            continue
        try:
            tree = ast.parse(text, filename=str(path))
        except SyntaxError as exc:
            unread.append((relative, f"SyntaxError line {exc.lineno}: {exc.msg}"))
            continue
        for line, name, number in constants_in(tree):
            rows.append({"file": relative, "line": line, "name": name, "value": number})

    print(f"tip:         {tip()}")
    print(f"interpreter: python {platform.python_version()} ({sys.implementation.name})")
    print()
    print(f"module-level numeric constants: {len(rows)}")
    lower = sorted({r['name'] for r in rows if not str(r['name']).isupper()})
    print(f"  names that are not upper case: {len(lower)}")
    for name in lower[:10]:
        print(f"      {name}")
    print()

    by_directory: dict[str, int] = {}
    for row in rows:
        head = str(row["file"]).split("/")[0]
        key = head if "/" in str(row["file"]) else "(repository root)"
        by_directory[key] = by_directory.get(key, 0) + 1
    for key in sorted(by_directory, key=lambda k: -by_directory[k]):
        print(f"{by_directory[key]:5d}  {key}")

    if args.json:
        args.json.write_text(json.dumps(rows, indent=1), encoding="utf-8")
        print(f"\nrows written to {args.json}")

    if unread:
        print()
        print(f"THE COUNT ABOVE IS A LOWER BOUND. {len(unread)} file(s) were not read")
        print("by this interpreter, so their constants are absent from it:")
        for relative, why in unread:
            print(f"    {relative}: {why}")
        print()
        print("A syntax error here is more often the WRONG INTERPRETER than a")
        print("broken file. spikes/pixi.toml pins python 3.12. Check the pin")
        print("before reporting a file as broken.")
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
