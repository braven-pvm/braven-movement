"""How far the solve has moved since the build a set of clips was exported from.

Reads `spikes/clip-baseline.json` at two commits and compares `engineDegrees`
for every `(phase, measure)` the two have in common. No solve, no assets, no
network: it is a file diff, and it runs in seconds.

WHY THIS FILE EXISTS RATHER THAN A COMMAND IN A DOCUMENT. The figures in
`docs/TACTICS_CONTRACT_QUESTIONS.md` were first produced by an inline script
that used two different median conventions in one run: the summary took the
lower of the two middle values and the per-clip rows took the upper. Both are
defensible, neither was stated, and the two cannot be compared with each other.
A reviewer reproduced the numbers and could not reproduce the medians.

So the convention is fixed here, in one place, and named:

    MEDIAN = the mean of the two middle values for an even count.

That is the ordinary median. It is not the convention the first draft used, so
the medians this prints are slightly different from the ones first published,
and the document says so.

Usage:

    python spikes/clip_gap_read.py <old-commit> <new-commit>
"""

from __future__ import annotations

import json
import subprocess
import sys

BASELINE = "spikes/clip-baseline.json"

# Above this, a reading has moved enough that somebody should look at it. The
# project's own threshold for a difference that means something is 5 degrees;
# 15 is used here because it is the figure the earlier reads reported and
# changing it would make the history incomparable.
NOTABLE_DEGREES = 15.0


def baseline_at(commit: str) -> dict:
    """The clip baseline as it stood at one commit."""
    raw = subprocess.run(
        ["git", "show", f"{commit}:{BASELINE}"],
        capture_output=True,
        check=True,
        text=True,
    ).stdout
    return json.loads(raw)


def median(values: list[float]) -> float:
    """The ordinary median: the mean of the two middle values for an even count.

    Stated explicitly because the first version of this read did not state it,
    used two conventions in one run, and could not be reproduced.
    """
    ordered = sorted(values)
    n = len(ordered)
    if not n:
        raise ValueError("no values to take a median of")
    middle = n // 2
    if n % 2:
        return ordered[middle]
    return (ordered[middle - 1] + ordered[middle]) / 2.0


def readings(clip: dict) -> dict[tuple[str, str], float]:
    return {(r["phase"], r["measure"]): r["engineDegrees"] for r in clip["rows"]}


def main(old_commit: str, new_commit: str) -> int:
    old = baseline_at(old_commit)
    new = baseline_at(new_commit)

    shared_clips = sorted(set(old) & set(new))
    every_move: list[float] = []

    print(f"{old_commit} -> {new_commit}, instrument {BASELINE}")
    print(f"convention: median is the mean of the two middle values\n")
    print(f"{'clip':38s} {'worst':>9s} {'median':>9s}  worst at")
    print("-" * 96)

    for name in shared_clips:
        a, b = readings(old[name]), readings(new[name])
        moves = sorted(
            ((abs(a[key] - b[key]), key) for key in set(a) & set(b)), reverse=True
        )
        if not moves:
            continue
        every_move += [m for m, _ in moves]
        worst, where = moves[0]
        print(
            f"{name:38s} {worst:9.2f} {median([m for m, _ in moves]):9.2f}"
            f"  {where[0]} / {where[1]}"
        )

    # The clips present in one build and not the other. Named rather than
    # silently skipped: a clip that appears is a new technique, and a clip that
    # disappears is a defect.
    only_old = sorted(set(old) - set(new))
    only_new = sorted(set(new) - set(old))
    if only_old:
        print(f"\nonly in {old_commit}: {', '.join(only_old)}")
    if only_new:
        print(f"\nonly in {new_commit}: {', '.join(only_new)}")

    print(
        f"\nacross {len(every_move)} shared readings on {len(shared_clips)} clips:"
        f"  median {median(every_move):.2f}  worst {max(every_move):.2f}"
        f"  over {NOTABLE_DEGREES:.0f} degrees: "
        f"{sum(1 for m in every_move if m > NOTABLE_DEGREES)}"
    )

    # A reading can move because the body moved or because the instrument
    # changed. These three say which, and they cost nothing to print.
    names_old = {r["measure"] for c in old.values() for r in c["rows"]}
    names_new = {r["measure"] for c in new.values() for r in c["rows"]}
    print(f"measure names only in {old_commit}: {sorted(names_old - names_new) or 'none'}")
    print(f"measure names only in {new_commit}: {sorted(names_new - names_old) or 'none'}")
    moved_travel = sum(
        1
        for n in shared_clips
        if abs(old[n]["rootTravelM"] - new[n]["rootTravelM"]) > 1e-9
    )
    print(f"clips whose root travel changed: {moved_travel} of {len(shared_clips)}")
    return 0


if __name__ == "__main__":
    if len(sys.argv) != 3:
        print(__doc__)
        raise SystemExit(2)
    raise SystemExit(main(sys.argv[1], sys.argv[2]))
