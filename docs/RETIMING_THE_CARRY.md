# Retiming the carry moves the graded window. The easing does not.

Measured on 2026-09-09 against `13148a7`. The instruments are
`scripts/sweep_carry_timing.py` and `scripts/sweep_release_easing.py`, both
committed. `spikes/movements/` is copied to a temporary directory and patched
there; the repository's own files are never written.

**This is the number Marius's ruling assumed and nobody had taken.** He ruled the
release timing mechanical on the condition that it lands before Erin grades,
because a retiming moves the arm inside the frames her checkpoints measure.
**That is now measured, and he was right.**

## What was varied, and why it authors nothing

Each pass's technique file carries an `afterContact` path. The last key is the
release. **Moving the key before it LATER compresses the same travel into fewer
frames before the release**, which is what "the hand accelerates into the
release" means in the numbers the engine already has.

| drill | key moved | shipped | release |
|---|---|---|---|
| `chest_pass` | `drive` | 0.62 | 0.80 |
| `overhead_pass` | `step` | 0.58 | 0.80 |
| `bounce_pass` | `drive` | 0.62 | 0.80 |
| `one_hand_high_pass` | `step` | 0.55 | 0.80 |

Swept at **−0.25, 0.0, +0.25, +0.50, +0.75** of the gap to the release, so the
shipped build sits **inside** the range and not at its end. One existing number
per drill. **Nothing is created.**

**The chest pass's `step` key is deliberately not touched.** Its own note reads
"SHE STEPS AND THE BALL DOES NOT MOVE … the manual's 'Keep hands where they were
with catch, don't pull ball back' … NOTHING GRADES IT". It is authored coaching
intent, and a retune that accelerated the whole carry would delete a manual cue
that no instrument would catch.

## The result: one checkpoint per drill, and it moves a great deal

| checkpoint | −0.25 | +0.25 | +0.50 | +0.75 |
|---|---|---|---|---|
| `bounce_pass/drive/leftElbowFlexionDegrees` | −6.01 | +7.24 | +14.65 | **+22.02** |
| `chest_pass/drive/leftElbowFlexionDegrees` | −4.45 | +5.15 | +10.21 | **+14.95** |

**Both are monotonic in the shift.** That is the signature this sweep exists to
distinguish: **a dose-response, not a basin.** The easing sweep's large rows
appeared and disappeared as the parameter moved; these grow with it in both
directions, including the negative one.

**Up to 22 degrees at the bounce pass's drive phase, against a 5.0 degree band
floor.** That is four band floors.

## Against this sweep's own null

The largest move in a phase the change **cannot reach** — `ready` and `step`,
which precede the moved key — is **6.00 degrees**, on
`one_hand_high_pass/ready/leftKneeFlexionDegrees`. That row has no effect present
to contaminate it, so it is this sweep's own noise.

**The null is large, and it is honest to say so.** It is three times the easing
sweep's 1.71, and it sits on the same drill's ready knee, which was the noisiest
row there too. The lower body is discontinuous in its inputs and this measures
that again.

**The two drive-phase rows clear that null by three to four times AND are
monotonic.** Nothing else in the sweep clears it at all.

## Why only two drills respond

**A checkpoint moves when it is graded AT the phase whose key moved.** The chest
and bounce passes both grade an elbow at a `drive` phase, and `drive` is the key
that moved on both. The overhead and one-hand-high passes moved a `step` key and
grade a knee at `step`, and those moved 0.63 and 0.46 — inside the null.

So the effect is not "retiming moves everything". It is **precise and local: it
moves the elbow at the phase being retimed.**

## The two decisions, now measured and genuinely different

| | what it varies | largest graded move | against its own null | shape |
|---|---|---|---|---|
| **the easing** | the follow-through after the release | 8.40 | 1.71 | **non-monotonic**, a basin |
| **the carry timing** | the drive key before the release | 22.02 | 6.00 | **monotonic**, a dose-response |

