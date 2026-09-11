"""One build, two jobs: what a retiming changes, and which view shows it.

A before-and-after pair normally separates two BUILDS. This pair does not. Both
sides come from the same commit and the same solve parameters, and they differ
only in the job file the renderer consumed. So `before_after_sheet` cannot
label these columns, because it labels a column by the build in its receipt and
both receipts name the same build. The columns here are labelled by the JOB.

THIS PAIR IS VERIFIED BY NOTHING. A retiming is an authored key. The job file
is silent about authored keys: both jobs carry byte-identical
`solveParameters`, so no instrument in this repository can look at the two jobs
and say which one is the retimed one. The pictures show a difference. Nothing
here shows the difference is the intended retiming rather than any other edit
to the same file. That sentence belongs ON the sheet, not in a footnote.

Three quantities are measured, each from the files that ship beside the sheet:

    reach        shoulder-to-wrist distance over the arm's own length, from
                 the receipt's joint positions. 1.0 is a straight arm.
    across       how much of the wrist's travel lies ACROSS a view's lens,
                 in centimetres, from the job's own camera direction.
    changed      the share of pixels that moved, from `before_after_sheet`.

The middle one decides the view, and it is deliberately not a pixel count. A
camera sees the component of a movement perpendicular to where it points, and
that component is a length. It needs no sensor size, no resolution and no
pixel scale, so no scale error can reach it. Only the rings drawn on the
pictures need a pixel scale, and `--check` proves that scale against the ball.

The last one CANNOT decide the view: a retiming moves the whole figure at that
frame, so every view's silhouette moves and the changed share is about equal in
all three. It answers "did anything change", not "can a coach read the reach
change here". It is printed so that nobody uses it for the second question.

    python scripts/retiming_pair_sheet.py --check
    python scripts/retiming_pair_sheet.py --out out/retiming/retiming-pair.png
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import numpy
from PIL import Image, ImageDraw

from before_after_sheet import build_of, difference, load_font, verdict

REPO = Path(__file__).resolve().parents[1]
RENDERS = REPO / "out" / "retiming"
JOBS = REPO.parent / "amazing-chatelet-ed2e1c" / "spikes" / "poc-output" / "retiming-pair"

# Bounce first. The overseer asked for that order.
PAIRS = [
    ("netball_bounce_pass", "bounce_pass"),
    ("netball_chest_pass", "chest_pass"),
]
SIDES = ["shipped", "retimed"]
VIEWS = ["side", "quarter", "front"]
PHASE = "drive"


def receipt_of(drill: str, tag: str, side: str) -> dict:
    path = RENDERS / f"{tag}.{side}" / f"{drill}.render.json"
    return json.loads(path.read_text(encoding="utf-8"))


def job_of(tag: str, side: str) -> tuple[dict, str]:
    """The job and its hash, so the receipt's claim can be checked."""
    path = JOBS / f"netball_{tag}.{side}.job.json"
    raw = path.read_bytes()
    return json.loads(raw.decode("utf-8")), hashlib.sha256(raw).hexdigest()


def arm_lengths(arm: dict) -> tuple[float, float]:
    """Shoulder to wrist in metres, and the arm's own length in metres.

    Both are returned because the sheet needs both and neither should be
    recomputed from the other. The straight-line distance is what a coach
    sees. The arm's length is the divisor that removes the athlete's size.
    """
    shoulder = numpy.array(arm["shoulder"], dtype=float)
    elbow = numpy.array(arm["elbow"], dtype=float)
    wrist = numpy.array(arm["wrist"], dtype=float)
    whole = numpy.linalg.norm(elbow - shoulder) + numpy.linalg.norm(wrist - elbow)
    return float(numpy.linalg.norm(wrist - shoulder)), float(whole)


