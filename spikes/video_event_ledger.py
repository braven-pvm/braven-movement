"""What happens, and when, in each view of a filmed set — and whether one
constant offset maps one view's events onto the other's.

WHY THIS EXISTS. Two offsets have now been published for session 0.1 and both
were wrong. The second, -0.7295 s, was graded "shared-event" on the frame the
ball first meets her hands, read in both views, and it still paired TWO
DIFFERENT CATCHES: the side's was of a ball she had released herself 1.36 s
earlier, the front's of a ball arriving into hands empty for 2.5 s. Under it,
the side's release maps onto front frames of her standing with her arms at her
sides.

BOTH FAILURES HAVE ONE SHAPE. A single moment that looks alike in two views is
not evidence, because the movement is periodic: she catches and tosses about
every 1.866 seconds (the mean of nine gaps between ten catches), so a
The check that passed the second offset — "both views show a catch 15 s later" —
matched a POSTURE inside that period.

SO THE UNIT OF EVIDENCE IS NOT A MOMENT, IT IS A SEQUENCE. This module records
every catch, release and clap in a view as an ordered ledger, and asks whether
ONE constant offset maps one ledger onto the other. A single pair can be a
coincidence; a whole sequence at one offset cannot, and a sequence that fits at
no offset says the two recordings are not a synchronous pair.

HOW THE EVENTS ARE READ. By a person, from contact sheets built here. There is
no ball detector, and the only instrument that has ever answered "is this a
catch" in this repository is someone looking at frames. Frames are selected BY
INDEX from the container's own timestamp list and never by seeking: a seek on
the variable-rate side file does not land where the arithmetic says.
"""

from __future__ import annotations

import json
import subprocess
from pathlib import Path

SPIKE_DIR = Path(__file__).resolve().parent
ANNOTATION_DIR = SPIKE_DIR / "video-annotations"
SAMPLES = Path("F:/Repositories/braven-movement/.assets/video-samples/session-1.0")
SCHEMA_VERSION = "video-event-ledger-1"

# What a ledger row may be. A CLOSED VOCABULARY, so that a fit compares like
# with like: a catch may only ever be matched to a catch.
KINDS = ("catch", "release", "clap")

# How close a mapped event must land to its partner. ONE FRAME. Two independent
# frame calls can each be a frame out, so this is the floor rather than a
# comfortable margin, and a fit at exactly this tolerance deserves the same
# suspicion as a fit at none.
TOLERANCE_SECONDS = 1.0 / 30.0

# How far apart two anchors must be before they count as independent evidence.
# CHOSEN at ten seconds because her toss cycle is 1.866 s — the mean gap
# between the ten catches of side 0.1 between 8.26 and 25.06 s: anchors closer
# than several cycles can both be satisfied by an offset that is a whole number
# of cycles wrong, which is exactly how -0.7295 survived its own check.
ANCHOR_GAP_SECONDS = 10.0

# AND THE ANCHOR RULE IS NOT ENOUGH ON ITS OWN. Measured by
# `anchor_rule_null_rate` below, on the committed ledger of session 0.1, 500
# trials at seed 0: a randomly generated side ledger of the same size satisfies
# "two matched events ten seconds apart" **43.2 per cent** of the time at
# one-frame tolerance and **83.2 per cent** at a quarter second. With ten events
# in each view and a search over twelve seconds of offsets, coincidence is the
# normal case rather than the exception.
#
# THOSE TWO FIGURES HAVE NOW BEEN WRONG TWICE, IN TWO DIFFERENT PAIRS, and both
# times because no committed code produced them. The first pair was 48 and 88,
# from a scratch script that no longer exists. The second was 43 and 85, which
# named `null_matches` and `_best_match` as the source and said it "can be
# re-run" - but neither function applies the anchor rule, so nothing in the
# tree computed the quantity at all. `anchor_rule_null_rate` does, and
# `test_video_event_ledger.py` runs it and pins both numbers. Commit the
# instrument with its numbers.
#
# So a fit must also BEAT ITS OWN NULL. The side ledger is randomised inside the
# span its real events occupy, the best match count is taken each time, and the
# real count has to exceed that distribution's 99th percentile. This is the
# instrument the clap finding used, and it is here for the same reason: a rule
# whose chance rate nobody has measured is not a rule.
NULL_TRIALS = 500
NULL_SEED = 0
NULL_PERCENTILE = 99

