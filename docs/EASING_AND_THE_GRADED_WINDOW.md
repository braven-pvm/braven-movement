# The easing's effect on grading is below the solver's own noise

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

## The result, stated against this sweep's own null

**A FIRST VERSION OF THIS SECTION SAID "no graded checkpoint moves by as much as
the 5.0 degree band floor anywhere in the sweep". THAT SENTENCE IS WITHDRAWN AND
IT WAS DISPROVED BY THE TABLE FOUR LINES BELOW IT**, which carries +8.40 and
+8.30. A summary sentence contradicted by its own list is the fault this
repository records most often, and it was written here in the document that
catches a basin. Count the items, then write the sentence.

**THE HONEST STATEMENT USES THIS SWEEP'S OWN NULL RATHER THAN AN ABSOLUTE
FLOOR.**

> **At every graded checkpoint the easing's effect is indistinguishable from the
> solver's own noise, measured independently at 1.7 degrees on a knee in a phase
> the easing cannot reach. The two rows that exceed it are basin crossings,
> non-monotonic in the parameter, and a basin is not an easing effect.**

**Where the null comes from, and why it is not borrowed.**
`one_hand_high_pass/ready/leftKneeFlexionDegrees` sits at a `ready` phase, which
happens BEFORE the release. The easing shapes only frames after the release, so
**it cannot reach that checkpoint at all.** Every number in that row is solver
variation with no effect present to contaminate it, and its largest excursion is
1.71 degrees. That is this sweep measuring its own noise, on its own drills, in
its own units.

**Fourteen of the sixteen rows that moved sit below that null.** They are not
"small". They are **unresolvable**: this instrument cannot tell them from the
solver restarting.

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

## The caveat that must travel with the scheduling finding

**"Not urgent" is true of the DECISION and not of every ANSWER.** A ruling that
said "any easing is fine, it does not reach her" would be wrong at two of the
six values tested. Measured, the largest move at any graded checkpoint:

| variant | largest move at any checkpoint | against the 1.7 null |
|---|---|---|
| `linear` | 0.79 | below |
| `p = 1.25` | 0.88 | below |
| **`p = 1.5`** | **8.40** | **five times above** |
| `p = 2.0` | the baseline, zero by construction | — |
| `p = 2.5` | 1.54 | below |
| **`p = 3.0`** | **8.30** | **five times above** |
| `smoothstep` | 0.91 | below |

**At p = 1.5 or p = 3.0 a knee Erin grades moves 8.4 degrees**, and it does not
matter to her mark that the cause is a solver basin rather than the easing. So
the constraint is on the answer, not on the timing: **four of the six are safe
and two are not.**

**"Safe" here means no basin was crossed on THESE FOUR DRILLS at THESE VALUES.**
It is not a guarantee. The lower body is discontinuous in its inputs, so another
drill may cross at another value, and any chosen easing must be re-swept across
the drills it will ship on.

**The easing still needs its ruling.** `KNOWN_ISSUES` shows no easing wins on
the spike instrument, and this document adds only that grading cannot break the
tie either. **It is not urgent against Erin's date**, which is the finding.

## The guard that makes a null result trustworthy

A sweep reporting "no effect" is worthless unless it can be shown to be capable
of reporting an effect. Three guards, and the third is the one that matters:

1. the run fails if `possession.py:658` no longer matches the line it patches;
2. it asserts the substitution changed the file;
3. **it asserts that the PATCHED module is the one that got imported.**

**Without the third, a sweep that silently imported the repository's own module
would report exactly the no-effect result this one superficially resembles**, and
the conclusion would be unfalsifiable. The instrument also refuses a flat result
outright: if nothing moves anywhere, it exits with an error rather than
reporting "no effect", because a sweep that cannot move anything is more likely
to be disconnected than to be evidence.

## What is not answered here

**Whether an accelerating carry closes the seam.** That is the carry-side half,
and it cannot be swept the same way: there is no carry path to vary. Refer to
`docs/THE_CARRY_HAS_NO_PATH.md`. It needs a path authored where none exists, and
no path is authored until Marius has scoped it.
