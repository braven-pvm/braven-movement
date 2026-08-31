"""Find frames where a measured angle changes rate against its neighbours.

STDLIB ONLY, AND DELIBERATELY. This lived in `possession_solve.py`, which
imports the solver at module level, so a test of this instrument could not even
LOAD on a runner without one — the same fault that took `build_stamp.py` out of
`build_library.py` earlier the same day. An INSTRUMENT with no test that runs
everywhere is the last thing this project should have: the whole reason this
file was rewritten is that the old statistic was wrong and nothing said so.

`statistics.median` rather than numpy's, so there is nothing to import beyond
the standard library.
"""

from __future__ import annotations

from statistics import median

# Below this a band cannot be judged, and a step under it is not a movement
# worth naming. It is the same figure `movement_definition` uses, restated here
# rather than imported, because importing it would drag the solver back in.
# `test_snap_report` asserts the two agree.
MINIMUM_MEANINGFUL_BAND_DEGREES = 5.0


# How many steps either side of a frame make its neighbourhood. Three is
# enough to have a median that one odd value cannot move, and short enough that
# the neighbourhood is still local to the frame.
SNAP_WINDOW = 3
# Below this a step is solver noise rather than movement, and dividing by it
# produces enormous ratios that mean nothing. It replaces a skip-gate that
# EXEMPTED the interesting case: a step out of a dead stall had a near-zero
# denominator, so the check skipped precisely the frames it exists to name.
SNAP_FLOOR_DEGREES = 0.2


def _same_direction(signed: list[float], number: int) -> bool:
    """Whether the movement keeps going the same way across this step.

    Reads the nearest step either side that actually moves, so a run of tiny
    steps between two real ones does not read as a reversal by accident.

    AT AN EDGE, THE ONE NEIGHBOUR THAT EXISTS DECIDES. An earlier version
    returned True where either side was missing, which let an edge turning
    point through: the jump-and-pull-in hooks ends with steps of -14.67 and
    then +1.56, a reversal on the drill's very last frame, and it was reported
    as a stall of ratio 7.74. With no neighbour at all there is no evidence
    either way, so it returns False and nothing is flagged.
    """
    before = next(
        (signed[i] for i in range(number - 1, -1, -1)
         if abs(signed[i]) >= SNAP_FLOOR_DEGREES),
        None,
    )
    after = next(
        (signed[i] for i in range(number + 1, len(signed))
         if abs(signed[i]) >= SNAP_FLOOR_DEGREES),
        None,
    )
    if before is None and after is None:
        return False
    if before is None:
        return True
    if after is None:
        # Only the step before exists. A step that reverses against it is the
        # movement turning round at the end of the drill, not pausing in it.
        return before * signed[number] >= 0
    return before * after > 0


def spike_report(measurements: list[dict]) -> dict:
    """Find frames where a measured angle changes rate against its neighbours.

    A snap is a local change of rate, not a fast movement. Comparing the
    largest step in a run against the largest step in an easier run measures
    which run is easier, which is a different question and the wrong one: a
    wide ball is taken faster than a central one by a real athlete too.

    TWO THINGS WERE WRONG WITH THE FIRST VERSION and both are fixed here.

    IT DIVIDED BY THE MEAN OF TWO NEIGHBOURS, which has a breakdown point of
    zero: one small neighbour drags the ratio wherever it likes, so a perfectly
    ordinary step beside a stall was flagged. The denominator is now the MEDIAN
    over `SNAP_WINDOW` steps either side, excluding the frame itself, which
    three odd values cannot move.

    AND IT COULD NOT SEE A STALL AT ALL. The old skip-gate exempted any frame
    whose neighbours were smaller than 0.2 degrees, which is exactly a snap out
    of stillness; and its significance gate required the STEP to be large,
    which a stall never is. A one-frame pause between two large steps is a
    hitch as much as a one-frame jump is, and it is the shape the contact
    hand-over actually produces. So the ratio is symmetric — the larger of
    step-over-neighbours and neighbours-over-step — and a frame counts as
    worth judging when EITHER its step or its neighbourhood is meaningful.

    `SNAP_RATIO` in proof.py and retarget.py is the threshold this feeds, and
    it was recalibrated only after this denominator became robust, never
    before: a threshold tuned against a statistic with breakdown point zero is
    tuned against noise.
    """
    worst_ratio = 0.0
    worst_where = None
    for key, value in measurements[0].items():
        if not key.endswith("Degrees") or not isinstance(value, (int, float)):
            continue
        series = [frame[key] for frame in measurements]
        signed = [series[i + 1] - series[i] for i in range(len(series) - 1)]
        steps = [abs(one) for one in signed]
        for number in range(len(steps)):
            low = max(0, number - SNAP_WINDOW)
            high = min(len(steps), number + SNAP_WINDOW + 1)
            around = [steps[i] for i in range(low, high) if i != number]
            if not around:
                continue
            neighbours = float(median(around))
            # Meaningful if EITHER side is: a big step among small ones is a
            # jump, and a small step among big ones is a stall. Requiring the
            # step alone to be big is what made every stall invisible.
            if max(steps[number], neighbours) < MINIMUM_MEANINGFUL_BAND_DEGREES:
                continue
            step = max(steps[number], SNAP_FLOOR_DEGREES)
            neighbours = max(neighbours, SNAP_FLOOR_DEGREES)
            if step < neighbours and not _same_direction(signed, number):
                # A TURNING POINT IS NOT A HITCH. An angle that reverses has a
                # step through zero at the reversal, so a stall test with no
                # further condition flags every turn in the library — which a
                # first version of this did, on five drills of eleven.
                #
                # The discriminator is the SIGN of the steps either side. If
                # they differ the movement reversed there and the small step is
                # the turn itself. If they agree the movement paused for one
                # frame in the middle of going somewhere, which is the hitch
                # the contact hand-over actually produces.
                continue
            ratio = max(step / neighbours, neighbours / step)
            if ratio > worst_ratio:
                worst_ratio = ratio
                worst_where = {
                    "measure": key,
                    # The step from frame `number` to `number + 1`, named by
                    # the frame it arrives at, as before.
                    "frame": number + 1,
                    "stepDegrees": round(steps[number], 2),
                    "neighbourMedianDegrees": round(neighbours, 2),
                    "kind": "jump" if step >= neighbours else "stall",
                }
    return {
        "worstNeighbourRatio": round(worst_ratio, 2),
        "at": worst_where,
    }