def reach(arm: dict) -> float:
    """Shoulder to wrist, over the arm's own length. 1.0 is a straight arm.

    The divisor is THIS arm's upper-arm plus forearm, measured on the same
    frame, so the number is a fraction of a real arm and not of a constant.
    A ratio removes the athlete's size from the comparison, which matters
    because the two jobs are the same athlete and any size change would be a
    defect rather than a retiming.

    THIS DEFINITION IS THE SHEET'S, and it is written down because an earlier
    reading of the same pair gave 0.586 -> 0.421 for the bounce pass where this
    gives 0.568 -> 0.406. Every row of that earlier reading is HIGHER than this
    one, and a uniform same-direction offset is a different origin, not
    rounding. The earlier definition was never committed and cannot be
    recovered, so it is withdrawn rather than reconciled.
    """
    straight, whole = arm_lengths(arm)
    return straight / whole


def to_pixels(point, view: dict) -> tuple[float, float]:
    """Where a world point lands in this view's picture, in pixels.

    THIS IS A REBUILD OF BLENDER'S CAMERA AND IT IS CHECKED, not trusted. The
    renderer never sets `sensor_fit`, so Blender's AUTO applies `sensorWidthMm`
    to the LARGER pixel dimension. These views are 1080 wide by 1350 high, so
    the sensor is the VERTICAL axis and the horizontal field is narrower. Fit
    the wrong axis and every horizontal reading is out by 1350/1080.

    `--check` proves the rebuild against the ball, whose radius is known and
    whose outline a scale error moves by tens of pixels. Measured on this pair:
    the correct fit predicts the ball's outer edge to within 0.6 to 1.7 px, and
    the width fit misses it by 22.1 to 45.4 px.
    """
    location = numpy.array(view["locationM"], dtype=float)
    target = numpy.array(view["targetM"], dtype=float)
    width, height = view["resolutionPx"]

    forward = target - location
    forward /= numpy.linalg.norm(forward)
    # `to_track_quat("-Z", "Y")` points -Z at the target and keeps world Z up.
    right = numpy.cross(forward, numpy.array([0.0, 0.0, 1.0]))
    right /= numpy.linalg.norm(right)
    up = numpy.cross(right, forward)

    offset = numpy.array(point, dtype=float) - location
    depth = float(offset @ forward)
    if depth <= 0:
        return float("nan"), float("nan")

    longest = max(width, height)
    scale = view["lensMm"] / view["sensorWidthMm"] * longest
    x = width / 2.0 + float(offset @ right) / depth * scale
    y = height / 2.0 - float(offset @ up) / depth * scale
    return x, y


def picture(tag: str, drill: str, side: str, view: str) -> Path:
    return RENDERS / f"{tag}.{side}" / f"{drill}.{PHASE}.{view}.png"


