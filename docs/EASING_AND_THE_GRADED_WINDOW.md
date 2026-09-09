# The follow-through easing is invisible to grading

Measured on 2026-09-09 against `13148a7`. The instrument is
`scripts/sweep_release_easing.py`, committed beside this document.
`spikes/movements/` is gate 4 and untouched, and the repository's own
`possession.py` is never written: it is copied to a temporary directory,
patched there, and that directory goes first on `sys.path`.

## The question this answers, and why it was open

`docs/KNOWN_ISSUES.md`, under "The release seam and the frame-81 stall are one
defect", already compares three easings across the whole library. **It measures
joint steps and the receipt's `worstNeighbourRatio`, and it never measures a
graded checkpoint.** So the number a coach would have to re-grade had never been
taken. This takes it.

## What was varied, and why as a family

One line, `possession.py:658`, which shapes the follow-through aim point after
the release:

    out = 1.0 - (1.0 - out) ** 2

That is `1 - (1 - t)^p` at `p = 2`. **The shipped value sits inside the family
that was swept**, which is what makes this a sweep and not three builds:

| | |
|---|---|
| swept | `linear`, `p = 1.25, 1.5, 2.0, 2.5, 3.0`, `smoothstep` |
| shipped | `p = 2.0`, the baseline every difference is taken against |
| drills | the four passes |
| measured | `measured` from the receipt, per phase, per checkpoint |

**Population limit, stated:** four passes, not the library. The easing affects
every drill that releases. These are the four where the release is the
technique.

## The result

**NO GRADED CHECKPOINT MOVES BY AS MUCH AS THE BAND FLOOR ANYWHERE IN THE
SWEEP.** The floor is 5.0 degrees. Of sixteen checkpoints that moved at all,
fourteen moved by **less than 1.3 degrees** across every variant.

The two that moved further did not move because of the easing. Refer below.

## The two large moves are basin crossings


| checkpoint | linear | 1.25 | 1.5 | 2.5 | 3.0 | smoothstep |
|---|---|---|---|---|---|---|
| `overhead_pass/step/leftKneeFlexionDegrees` | −0.01 | +0.00 | **+8.40** | +0.00 | **+8.30** | +0.00 |
| `one_hand_high_pass/ready/leftKneeFlexionDegrees` | −0.79 | −0.88 | +1.71 | +1.54 | +1.53 | +0.91 |

**The first is not monotonic in `p`.** It is zero at 1.25, jumps 8.4 degrees at
1.5, returns to zero at 2.5, jumps again at 3.0, and is zero under smoothstep.
An effect of the easing would grow or shrink with the easing. **This appears and
disappears, which is a different solution and not a different follow-through.**

**The second is at a `ready` phase, which happens BEFORE the release.** The
easing shapes only frames after the release, so it cannot cause anything at
`ready`. Every number in that row is solver variation, and the row is useful for
exactly that reason: **it measures the solver's own noise at about 1.7 degrees
on a knee**, with no easing effect present to confuse it.

Both are lower-body checkpoints. This repository already records that the lower
body is discontinuous in its inputs and that every planted increment lands in a
different basin.

**A single variant would have reported "changing the easing moves a knee by 8.4
degrees". That claim is false, and only the sweep shows it.**

## The joint steps beside the points

| drill | linear | 1.25 | 1.5 | **2.0** | 2.5 | 3.0 | smoothstep |
|---|---|---|---|---|---|---|---|
| `chest_pass` | 11.049 | 11.047 | 11.053 | **11.045** | 11.047 | 11.045 | 11.044 |
| `overhead_pass` | 7.331 | 7.332 | 7.332 | **7.336** | 8.338 | 9.666 | 7.323 |
| `bounce_pass` | 6.078 | **11.589** | 6.079 | **6.077** | 6.079 | 6.079 | 6.091 |
| `one_hand_high_pass` | 15.175 | 15.177 | 15.177 | **15.177** | 15.171 | 15.169 | 15.187 |

The bounce pass's 11.589 at `p = 1.25`, against 6.08 everywhere else including
its neighbours, is the same shape: **a solution that appears at one point of the
sweep and not at the points either side of it.**

## What this means for the unit

**THE EASING DECISION DOES NOT HAVE TO LAND BEFORE ERIN GRADES.** Marius ruled
the release timing mechanical on the condition that it lands before she grades,
because a retiming moves the arm inside the window her checkpoints measure.
**That reasoning is correct and it does not apply to the easing**, which shapes
the follow-through after the ball has gone and moves no checkpoint she reads.

So the two decisions this paper once had as one are separable, and they separate
in a specific direction:

- **The CARRY is inside her window.** It is her graded frames, and it is what
  the ruling was about.
- **The EASING is outside it.** It governs the seam and the frame-81 stall,
  which are animation defects a coach sees in motion and not in a graded still.

**The easing still needs its ruling.** `KNOWN_ISSUES` shows no easing wins on
the spike instrument, and this document adds only that grading cannot break the
tie either. **It is not urgent against Erin's date**, which is the finding.

## What is not answered here

**Whether an accelerating carry closes the seam.** That is the carry-side half,
and it cannot be swept the same way: there is no carry path to vary. Refer to
`docs/THE_CARRY_HAS_NO_PATH.md`. It needs a path authored where none exists, and
no path is authored until Marius has scoped it.
