# The lob pass: what the manual says, and what a ball file can carry

Written 2026-09-02 by the content lane so that the lob's ball file is authored
from the source on the day its parent technique exists. Nothing is authored yet.

**READ SECTION 4b FIRST.** Sections 2 and 5 were written before the lob's parent
was measured and they name the CHEST pass. Section 4b measured that and it is
wrong: the lob rides the overhead or the 1 Hand High pass. Every passage that
still says otherwise is marked SUPERSEDED in place rather than deleted, because
the reasoning that produced the wrong answer is worth reading beside the
measurement that overturned it.

Most numbers below are quoted from the manual or arithmetic on `solve_launch`.
**Section 4b RAN THE POSSESSION SOLVER**, on a775502.

**The variant mechanism already EXISTS.** `ball_track.ball_variants` and
`ball_path(movement_id, variant)` are on main, and
`netball_two_hand_snatch_pull_in` already carries high, low and wide balls. What
is missing is the lob's PARENT TECHNIQUE, and an entry in
`test_authored_launch.AUTHORS_A_LAUNCH` for the new file's name.

The orchestrator ruled on 2026-09-02 that the lob is a BALL FILE VARIANT and
not a technique. The manual settles that in the lob's own first step, and the
ruling is recorded here because a future reader will otherwise ask why the
library has no `netball_lob_pass`.

## 1. Every line the manual gives about the lob

Quoted exactly, ampersands and all. Line numbers are into
`.assets/manual/202526 updated coaches manual.md`.

**The technique block, manual page 83 (marker `_page_82`, line 2720).** The
manual is the *Netball Skills and Conditioning Manual, Level 1, 3rd version*, by
Niel du Plessis and Erin Burger, which is the form the library's definitions
cite.

> **LOB PASS (BOMB)**
>
> The ball needs to reach the highest point where the defender is, then come
> down on the receivers outside hand (Face side)
>
> - 1. Use one of the different passing types (1 Hand high/wide or double hand)
> - 2. Pull the ball up as high as arm can go
> - 3. Keep hand behind the ball and fingers up

**Where it sits in the syllabus.** Listed under Passes in both INDIVIDUAL and
BLOCK (lines 2634, 2646), SEVENTH of eight in both, before Fake pass. Named
"Bomb pass (ball first)
(p83)" in the TECHNIQUE row of the skill progression (line 346).

**When it is chosen.** The passing progression's last stage (line 2651):
"Game where they use different passes, without defender Add defender static
(pressure) **Defender arms high - choose which pass to use**" (emphasis
added).

**Who reads it.** A whole drill exists for the defender reading the flight
(line 4786): "Passer starts with ball, and can decide if they are passing a
straight pass or a lob pass", under the heading "Reading trajectory of ball, to
go front or at the back".

**It is also the fallback feed.** In HOOKS OUTSIDE HAND and HOOKS INSIDE HAND
(lines 2469, 2482). The two differ by one letter and both are quoted: 2469
reads "If worker struggle the passer will pass a lob pass" and 2482 reads
"If worker struggles the passer will pass a lob pass".

**Distance.** `5-7m` occurs 64 times across the document; the exact phrase
"5-7m apart" occurs 22 times, all in the unit drills. The passing technique
drills say "Area: Court (5-7m)". **The manual's own Bomb pass drill stands the
players 5-7 m apart** (line 4088), which is the lob's own distance and the one
to author against.

## 2. THE FIRST STEP IS WHY THIS IS A VARIANT

> Use one of the different passing types (1 Hand high/wide or double hand)

The manual does not describe a lob hand action, because there is not one. A lob
is a TRAJECTORY laid over a pass the player already knows. Line 4786 says the
same thing from the other end: the passer decides between a straight pass and a
lob with the ball already in her hands.

That is this engine's own split. The technique file says how she handles the
ball; the ball file says where it goes, exactly as
`netball_two_hand_snatch_pull_in` already carries high, low and wide balls.

**SUPERSEDED BY SECTION 4b.** This section originally concluded that the lob is
`netball_chest_pass.lob.ball.json`, the CHEST pass's technique against a second
ball. **That is wrong and 4b measures why:** a lob ball against the chest pass
leaves the release pose unchanged, 48.4 cm below what the manual asks. The
conclusion that the lob is a BALL FILE stands; the PARENT is the overhead or the
1 Hand High pass, not the chest pass.

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
says as high as the arm can go.

