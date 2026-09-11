"""Every code identifier a document names that the code does not contain.

A document saying "the receipt now carries `solveParameters`" is making a claim
about a TREE, not about a design. When the identifier is not in that tree the
sentence is false, and nothing on the page says so. This lists the identifiers a
document names and the code does not have, so a lane can read its own.

IT REPORTS CANDIDATES, NEVER FAULTS, and the difference is the whole method. An
identifier is legitimately absent when the document proposes it, quotes a
withdrawn name, describes another repository, or names a rig channel that lives
in `.assets`. On the first run 48 of 51 candidates were exactly those. **Only the
sentence says which, so every candidate must be READ.**

It reads a NAMED REF rather than the working tree, because a claim about code is
a claim about one commit and so is this measurement.

    python scripts/docs_present_tense_audit.py
    python scripts/docs_present_tense_audit.py origin/main

TWO EARLIER VERSIONS WERE WRONG AND BOTH COUNTS WERE PUBLISHED-SHAPED NONSENSE.
They are recorded because the number this prints is only worth what its
predecessors' failures show it survived.

  1. The first OVER-COLLECTED and reported 129: `.md` filenames, OCR page
     markers such as `_page_81`, a truncated hash, and dotted paths like
     `MotionTrack.is_symmetric` whose last segment does exist.

  2. The second SEARCHED FILE CONTENTS FOR A FILENAME and reported 75. A Python
     file does not contain its own name, so every `test_*.py` a document named
     looked absent while all 77 test files sat in the tree. Its top eleven
     candidates were all real files.

     THAT IS A HAYSTACK ERROR RATHER THAN A NEEDLE ERROR, and it fails in the
     direction that manufactures work. The haystack is now the path list PLUS
     the file contents, and `_prove_the_haystack` refuses to report until three
     known-present names are found in it.
"""

from __future__ import annotations

import collections
import re
import subprocess
import sys

BACKTICKED = re.compile(r"`([^`\n]{2,80})`")

# The shapes an identifier takes in this repository.
SNAKE = re.compile(r"^[a-z][a-z0-9]*(?:_[a-z0-9]+)+$")
CONST = re.compile(r"^[A-Z][A-Z0-9]*(?:_[A-Z0-9]+)+$")
CAMEL = re.compile(r"^[a-z]+(?:[A-Z][a-z0-9]*)+$")
PASCAL = re.compile(r"^[A-Z][a-z0-9]+(?:[A-Z][a-z0-9]*)+$")
FILE_SUFFIX = (".py", ".json", ".js", ".html", ".ps1", ".txt")

HASH = re.compile(r"[0-9a-f]{6,}\.*")
PAGE_MARKER = re.compile(r"_?page_?\d+_?")

# Names that must be found, or the haystack is built wrongly. A filename, a
# module and a constant, because each is found by a different mechanism.
CONTROLS = ("test_elbow_pole.py", "possession_solve.py", "MEASURE_UNITS")


def _read(*args: str) -> str:
    return subprocess.run(args, capture_output=True).stdout.decode(
        "utf-8", errors="replace")


def identifier(span: str) -> str | None:
    """Return the name to look up, or None when this span is not one.

    A dotted path names its own last segment, so `ball_track.offset_at` is a
    question about `offset_at`. A filename is returned whole, because it is
    found in the path list rather than in any file's contents.
    """
    span = span.strip().removesuffix("()")
    if span.endswith(".md") or "/" in span or " " in span:
        return None
    if "<" in span or ">" in span:
        return None                                  # a placeholder
    if span.endswith(FILE_SUFFIX):
        return span
    last = span.split(".")[-1]
    if not last or len(last) < 4:
        return None
    if HASH.fullmatch(last) or PAGE_MARKER.fullmatch(last):
        return None
    if any(p.fullmatch(last) for p in (SNAKE, CONST, CAMEL, PASCAL)):
        return last
    return None


def _prove_the_haystack(haystack: str) -> None:
    """Refuse to report unless names known to be present are found.

    The second version of this script reported 75 missing identifiers while 76
    of them were in the tree. A count is worthless without this.
    """
    missing = [name for name in CONTROLS if name not in haystack]
    if missing:
        raise SystemExit(
            "REFUSED: the haystack is built wrongly. These are in the tree and "
            "were not found: " + ", ".join(missing))


def main(ref: str) -> int:
    docs = [p for p in _read("git", "ls-tree", "-r", "--name-only", ref,
                             "docs/").splitlines() if p.endswith(".md")]
    if not docs:
        raise SystemExit(f"REFUSED: no documents under docs/ at {ref}")
    every = _read("git", "ls-tree", "-r", "--name-only", ref).splitlines()
    code = [p for p in every
            if not p.startswith("docs/") and not p.endswith(".md")]

    spans = 0
    rejected = 0
    where: dict[str, set[str]] = collections.defaultdict(set)
    for path in docs:
        for span in BACKTICKED.findall(_read("git", "show", f"{ref}:{path}")):
            spans += 1
            name = identifier(span)
            if name is None:
                rejected += 1
                continue
            where[name].add(path)

    # A filename lives in the PATH. An identifier lives in the CONTENT.
    haystack = "\n".join(code) + "\n" + "\n".join(
        _read("git", "show", f"{ref}:{p}") for p in code)
    _prove_the_haystack(haystack)

    missing = sorted(name for name in where if name not in haystack)
    resolved = len(where) - len(missing)

    print(f"read at {ref}")
    print(f"  {len(docs)} documents, {len(code)} tracked non-document files")
    print(f"  {spans} backticked spans, {rejected} rejected as not identifiers")
    print(f"  {len(where)} distinct identifiers kept, "
          f"{resolved} resolve ({100 * resolved / len(where):.1f}%)")
    print(f"  haystack proved on {len(CONTROLS)} known-present names")
    print()
    print(f"CANDIDATES: {len(missing)} named in docs and in NO tracked code file")
    print("READ THE SENTENCE FOR EACH. Most are proposals, other repositories,")
    print("rig channels in .assets, or names a document says do not exist.")
    print()
    for name in missing:
        files = sorted(f.removeprefix("docs/") for f in where[name])
        print(f"  {name:<44} {len(files):>2}  {', '.join(files[:3])}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1] if len(sys.argv) > 1 else "origin/main"))
