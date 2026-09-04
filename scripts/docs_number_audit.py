"""Every number in the docs that was measured on an older build.

A number in a document is a reading from ONE build. When the build moves, the
number is either still true or it is stale, and nothing on the page says
which. This lists them so each lane can refresh its own.

It reports, per row: the document, the line, the numbers on that line, and the
build the surrounding section names. It does NOT edit the documents. It does
not decide whether a number is stale either, because that needs the same
quantity measured again, and only some of these quantities are in the render
receipts at all.

    python scripts/docs_number_audit.py
    python scripts/docs_number_audit.py --doc HAND_MIRROR_EVIDENCE.md
"""

from __future__ import annotations

import argparse
import re
from pathlib import Path

DOCS = Path(__file__).resolve().parents[1] / "docs"

BUILD = re.compile(r"\b[0-9a-f]{7}\b")
NUMBER = re.compile(r"(?<![\w.])-?\d+\.\d+(?![\w])")
HEADING = re.compile(r"^#{1,6}\s+(.*)")

# A bare `1.0` inside a version string or a schema number is not a measurement.
NOISE = re.compile(r"schemaVersion|version|python|blender|\bv\d")

# NOR IS A NUMBER INSIDE A FILE NAME. `elbow-curve-0.1.json` was reported as
# an unattributed measurement of 0.1 and would have been sent to a lane to
# refresh. A number in an inline code span carrying a path separator or a file
# extension is an identifier, so the span is removed before the numbers are
# read. The rule is narrow on purpose: a plain number in backticks is still a
# measurement and is still reported.
CODE_PATH = re.compile(r"`[^`]*[/\][^`]*`|`[^`]*\.[A-Za-z]{2,5}`")

# THE ONLY ROWS WORTH LISTING ARE THE ONES A RECEIPT CAN ANSWER. Extracting
# every number in the docs yields 1104 lines, which is not an instrument. These
# are the quantities the render receipts actually carry, so a row matching one
# of them can be re-measured on the current build. Everything else is prose,
# a threshold, a count, or an engine number this lane cannot re-measure.
REFRESHABLE = {
    "elbow": "arms.*.elbow, an angle from three joint positions",
    "wrist bend": "hands.*.wristBendDegrees",
    "wristbend": "hands.*.wristBendDegrees",
    "forearm roll": "hands.*.forearmRollDegrees",
    "palm normal": "hands.*.palmNormalErrorDegrees",
    "clearance": "hands.*.surfaceClearanceMm",
    "vertices inside": "bodyClearanceMm.verticesInside",
    "nearest": "bodyClearanceMm.nearestMm",
    "ball centre": "ballCentreM",
    "ball center": "ballCentreM",
    "shoulder": "arms.*.shoulder",
    "fan": "index tip to pinky tip, computed from the rig",
}

# Below the hips nothing may be presented as a graded value, so those rows are
# marked rather than dropped. A reader who does not know that would refresh one
# and publish it.
LOWER_BODY = re.compile(
    r"knee|ankle|foot|feet|hip|thigh|calf|stance|shin|toe", re.IGNORECASE)


ARCHIVE = Path("F:/Repositories/braven-movement/.assets/archives/"
               "coach-figures-aa3f244")


def elbow_degrees(arm: dict) -> float:
    """The angle at the elbow, from the three joint positions."""
    import math

    shoulder, elbow, wrist = arm["shoulder"], arm["elbow"], arm["wrist"]
    upper = [a - b for a, b in zip(shoulder, elbow)]
    lower = [a - b for a, b in zip(wrist, elbow)]
    dot = sum(a * b for a, b in zip(upper, lower))
    sizes = (sum(v * v for v in upper) ** 0.5) * (sum(v * v for v in lower) ** 0.5)
    return math.degrees(math.acos(max(-1.0, min(1.0, dot / sizes))))


