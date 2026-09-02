# The lob pass: what the manual says, and what a ball file can carry

Written 2026-09-02 by the content lane, before the variant mechanism exists, so
that `netball_chest_pass.lob.ball.json` is authored from the source on the day
it can be. Nothing here is authored yet. No solver was run: every number below
is either quoted from the manual or arithmetic on `solve_launch`.

The orchestrator ruled on 2026-09-02 that the lob is a BALL FILE VARIANT and
not a technique. The manual settles that in the lob's own first step, and the
ruling is recorded here because a future reader will otherwise ask why the
library has no `netball_lob_pass`.

## 1. Every line the manual gives about the lob

Quoted exactly, ampersands and all. Line numbers are into
`.assets/manual/202526 updated coaches manual.md`.

**The technique block, page 82 (line 2720).**

> **LOB PASS (BOMB)**
>
> The ball needs to reach the highest point where the defender is, then come
> down on the receivers outside hand (Face side)
>
> - 1. Use one of the different passing types (1 Hand high/wide or double hand)
> - 2. Pull the ball up as high as arm can go
> - 3. Keep hand behind the ball and fingers up

**Where it sits in the syllabus.** Listed under Passes in both INDIVIDUAL and
BLOCK (lines 2634, 2646), last of eight in both. Named "Bomb pass (ball first)
(p83)" in the TECHNIQUE row of the skill progression (line 346).

**When it is chosen.** The passing progression's last stage (line 2651):
"Game where they use different passes, without defender Add defender static
(pressure) **Defender arms high - choose which pass to use**".

**Who reads it.** A whole drill exists for the defender reading the flight
(line 4786): "Passer starts with ball, and can decide if they are passing a
straight pass or a lob pass", under the heading "Reading trajectory of ball, to
go front or at the back".

**It is also the fallback feed.** In HOOKS OUTSIDE HAND and HOOKS INSIDE HAND
(lines 2469, 2482): "If worker struggle the passer will pass a lob pass".

**Distance.** The manual's drills stand players "5-7m apart", 64 times across
the document, including the passing drills.

## 2. THE FIRST STEP IS WHY THIS IS A VARIANT

> Use one of the different passing types (1 Hand high/wide or double hand)

The manual does not describe a lob hand action, because there is not one. A lob
is a TRAJECTORY laid over a pass the player already knows. Line 4786 says the
same thing from the other end: the passer decides between a straight pass and a
lob with the ball already in her hands.

That is this engine's own split. The technique file says how she handles the
ball; the ball file says where it goes. So the lob is
`netball_chest_pass.lob.ball.json`, the chest pass's technique against a second
ball, exactly as `netball_two_hand_snatch_pull_in` already has high, low and
wide balls.

Authoring a `netball_lob_pass` technique instead would duplicate a technique the
manual explicitly declines to give, and would contradict step 1.

## 3. What the ball file must carry, and what the numbers do

A `launch` block states a `target` in arm lengths and a `speedCmPerSecond`.
**The speed is the HORIZONTAL component only**; the vertical is solved from
gravity so the ball reaches the target. Refer to the `Launch` docstring in
`ball_track.py`, which warns about exactly this case: a lob's vertical is most
of its speed and none of that field.

**So a lob is authored by LOWERING the horizontal speed, not by aiming upward.**
The arc follows.

Apex against horizontal speed, from `solve_launch`. **Release at 205 cm and
the receiver's hands at 140 cm** — a LOB's release, overhead, because step 2
says as high as the arm can go. Every apex below is tied to that 205 and moves
one for one with it.

