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

# FOUR DECLARED STATES, AND THE DEFAULT IS THE LOUD ONE.
#
# A document records a DECISION, not only a specification, so "absent from the
# code" splits four ways and no text test can tell them apart. The check asks
# "is this name in the code". The sentence that matters asks "is this name
# CLAIMED to be in the code", and only a reader answers that. So a state is
# DECLARED here, never detected.
#
#   ASSUMED             a name a document treats as existing. THE DEFAULT.
#   DEFINED             a specification naming its own fields.
#   UNDER_CONSTRUCTION  named, and a lane is building it.
#   REJECTED            named, and a decision says do not build it.
#
# THE DEFAULT STAYS ASSUMED BECAUSE IT CAUGHT ITS OWN AUTHOR. `sourceScope` was
# added to this register's schema on 9 September and never filed, and it
# reported itself in the dangerous class on 14 September. A default that fails
# toward visibility is right, and it proving itself on the lane that wrote it is
# the best evidence there is.
#
# A LINE NUMBER IS ITSELF A NUMBER THAT GOES STALE, AND THAT IS THE POINT.
# Adding a section to the schema moved `sourceScope` off line 89 within minutes
# of this table being written, and the run refused. A vaguer pointer — the
# document alone — could not decay because it says less. THIS ONE DECAYS AND
# THE DECAY IS CAUGHT, which is the trade this register makes everywhere: a
# claim precise enough to be wrong, beside the instrument that finds it wrong.
#
# EVERY NON-DEFAULT STATE CARRIES A `file:line` AND THE RUN REFUSES WITHOUT ONE
# THAT RESOLVES. Not prose: a line a reader can open. An exemption list grows
# quietly and nobody can audit it. A table where every entry points at the
# sentence that justifies it can be checked line by line by somebody who
# disagrees. It is the movement lane's `unitEvidence` rule one level over:
# carry the evidence, never the belief.
ASSUMED = "ASSUMED"
DEFINED = "DEFINED"
UNDER_CONSTRUCTION = "UNDER_CONSTRUCTION"
REJECTED = "REJECTED"

