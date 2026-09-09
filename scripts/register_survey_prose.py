"""Population C: parameters named in the documents that the code does not carry.

    python scripts/register_survey_prose.py
    python scripts/register_survey_prose.py --show

WHY THIS POPULATION EXISTS, AND IT EXISTS BECAUSE THE CHARTER WAS WRONG. This
lane was briefed to register `wristToDegrees` and `fingerToDegrees` as
unsourced constants in the release model. **They are not constants. They do not
appear anywhere in main's code.** They are two names in a paragraph.

That is a WORSE failure than an unsourced constant, because an unsourced
constant at least has a value and a call site. A name in a paragraph can be
reasoned about, carried into a second document and put in front of a coach,
while denoting nothing that runs.

WHAT IT READS. Every backticked token in `docs/*.md` shaped like an identifier,
in the two shapes that name a parameter here:

    camelCase    the shape of the library's measure and key names, and the
                 shape of the charter's own two examples
    UPPER_CASE   the shape of a python module constant

**WHAT IT DELIBERATELY DOES NOT READ, so a reader can disagree with the
boundary rather than discover it.** `snake_case` is excluded: 1181 tokens
dominated by drill names, file stems and function names, where absence from the
code means nothing. `dotted` is excluded because it is a compound of the two
shapes above and each half is already tested. Paths, phrases and commit hashes
are excluded on their face.

WHAT COUNTS AS PRESENT. A token is present if it appears anywhere in a tracked
`.py` or `.json` file: as an identifier, a dictionary key, or a string. That is
a DELIBERATELY WEAK test. A weak presence test makes the absent list SHORTER
and therefore stronger, because anything it reports is absent under the most
generous reading available.

**AND IT SEARCHES THE SIBLING REPOSITORY TOO, BECAUSE WITHOUT IT ELEVEN OF THE
TWENTY-FIVE WERE FALSE.** `docs/TACTICS_CLIP_CONTRACT.md` and
`docs/TACTICS_CONTRACT_QUESTIONS.md` describe the consumer's code, which lives
in `braven-tactics`. `isKick`, `actionShapeOf`, `CARRY_OFFSET`,
`requestAnimation` and seven more are absent from THIS repository and present
in that one. A name that denotes something in the repository it describes is
not a name denoting nothing.

**IF THE SIBLING IS NOT ON THIS MACHINE THE RUN SAYS SO AND MARKS EVERY
OTHERWISE-ABSENT ROW UNTESTED.** Reporting eleven cross-repository references
as absent, on a machine that simply lacks the checkout, would be a finding
manufactured by a missing directory.

    exit 0  the sibling was searched
    exit 2  the sibling was not found, so the absent list is untested
"""

from __future__ import annotations

import argparse
import collections
import platform
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from register_survey_constants import tip  # noqa: E402

BACKTICKED = re.compile(r"`([^`\n]{1,80})`")
CAMEL = re.compile(r"[a-z]+[A-Z][A-Za-z0-9]*")
UPPER = re.compile(r"[A-Z][A-Z0-9_]{2,}")

# A word that is upper case in prose and is not a parameter.
NOT_A_PARAMETER = {
    "KNOWN_ISSUES", "README", "MEASURE_UNITS", "TODO", "NOTE", "AND", "NOT",
    "THE", "ALL", "ANY", "CSV", "JSON", "HTML", "GLB", "FPS", "SHA", "URL",
    "CPU", "GPU", "API", "CLI", "PNG", "JPEG", "MP4", "AAOS", "ISB", "SMPL",
    "MHR", "MPFB", "PR", "CI", "OK",
}


