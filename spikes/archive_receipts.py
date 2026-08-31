"""Put a graded build's receipts somewhere they cannot be overwritten.

Principle P1: comparability is per-build. A coach's marks are scored against
the receipts of the build that coach actually graded, and the live engine
improves freely without invalidating them.

WHY A SCRIPT AND NOT A NOTE. `build_stamp.py` made a receipt able to say which
build produced it. That is not the same as an archive existing. The set Erin
Burger graded survived only because somebody had copied it aside for an
unrelated reason: the live directory was overwritten four times in one session
before anyone asked for it. A stamp makes an archive self-describing; it does
not make one.

So this is the deliberate action, and it runs BEFORE a grading pack goes out
rather than after somebody wants the answer.

    pixi run python archive_receipts.py --label erin-2026-08-28
    pixi run python archive_receipts.py --label coach-morning --note "..."

WHAT IT REFUSES, and each refusal is a thing that has actually gone wrong:

- **A set that is not one set.** Every receipt carries its build's stamp, so a
  directory half rebuilt from two builds can now be detected instead of
  archived as though it were whole. Before the stamp, nothing could tell.
- **Overwriting an existing archive.** An archive that a later run can replace
  is not an archive.
- **An empty or absent source.** Better to say so than to write a directory
  holding nothing and a digest of nothing.

WHAT IT ONLY WARNS ABOUT. A build from a dirty tree is archivable — most of a
working day produces one — but it is recorded loudly, because "this commit plus
edits nobody wrote down" is what made the first archive rest on an argument.

STDLIB ONLY. No solver. This must run and be testable wherever git runs.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import sys
from pathlib import Path

SPIKE_DIR = Path(__file__).resolve().parent
LIBRARY = SPIKE_DIR / "poc-output" / "library"
# The file this script writes. It is excluded from the digest so that editing
# it — a retroactive note, a correction — cannot change the digest of the set.
PROVENANCE = "PROVENANCE.md"


def receipts(directory: Path) -> list[Path]:
    """The receipt files, which are the record.

    What `build_library.py` writes as `{movement_id}.json`, and nothing else.
    Two other things live in the same directory and neither is a receipt:

    - `{movement_id}.proof.json`, written by `proof.py`, which holds solver
      repeat runs and carries no `generatedFrom` at all;
    - the `.glb` exports, which travel with the set but are not the record
      because they can differ in bytes between runs.

    A first version globbed `netball_*.json` and swept the proof file in with
    the receipts, so the one-set check below refused every real archive on the
    first attempt. Both are still COPIED and both are still in the digest. Only
    the stamp check needs to know which files are supposed to carry a stamp.
    """
    return sorted(
        path
        for path in directory.glob("netball_*.json")
        if not path.name.endswith(".proof.json")
    )


def stamps(directory: Path) -> dict[str, dict | None]:
    """Each receipt's `generatedFrom`, or None where a receipt predates it."""
    found: dict[str, dict | None] = {}
    for path in receipts(directory):
        try:
            found[path.name] = json.loads(
                path.read_text(encoding="utf-8")
            ).get("generatedFrom")
        except (json.JSONDecodeError, OSError) as problem:
            raise SystemExit(f"{path.name} cannot be read: {problem}") from None
    return found


def one_set(found: dict[str, dict | None]) -> tuple[bool, str]:
    """Whether every receipt came from the same build.

    Returns the verdict and the sentence that explains it, so a caller can
    print the reason rather than a boolean.
    """
    if not found:
        return False, "no receipts at all"
    missing = sorted(name for name, stamp in found.items() if not stamp)
    if missing:
        return False, (
            f"{len(missing)} of {len(found)} receipts carry no generatedFrom "
            f"stamp, so this set cannot say which build made it: "
            f"{', '.join(missing[:3])}"
            + (" and others" if len(missing) > 3 else "")
        )
    distinct = {json.dumps(stamp, sort_keys=True) for stamp in found.values()}
    if len(distinct) > 1:
        commits = sorted({stamp["commit"][:8] for stamp in found.values()})
        times = sorted({stamp["utcTimestamp"] for stamp in found.values()})
        return False, (
            f"these {len(found)} receipts carry {len(distinct)} different "
            f"stamps, so the directory holds more than one build. Commits: "
            f"{', '.join(commits)}. Times: {', '.join(times)}. Rebuild the "
            "whole library before archiving it."
        )
    return True, "every receipt carries the same stamp"


