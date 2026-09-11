"""What render artefacts exist, and which of them a coach in a room can use.

`docs/COACH_REVIEW_SPEC_INTERFACE.md` section 4 gives three artefact forms to
this lane, and neither of the other two lanes may promise them:

    still_render(drill, moment, build)
    player(dataset)
    render_pair(parameter, value_a, value_b)

`docs/COACH_MORNING_RUNNING_ORDER.md` recommends holding the morning date until
items 2, 4, 17 and 18 have renders. This reads the disk and answers whether each
one exists, so the recommendation rests on a measurement rather than on memory.

THREE RULES IT APPLIES, and they are the reason the answer is not a file count.

1. EXISTS MEANS A PERSON IN A ROOM CAN LOOK AT IT. A dataset a page can play is
   not a still a coach can mark. A player draws a skeleton from numbers; a still
   render is a picture of the athlete the manual prints.
2. AN ARTEFACT MUST NAME ITS BUILD. A coach's mark is scored against the build
   she graded. An unstamped render cannot be scored at all, so it is reported as
   unusable however good it looks.
3. AN ARTEFACT MUST BE TRACEABLE TO A SOLVE. A receipt records `jobSha256`. When
   the job that produced it no longer hashes to that, the picture cannot be tied
   to any solve, and it is unusable for the same reason.

    python scripts/render_artefact_inventory.py
"""

from __future__ import annotations

import hashlib
import json
import subprocess
from pathlib import Path

HERE = Path(__file__).resolve()
REPO = HERE.parents[1]

# The commit that fixed the anti-mirrored right hand, which item 17 asks about.
HAND_FIX = "fde5d5a"


def archives_root() -> Path:
    for base in [HERE] + list(HERE.parents):
        candidate = base / ".assets" / "archives"
        if candidate.is_dir():
            return candidate
    raise SystemExit("no .assets/archives found from this file")


def worktrees_root() -> Path | None:
    for base in [HERE] + list(HERE.parents):
        candidate = base / ".claude" / "worktrees"
        if candidate.is_dir():
            return candidate
    return None


def read_receipts(directory: Path) -> list[dict]:
    out = []
    for path in sorted(directory.rglob("*.render.json")):
        try:
            out.append({"path": path,
                        "receipt": json.loads(path.read_text(encoding="utf-8"))})
        except (json.JSONDecodeError, OSError):
            out.append({"path": path, "receipt": None})
    return out


def describe(directory: Path) -> dict:
    """Everything that decides whether this directory is usable in a room."""
    entries = read_receipts(directory)
    stamps, animated, unstamped, phaseless = set(), 0, 0, 0
    for entry in entries:
        receipt = entry["receipt"]
        if receipt is None:
            continue
        stamp = receipt.get("generatedFrom")
        if stamp is None:
            unstamped += 1
        else:
            stamps.add(json.dumps(stamp, sort_keys=True))
        if receipt.get("animation"):
            animated += 1
        if not receipt.get("phases"):
            phaseless += 1
    return {
        "receipts": len(entries),
        "stills": len(list(directory.rglob("*.png"))),
        "movies": len(list(directory.rglob("*.mp4"))),
        "stamps": sorted(stamps),
        "unstamped": unstamped,
        "animated": animated,
        "phaseless": phaseless,
    }


def job_still_matches(entry: dict, jobs: Path) -> bool | None:
    """Does the job that made this receipt still hash to what it recorded?"""
    receipt = entry["receipt"]
    if not receipt or "jobSha256" not in receipt:
        return None
    job = jobs / f"{receipt['movementId']}.job.json"
    if not job.is_file():
        return None
    return hashlib.sha256(job.read_bytes()).hexdigest() == receipt["jobSha256"]


def contains_commit(ancestor: str, descendant: str) -> bool | None:
    """Is `ancestor` in the history of `descendant`? None when git cannot say."""
    try:
        done = subprocess.run(
            ["git", "merge-base", "--is-ancestor", ancestor, descendant],
            cwd=REPO, capture_output=True, text=True)
    except OSError:
        return None
    if done.returncode not in (0, 1):
        return None
    return done.returncode == 0


def records_a_parameter(entries: list[dict]) -> bool:
    """Does any receipt record the parameter value that produced the picture?

    `render_pair(parameter, value_a, value_b)` cannot be verified without it: the
    receipt could not say which value drew which picture.
    """
    def walk(node, path=""):
        if isinstance(node, dict):
            for key, value in node.items():
                yield from walk(value, f"{path}.{key}")
        elif isinstance(node, list) and node:
            yield from walk(node[0], f"{path}[]")
        else:
            yield path

    wanted = ("pole", "param", "dial", "variant")
    for entry in entries:
        if not entry["receipt"]:
            continue
        for key in walk(entry["receipt"]):
            if any(word in key.lower() for word in wanted):
                return True
    return False