DECLARED: dict[str, dict[str, str]] = {
    DEFINED: {
        # A specification that did not name its own fields would be no
        # specification.
        "movesWith": "COACH_REVIEW_SPEC_INTERFACE.md:72",
        # This register's own schema columns. Naming them specifies them.
        "sourceKind": "MOVEMENT_PARAMETER_REGISTER_SCHEMA.md:54",
        "unitDeclared": "MOVEMENT_PARAMETER_REGISTER_SCHEMA.md:48",
        "unitImplied": "MOVEMENT_PARAMETER_REGISTER_SCHEMA.md:49",
        "unitEvidence": "MOVEMENT_PARAMETER_REGISTER_SCHEMA.md:50",
        "derivedFrom": "MOVEMENT_PARAMETER_REGISTER_SCHEMA.md:55",
        "rootSource": "MOVEMENT_PARAMETER_REGISTER_SCHEMA.md:56",
        "reachedBy": "MOVEMENT_PARAMETER_REGISTER_SCHEMA.md:58",
        "existsInCode": "MOVEMENT_PARAMETER_REGISTER_SCHEMA.md:59",
        "whatWouldChangeIt": "MOVEMENT_PARAMETER_REGISTER_SCHEMA.md:60",
        "AUTHOR_INTENT": "MOVEMENT_PARAMETER_REGISTER_SCHEMA.md:75",
        "LITERATURE": "MOVEMENT_PARAMETER_REGISTER_SCHEMA.md:73",
        # The register's own STATE vocabulary. Filed for the same reason
        # AUTHOR_INTENT and LITERATURE are: naming a value of this schema
        # specifies it. THIS IS THE THIRD TIME TODAY the register's own
        # vocabulary reported itself in the dangerous class, and each time
        # the default was right to.
        "ASSUMED": "MOVEMENT_PARAMETER_REGISTER_SCHEMA.md:96",
        "DEFINED": "MOVEMENT_PARAMETER_REGISTER_SCHEMA.md:97",
        "UNDER_CONSTRUCTION": "MOVEMENT_PARAMETER_REGISTER_SCHEMA.md:98",
        "REJECTED": "MOVEMENT_PARAMETER_REGISTER_SCHEMA.md:99",
        # FILED 2026-09-15, AND IT CAUGHT ITS AUTHOR BEFORE IT WAS FILED.
        "sourceScope": "MOVEMENT_PARAMETER_REGISTER_SCHEMA.md:141",
    },
    UNDER_CONSTRUCTION: {
        # docs/RELEASE_HAND_PAPER.md names eleven quantities for the release
        # hand. On 14 September none existed in either repository. PR #131
        # landed a flick on the chest pass on 15 September and six of the
        # eleven now exist, all of them in one proposal file. These five do
        # not, and a reader finding them as "absent" would start building what
        # a lane is already building.
        "wristSpeedCmPerS": "RELEASE_HAND_PAPER.md:581",
        "leftWristFlexionDegrees": "RELEASE_HAND_PAPER.md:574",
        "rightWristFlexionDegrees": "RELEASE_HAND_PAPER.md:574",
        "leftFingerFlexionDegrees": "RELEASE_HAND_PAPER.md:576",
        "rightFingerFlexionDegrees": "RELEASE_HAND_PAPER.md:576",
    },
    REJECTED: {
        # THE CLIP CONTRACT PROPOSED `engineCommit` AND A RULING REPLACED IT
        # with `generatedFrom`, carrying commit, treeWasClean, utcTimestamp and
        # variant. The deciding argument: engineCommit alone drops
        # treeWasClean, so a clip exported from a dirty tree would name a
        # commit that does not contain the code that made it. A provenance
        # field that can quietly lie is worse than the commit message it
        # replaces. The documents keep the name ON PURPOSE so the decision can
        # be reopened, so its absence from code is the CORRECT outcome.
        "engineCommit": "TACTICS_CLIP_CONTRACT.md:248",
    },
}


def declared_state(token: str) -> tuple[str, str]:
    """The declared state of a name, and the line that justifies it."""
    for state, table in DECLARED.items():
        if token in table:
            return state, table[token]
    return ASSUMED, ""


def unresolvable_evidence(docs: Path) -> list[tuple[str, str, str, str]]:
    """Every declared entry whose evidence does not open.

    THE REFUSAL IS THE POINT. A state with evidence nobody can open is an
    exemption wearing a citation's clothes, which is the same fault this
    register reports in the library's own numbers.
    """
    broken: list[tuple[str, str, str, str]] = []
    for state, table in DECLARED.items():
        for token, where in table.items():
            document, _, line = where.partition(":")
            if not line.isdigit():
                broken.append((state, token, where, "not in file:line form"))
                continue
            page = docs / document
            if not page.exists():
                broken.append((state, token, where, f"{document} is not in docs/"))
                continue
            held = page.read_text(encoding="utf-8", errors="replace").splitlines()
            if int(line) > len(held):
                broken.append((state, token, where,
                               f"{document} has {len(held)} lines"))
            elif token not in held[int(line) - 1]:
                # THE LINE MUST NAME THE THING. A first draft of this table
                # used ":1" for thirteen entries, and every one resolved,
                # because a line 1 always exists. That is an exemption wearing
                # a citation's clothes, which is the fault this register
                # reports in the library's own numbers.
                broken.append((state, token, where,
                               f"line {line} does not name {token!r}"))
    return broken