**The easing is outside her window and the carry is inside it.** That is what
Marius's ruling assumed, and both halves are now measured rather than argued.

**His condition is correct and necessary.** A retimed build changes an elbow
Erin grades by up to 22 degrees. If it lands after she grades, she has graded a
build the engine no longer is.

## The seam test: the hypothesis is HALF right, and the failing half is the one the ledger measures

The orchestrator's hypothesis: the ease-out `out = 1 - (1 - t)^2` begins at full
speed, which is right only if the INCOMING speed matches it. Today it does not,
and the mismatch is the release seam. **If an accelerating carry supplies that
speed, the seam should close with no change to the easing, and two decisions
become one.**

Measured on the same sweep, two ways, because `docs/KNOWN_ISSUES.md` measures the
seam two ways.

### The hand's SPEED step closes, monotonically

| drill | −0.25 | shipped | +0.25 | +0.50 | +0.75 |
|---|---|---|---|---|---|
| `chest_pass` | 9.1x | **7.3x** | 5.6x | 3.6x | **1.7x** |
| `overhead_pass` | 12.9x | **10.2x** | 7.5x | 4.8x | **2.3x** |
| `bounce_pass` | 10.9x | **8.5x** | 6.3x | 4.0x | **1.9x** |
| `one_hand_high_pass` | 0.6x | **0.6x** | 0.6x | 0.6x | 0.7x |

**The mechanism is visible in the two columns underneath.** On the chest pass the
speed INTO the release rises 33.6 to 144.3 cm/s across the sweep while the speed
AFTER it stays at 245. **The carry supplies the incoming speed and the step
shrinks. The follow-through is untouched.**

`one_hand_high_pass` has no step to close, which is consistent: it is the drill
whose wrist already peaks AT the release frame.

### The shoulder's ANGLE step does not move at all

| drill | −0.25 | shipped | +0.25 | +0.50 | +0.75 |
|---|---|---|---|---|---|
| `chest_pass` | 5.32 | **5.32** | 5.31 | 5.31 | 5.31 |
| `overhead_pass` | 7.10 | **7.02** | 7.10 | 7.10 | 7.10 |
| `bounce_pass` | 6.67 | **6.66** | 6.66 | 6.67 | 6.67 |

**Flat to two decimals across a sweep that cuts the speed step by four times.**

**AND THE SHIPPED COLUMN REPRODUCES THE LEDGER EXACTLY.**
`docs/KNOWN_ISSUES.md` records "seam at 76 to 77, elevation" as **7.02 / 5.32**,
overhead first and chest second. This instrument, built independently, reads
7.02 and 5.32. **That is the instrument validating itself against a number it
was not built from.**

### So the two decisions do NOT collapse

**The seam that closes is the one this lane named. The seam that does not is the
one the ledger measures and the one a reviewer reported.** A retimed carry fixes
the hand's velocity discontinuity and leaves the shoulder's angle step exactly
where it was.

**The reading, offered as a reading and not as a measurement:** the carry decides
where the hand comes FROM, and the ease-out decides where it goes TO. The
elevation step is in the second, so nothing on the carry side reaches it.

**The easing therefore still needs its own ruling.** The hypothesis was worth
testing and it would have been worth acting on if it had held. It does not, and
finding that out cost one run of an instrument that already existed.

## What this does NOT say

**It does not say the retiming is right.** It says it is visible. Whether the
elbow SHOULD read 15 degrees more at the drive phase is a coaching judgment, and
`leftElbowFlexionDegrees` at `drive` has a band that a retimed value may leave.

**It does not test an accelerating carry against the release seam.** That was the
orchestrator's hypothesis and it needs the follow-through measured alongside a
retimed carry, which is a second run.

**And it does not license a retune.** No number under `spikes/movements/` is
changed by any of this. Gate 4 stands and the shape of the retiming is a
coaching judgment nobody has made.
