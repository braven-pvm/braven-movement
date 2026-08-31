"""Which build produced an artefact, in one shape for the whole repository.

STDLIB ONLY, AND THAT IS THE POINT. This began inside `build_library.py`, whose
first job is to import `pymomentum` and solve. The hosted runner has no
`pymomentum`, so `test_receipt_stamp.py` could not even LOAD there: eleven
working guards became one import error on every machine without a solver, which
is the opposite of what a guard is for. Marking them skipped would have been
worse — a green run reporting that nothing was checked.

Nothing here needs a solver. A stamp reads git and the clock.
"""

from __future__ import annotations

import functools
import hashlib
import subprocess
from datetime import datetime, timezone
from pathlib import Path

SPIKE_DIR = Path(__file__).resolve().parent


def git_output(*arguments: str) -> str:
    """Run git and return its output with the trailing newline removed.

    RSTRIP, NEVER STRIP. `git status --porcelain` puts the status in the first
    two columns, so a file modified in the worktree reads " M path" with a
    LEADING space. Stripping the whole output eats that space on the first line
    only, and `uncommitted_paths` below then loses that path's first character.
    One entry wrong, quietly, and only ever the first one.
    """
    return subprocess.run(
        ["git", *arguments], capture_output=True, text=True, cwd=SPIKE_DIR
    ).stdout.rstrip()


def uncommitted_paths(porcelain: str) -> list[str]:
    """The paths in `git status --porcelain` output.

    Two status columns, a space, then the path. A rename reads
    "R  old -> new" and is left whole rather than split, because a stamp that
    silently reported half a rename would be worse than one that reports an
    arrow.
    """
    return sorted(
        line[3:] for line in porcelain.splitlines() if len(line) > 3
    )


@functools.lru_cache(maxsize=1)
def generated_from() -> dict:
    """Which build produced this receipt.

    The same shape `export_reference_curves.py` already writes, because a
    second shape for the same idea is a second thing to keep in step.

    IT IS CACHED, and that is the point rather than an optimisation. Every
    receipt in one run carries the SAME stamp, so a directory of receipts can
    be recognised as one set. A per-receipt timestamp would let a half-rebuilt
    directory look like a whole one.

    WHY THIS EXISTS. On 2026-08-31 the receipts Erin Burger graded had to be
    identified by argument — the value she marked, and a reading of the commit
    history showing the solver had not moved between her review and the copy —
    because a receipt said nothing at all about the build that made it.
    Principle P1 scores each coach's marks against the build that coach
    actually graded, so a receipt that cannot name its build makes P1 rest on
    somebody's memory.

    `uncommittedDiffSha256` is not in the reference-curves shape and is here on
    purpose. A commit with `treeWasClean: false` says "this commit, plus edits
    nobody wrote down", which is the exact situation that made that archive an
    argument. The digest makes two dirty builds comparable, and a dirty tree is
    what most of a working day produces. It covers tracked changes only, so an
    untracked new file still will not show; `uncommittedPaths` is there to make
    that visible rather than silent.
    """

    dirty = git_output("status", "--porcelain")
    stamp = {
        "commit": git_output("rev-parse", "HEAD") or None,
        "treeWasClean": not dirty,
        "utcTimestamp": datetime.now(timezone.utc).isoformat(timespec="seconds"),
    }
    if dirty:
        stamp["uncommittedDiffSha256"] = hashlib.sha256(
            git_output("diff", "HEAD").encode("utf-8")
        ).hexdigest()
        stamp["uncommittedPaths"] = uncommitted_paths(dirty)
    return stamp