def code_text() -> str:
    """Every tracked .py and .json file, as one string.

    A DELIBERATELY WEAK PRESENCE TEST. Refer to the docstring.
    """
    listing = subprocess.run(
        ["git", "-C", str(ROOT), "ls-files", "*.py", "*.json"],
        capture_output=True, text=True, check=False,
    )
    if listing.returncode != 0:
        raise SystemExit(f"git ls-files exited {listing.returncode}")
    parts = []
    for name in listing.stdout.split():
        path = ROOT / name
        try:
            parts.append(path.read_text(encoding="utf-8", errors="replace"))
        except OSError:
            continue
    return "\n".join(parts)


def sibling_text(root: Path) -> str | None:
    """The consumer repository's source, or None when it is not on this machine."""
    if not (root / ".git").exists():
        return None
    listing = subprocess.run(
        ["git", "-C", str(root), "ls-files", "*.ts", "*.tsx", "*.js", "*.json"],
        capture_output=True, text=True, check=False,
    )
    if listing.returncode != 0:
        return None
    parts = []
    for name in listing.stdout.split():
        try:
            parts.append((root / name).read_text(encoding="utf-8", errors="replace"))
        except OSError:
            continue
    return "\n".join(parts)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--show", action="store_true",
                        help="list every absent token with the documents naming it")
    parser.add_argument("--sibling", type=Path,
                        default=Path("F:/Repositories/braven-tactics"),
                        help="the consumer repository the contract documents describe")
    args = parser.parse_args()

    docs = sorted((ROOT / "docs").glob("*.md"))
    named: dict[str, set[str]] = collections.defaultdict(set)
    for path in docs:
        text = path.read_text(encoding="utf-8", errors="replace")
        for match in BACKTICKED.finditer(text):
            token = match.group(1).strip()
            if not token or " " in token or "/" in token or "." in token:
                continue
            if CAMEL.fullmatch(token) or (
                UPPER.fullmatch(token) and token not in NOT_A_PARAMETER
            ):
                named[token].add(path.name)

    body = code_text()
    here = {token: where for token, where in named.items() if token not in body}
    sibling = sibling_text(args.sibling)
    if sibling is None:
        elsewhere: dict[str, set[str]] = {}
        absent = here
    else:
        elsewhere = {t: w for t, w in here.items() if t in sibling}
        absent = {t: w for t, w in here.items() if t not in sibling}

    print(f"tip:         {tip()}")
    print(f"interpreter: python {platform.python_version()}")
    print()
    print(f"documents read:                       {len(docs)}")
    print(f"identifier-shaped names in them:      {len(named)}")
    print(f"not found in THIS repository:         {len(here)}")
    if sibling is None:
        print(f"sibling repository:                   NOT FOUND at {args.sibling}")
    else:
        print(f"  of those, present in the sibling:   {len(elsewhere)}")
        print(f"  ABSENT FROM BOTH REPOSITORIES:      {len(absent)}")
    print()
    print("The presence test is deliberately weak: a token counts as present if")
    print("it appears anywhere in a tracked .py or .json file, as an identifier,")
    print("a key or a string. A weak test makes this list SHORTER and therefore")
    print("stronger. Everything below is absent under the most generous reading.")
    print()

    for token, where in sorted(absent.items()):
        docs_named = ", ".join(sorted(where))
        print(f"  {token:34s} {docs_named}")

    if elsewhere:
        print()
        print("PRESENT IN THE SIBLING REPOSITORY, so NOT population C. These are")
        print("cross-repository references and the documents describing them are")
        print("about the consumer's code, not this engine's:")
        for token, where in sorted(elsewhere.items()):
            print(f"  {token:34s} {', '.join(sorted(where))}")

    if sibling is None:
        print()
        print("THE LIST ABOVE IS UNTESTED. The sibling repository was not found,")
        print("so a cross-repository reference cannot be told from a name that")
        print("denotes nothing. Pass --sibling, or read this as a candidate list.")
        return 2

    if args.show:
        print()
        print("Every name read, present or absent:")
        for token in sorted(named):
            mark = "ABSENT " if token in absent else "present"
            print(f"  {mark}  {token}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
