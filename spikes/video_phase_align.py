"""Put a filmed repetition onto the engine's phase axis, and say how well.

The findings report did this once by hand: it read a catch at 9.13 s off a
contact sheet, took the pull-in window 9.2 to 9.6 s, and laid those numbers
beside `netball_two_hand_snatch_pull_in`. This is that, as one command, with
the parts that were judgement made into readings.

    pixi run python video_phase_align.py --set 0.1

TWO INSTRUMENTS, AND THE SECOND IS NOT AN IMPROVEMENT ON THE FIRST
------------------------------------------------------------------

**Anchored** is the primary. It maps three known instants onto three known
phases — the repetition's start onto 0, the pull-in's onset onto the
reference's own `contactPhase`, the pull-in's peak onto 1 — and interpolates
linearly between them. It cannot invent a warp, and every one of its inputs is
a number somebody can point at in a frame.

**Warped** is dynamic time warping on the two curves, after both are
z-normalised. It uses no landmark at all, so it fails where the anchor fails
least: it is blind to a mislocated catch and hostage to the shape.

They disagree in PHASE, and that disagreement is the reading. It is not
averaged, and neither is corrected toward the other.

FOUR FAILURE MODES, EACH MEASURED RATHER THAN WARNED ABOUT
----------------------------------------------------------

1. **The reference is flat for its first half.**
   `netball_two_hand_snatch_pull_in` holds 88.87 degrees EXACTLY from phase
   0.000 to 0.3814, and stays within five degrees of that until phase 0.4845.
   Both numbers are measured on the build named in the result; a first draft of
   this docstring said "0.371" and "37 percent", read off a printout that
   sampled every sixth frame. Warping onto a flat stretch costs nothing, so any
   amount of video can park there at no penalty. `featurelessSharePhase` is in
   every result, and where it is large the warp over that stretch is not an
   alignment, it is a place to put things. This is the same fact the movement
   lane records as "the snatch's react phase is 0.1 degrees from ready, so its
   checkpoint cannot fail", met from the other side.

2. **A warp will fit anything to anything.** So every result carries the
   warp distance to EVERY drill in the library, not only the intended one. If
   the intended drill is not clearly the closest, "it aligned" is not evidence
   and the file says which drill actually won.

3. **The video's anchor is not the engine's contact, and it is not the eye's
   catch either.** The engine's `contactPhase` is the frame its possession
   model says the ball is held. The video's anchor is the ONSET of the pull-in
   rise. On the findings report's own catch cycle the report placed the catch
   at 9.13 s by eye on a contact sheet and this places the onset at 8.767 s —
   363 ms apart, eleven frames. Three definitions of one word, and the anchored
   alignment inherits the difference. `catchProxyNote` carries it into the
   file. Eleven frames is not a rounding error and no downstream number should
   be quoted to a precision that pretends otherwise.

   The elbow MINIMUM was tried first and abandoned, because on that same cycle
   the smoothed curve has no turning point at all in the half second before the
   pull-in: the dip the eye sees is 4 to 11 degrees deep and this curve moves a
   90th percentile 11.3 degrees between neighbouring frames. **The catch
   instant is not recoverable as a turning point from this elbow curve.**

4. **Z-normalising throws the level away.** The alignment therefore says
   nothing whatever about the DEGREES, only about the shape — which is exactly
   the distinction the findings report ended on. The level difference is
   reported separately, as `medianLevelGapDegrees`, and is never folded into
   the match.

WHAT SEGMENTATION CAN AND CANNOT DO ON SESSION 1.0
--------------------------------------------------

Repetitions are found from the elbow curve itself. Measured on session 1.0,
all twelve pull-ins pass, and NOT ONE IS REFUSED — so on this material the
refusal path is exercised only by the tests, and a reader should treat it as
guarded rather than proven. What varies is not whether a repetition is found
but how well it aligns: the two instruments' phase disagreement runs from 0.034
to 0.265 across the twelve, and the level gap between video and engine runs
from -47.0 to +11.5 degrees. A single repetition's numbers are therefore not
the clip's numbers.

An earlier draft of this section claimed segmentation failed for the late
repetitions, reasoning from a wrist-height measurement: the athlete returns her
hands to her sides for the first few catches, giving a swing of about 280
pixels, and from about 11.8 s she stays in rhythm with her hands up and the
swing falls to about 60 pixels against a 13-pixel noise floor. That measurement
stands and the conclusion drawn from it did not: the ELBOW keeps a 25-degree
pull-in throughout, so segmentation off the elbow survives what segmentation
off the wrist would not have. The claim was corrected by re-running rather than
by rewording.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import numpy as np

SPIKE_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(SPIKE_DIR))

from build_stamp import generated_from  # noqa: E402

OUTPUT = SPIKE_DIR / "poc-output" / "video"
SCHEMA_VERSION = "video-phase-alignment-1"

NEAREST_DRILL = "netball_two_hand_snatch_pull_in"
MEASURE = "leftElbowFlexionDegrees"

# A centred moving average over this many samples. NINE, and it is a measured
# compromise rather than a round number: on session 1.0 the raw elbow curve
# moves a median 2.5 degrees between neighbouring frames and up to 38.5, which
# is larger than some whole repetitions. Nine cuts the 90th percentile step
# from 11.3 degrees to 6.7 and costs 4 samples of lag at each end. Fifteen cuts
# it to 4.3 and starts flattening the pull-in itself.
SMOOTHING_SAMPLES = 9

# A pull-in peak must stand this far above the surrounding curve to count. The
# reference's own pull-in rises about 65 degrees from its dip, so 25 keeps a
# half-hearted repetition and rejects noise.
PEAK_PROMINENCE_DEGREES = 25.0
# Two peaks closer than this are one repetition seen twice. The filmed cycle
# runs one to two seconds.
PEAK_SEPARATION_SECONDS = 0.7
# A repetition whose peak stands less than this many times the local
# frame-to-frame noise is refused rather than aligned.
MINIMUM_PEAK_TO_NOISE = 3.0

# How far back from a pull-in peak its onset is looked for.
#
# ONE SECOND, AND THE FIRST VALUE WAS HALF THAT AND WRONG. Half a second came
# from the findings report's single hand-read pair — a catch at 9.13 s and a
# pull-in at 9.37 s, 240 ms apart. Measured across all twelve pull-ins in
# session 1.0, the rise itself lasts 0.267 to 0.733 s, so a half-second window
# opened INSIDE four of the twelve rises and the flatness guard below correctly
# refused them: from inside a rise there is no onset to find. One number read
# by hand from one repetition set a threshold that then rejected a third of the
# clip, including the very repetition it came from.
#
# The window is additionally clamped at the previous pull-in, because the
# shortest gap between peaks here is 0.767 s and a lookback that crosses into
# the previous repetition would find its toss.
CATCH_LOOKBACK_SECONDS = 1.0

# How far up the pull-in the onset is taken. Fifteen percent of a rise that is
# 65 degrees and more is about 10 degrees, which clears this curve's 90th
# percentile frame-to-frame step of 11.3 degrees only just — so the onset is
# located to about one frame and no better, and nothing downstream should claim
# otherwise.
PULL_IN_ONSET_RISE_SHARE = 0.15

# Before the onset the curve must be climbing at most this fraction as steeply
# as after it. Without this an arm that simply rises through the whole window
# still returns an "onset" — the threshold crossing of a straight ramp, which is
# an arbitrary sample and not an event. A THIRD, because the reference's own
# lead is flat and its pull-in is steep, so anything close to a ramp is not the
# shape this looks for.
ONSET_FLATNESS_RATIO = 0.33

# A repetition may not begin more than this far before its catch. The filmed
# cycle runs one to two seconds, so a lead longer than a whole cycle is not
# part of this repetition — it is the previous one plus a pause. Without the
# cap a missed peak makes one "repetition" 3.5 seconds long, of which three
# seconds is the athlete standing still, and stretching that onto phase 0 to 1
# says she spent most of the movement reaching.
MAX_LEAD_SECONDS = 2.0

# How far a value may sit from the curve's first value and still count as "not
# yet moving". It is `multi_camera_fit.MEANINGFUL_DEGREES`, the clinical
# threshold for a difference worth showing a coach. The SAME threshold measures
# the reference's featureless share and the video window's still share, so the
# two are one quantity read on two curves and may be compared.
FEATURELESS_TOLERANCE_DEGREES = 5.0

# The warp may not stray further than this fraction of the curve from the
# diagonal. Without a band, dynamic time warping is free to spend the whole
# video in one reference frame and the whole reference in one video frame.
WARP_BAND_SHARE = 0.25


class AlignmentError(RuntimeError):
    """Something a caller must decide about rather than work around."""


def smooth(values: np.ndarray, window: int = SMOOTHING_SAMPLES) -> np.ndarray:
    """A centred moving average that does not invent data at the ends.

    `np.convolve(..., "same")` divides the edges by the full window and drags
    the first and last few samples toward zero, which on an angle curve puts a
    false dip exactly where a repetition may start. This divides by the number
    of samples actually averaged.
    """
    values = np.asarray(values, dtype=np.float64)
    if window <= 1 or len(values) < window:
        return values.copy()
    kernel = np.ones(window)
    total = np.convolve(values, kernel, mode="same")
    count = np.convolve(np.ones_like(values), kernel, mode="same")
    return total / count


def step_noise_degrees(values: np.ndarray) -> float:
    """The median frame-to-frame movement: this curve's own noise floor."""
    if len(values) < 2:
        return 0.0
    return float(np.median(np.abs(np.diff(np.asarray(values, dtype=np.float64)))))