# The offsets searched when asking whether ANY constant offset fits.
SEARCH_SECONDS = 6.0
SEARCH_STEP_SECONDS = 1.0 / 120.0


def frame_times(view: str, set_id: str) -> list[float]:
    """Every frame's true container timestamp, in order.

    NEVER A SEEK. The side files are variable-rate, and a seek on them does not
    land where the arithmetic says; asking for 16.93 s on set 0.1's side file
    with a keyframe-snapping reader lands at 9.996, which is where a different
    repetition lives. Frames are addressed by INDEX into this list.
    """
    path = SAMPLES / f"{view} {set_id}.mp4"
    if not path.exists():
        raise FileNotFoundError(path)
    out = subprocess.run(
        ["ffprobe", "-v", "error", "-select_streams", "v:0",
         "-show_entries", "frame=pts_time", "-of", "csv=p=0", str(path)],
        capture_output=True, text=True, check=True).stdout
    return [float(v.strip().rstrip(",")) for v in out.split()
            if v.strip().rstrip(",")]


def contact_sheet(view: str, set_id: str, first: int, last: int, step: int,
                  out_dir: Path, columns: int = 8, width: int = 150) -> Path:
    """A grid of frames for a person to read, labelled by index and true time.

    `width` matters more than it looks. The front camera of set 0.2 stands far
    enough back that the athlete is small, and at 150 px a ball in her hands
    cannot be told from empty hands. A ledger read from tiles too small to read
    is worse than no ledger, so the tile size is a parameter and the sheet that
    produced a reading is named beside it.
    """
    from PIL import Image, ImageDraw

    times = frame_times(view, set_id)
    wanted = list(range(first, min(last, len(times) - 1) + 1, step))
    out_dir.mkdir(parents=True, exist_ok=True)
    raw = out_dir / "raw"
    raw.mkdir(exist_ok=True)
    picks = "+".join(f"eq(n\\,{i})" for i in wanted)
    subprocess.run(
        ["ffmpeg", "-v", "error", "-y", "-i", str(SAMPLES / f"{view} {set_id}.mp4"),
         "-vf", f"select='{picks}',scale={width}:-1", "-vsync", "0",
         str(raw / "f-%03d.png")], check=True)
    files = sorted(raw.glob("f-*.png"))
    if not files:
        raise RuntimeError(f"no frames selected for {view} {set_id}")
    tile = Image.open(files[0])
    rows = (len(files) + columns - 1) // columns
    sheet = Image.new("RGB", (columns * tile.width,
                              rows * (tile.height + 14)), "white")
    pen = ImageDraw.Draw(sheet)
    for n, path in enumerate(files):
        x = (n % columns) * tile.width
        y = (n // columns) * (tile.height + 14)
        sheet.paste(Image.open(path), (x, y + 14))
        index = wanted[n] if n < len(wanted) else -1
        pen.text((x + 2, y + 2), f"{index} {times[index]:.3f}", fill="black")
    where = out_dir / f"{view.replace(' ', '')}-{first}-{last}.png"
    sheet.save(where)
    return where


def load(set_id: str) -> dict | None:
    path = ANNOTATION_DIR / f"event-ledger-{set_id}.json"
    if not path.exists():
        return None
    return json.loads(path.read_text(encoding="utf-8"))


def events(ledger: dict, view: str, kind: str | None = None) -> list[dict]:
    rows = [r for r in ledger["views"][view]["events"]
            if kind is None or r["kind"] == kind]
    return sorted(rows, key=lambda r: r["seconds"])


def _best_match(front: list[dict], side: list[dict], tolerance: float):
    """The offset explaining the most of `front`, and what it explains."""
    best = None
    offset = -SEARCH_SECONDS
    while offset <= SEARCH_SECONDS + 1e-9:
        matched = []
        for row in front:
            partners = [s for s in side
                        if s["kind"] == row["kind"]
                        and abs((row["seconds"] + offset) - s["seconds"]) <= tolerance]
            if partners:
                nearest = min(partners, key=lambda s: abs(
                    (row["seconds"] + offset) - s["seconds"]))
                matched.append({"kind": row["kind"],
                                "frontSeconds": row["seconds"],
                                "sideSeconds": nearest["seconds"],
                                "errorSeconds": round(
                                    (row["seconds"] + offset) - nearest["seconds"], 4)})
        if matched:
            span = matched[-1]["frontSeconds"] - matched[0]["frontSeconds"]
            # THE THIRD TERM PICKS THE L1 MEDIAN OF THE PLATEAU, not its
            # midpoint. Every offset within a tolerance of the true one matches
            # the same events, so the count alone leaves a plateau, and taking
            # its first member biased the answer to the low edge by up to a
            # whole tolerance. Minimising the SUM OF ABSOLUTE ERRORS is a
            # median rather than a mean: on errors of 0.80 / 0.82 / 0.82 it
            # returns 0.8167 where the midpoint is 0.8100. That is the right
            # choice for a reading with outliers and it is NOT the centre; the
            # name matters because a reader comparing two of these needs to
            # know which statistic they are comparing.
            error = sum(abs(m["errorSeconds"]) for m in matched)
            score = (len(matched), span, -error)
            if best is None or score > best[0]:
                best = (score, round(offset, 4), matched)
        offset += SEARCH_STEP_SECONDS
    return best


def null_matches(front: list[dict], side: list[dict], tolerance: float,
                 trials: int = NULL_TRIALS, seed: int = NULL_SEED) -> list[int]:
    """How many events a RANDOM side ledger of the same shape would explain."""
    import random
    rng = random.Random(seed)
    lo = min(r["seconds"] for r in side)
    hi = max(r["seconds"] for r in side)
    counts = []
    for _ in range(trials):
        fake = sorted(({"kind": r["kind"], "seconds": rng.uniform(lo, hi)}
                       for r in side), key=lambda r: r["seconds"])
        best = _best_match(front, fake, tolerance)
        counts.append(len(best[2]) if best else 0)
    return counts


def pairing_drift(front: list[dict], side: list[dict],
                  shift: int) -> dict | None:
    """Pair front catch i with side catch i+shift, and fit a rate to the gaps.

    WHY THIS IS HERE. Pairing the two catch sequences in order produces
    offsets that walk steadily, and a steady walk looks exactly like a CLOCK
    RATE difference: one camera running fast. The numbers are large, +12.6,
    +16.0 and +13.7 per cent depending on which shift is used.

    THE CLOCKS DIFFER BY 0.04 PER CENT. A 12 to 16 per cent walk is three
    orders of magnitude too big to be a rate, and what it actually measures is
    the COUNT MISMATCH: the front has 8 catches and the side has 10 over
    roughly the same span, so pairing them in order stretches one sequence
    against the other and the residual walks by construction. It is an artefact
    of the pairing, not a property of the cameras.

    The three rates were quoted in a review and in no committed code, so nobody
    could re-derive them. They are here now, and the test pins all three.
    """
    if len(front) < 2:
        return None
    pairs = [(front[i]["seconds"], side[i + shift]["seconds"])
             for i in range(len(front)) if 0 <= i + shift < len(side)]
    if len(pairs) < 2:
        return None
    offsets = [b - a for a, b in pairs]
    xs = [a for a, _ in pairs]
    mean_x = sum(xs) / len(xs)
    mean_y = sum(offsets) / len(offsets)
    bottom = sum((x - mean_x) ** 2 for x in xs)
    if bottom == 0:
        return None
    slope = sum((x - mean_x) * (y - mean_y)
                for x, y in zip(xs, offsets)) / bottom
    return {"shift": shift, "pairs": len(pairs),
            "firstOffsetSeconds": round(offsets[0], 4),
            "lastOffsetSeconds": round(offsets[-1], 4),
            "ratePerCent": round(slope * 100.0, 1)}


def anchor_rule_null_rate(front: list[dict], side: list[dict],
                          tolerance: float = TOLERANCE_SECONDS,
                          anchor_gap: float = ANCHOR_GAP_SECONDS,
                          trials: int = NULL_TRIALS,
                          seed: int = NULL_SEED) -> float:
    """How often a RANDOM side ledger satisfies the ANCHOR RULE ALONE.

    THIS FUNCTION EXISTS BECAUSE THE NUMBERS IT PRODUCES WERE QUOTED WITHOUT
    IT, TWICE, AND WERE WRONG BOTH TIMES. A docstring said 48 and 88, from a
    scratch script that no longer exists. A comment then said 43 and 85 and
    named `null_matches` and `_best_match` as the source, which was not true:
    neither of those applies the anchor rule, so no committed code computed the
    quantity. Run here, the figures are **43.2** and **83.2** per cent. A number
    nobody else can regenerate is not a measurement, and naming two functions
    that do not compute it is worse than naming none.

    It is the anchor rule ALONE, deliberately: the rule as it was BEFORE it had
    to beat its own null. That is the thing whose weakness is being reported.
    """
    counts_ok = 0
    import random
    rng = random.Random(seed)
    lo = min(r["seconds"] for r in side)
    hi = max(r["seconds"] for r in side)
    for _ in range(trials):
        fake = sorted(({"kind": r["kind"], "seconds": rng.uniform(lo, hi)}
                       for r in side), key=lambda r: r["seconds"])
        best = _best_match(front, fake, tolerance)
        if not best:
            continue
        matched = best[2]
        if len(matched) < 2:
            continue
        span = (max(m["frontSeconds"] for m in matched)
                - min(m["frontSeconds"] for m in matched))
        if span >= anchor_gap:
            counts_ok += 1
    return counts_ok / trials


def fits_one_offset(front: list[dict], side: list[dict],
                    tolerance: float = TOLERANCE_SECONDS,
                    anchor_gap: float = ANCHOR_GAP_SECONDS,
                    trials: int = NULL_TRIALS,
                    resolution: float | None = None) -> dict:
    """Does ONE constant offset map the front's events onto the side's?

    Returns the best offset and how much of the front's ledger it explains, and
    whether that is enough to write a sync: TWO anchors of the same kind, at
    least `anchor_gap` apart, each landing within `tolerance`.

    THE TWO-ANCHOR RULE IS THE WHOLE POINT. One anchor is always satisfiable —
    pick any front event and any side event and an offset exists that maps one
    to the other. It is the SECOND anchor, far away, that a wrong offset cannot
    survive, because a periodic movement only repeats on its own period.
    """
    if not front or not side:
        return {"fits": False, "why": "one of the ledgers has no events",
                "bestOffsetSeconds": None, "anchors": []}
    best = _best_match(front, side, tolerance)
    if best is None:
        return {"fits": False,
                "why": (f"no offset within +/-{SEARCH_SECONDS} s maps any front "
                        "event onto a side event of the same kind"),
                "bestOffsetSeconds": None, "anchors": []}
    (count, span, _), offset, matched = best
    null = sorted(null_matches(front, side, tolerance, trials))
    bar = null[min(len(null) - 1, (NULL_PERCENTILE * len(null)) // 100)]
    anchored = len(matched) >= 2 and span >= anchor_gap
    beats_chance = count > bar
    fits = anchored and beats_chance
    reason = []
    if not anchored:
        reason.append(f"a sync needs two anchors at least {anchor_gap} s apart "
                      f"and the best offset spans {span:.3f} s")
    if not beats_chance:
        reason.append(f"a RANDOM side ledger of the same shape explains {bar} "
                      f"events at the {NULL_PERCENTILE}th percentile, so {count} "
                      "is not better than chance")
    # THE ERRORS CANNOT BE FINER THAN THE LEDGER THEY CAME FROM. A ledger read
    # on an 8-frame grid quantises every event to 0.267 s, so a match reported
    # with a 7 ms error is reporting the lattice and not the recording: a
    # genuine +0.94 s offset read on such a grid comes back as +1.0583 with
    # sub-7 ms errors and no hint that it is 0.12 s out. `resolutionSeconds`
    # says what the reading can support, and it travels with the answer.
    return {
        "fits": fits,
        "bestOffsetSeconds": offset,
        "matchedEvents": count,
        "spanSeconds": round(span, 3),
        "nullPercentileMatches": bar,
        "nullTrials": trials,
        "resolutionSeconds": resolution,
        "errorsAreNoFinerThan": resolution,
        "anchors": matched,
        "why": (f"{count} events match at {offset:+.4f} s across {span:.3f} s, "
                f"against a chance ceiling of {bar}"
                if fits else "; ".join(reason)),
    }


def judge(ledger: dict | None) -> tuple[bool | None, str]:
    """Three values, and silence is not consent."""
    if ledger is None:
        return None, "no event ledger exists for this set"
    if ledger.get("schemaVersion") != SCHEMA_VERSION:
        return None, (f"the ledger's schema is {ledger.get('schemaVersion')!r}, "
                      f"not {SCHEMA_VERSION!r}")
    found = fits_one_offset(events(ledger, "front"), events(ledger, "side"))
    return (True, found["why"]) if found["fits"] else (False, found["why"])