def measure() -> dict:
    """Every number on the sheet, with the checks that let it be printed."""
    report = {"pairs": [], "refusals": []}
    for drill, tag in PAIRS:
        row = {"drill": drill, "tag": tag, "sides": {}, "views": {}}
        builds, jobs = set(), {}
        for side in SIDES:
            receipt = receipt_of(drill, tag, side)
            job, digest = job_of(tag, side)
            if receipt["jobSha256"] != digest:
                report["refusals"].append(
                    f"{tag}.{side}: the receipt names job {receipt['jobSha256'][:16]} "
                    f"and the job on disk is {digest[:16]}. This picture is tied "
                    f"to no solve.")
            builds.add(build_of(RENDERS / f"{tag}.{side}", drill))
            jobs[side] = job
            phase = next(p for p in receipt["phases"] if p["name"] == PHASE)
            reading = {
                "jobSha256": digest,
                "solveParameters": receipt.get("solveParameters"),
                "wristL": phase["arms"]["l"]["wrist"],
                "wristR": phase["arms"]["r"]["wrist"],
                "frame": phase["frame"],
            }
            for hand in ("L", "R"):
                straight, whole = arm_lengths(phase["arms"][hand.lower()])
                reading[f"reach{hand}"] = straight / whole
                reading[f"straightCm{hand}"] = straight * 100.0
                reading[f"armCm{hand}"] = whole * 100.0
            row["sides"][side] = reading
        if len(builds) != 1:
            report["refusals"].append(
                f"{tag}: the two sides name different builds ({', '.join(sorted(builds))}). "
                f"A pair that changes build AND job cannot attribute its difference "
                f"to the retiming.")
        row["build"] = sorted(builds)[0]

        first, second = row["sides"]["shipped"], row["sides"]["retimed"]
        row["solveParametersIdentical"] = (
            first["solveParameters"] == second["solveParameters"])
        row["solveParameters"] = first["solveParameters"]

        # A RETIMING MOVES THE ATHLETE IN TIME AND MUST NOT RESIZE HER. If the
        # arm's own length differs between the two sides, the pictures differ
        # by a rig change as well as a timing change, and the reach ratio's
        # divisor is then two different divisors. The reach numbers would still
        # print, and they would be comparing two athletes.
        for hand in ("L", "R"):
            gap = abs(first[f"armCm{hand}"] - second[f"armCm{hand}"])
            if gap > 0.01:
                report["refusals"].append(
                    f"{tag}: the {hand} arm is {first[f'armCm{hand}']:.2f} cm shipped "
                    f"and {second[f'armCm{hand}']:.2f} cm retimed. A retiming must not "
                    f"resize the athlete, so this pair differs by more than its timing.")
        row["armCm"] = first["armCmL"]

        for hand in ("L", "R"):
            travel = (numpy.array(second[f"wrist{hand}"], dtype=float)
                      - numpy.array(first[f"wrist{hand}"], dtype=float))
            row[f"travelCm{hand}"] = float(numpy.linalg.norm(travel)) * 100.0

        for view in VIEWS:
            definition = jobs["shipped"]["views"][view]
            if definition != jobs["retimed"]["views"][view]:
                report["refusals"].append(
                    f"{tag}/{view}: the two jobs define this camera differently, so "
                    f"a difference between the pictures is partly a camera move.")
            screen = {}
            for hand in ("L", "R"):
                screen[hand] = {side: to_pixels(row["sides"][side][f"wrist{hand}"],
                                                definition) for side in SIDES}
            # ACROSS THE LENS, NOT ON SCREEN. A camera sees the part of a
            # movement that is perpendicular to where it points. That
            # perpendicular part is a length in centimetres and it needs no
            # sensor size, no resolution and no pixel scale, so it cannot carry
            # the scale error that the camera rebuild can make. The three
            # cameras sit 2.79 m to 3.14 m away with the same lens, so their
            # centimetres are comparable without correction.
            location = numpy.array(definition["locationM"], dtype=float)
            forward = numpy.array(definition["targetM"], dtype=float) - location
            forward /= numpy.linalg.norm(forward)
            across = {}
            for hand in ("L", "R"):
                travel = (numpy.array(second[f"wrist{hand}"], dtype=float)
                          - numpy.array(first[f"wrist{hand}"], dtype=float))
                seen = float(numpy.linalg.norm(travel - (travel @ forward) * forward))
                across[hand] = {
                    "acrossCm": seen * 100.0,
                    "share": seen / float(numpy.linalg.norm(travel)),
                }
            reading = difference(
                Image.open(picture(tag, drill, "shipped", view)),
                Image.open(picture(tag, drill, "retimed", view)))
            row["views"][view] = {
                "wrist": screen,
                "across": across,
                "acrossCm": max(across[h]["acrossCm"] for h in "LR"),
                "share": min(across[h]["share"] for h in "LR"),
                **reading,
                "verdict": verdict(reading),
            }
        report["pairs"].append(row)
        report.setdefault("jobsByTag", {})[tag] = jobs
    return report


EDGE_TOLERANCE_PX = 5.0
# The ball's centre must project at least this many of its own radii from her
# shoulders, or "the edge facing away from her" is not a direction. In the
# front view of the chest pass it projects 0.45 radii away, because she faces
# the camera and holds the ball at her chest. There is no unoccluded edge to
# find there, and a check that reported a number anyway would be reporting the
# nearest patch of her forearm.
CLEAR_OF_BODY = 2.0