def featureless_share(values: list[float] | np.ndarray,
                      tolerance: float = FEATURELESS_TOLERANCE_DEGREES) -> float:
    """The leading share of a reference curve that has not started moving.

    A LEADING RUN, not a count of flat samples anywhere. A curve that pauses in
    the middle is still informative on both sides of the pause; a curve that
    has not moved by phase 0.37 offers nothing to align against for the first
    third of itself, and that is the fault this measures.
    """
    curve = np.asarray([v for v in values if v is not None], dtype=np.float64)
    if len(curve) < 2:
        return 1.0
    moved = np.abs(curve - curve[0]) > tolerance
    if not moved.any():
        return 1.0
    return float(int(np.argmax(moved)) / (len(curve) - 1))


def pull_in_onset(
    eased: np.ndarray, peak: int, lookback: int,
    rise_share: float = PULL_IN_ONSET_RISE_SHARE,
) -> int | None:
    """Where the pull-in starts: the anchor, and the third definition tried.

    TWO EARLIER DEFINITIONS FAILED, AND BOTH FAILURES ARE THE REASON THIS ONE
    IS RIGHT.

    First, `argmin` over a fixed half second. It returned the window's own left
    edge on the sample's first real catch, which is not a minimum but a
    truncation, and it placed the catch 263 ms earlier than the findings report
    placed it by hand.

    Second, the last TURNING POINT before the peak. That refused the report's
    own catch cycle outright: on the smoothed curve there is no turning point
    in the half second before the 9.367 s pull-in, because the dip the report
    saw by eye on a contact sheet is 4 to 11 degrees deep and this curve moves
    a median 2.5 degrees and a 90th percentile 11.3 degrees between neighbouring
    frames. **The catch instant is not recoverable as a turning point from this
    elbow curve.** That is a fact about the footage, not a threshold to lower.

    So the anchor is the ONSET OF THE RISE — the last sample before the curve
    has climbed `rise_share` of the way from its local floor to the pull-in
    peak. The rise is 65 degrees and more, an order of magnitude above the
    noise, so the onset survives what the dip does not. It also matches the
    engine: the reference's own curve leaves rest at phase 0.4845 and its
    contact is at 0.5361, so the engine's contact sits at the start of its own
    pull-in rather than at any minimum.

    None is a refusal rather than a fallback, and it fires on the case that
    matters: an arm already climbing when the window opens. A STRAIGHT RAMP
    CROSSES ANY THRESHOLD SOMEWHERE, so a crossing on its own is a sample and
    not an event. The shape must be flat before the onset and steep after it,
    and `ONSET_FLATNESS_RATIO` is that check. Without it a pure ramp returned a
    threshold crossing and called it a catch — measured, not imagined: the
    first version of this function did exactly that on
    `np.linspace(100, 140, 30)`.
    """
    peak, lookback = int(peak), int(lookback)
    low = max(0, peak - lookback)
    if peak - low < 4:
        return None
    floor = float(eased[low:peak].min())
    threshold = floor + rise_share * (float(eased[peak]) - floor)
    below = np.flatnonzero(eased[low:peak] <= threshold)
    if not len(below):
        return None
    onset = int(low + below[-1])
    if onset - low < 2 or peak - onset < 2:
        return None
    # SIGNED, NOT ABSOLUTE, and the difference is the whole guard. A real catch
    # has the arm EXTENDING before the pull-in, so the curve is falling into the
    # onset — an absolute change called that steep and refused every honest
    # repetition in the test set. What must not happen is the curve already
    # RISING when the window opens, which is the ramp with no event in it.
    before = (float(eased[onset]) - float(eased[low])) / (onset - low)
    after = (float(eased[peak]) - float(eased[onset])) / (peak - onset)
    if after <= 0.0 or before > ONSET_FLATNESS_RATIO * after:
        return None
    return onset


