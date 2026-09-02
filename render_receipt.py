"""What a render run may claim about itself, with no Blender in it.

The renderer's console line is what a person and a script both read first. It
said PASS whenever the function reached its end, which is not the same as
having rendered or measured anything.

`--no-stills` without `--animate` skips the phase loop entirely. Run that way
over the eight drills it printed PASS eight times and wrote eight receipts
carrying zero phases. The receipts were honest; the word was not.

This is the same fault this lane reports in other instruments, in its own file:
an absence of measurement read as a clean result. It lives here so that a test
can call it, because the renderer imports `bpy` and its tests skip.
"""

from __future__ import annotations

import subprocess
from pathlib import Path

PASS = "PASS"
NOTHING_RENDERED = "NOTHING RENDERED"

UNKNOWN_COMMIT = "unknown"


def build_stamp(revision: str, status: str, *, available: bool = True) -> dict:
    """Which build produced this, and whether the tree was clean.

    THIS DID NOT EXIST UNTIL 2026-09-02, and its absence was the whole problem.
    All 63 receipts on disk carry `jobSha256` and nothing else that identifies
    a build: the hash of the JOB, never of the code that rendered it. So when a
    fix landed on 1 Sep and someone asked which pictures predated it, the only
    available answer was the file's modification time — which says when a file
    was written, not what wrote it.

    `treeWasClean` is the half that is easy to leave out and worth more. A
    receipt naming a commit, produced from a working tree with edits in it,
    names a build that never existed. It must say so rather than name the
    commit alone.

    A tree whose state could not be read is `unknown` and NEVER clean. Absence
    of a check is not a passing check, which is the rule this pipeline has now
    applied to a render outcome, a video provenance and a flexion axis.
    """
    if not available or not revision:
        return {"commit": UNKNOWN_COMMIT, "treeWasClean": None,
                "note": "git could not be read, so neither field is a claim"}
    return {"commit": revision.strip(), "treeWasClean": status.strip() == ""}


def git_build_stamp(root: Path) -> dict:
    """Read the build stamp from a working tree, or say it could not be read."""
    def run(*arguments: str) -> str | None:
        try:
            finished = subprocess.run(
                ["git", "-C", str(root), *arguments],
                capture_output=True, text=True, timeout=30,
            )
        except (OSError, subprocess.SubprocessError):
            return None
        return finished.stdout if finished.returncode == 0 else None

    revision = run("rev-parse", "HEAD")
    status = run("status", "--porcelain")
    if revision is None or status is None:
        return build_stamp("", "", available=False)
    return build_stamp(revision, status)


def render_outcome(phase_count: int, animation: object | None) -> str:
    """PASS only when the run actually produced something.

    A run that posed no phase and exported no animation has measured nothing.
    It has not failed either, and it must not say so, because a legitimate
    `--turntable`-only or `--animate`-only run is not a defect. It says what
    happened, which is that nothing was rendered.
    """
    if phase_count <= 0 and not animation:
        return NOTHING_RENDERED
    return PASS


# THE EXIT CODE IS 0 EITHER WAY, and a script must not read it as a result.
# NOTHING RENDERED is not a failure: a turntable-only or animation-only run is
# legitimate, and so is a phase filter that matches nothing in this job. The
# renderer exits non-zero only when it actually raises.
#
# So a caller that wants to know whether anything was measured must read the
# receipt's `phases`, or match this word on the console. Reading the exit code
# alone is how eight empty runs looked like eight clean ones.