def main() -> None:
    root = archives_root()
    print("=== ARCHIVED RENDER SETS ===")
    print(f"{'directory':<38}{'receipts':>9}{'stills':>8}{'movies':>8}"
          f"{'stamps':>8}{'unstamped':>11}")
    archived = {}
    for directory in sorted(p for p in root.iterdir() if p.is_dir()):
        found = describe(directory)
        archived[directory.name] = found
        print(f"{directory.name:<38}{found['receipts']:>9}{found['stills']:>8}"
              f"{found['movies']:>8}{len(found['stamps']):>8}"
              f"{found['unstamped']:>11}")

    print()
    print("=== CAN A ROOM USE THEM? ===")
    for name, found in archived.items():
        reasons = []
        if found["unstamped"]:
            reasons.append(f"{found['unstamped']} receipts carry NO build stamp")
        if len(found["stamps"]) > 1:
            reasons.append(f"{len(found['stamps'])} different build stamps")
        if not found["stills"] and not found["movies"]:
            reasons.append("no picture of any kind")
        verdict = "USABLE" if not reasons else "NOT USABLE"
        print(f"  {name:<38}{verdict}")
        for reason in reasons:
            print(f"      {reason}")

    print()
    print("=== ITEM 17: IS THE HAND FIX IN THE USABLE SET? ===")
    for name, found in archived.items():
        if found["unstamped"] or len(found["stamps"]) != 1:
            continue
        stamp = json.loads(found["stamps"][0])
        commit = (stamp or {}).get("commit", "")[:7]
        answer = contains_commit(HAND_FIX, commit) if commit else None
        says = {True: "YES", False: "NO", None: "git cannot say"}[answer]
        print(f"  {name:<38}build {commit}   carries {HAND_FIX}: {says}")

    print()
    print("=== ITEM 2: CAN A RENDER PAIR BE VERIFIED AT ALL? ===")
    for name in archived:
        entries = read_receipts(root / name)
        found = records_a_parameter(entries)
        print(f"  {name:<38}records a parameter value: {'YES' if found else 'NO'}")
    print("  Without one, a receipt cannot say WHICH value drew WHICH picture,")
    print("  so `render_pair(parameter, value_a, value_b)` is unverifiable today.")

    print()
    print("=== ITEM 4: DOES ANY ARCHIVED SET CARRY A CLIP? ===")
    for name, found in archived.items():
        print(f"  {name:<38}receipts with an animation: {found['animated']}")

    print()
    print("=== UNARCHIVED RENDERS IN OTHER WORKTREES ===")
    trees = worktrees_root()
    if trees is None:
        print("  no .claude/worktrees found from this file")
        return
    for tree in sorted(p for p in trees.iterdir() if p.is_dir()):
        out = tree / "out"
        if not out.is_dir():
            continue
        movies = sorted(out.rglob("*.mp4"))
        if not movies:
            continue
        print(f"  {tree.name}: {len(movies)} movies, "
              f"{len(list(out.rglob('*.png')))} stills")
        jobs = tree / "spikes" / "poc-output"
        for entry in read_receipts(out):
            receipt = entry["receipt"]
            if not receipt or not receipt.get("animation"):
                continue
            faults = []
            stamp = receipt.get("generatedFrom")
            if stamp is None:
                faults.append("UNSTAMPED")
            elif stamp.get("treeWasClean") is False:
                # A STAMP IS NOT THE SAME AS A BUILD THAT REPRODUCES. This one
                # names a commit AND a set of uncommitted files, so checking the
                # commit out does not rebuild the athlete that was drawn.
                paths = stamp.get("uncommittedPaths") or []
                faults.append(f"DIRTY TREE, {len(paths)} uncommitted file(s), "
                              "so the build does not reproduce")
            if not receipt.get("phases"):
                faults.append("no phases")
            matches = job_still_matches(entry, jobs)
            if matches is False:
                faults.append("its job no longer hashes to what it recorded")
            elif matches is None:
                faults.append("its job is gone")
            print(f"      {receipt['movementId']:<40}"
                  f"{', '.join(faults) if faults else 'traceable'}")
    print()
    print("An unstamped clip cannot be scored against a build, and a clip whose")
    print("job has moved cannot be tied to a solve. Both are unusable in a room,")
    print("however good the picture is.")


if __name__ == "__main__":
    main()