def find_repetitions(
    times: np.ndarray, values: np.ndarray,
    prominence: float = PEAK_PROMINENCE_DEGREES,
    separation_seconds: float = PEAK_SEPARATION_SECONDS,
) -> tuple[list[dict], list[dict]]:
    """Split a curve into repetitions, and refuse the ones that are not clean.

    Returns the accepted candidates and the refusals. A refusal carries its
    reading and its reason, because a repetition silently dropped is a sample
    size nobody can audit.

    THE WINDOW IS THE REFERENCE'S OWN SHAPE. The engine's movement runs ready,
    react, contact, pull_in, and its `pull_in` phase is at 1.0 — the curve ENDS
    at its highest flexion. So a filmed repetition ends at a pull-in peak and
    begins at the previous one, with the catch between them. A first version
    ended the window at the peak's right base instead, which put the start and
    the catch on the same sample and raised "the three instants are not in
    order" on the very first repetition.
    """
    from scipy.signal import find_peaks  # noqa: PLC0415 — scipy is heavy

    times = np.asarray(times, dtype=np.float64)
    values = np.asarray(values, dtype=np.float64)
    if len(times) != len(values):
        raise AlignmentError("times and values are different lengths")
    eased = smooth(values)
    noise = step_noise_degrees(eased)
    step = float(np.median(np.diff(times))) if len(times) > 1 else 1.0
    distance = max(1, int(round(separation_seconds / max(step, 1e-6))))
    lookback = max(2, int(round(CATCH_LOOKBACK_SECONDS / max(step, 1e-6))))

    peaks, properties = find_peaks(eased, prominence=prominence, distance=distance)
    lead = max(2, int(round(MAX_LEAD_SECONDS / max(step, 1e-6))))
    accepted, refused = [], []
    for order, peak in enumerate(peaks):
        peak = int(peak)
        previous = int(peaks[order - 1]) if order else int(properties["left_bases"][order])
        catch = pull_in_onset(eased, peak, min(lookback, peak - previous))
        # THE LEAD IS CAPPED, and the cap is measured against the catch rather
        # than the peak, because it is the reach this bounds.
        start = previous if catch is None else max(previous, catch - lead)
        candidate = {
            "startSeconds": round(float(times[start]), 4),
            "catchSeconds": None if catch is None else round(float(times[catch]), 4),
            "peakSeconds": round(float(times[peak]), 4),
            "endSeconds": round(float(times[peak]), 4),
            "samples": int(peak - start + 1),
            "leadSeconds": (
                None if catch is None else round(float(times[catch] - times[start]), 4)),
            "prominenceDegrees": round(float(properties["prominences"][order]), 3),
            "stepNoiseDegrees": round(noise, 3),
            "peakToNoise": round(float(properties["prominences"][order]) / max(noise, 1e-6), 2),
        }
        if catch is None:
            candidate["reason"] = (
                f"the curve never sits below the onset threshold in the "
                f"{CATCH_LOOKBACK_SECONDS} s before the pull-in, so this "
                "pull-in has no start inside the window and there is nothing "
                "to anchor to"
            )
            refused.append(candidate)
            continue
        if peak - start < 5:
            candidate["reason"] = (
                f"the repetition spans {peak - start + 1} samples, under the "
                "five a curve needs to have a shape at all")
            refused.append(candidate)
            continue
        if not (start < catch < peak):
            candidate["reason"] = (
                "the start, the catch and the pull-in are not three distinct "
                "instants, so there is no reach to align")
            refused.append(candidate)
            continue
        if candidate["peakToNoise"] < MINIMUM_PEAK_TO_NOISE:
            candidate["reason"] = (
                f"the pull-in stands only {candidate['peakToNoise']:.1f} times "
                f"the curve's own frame-to-frame noise, under the bar of "
                f"{MINIMUM_PEAK_TO_NOISE}"
            )
            refused.append(candidate)
            continue
        candidate["indices"] = (start, catch, peak, peak)
        accepted.append(candidate)
    return accepted, refused