def current_build() -> None:
    """The same quantities on the archived build, for the list to compare to.

    This reads the ARCHIVED receipts rather than `out/`, because `out/` is not
    tracked and a restart has emptied a scratch directory here before.
    """
    import json

    receipts = sorted(ARCHIVE.glob("*.render.json"))
    if not receipts:
        print(f"NO RECEIPTS at {ARCHIVE}. Nothing can be compared.")
        return
    stamps = set()
    print(f"{'drill / phase':<38}{'elbow L':>9}{'elbow R':>9}{'bend L':>8}"
          f"{'bend R':>8}{'roll L':>8}{'roll R':>8}{'palm L':>8}{'palm R':>8}"
          f"{'nearest':>9}{'inside':>7}")
    for path in receipts:
        receipt = json.loads(path.read_text(encoding="utf-8"))
        stamp = receipt.get("generatedFrom")
        stamps.add(json.dumps(stamp, sort_keys=True) if stamp else "UNSTAMPED")
        drill = receipt["movementId"].replace("netball_", "")
        for phase in receipt["phases"]:
            arms, hands = phase["arms"], phase["hands"]
            body = phase["bodyClearanceMm"]
            print(f"{drill + '/' + phase['name']:<38}"
                  f"{elbow_degrees(arms['l']):>9.2f}"
                  f"{elbow_degrees(arms['r']):>9.2f}"
                  f"{hands['l']['wristBendDegrees']:>8.2f}"
                  f"{hands['r']['wristBendDegrees']:>8.2f}"
                  f"{hands['l']['forearmRollDegrees']:>8.2f}"
                  f"{hands['r']['forearmRollDegrees']:>8.2f}"
                  f"{hands['l']['palmNormalErrorDegrees']:>8.2f}"
                  f"{hands['r']['palmNormalErrorDegrees']:>8.2f}"
                  f"{body['nearestMm']:>9.2f}{body['verticesInside']:>7}")
    print()
    print(f"{len(receipts)} receipts, {len(stamps)} distinct build stamp(s).")
    if len(stamps) > 1:
        print("MIXED STAMPS. These rows are not one build and must not be "
              "read as one.")


def rows_for(path: Path):
    heading = ""
    build = ""
    for index, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        matched = HEADING.match(line)
        if matched:
            heading = matched.group(1).strip()
        found = BUILD.findall(line)
        if found:
            build = found[0]
        if NOISE.search(line):
            continue
        numbers = NUMBER.findall(CODE_PATH.sub("`identifier`", line))
        if not numbers:
            continue
        lowered = line.lower()
        answers = sorted({field for term, field in REFRESHABLE.items()
                          if term in lowered})
        yield {
            "answers": answers,
            "line": index,
            "heading": heading,
            "build": build,
            "numbers": numbers,
            "text": line.strip(),
            "lowerBody": bool(LOWER_BODY.search(f"{heading} {line}")),
        }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--doc", help="one document, by file name")
    parser.add_argument("--with-build-only", action="store_true",
                        help="only rows whose section names a build")
    parser.add_argument("--refreshable", action="store_true",
                        help="only rows a render receipt can re-measure")
    parser.add_argument("--current", action="store_true",
                        help="the same quantities on the archived build")
    arguments = parser.parse_args()

    if arguments.current:
        current_build()
        return

    paths = sorted(DOCS.glob("*.md"))
    if arguments.doc:
        paths = [p for p in paths if p.name == arguments.doc]

    total = attributed = lower = 0
    for path in paths:
        rows = list(rows_for(path))
        if arguments.with_build_only:
            rows = [row for row in rows if row["build"]]
        if arguments.refreshable:
            rows = [row for row in rows if row["answers"]]
        if not rows:
            continue
        print(f"\n=== {path.name}  ({len(rows)} numeric lines)")
        for row in rows:
            total += 1
            attributed += 1 if row["build"] else 0
            lower += 1 if row["lowerBody"] else 0
            build = row["build"] or "NO BUILD NAMED"
            mark = "  [below the hips, not a graded value]" if row["lowerBody"] else ""
            print(f"  {path.name}:{row['line']:<5} {build:<16}"
                  f"{', '.join(row['numbers'][:6])}{mark}")
            print(f"        under: {row['heading'][:70]}")
            if row["answers"]:
                print(f"        receipt: {'; '.join(row['answers'])}")
    print()
    print(f"{total} numeric lines, {attributed} in a section that names a "
          f"build, {total - attributed} with no build named.")
    print(f"{lower} touch the lower body and must not be refreshed into a "
          f"graded value.")
    print()
    print("THE RECEIPT FIELD NAMES A QUANTITY, NOT A POSE. `DESIGN.md:254` quotes the")
    print("elbows 27.3 cm apart, and that is the REFERENCE CATCH measured against")
    print("photographs, not a drill phase. The movement receipts hold the same quantity")
    print("from a different instrument, and refreshing one with the other would replace a")
    print("reference-pose number with a drill-phase number and call it an update.")
    print()
    print("A row with NO BUILD NAMED is the worse case. The number cannot be "
          "checked against")
    print("anything, because nothing records what it was measured on.")


if __name__ == "__main__":
    main()