def ball_edge_check(row: dict, view: str, jobs: dict) -> tuple[bool, str]:
    """Predict the ball's outer edge, then measure it. Agree, or refuse.

    THE FIRST VERSION OF THIS CHECK HAD NO POWER AND PASSED A WRONG CAMERA.
    It required each projected wrist to land in a pixel that changed. About
    50000 pixels change, in one blob around the arms, so a projection wrong by
    23 px landed in the blob and passed. Fitting the sensor to the wrong axis
    -- the exact error this rebuild can make -- survived it, and shifted every
    published figure by a fifth.

    The ball settles it, because a sphere of known radius at a known position
    has a predictable outline and a 25 percent scale error moves that outline
    by tens of pixels. The edge that is measured is the one FACING AWAY from
    the athlete, chosen by projecting the shoulder-midpoint-to-ball direction
    onto the picture. Her hands occlude the near edge and never the far one.

    Measured against predicted, on this pair: 1.3 px and 1.4 px with the sensor
    on the larger dimension, against 45.3 px and 21.1 px with it on the width.
    """
    definition = jobs["shipped"]["views"][view]
    receipt = receipt_of(row["drill"], row["tag"], "shipped")
    phase = next(p for p in receipt["phases"] if p["name"] == PHASE)
    radius = jobs["shipped"]["phases"][0]["ball"]["radiusM"]

    location = numpy.array(definition["locationM"], dtype=float)
    forward = numpy.array(definition["targetM"], dtype=float) - location
    forward /= numpy.linalg.norm(forward)
    centre = numpy.array(phase["ballCentreM"], dtype=float)
    depth = float((centre - location) @ forward)
    scale = (definition["lensMm"] / definition["sensorWidthMm"]
             * max(definition["resolutionPx"]))
    predicted_radius = radius / depth * scale
    middle = numpy.array(to_pixels(centre, definition))

    shoulders = numpy.array([
        to_pixels(phase["arms"][hand]["shoulder"], definition) for hand in "lr"
    ]).mean(axis=0)
    away = middle - shoulders
    clear = float(numpy.linalg.norm(away)) / predicted_radius
    if clear < CLEAR_OF_BODY:
        return None, (f"{row['tag']}/{view}: the ball projects {clear:.2f} ball-radii "
                      f"from her shoulders, so this view has no edge that is clear "
                      f"of her. Not checkable here.")
    away /= numpy.linalg.norm(away)

    frame = numpy.asarray(
        Image.open(picture(row["tag"], row["drill"], "shipped", view)).convert("RGB"),
        dtype=numpy.int16)
    # The ball is the only strongly red thing here. Skin reads about 16 apart
    # on red minus green, and the ball 70 to 150.
    red = (frame[:, :, 0] > 120) & (frame[:, :, 0] - frame[:, :, 1] > 50)
    lines, columns = numpy.nonzero(red)
    points = numpy.stack([columns, lines], axis=1).astype(float)
    # Only pixels near the predicted ball, so a red patch of skin further along
    # the same direction cannot stand in for the ball's edge.
    near = points[numpy.linalg.norm(points - middle, axis=1) < 2.0 * predicted_radius]
    if len(near) < 100:
        return False, (f"{row['tag']}/{view}: only {len(near)} ball pixels near the "
                       f"predicted centre. The ball is not where this camera says.")
    measured = float(((near - middle) @ away).max())
    gap = abs(measured - predicted_radius)
    detail = (f"{row['tag']}/{view}: outer edge predicted {predicted_radius:.1f} px "
              f"from centre, measured {measured:.1f}, gap {gap:.1f}")
    return gap <= EDGE_TOLERANCE_PX, detail


