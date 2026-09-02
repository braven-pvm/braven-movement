# The bounce pass: what the manual cues, and what the engine can measure

Written 2026-09-02 by the content lane, BEFORE anything is authored, on the
orchestrator's instruction. Nothing in `spikes/movements/` is touched by this
document.

Measured on `32663a9`, the tip after PR #60 merged, in the content-lane
worktree, `pixi run --frozen`, `MKL_THREADING_LAYER=SEQUENTIAL`. The manual is
the *Netball Skills and Conditioning Manual, Level 1, 3rd version*, by Niel du
Plessis and Erin Burger, read at `.assets/manual/202526 updated coaches
manual.md`.

**The conclusion first, because it decides the shape of the work: THE ENGINE HAS
NO FLOOR. A released ball is one unbroken parabola and it falls through the
ground. A bounce pass cannot be represented today, and the clip would be too
short to contain the bounce even if it could.**

## 1. What the manual says

**The technique block, manual page 82 (marker `_page_81`, lines 2702 to 2708).**
Quoted exactly.

> **1/2 HAND BOUNCE PASS**
>
> - 1. Pull the ball to the side, bend slightly (can step into bounce)
> - 2. Give a small step, and with wrist and hands pass the ball to another player/wall
> - 3. Keep hand behind the ball
> - 4. Bounce ball approximately 1m in front of receiver
> - 5. Keep ball low

**Where it sits.** Listed as "Bounce pass" under Passes in both INDIVIDUAL and
BLOCK (lines 2632 and 2644), FIFTH of eight, after 1 Hand wide release and
before Underarm.

**Elsewhere.** Line 4274 uses it as a negative in a game: a team instructed to
play bomb passes turns the ball over "if the play a bounce pass". Lines 2470 and
2483, in the two hooks drills, allow a player to "bounce ball to gain control and
catch it" — that is a recovery, not this pass.

**Why it was chosen as the next drill.** It is the only pass the manual teaches
that Braven Tactics' `RELEASE_KINDS` can already name, so it needs no
vocabulary ruling, and it has a technique block of its own so it needs no
parent. Refer to item 10 of `docs/COACH_MORNING_2026-09.md`.

## 2. THE STRUCTURAL FINDING: there is no floor

**The released ball is one unbroken parabola.** `possession.py` integrates it as

```
centre = origin + velocity * at
centre[1] -= 0.5 * GRAVITY_CM * at * at
```

and there is no floor term, no bounce and no restitution anywhere in
`possession.py`, `ball_track.py` or `possession_solve.py`. Searched for floor,
ground, bounce, rebound and restitution; the only hits are a horizontal
projection in `incoming_speed_cm` and the foot-height code, neither of which
touches the ball.

**Measured.** A launch aimed at a floor point 4.00 m ahead of a release at
142.4 cm, at the library's 600 cm/s, solved by `ball_track.solve_launch` and
integrated with the engine's own formula:

| t (s) | ball height (cm) | ahead (cm) |
|---|---|---|
| 0.00 | 142.4 | 46.3 |
| 0.30 | 132.3 | 226.3 |
| 0.50 | 76.5 | 346.3 |
| 0.60 | 33.9 | 406.3 |
| **0.70** | **−18.6** | 466.3 |
| 1.00 | −234.7 | 646.3 |
| 1.50 | −791.1 | 946.3 |

**The ball reaches the ground at about 0.67 s and keeps falling. By 1.5 s it is
7.9 m below the court.** Nothing stops it and nothing reports it.

**And the clip is too short to hold the bounce anyway.** On the two passes
already authored the release is at phase 0.80 of a 1.60 s clip, which leaves
**0.32 s of flight**. The ball reaches the floor at 0.67 s, **2.1 times longer
than the clip has left**. So even with a floor, the bounce would happen after
the last frame, and the clip a board plays would show a ball still descending.

**A bounce pass therefore needs two things this engine does not have**: a floor
the ball reacts to, and a longer clip or an earlier release. Both are engine and
authoring decisions rather than content ones.

## 3. The instrument audit, cue by cue