def digest(directory: Path) -> tuple[str, dict[str, str]]:
    """The combined digest, and each file's own.

    Each file's NAME then its digest, in sorted order, so that a renamed file
    changes the answer. `PROVENANCE.md` is excluded; refer to its constant.
    """
    per: dict[str, str] = {}
    rolling = hashlib.sha256()
    for path in sorted(directory.iterdir()):
        if not path.is_file() or path.name == PROVENANCE:
            continue
        one = hashlib.sha256(path.read_bytes()).hexdigest()
        per[path.name] = one
        rolling.update(path.name.encode("utf-8"))
        rolling.update(bytes.fromhex(one))
    return rolling.hexdigest(), per


def provenance(label: str, stamp: dict, combined: str, per: dict[str, str],
               note: str | None) -> str:
    lines = [
        f"# The receipts graded as `{label}`",
        "",
        "Written by `archive_receipts.py` under principle P1: comparability is",
        "per-build, so a coach's marks are scored against the receipts of the",
        "build that coach actually graded. These are that build's.",
        "",
    ]
    if note:
        lines += [note, ""]
    lines += [
        "## The build",
        "",
        "Copied from each receipt's own `generatedFrom`, which every receipt in",
        "this set carries identically. That was checked before the copy, not",
        "asserted afterwards.",
        "",
        "```json",
        json.dumps(stamp, indent=2),
        "```",
        "",
    ]
    if not stamp.get("treeWasClean", True):
        lines += [
            "**The tree was NOT clean.** This build carries edits that were not",
            "committed. `uncommittedDiffSha256` covers the tracked ones and",
            "`uncommittedPaths` names every path git reported, so two dirty",
            "builds can at least be told apart — but the edits themselves are",
            "not recoverable from here. Prefer archiving a clean build.",
            "",
        ]
    lines += [
        "## Hashes",
        "",
        "Combined SHA-256 over every file EXCEPT `PROVENANCE.md`, each file's",
        "name then its own digest, in sorted order. This file is excluded so",
        "that editing it cannot change the digest of the set.",
        "",
        f"    {combined}",
        "",
        "Per file:",
        "",
    ] + [f"    {value}  {name}" for name, value in per.items()] + [
        "",
        "## How to reproduce it",
        "",
        f"Solve the library at commit `{stamp.get('commit')}`. The `.glb`",
        "exports may differ in bytes between runs; the `.json` receipts are the",
        "record that matters.",
        "",
    ]
    return "\n".join(lines)


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--label", required=True,
                        help="what this build is, e.g. erin-2026-08-28")
    parser.add_argument("--note", default=None,
                        help="a sentence about why it is being kept")
    parser.add_argument("--source", default=str(LIBRARY))
    arguments = parser.parse_args(argv[1:])

    source = Path(arguments.source)
    if not source.is_dir():
        print(f"{source} is not a directory; nothing to archive.")
        return 1

    found = stamps(source)
    whole, why = one_set(found)
    if not whole:
        print(f"REFUSED: {why}")
        return 1

    destination = source.parent / f"library-{arguments.label}"
    if destination.exists():
        print(
            f"REFUSED: {destination} already exists. An archive a later run "
            "can replace is not an archive. Choose another label, or delete "
            "that directory deliberately if it was a mistake."
        )
        return 1

    shutil.copytree(source, destination)
    (destination / PROVENANCE).unlink(missing_ok=True)
    combined, per = digest(destination)
    stamp = next(iter(found.values()))
    (destination / PROVENANCE).write_text(
        provenance(arguments.label, stamp, combined, per, arguments.note),
        encoding="utf-8",
    )

    print(f"archived {len(per)} files -> {destination}")
    print(f"  build     {stamp.get('commit')}")
    print(f"  clean     {stamp.get('treeWasClean')}")
    print(f"  built at  {stamp.get('utcTimestamp')}")
    print(f"  digest    {combined}")
    if not stamp.get("treeWasClean", True):
        print("  WARNING: archived from a dirty tree; refer to PROVENANCE.md")
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main(sys.argv))