def anchored_phase(
    times: np.ndarray, start: float, catch: float, end: float, contact_phase: float
) -> np.ndarray:
    """Phase for each sample, from three instants mapped onto three phases.

    Piecewise linear and strictly increasing: start onto 0, catch onto the
    reference's own contact phase, end onto 1. Two segments, each with its own
    rate, which is what lets a slow reach and a fast pull-in both land where
    they belong without any warp being fitted.
    """
    if not (start < catch < end):
        raise AlignmentError(
            f"the three instants are not in order: start {start}, catch "
            f"{catch}, end {end}")
    if not 0.0 < contact_phase < 1.0:
        raise AlignmentError(f"contact phase {contact_phase} is not inside 0 to 1")
    times = np.asarray(times, dtype=np.float64)
    before = (times - start) / (catch - start) * contact_phase
    after = contact_phase + (times - catch) / (end - catch) * (1.0 - contact_phase)
    return np.clip(np.where(times <= catch, before, after), 0.0, 1.0)


def z_normalise(values: np.ndarray) -> np.ndarray:
    """Shape without level. A flat curve returns zeros rather than dividing."""
    values = np.asarray(values, dtype=np.float64)
    spread = float(values.std())
    if spread < 1e-9:
        return np.zeros_like(values)
    return (values - values.mean()) / spread