def check(report: dict, jobs_by_tag: dict) -> int:
    """Prove the camera rebuild before any ring drawn from it reaches a sheet.

    THE VIEW THE SHEET DRAWS MUST BE ONE OF THE VIEWS THAT VERIFIED. A pass
    somewhere else is not a pass here, and a check that let the drawn view be
    the unverifiable one would be a guard over the wrong thing.
    """
    print(f"CAMERA CHECK: the ball's outer edge, predicted against measured "
          f"(tolerance {EDGE_TOLERANCE_PX:.0f} px)")
    failed, verified = 0, set()
    for row in report["pairs"]:
        for view in VIEWS:
            passed, detail = ball_edge_check(row, view, jobs_by_tag[row["tag"]])
            print(f"   {'--  ' if passed is None else 'ok  ' if passed else 'FAIL'}"
                  f" {detail}")
            if passed is None:
                continue
            if passed:
                verified.add((row["tag"], view))
            else:
                failed += 1
    if failed:
        print(f"\n{failed} views failed. The camera rebuild is wrong, so the wrist "
              f"rings must not be drawn.")
        return 1
    missing = [tag for _, tag in PAIRS if (tag, SHOWN) not in verified]
    if missing:
        print(f"\nThe {SHOWN} view is what this sheet draws, and it did not verify "
              f"for: {', '.join(missing)}. A pass in another view does not carry.")
        return 1
    print(f"   the rebuild reproduces the renderer's camera, and the {SHOWN} view "
          f"verified for every pair the sheet draws.")
    return 0


def report_text(report: dict) -> list[str]:
    lines = []
    for row in report["pairs"]:
        drill = row["drill"].replace("netball_", "")
        first, second = row["sides"]["shipped"], row["sides"]["retimed"]
        lines.append(f"{drill}, phase {PHASE}, frame {first['frame']}, "
                     f"build {row['build']}")
        lines.append(f"   the arm's own length is {row['armCm']:.2f} cm on both "
                     f"sides, so the retiming did not resize her")
        for hand, name in (("L", "left"), ("R", "right")):
            before, after = first[f"reach{hand}"], second[f"reach{hand}"]
            lines.append(
                f"   reach, {name:<5} arm   {before:.3f} -> {after:.3f} of the arm "
                f"({after - before:+.3f}),   "
                f"{first[f'straightCm{hand}']:.1f} -> {second[f'straightCm{hand}']:.1f} cm "
                f"({second[f'straightCm{hand}'] - first[f'straightCm{hand}']:+.1f} cm)")
        lines.append(f"   the wrist travels {row['travelCmL']:.2f} cm (left) and "
                     f"{row['travelCmR']:.2f} cm (right) in the world")
        lines.append(f"   {'view':<10}{'across the lens':>18}{'visible':>10}"
                     f"{'pixels that changed':>22}")
        for view in VIEWS:
            reading = row["views"][view]
            lines.append(f"   {view:<10}{reading['acrossCm']:>15.2f} cm"
                         f"{reading['share']:>10.0%}{reading['changedShare']:>21.2%}")
        lines.append("")
    return lines


BACK = (24, 24, 27)
TITLE = (240, 240, 245)
BODY = (186, 186, 196)
BLUE = (150, 190, 240)
WARN = (255, 150, 90)
GOOD = (150, 200, 150)

# The one view the sheet shows. The table says why.
SHOWN = "side"
PICTURE_HEIGHT = 560
MARK = {"shipped": (120, 180, 255), "retimed": (255, 150, 90)}


def mark_wrists(panel: Image.Image, row: dict, side: str, view: dict):
    """Ring both jobs' wrist positions on one panel, and join them.

    THE PICTURES ALONE DO NOT SHOW THIS CHANGE. The wrist moves 49 px in a
    1080 px render, which is about 20 px once the panel is scaled to fit a
    sheet, and a reader scanning two crouched figures will not find it. So the
    panel carries the measurement it is evidence for: a filled ring at THIS
    job's wrist, a hollow ring at the other job's, and a line between them.

    These are the SAME projected points the `--check` pass proved land in
    changed pixels. The marks are drawn on the sheet's copy only. The stills
    in `out/retiming/` stay unmarked, because a render with drawing on it is
    no longer a render.
    """
    canvas = ImageDraw.Draw(panel)
    other = "retimed" if side == "shipped" else "shipped"
    scale = panel.width / view["resolutionPx"][0]
    for hand in ("L", "R"):
        here = [v * scale for v in to_pixels(row["sides"][side][f"wrist{hand}"], view)]
        there = [v * scale for v in to_pixels(row["sides"][other][f"wrist{hand}"], view)]
        canvas.line([tuple(here), tuple(there)], fill=(255, 255, 255), width=2)
        for point, colour, fill in ((there, MARK[other], None),
                                    (here, MARK[side], MARK[side])):
            box = [point[0] - 9, point[1] - 9, point[0] + 9, point[1] + 9]
            canvas.ellipse(box, outline=colour, fill=fill, width=3)
    return panel


