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

# A NAME A DOCUMENT DEFINES IS NOT A NAME A DOCUMENT ASSUMES, and only a reader
# can tell them apart. The check asks "is this name in the code". The sentence
# that matters asks "is this name CLAIMED to be in the code", and no text test
# answers that. So this list is HAND-WRITTEN, with the evidence per entry.
#
# A specification that did not name its own fields would be no specification.
# `movesWith` sits in COACH_REVIEW_SPEC_INTERFACE.md's field table at line 72
# and has its own section 7 at line 282, "movesWith, and why a specification
# needs it", setting out its three resolvable forms. It is being specified.
#
# The register's own schema columns are the same thing: naming `sourceKind` and
# `unitEvidence` specifies them, it does not claim they exist. They stop being
# population C when the sidecar and the renderer are built.
#
# THE DEFAULT IS THE LOUD ONE ON PURPOSE. A name not listed here is reported as
# ASSUMED, so a new one appears in the dangerous class rather than the safe one.
DEFINED_NOT_ASSUMED = {
    "movesWith": "COACH_REVIEW_SPEC_INTERFACE.md field table line 72, and its "
                 "own section 7 at line 282",
    "sourceKind": "a column of this register's own schema, not yet built",
    "unitDeclared": "a column of this register's own schema, not yet built",
    "unitImplied": "a column of this register's own schema, not yet built",
    "unitEvidence": "a column of this register's own schema, not yet built",
    "derivedFrom": "a column of this register's own schema, not yet built",
    "rootSource": "a column of this register's own schema, not yet built",
    "reachedBy": "a column of this register's own schema, not yet built",
    "existsInCode": "a column of this register's own schema, not yet built",
    "whatWouldChangeIt": "a column of this register's own schema, not yet built",
    "AUTHOR_INTENT": "a sourceKind of this register's own schema, not yet built",
    "LITERATURE": "a sourceKind of this register's own schema, not yet built",
}

# A word that is upper case in prose and is not a parameter.
NOT_A_PARAMETER = {
    "KNOWN_ISSUES", "README", "MEASURE_UNITS", "TODO", "NOTE", "AND", "NOT",
    "THE", "ALL", "ANY", "CSV", "JSON", "HTML", "GLB", "FPS", "SHA", "URL",
    "CPU", "GPU", "API", "CLI", "PNG", "JPEG", "MP4", "AAOS", "ISB", "SMPL",
    "MHR", "MPFB", "PR", "CI", "OK",
}


# THIS REGISTER'S OWN FILES ARE NOT PART OF THE CORPUS, AND THE REASON IS A
# DEFECT THIS FILE CAUSED. Once `register_survey_prose.py` was committed it
# became a tracked file, so `git ls-files` handed its own source to the
# presence test. Its docstring names `wristToDegrees` and `fingerToDegrees`,
# and its DEFINED_NOT_ASSUMED table names ten more. The absent count fell from
# 25 to 7 and the population's entire dangerous class vanished, because the
# instrument had found its own mentions of the names it was searching for.
#
# An instrument that searches for a name must not count its own mention of it.
OWN_FILES = "scripts/register_"


def code_text() -> str:
    """Every tracked .py and .json file, as one string, minus this register's.

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
        if name.startswith(OWN_FILES):
            continue
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

    defined = {t_: w for t_, w in absent.items() if t_ in DEFINED_NOT_ASSUMED}
    assumed = {t_: w for t_, w in absent.items() if t_ not in DEFINED_NOT_ASSUMED}

    print(f"  DEFINED, absent by design: {len(defined)}")
    print(f"  ASSUMED, and absent:       {len(assumed)}")
    print()
    print("**ASSUMED IS THE POPULATION. DEFINED IS ITS MEASUREMENT ARTEFACT.**")
    print("A specification that did not name its own fields would be no")
    print("specification. A document that reasons about a parameter, names its")
    print("unit and puts it in front of a coach, while nothing carries it, is")
    print("the defect this lane exists to catch.")
    print()
    for token, where in sorted(assumed.items()):
        print(f"  ASSUMED  {token:22s} {', '.join(sorted(where))}")
    print()
    for token, where in sorted(defined.items()):
        print(f"  defined  {token:22s} {DEFINED_NOT_ASSUMED[token]}")

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