def warped_phase(
    video: np.ndarray, reference: np.ndarray, reference_phase: np.ndarray,
    band_share: float = WARP_BAND_SHARE,
) -> tuple[np.ndarray, float]:
    """Dynamic time warping, banded and monotone, on z-normalised curves.

    Returns a phase per video sample and the mean cost along the path. The cost
    is in units of normalised curve, so it may be compared between drills and
    may NOT be read as degrees.

    THE BAND IS NOT A TUNING KNOB. Unbounded warping can map the whole video
    onto one reference sample, which costs almost nothing and means nothing.
    The band forbids the path from straying more than a quarter of the curve
    from the diagonal, so a match has to keep roughly the right order of
    events to be cheap.
    """
    first = z_normalise(video)
    second = z_normalise(reference)
    rows, columns = len(first), len(second)
    if rows < 2 or columns < 2:
        raise AlignmentError("a warp needs at least two samples in each curve")
    band = max(2, int(round(band_share * max(rows, columns))))

    cost = np.full((rows + 1, columns + 1), np.inf)
    cost[0, 0] = 0.0
    for row in range(1, rows + 1):
        centre = (row - 1) * columns / rows
        low = max(1, int(centre - band) + 1)
        high = min(columns, int(centre + band) + 1)
        for column in range(low, high + 1):
            gap = (first[row - 1] - second[column - 1]) ** 2
            cost[row, column] = gap + min(
                cost[row - 1, column], cost[row, column - 1], cost[row - 1, column - 1])
    if not np.isfinite(cost[rows, columns]):
        raise AlignmentError(
            "no warp path fits inside the band; the two curves are too "
            "different in length for this band share")

    # Walk the path back, and take for each video sample the MEDIAN reference
    # index it touched. A video sample can map onto several reference samples,
    # and the median is the one that does not lurch on a single tie.
    touched: dict[int, list[int]] = {}
    path: list[tuple[int, int, float]] = []
    row, column, steps = rows, columns, 0
    while row > 0 and column > 0:
        touched.setdefault(row - 1, []).append(column - 1)
        path.append((row - 1, column - 1,
                     float((first[row - 1] - second[column - 1]) ** 2)))
        options = (
            (cost[row - 1, column - 1], row - 1, column - 1),
            (cost[row - 1, column], row - 1, column),
            (cost[row, column - 1], row, column - 1),
        )
        _, row, column = min(options, key=lambda option: option[0])
        steps += 1
    phase = np.array([
        float(reference_phase[int(np.median(touched.get(n, [0])))]) for n in range(rows)
    ])
    return phase, float(cost[rows, columns] / max(steps, 1)), path


def informative_distance(
    path: list[tuple[int, int, float]], reference: np.ndarray,
    tolerance: float = FEATURELESS_TOLERANCE_DEGREES,
) -> float | None:
    """The warp cost counted ONLY where the reference has left rest.

    WHY IT EXISTS, AND THE CLAIM THAT DID NOT SURVIVE ITS OWN TEST.

    The suspicion was that a drill which does nothing for most of its length is
    cheap to match, so the whole-curve ranking is partly a ranking of how little
    each drill does. `double_foot_landing` is the most featureless of the eight
    at 58 percent and it won five of the twelve repetitions, which is what
    raised it.

    Measured across 96 pairings the correlation between featureless share and
    whole-curve distance is Spearman -0.510 at p below 0.0001, AND THAT P VALUE
    IS WORTHLESS. The 96 points are eight drills repeated over twelve
    repetitions, and the featureless share varies only across the eight, so the
    points are not independent. At the level where the property actually varies
    — eight drills, one point each — it is Spearman -0.643 at **p = 0.086** on
    the whole curve and -0.476 at p = 0.233 on this informative score. So the
    bias is SUGGESTED AND NOT ESTABLISHED, and an earlier version of this
    docstring published the inflated figure.

    Scoring only the informative stretch moves the asked-for drill from first
    place on 5 of 12 repetitions to first on 9 of 12. **That is not evidence
    that this score is the better one.** The findings report is explicit that
    the filmed drill is none of the eight, so there is no right answer here to
    be closer to, and a score that ranks the drill somebody expected higher is
    exactly what a biased score would also do.

    Both numbers therefore travel in every ranking and NEITHER is called
    correct. The ranking is evidence about the method, not about the athlete.

    This counts the same path's cost over the reference samples that are more
    than `tolerance` from the reference's own starting value.

    Returns None when the reference never leaves rest, which is a refusal to
    produce a number rather than a zero.
    """
    curve = np.asarray(reference, dtype=np.float64)
    if len(curve) < 2:
        return None
    moving = np.abs(curve - curve[0]) > tolerance
    if not moving.any():
        return None
    costs = [cost for _, column, cost in path if moving[column]]
    return float(np.mean(costs)) if costs else None