**The 140 cm receiver height has NO SOURCE.** It is a plausible chest height and
nothing more. The library's authored catch heights run from 126.4 to 186.5 cm.

| horizontal speed | 5 m: flight, apex above floor (205 to 140 cm) | 7 m: same geometry |
|---|---|---|
| 600 cm/s (the library's constant) | 0.83 s, 261 cm | 1.17 s, 341 cm |
| 450 cm/s | 1.11 s, 326 cm | 1.56 s, 470 cm |
| 350 cm/s | 1.43 s, 424 cm | 2.00 s, 664 cm |
| 300 cm/s | 1.67 s, 514 cm | 2.33 s, 841 cm |
| 250 cm/s | 2.00 s, 664 cm | 2.80 s, 1134 cm |

A netball goalpost is 305 cm, for scale.

**THE 205 cm RELEASE HEIGHT IS AN ASSUMPTION, NOT A MEASUREMENT.** The lob pose
does not exist yet, so nothing has been solved for it. Measure the real release
height when the pose is authored and recompute this table.

**IT DOES NOT MOVE ONE FOR ONE**, which an earlier draft claimed. At the table's
own fixed 140 cm catch, ten centimetres of extra release height buys between 5.1
and 6.0 cm of apex: `d(apex)/d(release)` is 0.60 at 600 cm/s over 5 m, falling to
0.51 at 250 cm/s over 7 m. It would be one for one only if the catch height rose
with the release.

**Two things fall out of the table and both matter.**

First, the plausible lob is a narrow band, and **an earlier draft placed it
wrongly.** It said the ball goes over the goalpost below 300 cm/s. **By this
table's own geometry the apex crosses 305 cm at 485 cm/s over 5 m and at 679
cm/s over 7 m** — so at 5 m every row here except 600 is already over the post,
and at 7 m every row is.

That may be exactly what a bomb is: the manual asks the ball to "reach the
highest point where the defender is", not to stay under a goalpost. But the
sentence that led to a 400-to-500 band was wrong, and the band is withdrawn
rather than re-derived. **The speed follows from a defender height a coach
gives, and no such height exists yet.** Refer to question 1 in section 5.

Second, and this is not about the lob: **the library's own 600 cm/s constant
turns from a flat pass into a lob inside the manual's own drill range.**

CORRECTED after Bruce could not reproduce a first version of this row. The
first version read 341 cm and used the LOB's 205 cm overhead release, which is
the wrong geometry for a claim about a straight pass. A straight pass leaves
from chest height, and the library's own figure for that is
`author_flight.DEFAULT_RELEASE_HEIGHT_CM`, 135 cm. Recomputed on that:

| distance | apex above floor at 600 cm/s, from a 135 cm release | reading |
|---|---|---|
| 5 m | **220 cm** level to 135, **225 cm** to a 145.4 cm catch | passes under a raised defender: a flat pass |
| 7 m | **302 cm** level to 135, **307 cm** to a 145.4 cm catch | a netball goalpost is 305 cm: a lob |

Both rows now give both conventions. An earlier draft gave 225 for 5 m and 302
for 7 m in the same sentence, which mixed them: 225 is the to-145.4 figure and
302 is the level one. **145.4 cm is ONE drill's catch height**,
`netball_two_hand_catch_chest`, not the library's; the other nine ball files run
from 126.4 to 186.5 cm.

**Why 135 and not this drill's own measured release.** Section 4b measures the
chest pass releasing at 142.4 cm at the ball and 137.1 at the wrist. This table
uses 135 because the claim is about `author_flight.DEFAULT_RELEASE_HEIGHT_CM`,
the constant the FEED tool throws from, and the fairest test of a constant is on
its own terms. From the measured 142.4 the figures are 228 and 309, and the
reading does not change.

Both arithmetics were correct and the flight time is identical at 1.167 s; the
whole difference was the release height. The finding is sharper for the
correction: the constant is fine at the near end of the manual's stated 5 to 7 m
and has become a lob by the far end, with no change to the number and nothing
in the file saying so. **THE 7 M FIGURE IS ALREADY ON MAIN AND THIS IS A CITATION, NOT A NEW
FINDING.** `docs/KNOWN_ISSUES.md` lines 1563-1566 and `docs/WRIST_AND_PACE.md`
lines 165-168 already publish the 302 cm against a 305 cm goalpost. What is
added here is the 5 m end, which shows the constant is distance-dependent across
the manual's own range rather than simply too slow.

That is another face of `docs/KNOWN_ISSUES.md`, "The ball
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
| "Pull the ball up as high as arm can go" | **QUALIFIED.** `leftShoulderElevationDegrees` and `rightShoulderElevationDegrees` do read the arm overhead and DO grade it on `netball_overhead_pass`. But the measure is IMPURE at exactly this height: it reads arm FOLD as well, leaking 8.2 degrees non-monotonically at a 184.4 cm ball centre, which is the lob's own height. No units-correct height measure in centimetres exists. Refer to the `docs/KNOWN_ISSUES.md` row "No units-correct distance measures, and three cues already want them", which names this cue as what a height measure would guard. An earlier draft said an unqualified YES. |
| "Keep hand behind the ball and fingers up" | **PARTLY.** `spikes/hand_orientation.py` reports `thumbUpDegrees`, `fingerUpDegrees` and `thumbToBallDegrees` into every receipt, so "fingers up" IS measured. It is REPORT-ONLY: the module says so on its first line, it is absent from `MEASURE_UNITS`, and no checkpoint can read it. Refer to `spikes/hand_orientation.py` and `docs/HAND_MIRROR_EVIDENCE.md:221`. An earlier draft cited `docs/COACH_REVIEW_2026-08-30.md`, which predates the instrument and says the engine measures no hand orientation. |

**The apex is the one worth building.** It is the lob's defining quantity, the
manual states it as the requirement, and it is a single number over a path the
engine already computes. A `peakHeightCm` on the outgoing launch would make the
lob's central cue gradeable for the first time. That is a movement-lane
instrument request and it is not raised as a blocker: the lob can ship without
it, ungraded on its main point and saying so.

## 4b. ANSWERED: THE LOB IS NOT A CHEST PASS VARIANT

Measured 2026-09-02 on `02b25cd`, which is what section 5's question 4 asked
for, and re-checked by the PR #62 reviewer on `a775502` with every figure
reproducing. **The variant ruling survives in FORM and its PARENT
changes.**

**A lob ball variant leaves the release pose IDENTICAL TO 0.1 cm AND 0.1 DEGREE at the release frame.** Not bit-identical, which an earlier draft claimed and the table's own 48.8 against 48.7 disproves: the largest parameter difference is 0.148 over frames 0 to 76, and 0.04 degrees at the release itself. The frames AFTER the release do differ, because the follow-through tracks the launch. What holds is the conclusion: a ball file cannot raise the release. Solved
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

**The manual asks for about 185.5 cm.** "As high as arm can go" on the
reference athlete is her `l_uparm` at 132.9 cm AT FRAME 0, her ready stance, plus
a 52.68 cm arm. The frame matters: the same joint reads 136.2 at the release
frame and 141.9 at rest. Both figures are wrist heights, so comparing this with
the 137.1 wrist below compares the same quantity. The chest pass releases at
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
   hand", and the lob's step 2 is the 1 HAND HIGH pass's step 1 word for word.
   **SUPERSEDED IN PART.** This question originally assumed double hand because
   the chest pass was already in the library; section 4b measured that the chest
   pass cannot carry a lob at all. The overhead pass is now authored and is the
   two-handed candidate. What a coach still owns is the choice between it and the
   one-handed high pass, which the manual's own wording favours. ("First pass" in
   the original reasoning meant first in the manual's two practice plans; the
   technique section's first block is the OVERHEAD PASS.) A
   one-handed lob would need the one-handed pass first.
4. **ANSWERED, NOT A COACH QUESTION AFTER ALL.** Measured on the pinned build:
   the lob is not a chest pass variant and the manual names the right parent.
   Refer to section 4b. What remains for a coach is which parent — the manual
   offers "1 Hand high/wide or double hand" and the library has none of them.
