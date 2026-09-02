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

Apex against horizontal speed, from `solve_launch`. Release at 205 cm and the
receiver's hands at 140 cm.

| horizontal speed | 5 m: flight, apex above floor | 7 m: flight, apex above floor |
|---|---|---|
| 600 cm/s (the library's constant) | 0.83 s, **261 cm** | 1.17 s, **341 cm** |
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

Second, and this is not about the lob: **at 7 m the library's own 600 cm/s
constant produces a 341 cm apex, which is a lob.** The single undocumented ball
speed does not make a flat pass at the manual's own drill distance. That is
another face of `docs/KNOWN_ISSUES.md`, "The ball speed for the whole library is
one undocumented constant", and it belongs with that entry rather than with
this one.

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
4. **Does the lob keep the chest pass's phases?** The chest pass releases at
   0.80 from a chest-height drive. Step 2, "pull the ball up as high as arm can
   go", is a different shape and may need its own motion keys, which would make
   the lob more than a ball file after all. **THIS IS THE ONE THAT COULD
   OVERTURN THE VARIANT RULING** and it should be checked first, on the pinned
   build, before the ball file is written.