def rank_against_library(
    video: np.ndarray, reference: dict, measure: str = MEASURE,
) -> list[dict]:
    """The warp distance to every drill, best first.

    THIS IS THE GUARD ON THE WHOLE METHOD. A warp fits anything to anything, so
    a distance to one drill is not evidence about that drill. A distance to all
    eight, with the intended one's rank, is.
    """
    found = []
    for name, drill in reference["movements"].items():
        curve = [v for v in drill["curves"].get(measure, []) if v is not None]
        if len(curve) < 2:
            continue
        phase = np.linspace(0.0, 1.0, len(curve))
        try:
            _, distance, path = warped_phase(video, np.asarray(curve), phase)
        except AlignmentError:
            continue
        informative = informative_distance(path, np.asarray(curve))
        found.append({
            "movement": name,
            "warpDistance": round(distance, 5),
            "informativeWarpDistance": (
                None if informative is None else round(informative, 5)),
            "featurelessSharePhase": round(featureless_share(curve), 4),
        })
    # SORTED ON THE INFORMATIVE DISTANCE, because the whole-curve distance is
    # measurably biased toward drills that do nothing. The whole-curve number
    # travels beside it so the bias stays visible rather than being corrected
    # away silently.
    return sorted(
        found,
        key=lambda row: (
            row["warpDistance"] if row["informativeWarpDistance"] is None
            else row["informativeWarpDistance"]))