| horizontal speed | 5 m: flight, apex above floor | 7 m: flight, apex above floor |
|---|---|---|
| 600 cm/s (the library's constant) | 0.83 s, 261 cm | 1.17 s, 341 cm |
| 450 cm/s | 1.11 s, 326 cm | 1.56 s, 470 cm |
| 350 cm/s | 1.43 s, 424 cm | 2.00 s, 664 cm |
| 300 cm/s | 1.67 s, 514 cm | 2.33 s, 841 cm |
| 250 cm/s | 2.00 s, 664 cm | 2.80 s, 1134 cm |

A netball goalpost is 305 cm, for scale.

**THE 205 cm RELEASE HEIGHT IS AN ASSUMPTION, NOT A MEASUREMENT.** The lob pose
does not exist yet, so nothing has been solved for it. Measure the real release
height when the pose is authored and recompute this table. Every apex moves one
for one with it.

**Two things fall out of the table and both matter.**

First, the plausible lob is a narrow band. At 5 m, 450 cm/s clears a raised
defender comfortably and 350 cm/s is already floating. Below 300 cm/s the ball
goes over the goalpost. The authoring choice is roughly 400 to 500 cm/s at 5 m,
and it is a coach's call inside that.

Second, and this is not about the lob: **the library's own 600 cm/s constant
turns from a flat pass into a lob inside the manual's own drill range.**

CORRECTED after Bruce could not reproduce a first version of this row. The
first version read 341 cm and used the LOB's 205 cm overhead release, which is
the wrong geometry for a claim about a straight pass. A straight pass leaves
from chest height, and the library's own figure for that is
`author_flight.DEFAULT_RELEASE_HEIGHT_CM`, 135 cm. Recomputed on that:

| distance | apex above floor at 600 cm/s | reading |
|---|---|---|
| 5 m | **225 cm** | passes under a raised defender: a flat pass |
| 7 m | **302 cm** level, **307 cm** to the library's own 145.4 cm catch height | a netball goalpost is 305 cm: a lob |

Both arithmetics were correct and the flight time is identical at 1.167 s; the
whole difference was the release height. The finding is sharper for the
correction: the constant is fine at the near end of the manual's stated 5 to 7 m
and has become a lob by the far end, with no change to the number and nothing
in the file saying so. That is another face of `docs/KNOWN_ISSUES.md`, "The ball
speed for the whole library is one undocumented constant", and it belongs with
that entry rather than with this one.

## 4. WHAT HAS NO INSTRUMENT

The lob's opening sentence is its whole point and almost none of it can be
graded. Stated here rather than discovered after the fact, because a green
receipt on this drill will cover less than it appears to.

| the manual says | instrument |
|---|---|
| "reach the highest point where the defender is" | **NONE.** No defender is modelled, and nothing reports the ball's apex on an outgoing launch. `author_flight.py` writes `peakHeightCm` for an INCOMING flight only. |
| "come down on the receivers outside hand (Face side)" | **NONE.** No receiver is modelled. The launch has a target point and nobody standing at it. |
| "Pull the ball up as high as arm can go" | **YES.** `leftShoulderElevationDegrees` and `rightShoulderElevationDegrees` read the arm overhead, and this is gradeable as a checkpoint. |
| "Keep hand behind the ball and fingers up" | **PARTLY.** The `handOrientation` receipt section reads the hand against the ball, but it is report-only and not graded. Refer to `docs/COACH_REVIEW_2026-08-30.md`. |

**The apex is the one worth building.** It is the lob's defining quantity, the
manual states it as the requirement, and it is a single number over a path the
engine already computes. A `peakHeightCm` on the outgoing launch would make the
lob's central cue gradeable for the first time. That is a movement-lane
instrument request and it is not raised as a blocker: the lob can ship without
it, ungraded on its main point and saying so.

## 4b. ANSWERED: THE LOB IS NOT A CHEST PASS VARIANT

Measured 2026-09-02 on the pinned build `02b25cd`, which is what section 5's
question 4 asked for. **The variant ruling survives in FORM and its PARENT
changes.**

**A lob ball variant leaves the release pose bit-identical.** Solved
`netball_chest_pass` with and without a `lob` ball carrying a 450 cm/s launch
at 9.5 arm lengths:

| | plain | lob variant |
|---|---|---|
| release frame | 76 | 76 |
| ball height | 142.4 cm | 142.4 cm |
| wrist height | 137.1 cm | 137.1 cm |
| shoulder elevation | 48.8 deg | 48.8 / 48.7 deg |

Nothing moved. **A ball variant cannot raise the release by one centimetre**,
because the carry lives in the technique's `afterContact` keys and a ball file
does not touch them. `possession_solve.solve_movement` says so in its own
docstring — "the technique never changes with it" — and this measures it.

**The manual asks for 185.5 cm.** "As high as arm can go" on the reference
athlete is her shoulder at 132.9 plus a 52.7 cm arm. The chest pass releases at
137.1 at the wrist. **THE GAP IS 48.4 cm**, about two netball diameters, and no
ball file can close it.

**THE MANUAL NAMES THE RIGHT PARENT, and the wording is exact.** Three lines:

| line | pass | text |
|---|---|---|
| 2663 | OVERHEAD PASS, step 1 | "Pull the ball up into the air above your head" |
| 2672 | 1 HAND HIGH PASS, step 1 | "Pull the ball up as high as arm can go" |
| 2725 | **LOB PASS, step 2** | **"Pull the ball up as high as arm can go"** |

**Lines 2672 and 2725 are identical.** The lob's own second step is the 1 Hand
High pass's first step, word for word, and its first step names that pass as an
option. The manual is not describing a new carry; it is pointing at one it has
already given.

**So the lob is a variant of the OVERHEAD or the 1 HAND HIGH pass, and neither
is in the library.** Authoring the lob now requires authoring its parent first.
Neither parent is in Tactics' `RELEASE_KINDS` either, so the
overhead-versus-vocabulary reconciliation already on the coach agenda becomes
the lob's gate.

Nothing is lost by finding out first: no ball file was written, and the finding
is one measurement plus three lines of the manual.

## 5. Open questions a coach must settle

None of these is a code question and none should be guessed.

1. **How high is high enough?** The manual says "the highest point where the
   defender is" and gives no height. A defender with arms raised is the number
   wanted, and the table in section 3 turns it into a speed.
2. **Which distance is the lob authored at?** The drills say 5 to 7 m and the
   apex nearly doubles across that range at a fixed speed.
3. **Which pass type carries it?** Step 1 offers "1 Hand high/wide or double
   hand". This brief assumes double hand, because the chest pass is the
   technique already in the library and it is the manual's own first pass. A
   one-handed lob would need the one-handed pass first.
4. **ANSWERED, NOT A COACH QUESTION AFTER ALL.** Measured on the pinned build:
   the lob is not a chest pass variant and the manual names the right parent.
   Refer to section 4b. What remains for a coach is which parent — the manual
   offers "1 Hand high/wide or double hand" and the library has none of them.