Every measure a checkpoint can read today, from
`segment_measures.MEASURE_UNITS`: `trunkLeanDegrees`, `trunkTurnDegrees`,
left and right `ElbowFlexionDegrees`, `ShoulderElevationDegrees` and
`KneeFlexionDegrees`, all in degrees, plus `footHeightGapCm` in centimetres.
Nine measures, eight of them angles.

| manual cue | instrument | verdict |
|---|---|---|
| 1a. "Pull the ball to the side" | **NONE.** No measure reads a lateral ball position. The nearest proxy is the divergence between the two shoulder elevations, and it is impure and coarse: measured on `netball_overhead_pass`, a carry 0.42 torso lengths off the midline separates them by 7.35 degrees with both still inside their band, and it takes about 62 cm to push one out. | cannot grade |
| 1b. "bend slightly" | **YES.** `leftKneeFlexionDegrees`, natively in degrees. This is the one cue in the block that grades cleanly. | gradeable |
| 1c. "(can step into bounce)" | **NONE.** Step length has no measure. Recorded already on the chest pass and the overhead pass. | cannot grade |
| 2a. "Give a small step" | **NONE.** The same missing measure. | cannot grade |
| 2b. "with wrist and hands pass the ball" | **YES.** `leftElbowFlexionDegrees`. `netball_overhead_pass` grades this exact cue. | gradeable |
| 3. "Keep hand behind the ball" | **REPORT ONLY.** `spikes/hand_orientation.py` reports `thumbToBallDegrees`, `thumbUpDegrees` and `fingerUpDegrees` into every receipt and declares itself report-only. It is absent from `MEASURE_UNITS`, so no checkpoint can read it. | cannot grade |
| 4. "Bounce ball approximately 1m in front of receiver" | **NONE, TWICE OVER.** There is no floor for the ball to strike, so the event does not exist; and there is no measure of a position on the court, so it could not be read if it did. | cannot grade, cannot represent |
| 5. "Keep ball low" | **NONE.** The ball's height through its flight has no measure. This is the height row already open in `docs/KNOWN_ISSUES.md`, "No units-correct distance measures, and three cues already want them". | cannot grade |

**Two of eight cue parts are gradeable. One is report-only. Five have no
instrument, and one of those five has no physics either.**

**The two missing length measures bite here exactly as predicted.** Both open
rows in `KNOWN_ISSUES` are wanted by this one block: a HEIGHT for "keep ball
low", and a POSITION for "bounce approximately 1m in front of the receiver". A
bounce point is both at once — where the ball's lowest point meets the floor.

## 4. What follows for the authoring

**No proxy should be graded for cues 4 and 5.** They are the two cues that make
a bounce pass a bounce pass, and grading an angle in their place would be the
fault this library has now recorded twice: the chest pass's pull-back
checkpoint, deleted for being insensitive, and the overhead pass's, deleted for
firing on a solver basin. A third would be a pattern rather than an accident.

**What a bounce pass CAN carry today** is the arm and leg shape of the throw:
the knee bend, the elbow through the release, and a follow-through phase. That
is a real drill and it is worth authoring. It is NOT a graded bounce.

**What it cannot carry** is the bounce.

## 5. What I am asking before authoring

1. **Does the engine gain a floor?** A ball that reacts to the ground is a
   movement-lane change and it is the difference between a bounce pass that can
   be watched and one that is a flat pass with a misleading name.
2. **If not, is a bounce pass with an ungraded, unrepresented bounce still worth
   authoring?** It would be an honest drill for the throw and silent on the
   thing the manual names in two of its five steps. I can build that and say so
   plainly in the file, which is what the chest pass did with its pull-back.
3. **Should the clip be longer, or the release earlier?** 0.32 s of flight does
   not reach the floor at any plausible speed. This is worth settling even
   without a floor, because the same shortness truncates the two passes already
   merged.
4. **Which drill distance?** The manual's passing drills say "Area: Court
   (5-7m)" and its unit drills stand players 5 to 7 m apart. The bounce point is
   1 m short of the receiver, so the distance sets the bounce point.