def align_repetition(
    times: np.ndarray, values: np.ndarray, candidate: dict,
    reference: dict, movement: str, measure: str = MEASURE,
) -> dict:
    """One repetition, by both instruments, with their disagreement."""
    drill = reference["movements"][movement]
    curve = np.asarray(
        [v for v in drill["curves"][measure] if v is not None], dtype=np.float64)
    reference_phase = np.asarray(drill["phase"][:len(curve)], dtype=np.float64)
    contact_phase = drill["landmarks"]["contactPhase"]
    if contact_phase is None:
        raise AlignmentError(f"{movement} has no contact phase to anchor to")

    left, _, _, right = candidate["indices"]
    window_times = np.asarray(times[left:right + 1], dtype=np.float64)
    window_values = smooth(np.asarray(values, dtype=np.float64))[left:right + 1]

    anchored = anchored_phase(
        window_times, candidate["startSeconds"], candidate["catchSeconds"],
        candidate["endSeconds"], contact_phase)
    warped, distance, _ = warped_phase(window_values, curve, reference_phase)
    gap = np.abs(anchored - warped)

    # The level, kept out of the match and reported on its own. Both curves are
    # sampled onto a common phase grid first, because comparing them sample for
    # sample would compare two different tempos.
    grid = np.linspace(0.0, 1.0, 50)
    video_on_grid = np.interp(grid, anchored, window_values)
    engine_on_grid = np.interp(grid, reference_phase, curve)
    level = float(np.median(video_on_grid - engine_on_grid))

    # The findings report's own three columns, computed rather than read off a
    # contact sheet. "Before" is the phase the engine reference is still at
    # rest; "pulling in" is the highest flexion after contact on each curve.
    before = max(0.0, contact_phase - 0.25)
    after = grid >= contact_phase
    hand = {
        "note": (
            "The three columns the findings report filled in by hand, on the "
            "phase axis both curves now share. 'Before' is a quarter of a "
            "phase ahead of contact; 'pulling in' is the highest flexion after "
            "contact. Degrees are the engine's convention, a straight arm at "
            "zero."
        ),
        "beforeThePhase": round(before, 4),
        "videoBeforeDegrees": round(float(np.interp(before, grid, video_on_grid)), 1),
        "engineBeforeDegrees": round(float(np.interp(before, grid, engine_on_grid)), 1),
        "videoAtContactDegrees": round(
            float(np.interp(contact_phase, grid, video_on_grid)), 1),
        "engineAtContactDegrees": round(
            float(np.interp(contact_phase, grid, engine_on_grid)), 1),
        "videoPullInDegrees": round(float(video_on_grid[after].max()), 1),
        "enginePullInDegrees": round(float(engine_on_grid[after].max()), 1),
    }

    # How much of the VIDEO window is itself standing still, measured the same
    # way as the reference's featureless share. Where both shares are large the
    # alignment over that stretch is two flat curves being matched, which no
    # method can do better than any other.
    still = featureless_share(window_values)

    # THE RANKING IS PER REPETITION, and a first version ranked only the first
    # one. Swapping which repetition was ranked moved the intended drill from
    # first place to second on this very clip, which is the clearest possible
    # demonstration that one repetition's ranking is not the clip's ranking.
    ranking = rank_against_library(window_values, reference, measure)
    rank = next(
        (n + 1 for n, row in enumerate(ranking) if row["movement"] == movement), None)
    by_whole = sorted(ranking, key=lambda row: row["warpDistance"])
    rank_whole = next(
        (n + 1 for n, row in enumerate(by_whole) if row["movement"] == movement), None)

    return {
        "movement": movement,
        "measure": measure,
        "window": {
            "startSeconds": candidate["startSeconds"],
            "catchSeconds": candidate["catchSeconds"],
            "peakSeconds": candidate["peakSeconds"],
            "endSeconds": candidate["endSeconds"],
            "samples": candidate["samples"],
            "peakToNoise": candidate["peakToNoise"],
        },
        "anchored": {
            "contactPhase": contact_phase,
            "note": (
                "Three instants onto three phases: the repetition's start onto "
                "0, the catch onto the reference's own contactPhase, the end "
                "onto 1. No warp is fitted."
            ),
        },
        "warped": {
            "distance": round(distance, 5),
            "bandShare": WARP_BAND_SHARE,
            "note": (
                "Banded dynamic time warping on z-normalised curves. The "
                "distance is in units of normalised curve and is NOT degrees."
            ),
        },
        "agreementPhase": {
            "median": round(float(np.median(gap)), 4),
            "p90": round(float(np.percentile(gap, 90)), 4),
            "worst": round(float(gap.max()), 4),
            "note": (
                "How far apart the two instruments place the same video sample "
                "on the engine's phase axis. It is not averaged away and "
                "neither instrument is corrected toward the other."
            ),
        },
        "handColumns": hand,
        "libraryRanking": ranking,
        "rankOfAskedDrill": rank,
        "rankOfAskedDrillWholeCurve": rank_whole,
        "rankNote": (
            "Two scorings, and neither is called correct. rankOfAskedDrill is "
            "on the informative stretch of each reference; "
            "rankOfAskedDrillWholeCurve is on the whole curve. Where they "
            "disagree, the ranking is a property of the method rather than of "
            "the movement."
        ),
        "rankingMargin": (
            None if len(ranking) < 2 else
            round(ranking[1]["warpDistance"] - ranking[0]["warpDistance"], 5)),
        "featurelessSharePhase": round(featureless_share(curve), 4),
        "videoStillSharePhase": round(still, 4),
        "bothFeaturelessSharePhase": round(min(featureless_share(curve), still), 4),
        "featurelessNote": (
            "The leading share of the engine curve that has not yet moved by "
            f"{FEATURELESS_TOLERANCE_DEGREES} degrees. Warping onto a flat "
            "stretch costs nothing, so over this share the warp is not an "
            "alignment. Read the two instruments' agreement outside it."
        ),
        "medianLevelGapDegrees": round(level, 3),
        "levelNote": (
            "Video minus engine, on a common phase grid, in the engine's own "
            "convention where a straight arm is zero. It is reported here and "
            "kept OUT of the match: z-normalising threw the level away on "
            "purpose, so nothing in the alignment is evidence about degrees."
        ),
        "catchProxyNote": (
            "The video's catch is the elbow flexion MINIMUM before the pull-in "
            "— the arm at its most extended. The engine's contactPhase is the "
            "frame its possession model holds the ball. Two definitions of one "
            "word, and the anchored alignment inherits the difference."
        ),
        "phasePerSample": [
            {"ptsSeconds": round(float(when), 4),
             "degrees": round(float(value), 2),
             "anchoredPhase": round(float(a), 4),
             "warpedPhase": round(float(w), 4)}
            for when, value, a, w in zip(window_times, window_values, anchored, warped)
        ],
    }


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--set", dest="set_id", default="0.1")
    parser.add_argument("--movement", default=NEAREST_DRILL)
    parser.add_argument("--instrument", default="fromLiftDegrees",
                        choices=("fromLiftDegrees", "fromSideViewDegrees"))
    parser.add_argument("--out", default=None)
    arguments = parser.parse_args(argv[1:])

    curve_path = OUTPUT / f"elbow-curve-{arguments.set_id}.json"
    if not curve_path.exists():
        raise SystemExit(f"{curve_path} is missing; run video_elbow_curve.py first")
    measured = json.loads(curve_path.read_text(encoding="utf-8"))
    reference = json.loads(
        (OUTPUT / "reference-curves.json").read_text(encoding="utf-8"))

    times = np.array([row["ptsSeconds"] for row in measured["rows"]])
    values = np.array([row[arguments.instrument] for row in measured["rows"]])
    accepted, refused = find_repetitions(times, values)
    print(f"set {arguments.set_id}, {arguments.instrument}, {len(times)} samples")
    print(f"  {len(accepted)} repetitions accepted, {len(refused)} refused")
    for row in refused:
        print(f"    REFUSED at {row.get('peakSeconds')} s: {row['reason']}")
    if not accepted:
        raise SystemExit(
            "no repetition passed the quality bar, so nothing is aligned. The "
            "readings above are the evidence; do not lower the bar to get a "
            "number out of this clip.")

    aligned = [
        align_repetition(times, values, candidate, reference, arguments.movement)
        for candidate in accepted
    ]

    print(f"\n  {'window':>18s}  {'catch':>7s}  {'still':>6s}  "
          f"{'phase disagreement':>20s}  {'level':>7s}")
    for row in aligned:
        window = row["window"]
        print(f"  {window['startSeconds']:7.3f} to {window['endSeconds']:7.3f}"
              f"  {window['catchSeconds']:7.3f}"
              f"  {row['videoStillSharePhase'] * 100:5.0f}%"
              f"  median {row['agreementPhase']['median']:.3f} worst "
              f"{row['agreementPhase']['worst']:.3f}"
              f"  {row['medianLevelGapDegrees']:+7.1f}")

    # The repetition that holds the catch the findings report placed by hand.
    HAND_CATCH_SECONDS = 9.13
    named = min(aligned, key=lambda row: abs(
        row["window"]["catchSeconds"] - HAND_CATCH_SECONDS))
    hand = named["handColumns"]
    print(f"\n  THE FINDINGS REPORT'S OWN TABLE, for the repetition holding its "
          f"{HAND_CATCH_SECONDS} s catch")
    print(f"  (this run places that catch at {named['window']['catchSeconds']:.3f} s, "
          f"pull-in at {named['window']['peakSeconds']:.3f} s)")
    print(f"    {'':22s} {'before':>10s} {'at contact':>12s} {'pulling in':>12s}")
    print(f"    {'measured from video':22s} {hand['videoBeforeDegrees']:10.1f} "
          f"{hand['videoAtContactDegrees']:12.1f} {hand['videoPullInDegrees']:12.1f}")
    print(f"    {'the engine':22s} {hand['engineBeforeDegrees']:10.1f} "
          f"{hand['engineAtContactDegrees']:12.1f} {hand['enginePullInDegrees']:12.1f}")

    print(f"\n  the engine curve is featureless for its first "
          f"{aligned[0]['featurelessSharePhase'] * 100:.0f} percent, and that "
          f"repetition's video is still for "
          f"{named['videoStillSharePhase'] * 100:.0f} percent of itself")
    print(f"  level gap, video minus engine: "
          f"{named['medianLevelGapDegrees']:+.1f} deg (kept out of the match)")
    firsts = sum(1 for row in aligned if row["rankOfAskedDrill"] == 1)
    print("\n  THE NULL TEST. A warp fits anything to anything, so the reading is")
    print("  where the asked-for drill ranks against all eight, on EVERY")
    print("  repetition rather than on one that was chosen.")
    whole_firsts = sum(1 for row in aligned if row["rankOfAskedDrillWholeCurve"] == 1)
    print(f"    {arguments.movement[8:]} ranks first on {firsts} of "
          f"{len(aligned)} repetitions scoring the informative stretch,")
    print(f"    and on {whole_firsts} of {len(aligned)} scoring the whole curve. "
          "NEITHER scoring is")
    print("    called correct: the filmed drill is none of the eight, so there is no")
    print("    right answer here to be closer to.")
    print(f"    informative ranks: {[row['rankOfAskedDrill'] for row in aligned]}")
    print(f"    whole-curve ranks: "
          f"{[row['rankOfAskedDrillWholeCurve'] for row in aligned]}")
    print("\n  the named repetition's full ranking, best first:")
    print(f"    {'informative':>11s} {'whole curve':>12s}  drill")
    for row in named["libraryRanking"]:
        mark = "  <-- asked for" if row["movement"] == arguments.movement else ""
        print(f"    {row['informativeWarpDistance']:11.4f} {row['warpDistance']:12.4f}"
              f"  {row['movement'][8:44]:36s}"
              f" featureless {row['featurelessSharePhase'] * 100:3.0f}%{mark}")

    document = {
        "schemaVersion": SCHEMA_VERSION,
        "set": arguments.set_id,
        "instrument": arguments.instrument,
        "sourceCurve": curve_path.name,
        "engineReferenceStamp": reference.get("generatedFrom"),
        "stampNote": (
            "TWO BUILDS MEET HERE. The video curve comes from the keypoint "
            "files, whose own stamps are in those files; the engine curve "
            "comes from the build named above. A comparison across two builds "
            "is only as good as the older half, and naming both is the least "
            "that can be done about it."
        ),
        "repetitionsAccepted": len(accepted),
        "repetitionsRefused": refused,
        "alignments": aligned,
        "askedDrillRanksFirstOn": firsts,
        "askedDrillRanksFirstOnWholeCurve": whole_firsts,
        "askedDrillRanks": [row["rankOfAskedDrill"] for row in aligned],
        "askedDrillRanksWholeCurve": [
            row["rankOfAskedDrillWholeCurve"] for row in aligned],
        "rankingNote": (
            "The warp distance to every drill, best first. A warp fits anything "
            "to anything, so a distance to one drill is not evidence about that "
            "drill. If the intended drill is not clearly first, the alignment "
            "shows only that a monotone warp exists, which is always true."
        ),
        "generatedFrom": generated_from(),
    }
    where = Path(arguments.out) if arguments.out else (
        OUTPUT / f"phase-alignment-{arguments.set_id}.json")
    where.write_text(json.dumps(document, indent=1) + "\n", encoding="utf-8")
    print(f"\nwritten -> {where}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