# A word that is upper case in prose and is not a parameter.
NOT_A_PARAMETER = {
    "KNOWN_ISSUES", "README", "MEASURE_UNITS", "TODO", "NOTE", "AND", "NOT",
    "THE", "ALL", "ANY", "CSV", "JSON", "HTML", "GLB", "FPS", "SHA", "URL",
    "CPU", "GPU", "API", "CLI", "PNG", "JPEG", "MP4", "AAOS", "ISB", "SMPL",
    "MHR", "MPFB", "PR", "CI", "OK", "GIT_DIR",
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

    # `docs` in this function is a LIST of pages, not the directory.
    doc_dir = ROOT / "docs"
    broken = unresolvable_evidence(doc_dir)

    by_state: dict[str, dict[str, set[str]]] = {
        ASSUMED: {}, DEFINED: {}, UNDER_CONSTRUCTION: {}, REJECTED: {},
    }
    for token, where in absent.items():
        state, _evidence = declared_state(token)
        by_state[state][token] = where

    for state in (ASSUMED, UNDER_CONSTRUCTION, REJECTED, DEFINED):
        print(f"  {state:20s} {len(by_state[state]):3d}")
    print()
    print("**ASSUMED IS THE POPULATION. THE OTHER THREE ARE ITS MEASUREMENT")
    print("ARTEFACTS.** A specification naming its own fields, a name a lane is")
    print("building, and a name a decision rejected are all correctly absent. A")
    print("document that reasons about a parameter, names its unit and puts it in")
    print("front of a coach while nothing carries it is the defect this lane")
    print("exists to catch. A STATE IS DECLARED AND NEVER DETECTED: no text test")
    print("can tell a name being proposed from a name being buried.")
    print()
    for state in (ASSUMED, UNDER_CONSTRUCTION, REJECTED, DEFINED):
        for token, where in sorted(by_state[state].items()):
            _s, evidence = declared_state(token)
            tail = evidence if evidence else ", ".join(sorted(where))
            print(f"  {state:20s} {token:26s} {tail}")

    # THE TRIAGE SIGNAL, AND IT IS TRIAGE. A name absent from all code, in a
    # document that ALSO names a term which IS in code, is the signature of a
    # replaced proposal. `engineCommit` has 0 code hits and `generatedFrom`,
    # named in the same contract, has 24. IT PROVES NOTHING. It shortens the
    # list a person reads, exactly as the keyword pass over the library's 94
    # `why` fields does, and a triage signal that drifts into a verdict is the
    # fault this register exists to catch.
    print()
    print("TRIAGE, NOT A VERDICT: an ASSUMED name whose document also names a")
    print("term that IS in the code. That is the signature of a replaced")
    print("proposal, and it proves nothing. It shortens what a person reads.")
    flagged = 0
    for token, where in sorted(by_state[ASSUMED].items()):
        companions = set()
        for document in where:
            page = (doc_dir / document).read_text(encoding="utf-8", errors="replace")
            for other in BACKTICKED.findall(page):
                other = other.strip()
                if other == token or " " in other or "." in other or "/" in other:
                    continue
                if (CAMEL.fullmatch(other) or UPPER.fullmatch(other)) and other in body:
                    companions.add(other)
        if companions:
            flagged += 1
            shown = ", ".join(sorted(companions)[:4])
            print(f"    {token:26s} shares a document with: {shown}")
    if not flagged:
        print("    none")

    if elsewhere:
        print()
        print("PRESENT IN THE SIBLING REPOSITORY, so NOT population C. These are")
        print("cross-repository references and the documents describing them are")
        print("about the consumer's code, not this engine's:")
        for token, where in sorted(elsewhere.items()):
            print(f"  {token:34s} {', '.join(sorted(where))}")

    if broken:
        print()
        print(f"{len(broken)} DECLARED STATE(S) CARRY EVIDENCE THAT DOES NOT OPEN.")
        print("A state whose line nobody can read is an exemption wearing a")
        print("citation's clothes, which is the fault this register reports in")
        print("the library's own numbers. Fix the line, or drop the state:")
        for state, token, where, why in broken:
            print(f"    {state} {token}  ->  {where}")
            print(f"        {why}")
        return 2

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