def draw_sheet(report: dict, out: Path) -> Path:
    """The two pairs, the numbers, and the caveat, on one page.

    THE CAVEAT IS NOT A FOOTNOTE. It sits directly under the title, above the
    pictures, because a reader who takes only the pictures must still take it.
    """
    title, head, body, mono = (load_font(31), load_font(20),
                               load_font(17), load_font(16))
    width = 1914
    sheet = Image.new("RGB", (width, 2200), BACK)
    canvas = ImageDraw.Draw(sheet)
    pad = 28
    y = 22

    canvas.text((pad, y), "Retiming pair: one build, two jobs", font=title, fill=TITLE)
    y += 40
    build = report["pairs"][0]["build"]
    canvas.text((pad, y), f"build {build}   phase {PHASE}   frame "
                          f"{report['pairs'][0]['sides']['shipped']['frame']}   "
                          f"{SHOWN} view   1080x1350", font=head, fill=BLUE)
    y += 34

    canvas.text((pad, y), "THIS PAIR IS VERIFIED BY NOTHING.", font=head, fill=WARN)
    y += 26
    for line in [
        "A retiming is an authored key. The job file is silent about authored keys: both jobs carry the same",
        f"solveParameters ({report['pairs'][0]['solveParameters']}), so no instrument here can read the two jobs and say which one is retimed.",
        "These pictures show that something changed. Nothing shows the change is the intended retiming.",
    ]:
        canvas.text((pad, y), line, font=body, fill=WARN)
        y += 22
    y += 14

    # The pictures. Two pairs, the second pair set apart so no reader takes
    # column three for the "after" of column two.
    cell = round(1080 * PICTURE_HEIGHT / 1350)
    x = pad
    for row in report["pairs"]:
        _, job = job_of(row["tag"], "shipped")
        definition = json.loads(
            (JOBS / f"netball_{row['tag']}.shipped.job.json").read_text(
                encoding="utf-8"))["views"][SHOWN]
        for side in SIDES:
            path = picture(row["tag"], row["drill"], side, SHOWN)
            panel = Image.open(path).convert("RGB").resize(
                (cell, PICTURE_HEIGHT), Image.LANCZOS)
            sheet.paste(mark_wrists(panel, row, side, definition), (x, y))
            x += cell + 10
        x += 36
    y += PICTURE_HEIGHT + 8
    canvas.text((pad, y), "each panel rings BOTH wrist positions: filled is this "
                          "job, hollow is the other. The rings are the measured "
                          "points, not a drawing over the figure.",
                font=body, fill=BODY)
    y += 24

    x = pad
    for row in report["pairs"]:
        drill = row["drill"].replace("netball_", "")
        for side in SIDES:
            canvas.text((x, y), f"{drill}  {side}", font=body, fill=TITLE)
            canvas.text((x, y + 20), f"job {row['sides'][side]['jobSha256'][:16]}",
                        font=mono, fill=BODY)
            x += cell + 10
        x += 36
    y += 52

    # The reach, per drill.
    for row in report["pairs"]:
        drill = row["drill"].replace("netball_", "")
        first, second = row["sides"]["shipped"], row["sides"]["retimed"]
        canvas.text((pad, y), f"{drill}: what the retiming changed", font=head, fill=TITLE)
        y += 26
        canvas.text((pad, y), f"the arm's own length is {row['armCm']:.2f} cm on both "
                              f"sides, so the retiming did not resize her",
                    font=mono, fill=GOOD)
        y += 22
        for hand, name in (("L", "left"), ("R", "right")):
            before, after = first[f"reach{hand}"], second[f"reach{hand}"]
            canvas.text(
                (pad, y),
                f"reach, {name:<5} arm   {before:.3f} -> {after:.3f} of the arm "
                f"({after - before:+.3f})     "
                f"{first[f'straightCm{hand}']:.1f} -> {second[f'straightCm{hand}']:.1f} cm "
                f"({second[f'straightCm{hand}'] - first[f'straightCm{hand}']:+.1f} cm)",
                font=mono, fill=BODY)
            y += 22
        y += 16

    # The view table.
    canvas.text((pad, y), "Why the side view", font=head, fill=TITLE)
    y += 26
    canvas.text((pad, y), f"{'':<16}{'across the lens':>20}{'visible':>12}"
                          f"{'pixels that changed':>24}", font=mono, fill=BLUE)
    y += 22
    for row in report["pairs"]:
        drill = row["drill"].replace("netball_", "")
        canvas.text((pad, y), f"{drill}: the wrist travels {row['travelCmL']:.2f} cm "
                              f"(left) and {row['travelCmR']:.2f} cm (right)",
                    font=mono, fill=BODY)
        y += 22
        for view in VIEWS:
            reading = row["views"][view]
            colour = GOOD if view == SHOWN else BODY
            canvas.text((pad, y), f"{'   ' + view:<16}{reading['acrossCm']:>17.2f} cm"
                                  f"{reading['share']:>12.0%}"
                                  f"{reading['changedShare']:>24.2%}",
                        font=mono, fill=colour)
            y += 22
        y += 8

    for line in [
        "A camera sees the part of a movement that lies ACROSS its lens. The side view sees 92% to 100% of the wrist's",
        "travel. The front view sees 48% and 66% on the bounce pass and 25% on the chest pass, so it hides three quarters",
        "of the chest pass change. That is why this sheet is the side view. On the bounce pass the quarter view is a close",
        "second at 89% and 97%, so the quarter view would also serve. The front view would not.",
        "",
        "THE FRONT VIEW IS NOT BLANK, and nobody should expect it to be. It shows a real change, understated. A person who",
        "renders the front and reads a reach off it will read a number that is too small, not a number that is zero.",
        "",
        "The share of pixels that changed CANNOT pick the view, and it sits here so that nobody uses it to. A retiming moves",
        "the whole figure at that frame, so every silhouette moves and all six readings fall between 2.97% and 3.98%. That",
        "column answers 'did anything change'. Only the across-the-lens column answers 'can a coach read the reach here'.",
    ]:
        canvas.text((pad, y), line, font=body,
                    fill=WARN if line.startswith("THE FRONT") else BODY)
        y += 21
    y += 14

    canvas.text((pad, y), "How to re-measure every number above", font=head, fill=TITLE)
    y += 26
    for line in [
        "pixi run --frozen python -B ../scripts/retiming_pair_sheet.py --check     (run it from spikes/)",
        "The reach and the across-the-lens column come from the receipt's own joint positions and the job's own camera",
        "direction. Neither uses a pixel scale, so neither can carry a scale error. Only the rings drawn on the pictures",
        "use one, and --check proves that scale against the ball: predicted outer edge against measured, to within 5 px.",
    ]:
        canvas.text((pad, y), line, font=mono if line.startswith("pixi") else body,
                    fill=BLUE if line.startswith("pixi") else BODY)
        y += 21

    sheet = sheet.crop((0, 0, width, y + pad))
    out.parent.mkdir(parents=True, exist_ok=True)
    sheet.save(out)
    return out


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true",
                        help="prove the camera rebuild and print the numbers")
    parser.add_argument("--out", type=Path, help="write the sheet here")
    arguments = parser.parse_args(argv)

    report = measure()
    for refusal in report["refusals"]:
        print(f"REFUSED. {refusal}")
    if report["refusals"]:
        return 2
    code = check(report, report["jobsByTag"])
    print()
    for line in report_text(report):
        print(line)
    if code:
        # THE SHEET IS NOT DRAWN WHEN THE PROJECTION CHECK FAILS. The view
        # table is the reason this sheet exists, and a failed check means the
        # table's only column with power to choose a view is wrong.
        return code
    if arguments.out:
        written = draw_sheet(report, arguments.out)
        print(f"sheet: {written}")
        arguments.out.with_suffix(".json").write_text(
            json.dumps(report, indent=2), encoding="utf-8")
        print(f"numbers: {arguments.out.with_suffix('.json')}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
