# Known issues

Sectioned by lane. The rendering and modelling lane owns the athlete a person
looks at; the movement lane owns the engine, the anatomy, the solver and the
grading. An entry belongs to whichever lane can fix it.

# Rendering and modelling

## Reference catch is not yet a final coaching sample

The current MPFB catch render remains a review artifact. Its hand orientation in the locked
reference view was visually approved on 2026-08-17 and the first premium coaching-studio
presentation pass is complete, but final coaching-sample acceptance is still pending.

The athlete now has a deliberately lean-muscular MPFB phenotype, a loaded lower-body stance,
forward torso intent, and a restrained concentration expression. These parameters are repeatable
and receipt-backed, but MPFB's base topology and identity still limit fine facial acting and
sport-specific muscle definition. The Faceunits 01 pack is a required authoring dependency.

The MPFB hands deliberately retain the signed local index-to-pinky cross product from the rig.
Normalising that sign across left and right hands produces the rejected two-left-hands projection.
The Blender integration test locks the approved thumb side and hand-plane error for both hands.

Do not set `--reference-compared` or publish the current generated pose.

## Fingertip evidence is soft guidance

The supplied photograph is blurred and fingers overlap. Earlier hard per-pixel fingertip IK
produced anatomically painful joints even while reporting low pixel error. Finger targets now guide
comparison, but joint limits and visual anatomy take priority over exact fingertip pixels.

## Presentation is ready for review, not final publication

The deterministic presentation now includes a graphite training kit, sports trainers, a curved
blue-grey studio background, a four-light rig, and a regulation-scale three-colour panelled
netball with embossed seams and procedural grip. The athlete identity, final branded kit, ball
artwork, and production colour grade remain intentionally replaceable through the versioned
configuration after coaching acceptance.

## Reference media is local-only

The source photograph is not committed because publication rights have not been established. The
configuration records its SHA-256 and dimensions so an authorised local copy can be verified.

# Movement

## Five coaching phases cannot fail

`build_library.py` reports these in every receipt under `phaseSeparation`, and
flags the movement rather than calling it ok.

| drill | phase | its measures move | was |
|---|---|---|---|
| 1 Hand Snatches to Other Hand | **contact** | **1.67** | **7.63, so it could fail** |
| Double Foot Landing | flight | 1.95 | 5.70, so it could fail |
| Double Foot Landing | land | 0.16 | 0.33 |
| 1 Hand Snatches to Other Hand | reach | 0.15 | 0.21 |
| 2 Hand Snatches and Pull In | react | 0.00 | 0.17 |

**The contact row is newer still, and the waiting-distance correction caused
it.** That drill's waiting point sat 53.53 cm against a 52.68 cm arm, so its
free arm moves when the correction lands, and its contact checkpoints now read
closer to its reach ones. Disclosed rather than retimed, like the rest.

**The flight row came before it, and the elbow pole pack caused that one.** Its measure is
`leftShoulderElevationDegrees`, and a pole with constant authority makes the
shoulder vary less between the approach and the flight. It was 5.70 before,
which is 0.70 above the threshold, so it was already marginal. The other three
all moved closer to zero for the same reason.

Nothing is retimed and no band is widened to recover it, for the reason the
whole entry gives below. This is the cost of a smoother arm, stated rather
than absorbed, and it goes to the coach morning with the other three.

A checkpoint grades a measure at a phase. If that measure reads the same as at
the previous phase, the checkpoint cannot tell them apart, so it cannot fail.
It passes whatever the athlete does. The library still meets every coaching
checkpoint; three of those meetings are unearned.

This matters for P1. Agreement between engine and coach is the trust bar, and
a check that always passes agrees with a coach for free. The P1 result is
computed twice, with and without these three, for that reason.

Two causes, and only one is a timing problem.

**Wrong moment.** Both snatch drills grade before the ball is doing anything.
`react` sits at phase 0.30 and the pass is not released until 0.3782. Their
own measures first move five degrees at 0.45 and 0.48.

**Wrong measure.** `land` is correctly timed. Its checkpoints are
`footHeightGapCm`, 0.01 to 0.01, and `trunkLeanDegrees`, 2.20 to 1.87. Both
are genuinely static across a landing: the feet are together in flight and on
the floor, and she does not lean. Knee flexion would distinguish it, and the
`absorb` phase already uses it.

Nothing is retimed and no checkpoint is changed, deliberately. Retiming a
phase to a number the engine chose is the engine marking its own homework, and
what a coach checks at a landing is coaching judgement. Both wait for the
coach review, whose marks and notes on exactly these phases are the evidence
the fix needs. The pack does not mark them as suspect, because that would
steer the coaches being measured.

Event-anchored phases are the durable fix, queued as their own pack: anchoring
`react` to release rather than to 0.30 survives a change in ball timing, where
a fixed fraction does not.

## The library is not smooth enough to animate

Worst per-frame upper arm swing, in degrees, at 60 frames a second:

| drill | before the aim term | after |
|---|---|---|
| hooks outside hand | 44.8 | 48.1 |
| one hand snatch to other hand | 20.3 | 26.0 |
| the other six | | all improved or unchanged |

A joint swinging 48 degrees between two frames is not a movement a person
makes, on either number. The aim term aggravated two drills and improved five;
independent review judged the regressions aggravated rather than caused, on
the same frame and the same arm as before.

It is invisible in a phase figure and ruinous in a clip, so it must be fixed
before the library ships as animation. Ordering agreed: the tactics spike
proves the contract on one clip, this is fixed, then clips ship.

Starting points, recorded so they are not rediscovered:

1. Whether the extra 3.3 degrees on `hooks outside hand` is the aim term
   interacting with the mid-movement second-hand join, or noise on a solve
   already three times rougher than any other drill.
2. Whether the aim term steers the free arm on one-handed drills more firmly
   than the grip does.
3. An **11.7 degree** hip-line step between frames **45 and 46** of
   `netball_two_hand_snatch_pull_in`. The hips snap from 176.4 to 164.7 in one
   frame while the shoulder line holds still, moving 0.02.

   This was originally reported by the tactics lane as six degrees between
   frames 41 and 42. That does not re-derive on this tip: frames 41 to 42 move
   0.57 degrees. Independently re-derived twice, by this lane and by review,
   agreeing to within the metric's definition. The original figure may have
   been specific to the reporting pipeline or to the export it read, and the
   frames it named are not where the discontinuity is.

   Recorded this way because a debt entry that sends the fixer to the wrong
   frames is worse than no entry at all.

The elbow pole pack moved this a long way. Per-frame arm direction steps above
each threshold, across both arms and both arm segments, whole library:

| | >5 | >10 | >15 | >20 | >30 | worst |
|---|---|---|---|---|---|---|
| before the ball pack | 71 | 14 | 5 | 4 | 1 | 48.1 |
| after the ball pack | 134 | 26 | 9 | 8 | 1 | 48.1 |
| after the catching-hand fix | 141 | 21 | 6 | 6 | 0 | 26.1 |
| after the pole angle | **109** | **9** | **2** | **0** | **0** | **19.3** |

The >20 column is empty for the first time. What remains at >15 is both on
`netball_hooks_outside_hand`, and is the free-arm flip recorded below.

This entry stays open. 19.3 degrees between two frames at 60 frames a second is
still not a movement a person makes.

When a coach number arrives for the chest catches, the 25 cm threshold in
`test_upper_arm_aim.py` needs rework alongside it: the `technique.py` comment
argues for a folded posture that the test currently forbids, so the two must
move together.

## Centimetres are stored in a field called degrees

`footHeightGapCm` is a checkpoint measure in centimetres, and its band is held
in `minimumDegrees` and `maximumDegrees`. Three occurrences across the
library.

Nothing is wrong today: the same numbers are compared against each other, and
the phase separation guard's threshold is far from the values it judges, so
all three dead phases are dead in either unit. It is recorded because a name
that does not say what it holds is how `fingerBaseDeviation` came to bound a
flexion axis, and that cost a day.

## A per-hand ready offset is a design candidate, not a gap

`BallOffset` is a point, and `ready` in a technique file uses it. Both hands
are then placed around that point by the grip spread, so an `across` of 0.3
means the point sits to her left rather than that each hand sits out to its
own side. Two hands reaching for an off-centre point carry the far one across
the body, which is what put a hand across the face on
`netball_deflect_high`.

That drill is corrected by putting its point on the midline, which is what its
own cue describes. The type is documented in `ball_track.py` rather than
widened.

**A per-hand form is deliberately not built.** One drill authors a ready
offset today, and a field invented for a need nobody has yet is a field that
ends up meaning nothing. Build it when a second drill needs a genuinely
asymmetric wait, and not before.

The trap for the next author: the motion track's `across` IS per hand, and
this one reads the same and is not.

## The coach animation exporter has no tests

`spikes/export_coach_animations.py` has no test file. Its determinism is
currently evidenced only by hand-run regeneration: the movements payload
hashes to `e2d3d815...` and has reproduced across two merges and two rebases,
by this lane and independently by review.

That is evidence, not a guard. Nothing fails if the schema changes shape, if a
key is dropped, or if the output stops being deterministic. A schema and
round-trip test is future work.

It matters more than a normal coverage gap because the coach pack embeds this
file at build time and reads it from a lane worktree, so a silent change
reaches coaches without passing through a review.

## The environment must be activated, not merely located

**Reproduced, and it is not a defect in the code.** Running the suite by
invoking the environment's interpreter directly fails:

```
cd spikes
./.pixi/envs/default/python.exe -m unittest discover -s . -p "test_*.py"
```

That path is the junction into `.assets/pixi-env`. Reaching the interpreter by
either route fails the same way; what matters is that it is named rather than
activated.

It dies at `test_grip.AxesTest.test_the_frame_is_orthonormal`, exit code 127,
no traceback and no summary line. The same command through `pixi run` passes
all 245 tests from the same directory, with the same `.pixi` present and the
same code.

Exit 127 with no Python traceback means the process died below Python rather
than raising, which points at a native library that could not be loaded.
`pixi run` sets up the environment's search paths; naming the executable does
not. That last sentence is inference from the exit code and the absence of a
traceback, not something measured directly.

**What is exonerated.** Two earlier hypotheses are dead, both by measurement
rather than argument. The assets are not the cause: an independent review
reproduced the crash with `spikes/mhr-assets` junctioned and verified, and
sixty-odd solver-dependent tests including character loads passed first.
Missing `.pixi` state is not the cause either: it reproduces here with the
`.pixi` junction present.

**What is unresolved.** Which native library, and why those two modules rather
than an earlier one. `test_grip` and `test_multi_camera_fit` are where it bites
because they are the first to make the call that needs it, not necessarily
because they are special.

**Mitigated rather than left as folklore.** `spikes/pixi.toml` had an empty
`[tasks]` section. It now defines `test`, `library`, `limits` and `proof`, so
the correct invocation is a file that can be run and checked rather than
knowledge someone has to be told:

```
cd spikes && pixi run test
```


## Four coaching checkpoints now fail, and no number was changed to stop them

The engine sends a released ball back to the passer at the speed it came in,
so the athlete now extends through the pass. She did not before: the ball
drifted out of her hands at 0.13 to 0.57 m/s and her arms stayed folded. At
the last frame the hand now reaches 0.93 to 0.95 of full extension, where it
used to sit at 0.70 to 0.75.

The same checkpoint fails on all four releasing drills:

| drill | phase | leftElbowFlexionDegrees | band |
|---|---|---|---|
| Deflects, High | send_on | 35.73 | 45 to 115 |
| Hooks, Jump and Pull In Ball | release | 49.98 | 50 to 120 |
| 2 Hands Catch | release | 41.05 | 55 to 115 |
| 2 Hand Snatches and Straight Back | return | 40.81 | 45 to 105 |

**Nothing is tuned, in either direction.** Rewidening a band to make the engine
pass is the engine marking its own homework. Shortening the follow-through to
fit the band is the same act in reverse. Both were available and both were
refused.

**What the evidence says.** Every one of these bands is marked in its own file
as authored by this project and PROVISIONAL until a coach sets it. The cue
beside the deflect band is the manual's own words: "Extend through the ball as
it goes." The engine now does that and the provisional number says it should
not. The bands were also authored against a solve in which the arm never
extended at all, so they have never been tested against a real follow-through.

`Hooks, Jump and Pull In Ball` misses by 0.02 degrees, which is worth stating
plainly: on that drill the disagreement is not a disagreement.

This is exactly the question the coach review exists to settle, so it goes to
the morning rather than to a commit.

## The follow-through is rough where the arm now moves

Worst per-frame upper arm swing, in degrees, on the drills the return changes:

| drill | before | after |
|---|---|---|
| deflect high | 6.7 | **26.1** |
| hooks jump and pull in | 6.9 | 10.6 |
| two hand snatch straight back | 4.6 | 9.7 |
| two hands catch chest | 10.3 | 10.3 |

The other four drills are unchanged.

**Aggravated, not caused.** The steps are isolated single-frame spikes, on
`netball_deflect_high` at frames 74 and 75, with 2 to 8 degrees on either side
of them. The ramp itself is smooth. The solver picks a different branch on
those two frames, and it does so despite the elbow poles and the upper arm aim
term, both of which run on released frames. An earlier version named the
continuity term in that list. It does not belong there: it has no target set,
so it pulls toward the rest pose rather than resisting a change from the
previous frame.

The arm never moved here before, so the solve was never asked this question.
Making the athlete follow through is what exposed it.

This belongs to the smoothness pack above, which already owns this class of
defect and is already queued. It is recorded separately only because these are
new instances with known frames, and a fixer should not have to find them
again.

## A field called secondsPerFrame holds the solver's cost

`possession_solve.py` puts the SOLVE time per frame in a result field named
`secondsPerFrame`. The animation timestep is 1 over the motion track's own
frame rate, which for this library is 60. The two differ by more than a factor
of two, and nothing in the name says which one it is.

This cost real work. A release velocity was reported from that field, then
"corrected" to figures that were too high by 2.2 times, then corrected back.
The wrong numbers were written into this file before they were caught.

`build_library.py` reads the same field and prints it as "ms/frame", which is
correct for what it holds and is where the meaning is visible.

Renaming it to `solveSecondsPerFrame` is a small change with a handful of
readers. It is not done here only because this pack is about the ball, and a
rename belongs in a commit where it is the subject.

This is the same shape as the entry above about centimetres in a field called
degrees.

## The deflect carry still passes close to her face

`netball_deflect_high` no longer interpolates the ball through her head, but
the worst clearance over its carry is 8.3 cm of ball surface to her eye, and
it now sits at the authored `control` key itself at phase 0.62. Raising the
route key's `ahead` value does not move it: 0.70 through 0.90 all give 8.3 cm.
The control key is where the binding is.

That is an authored coaching position, so it is not touched. A coach has to
say how far in front of her face the ball is controlled. The route key added
alongside it is marked PROVISIONAL for the same reason.

Second closest in the library is `netball_two_hand_snatch_pull_in` at 7.3 cm,
which is a different shape: its closest approach is 10.4 cm BELOW the eye
line, a ball pulled in to the chest. Every drill except the deflect keeps the
ball below the eyes. The deflect is the only one that holds it above, because
the manual says the ball is controlled beside the head.

**A threshold guard was measured and rejected.** The defect dipped 1.7 cm
toward her face between its keys, while `netball_hooks_outside_hand` dips
2.5 cm harmlessly. No distance threshold separates them, so any number chosen
would be a change detector. `spikes/test_carry_route.py` guards the authoring
rule instead, and does not claim to guard the clearance.

## A graded phase can sit in the middle of an interpolation

`netball_deflect_high` grades its control checkpoint at phase 0.70. The
technique authors its `control` key at 0.62 and its `send_on` key at 0.80. The
graded frame therefore falls between two authored keys and reads a position
nobody authored.

This is the same shape as the three checkpoints that cannot fail: a phase
number chosen in the coaching definition and a phase number chosen in the
technique are set independently, and nothing checks that they agree. There a
checkpoint reads a measure that has not moved yet. Here a checkpoint reads a
position that is a straight line between two authored ones.

Event-anchored phases, already queued for the cannot-fail entry, would fix
both. Recorded here so the two are fixed together rather than separately.

## A comment is not a test

Three defects this month were a comment describing the right behaviour sitting
directly above code that did the opposite:

- the bisection's "never inside";
- `curved_directions` and its first bone;
- `possession_solve`'s "only the hand that is taking the ball goes out to meet
  it", above a line that sent both hands to wait.

The third was the largest single-frame step in the library: 19.9 cm of wrist
travel in the contact frame and a 48.1 degree arm swing behind it.

Every one was found by an instrument reading output. None was found by anyone
reading the code, including the people who read that code closely enough to
change the lines around it. A comment states intent, and intent is not
enforced by anything.

The practical consequence for this project: when a comment states a behaviour,
that is a candidate for a test, not evidence that the behaviour happens.

## RESOLVED: the free arm started 46 degrees off and snapped through at frame 41

**Closed by the free-hand fix in `c3aa388`.** Measured on that tip, the left
upper arm's worst single-frame turn on this drill is 3.50 degrees, at frame 59.
At frame 41 it is 0.12 degrees and the forearm is 0.49. The numbers below are
kept because they are the record of the fault, not because they still hold.

The entry itself explains why it closed, in its own last paragraph: the free
hand's only positional target before contact was `waiting`, and `waiting` is
exactly what that fix changed. Nobody noticed at the time, because the pack
measured the free hand's POSITION and never its arm's frame-to-frame turn.

**One sentence of it was also wrong about the mechanism**, and that is
corrected in place below. The largest step on this drill is now the RIGHT upper
arm at 11.32 degrees at frame 45, so the "largest step left anywhere in the
library" claim no longer holds either.

## The record of it

`netball_hooks_outside_hand`, frame 41, left arm, 19.3 degrees on the upper and
18.6 on the forearm between two frames while the wrist moves 1.15 cm. It is the
largest step left anywhere in the library.

**The cause is the first frame, not frame 41.** The free arm's elbow angle about
the shoulder-to-wrist axis, against the 34.6 degrees the pole asks for:

| frame | 0 | 10 | 20 | 30 | 40 | **41** | 42 | 50 | 60 | 95 |
|---|---|---|---|---|---|---|---|---|---|---|
| angle | 81 | 84 | 84 | 72 | 66 | **12** | −13 | 20 | 28 | 30 |

It starts 46 degrees away and every one of the 41 frames before the snap sits
more than 20 degrees off. Then it crosses the whole gap in one frame,
overshoots, and settles at 28 to 30 for the remaining 57 frames. The catching
arm starts at 27.2 and stays between 27 and 30 throughout.

Before contact the free hand's only positional target is `waiting`, which
barely constrains the elbow's rotation about the reach axis. So the first
solve leaves the elbow almost straight out to her side, EACH FRAME'S SEED
carries that faithfully into the next, and the pole wins abruptly rather than
gradually.

That sentence said "the continuity term carries that faithfully". It does not
and cannot: it has no target set, so it pulls toward the rest pose. What
carries a pose from one frame to the next here is the seed.

The trunk goes with it. The shoulder line jerks −2.26 degrees at that frame
against a steady +0.85 either side, and this drill has no authored turn at all,
so that rotation is entirely emergent.

**This is a snap-through, not a mode flip:** a term that is correct, opposed by
the seed's inertia, winning all at once. The fix belongs at frame 0. That
sentence said "opposed by continuity", which named a term that pulls toward
rest and cannot oppose anything frame by frame.

**An earlier version of this entry was wrong** and said the pole pack reduced a
21.7 degree flip at frame 47 to 19.3. The frame-47 flip has gone: it is now
under 8 degrees. The 19.3 is a different event at a different frame, and the
two were conflated by reading a per-drill worst without asking where it was.

## What is left above 10 degrees, in full

So the remaining surface is small enough to name completely:

| drill | frame | segment | step |
|---|---|---|---|
| hooks outside hand | 41 | left upper, left fore | 19.3, 18.6 |
| deflect high | 37 | right upper, right fore | 11.5, 12.4 |
| deflect high | 71 to 73 | both forearms | 10.2 to 12.1 |

Nothing else in the library exceeds 10 degrees on any arm segment on any frame.
Frame 37 on the deflect is its contact frame, so that one is the contact join.
Frames 71 to 73 are its follow-through.

## How wide the elbows sit with the ball at the chest

The pole pack brought the most folded band from 62.9 cm between the elbows to
52.7. The manual's reference is 38.6 cm, and it does not apply here: those
photographs are a snatch AT CONTACT, with the arm at 0.85 to 0.90 of full
extension. No evidence in this project describes a folded arm.

So 52.7 is published rather than aimed at. Nothing was tuned to make it any
particular number, and the mechanical change that produced it needed no coach.

Some of the remaining relationship is real. Elbow separation still correlates
with arm extension at -0.847, against -0.865 before, and it should: a folded
arm's elbow IS further off the line from shoulder to hand. What the pack
removed is the artificial amplification on top of that, worth about 10 cm.

A coach looking at the pull-in should be asked whether 52.7 cm is right. If it
is not, `elbowAngleDegrees` in the technique file is the dial, in degrees, and
it now reaches the mechanism that decides the answer.

## The pole's frame is not orthogonal, so the target is not always reachable

`elbow_poles` builds its frame by projecting `out` and `down` off the reach
axis. It never orthogonalises them against each other. On a reach that is
oblique to both they are not perpendicular, `down * cos + out * sin` is not a
unit vector, and the target leaves the circle the elbow can occupy.

Measured over a spread of reach directions, worst deviation **10.2 cm**, where
the hand sits nearly below the shoulder and `out . down` reaches −0.963. On
that family the point target does argue with the reach — the one thing the
angle form was chosen to avoid.

**The calibration survives and the stated property does not.** 34.6 degrees was
bisected through the whole solve, not derived from the geometry, so it already
absorbs whatever the basis does. Every gate is green with the basis as it is.
What was wrong is the claim in the comment and the name of the test.

The guard exercises reaches along one axis, where `out . down` is exactly zero,
so it tests the family the defect cannot reach. It is left that way on purpose:
widening it turns the branch red for a defect whose fix moves figures.

**Filed as follow-up, after the render window:** an orthonormal basis by
Gram-Schmidt, then re-read the angle, then regenerate every table that depends
on it. It is not urgent, because nothing measured is wrong. It is not optional,
because the code claims a property it does not have.

## The dial was wired to a term that could not honour it

`elbowWidth` was a technique property, named for the case where a chest catch
folds the elbows where a snatch spreads them. It scaled the aim vector in
`upper_arm_aim`.

Sweeping that term's weight from 2.0 down to 0.0 moved folded elbow separation
by **0.2 cm**, from 65.4 to 65.6. So a coach could have set that dial to
anything and the athlete's elbows would not have moved.

No technique file ever authored it, which is the only reason no harm was done.
Had a coach been asked for a number at the review morning, the number would
have been recorded, honoured in the file, and ignored by the engine.

It is now `elbowAngleDegrees` on the elbow pole, which does control separation,
and it is in degrees rather than in multiples of nothing.

**The general shape, worth more than the instance:** a dial is not connected to
what its name says until something measures the connection. Before asking a
coach for any number, sweep the parameter it will feed and confirm the athlete
moves.

## The snap check flags the wrong frame, and there is a real hitch to find

Adjudicated during the pole pack's review. Both halves stand.

**The instrument is faulty.** `spike_report` divides a step by the mean of its
two immediate neighbours. A two-value mean has a breakdown point of zero, so
one small neighbour drags the ratio however it likes: a perfectly normal step
beside a stall is flagged, and a snap out of stillness cannot be seen at all
because the skip-gate exempts it. Filed as follow-up: a median over a window of
two or three either side, excluding the frame itself, with a floored
denominator in place of the skip-gate, and possibly a second-difference
statistic that names a hitch at its own frame. `SNAP_RATIO` recalibrates once
the denominator is robust, and not before.

**And there is a real hitch.** On the `wide` variant of
`netball_two_hand_snatch_pull_in` the elbow steps 8.50, then 0.19 at the
contact frame, then 4.41. That one-frame stall was introduced by the pole pack.
It is the same family as `netball_deflect_high` at frame 37: a discontinuity
where the approach hands over to the carry.

So the red row is honest about there being something wrong, and dishonest about
where and by how much. Neither half excuses the other.

## The cold-start seed set is four copies of one pose

`seeds()` yields four candidates that differ only in `{side}_lowarm_twist`.
That parameter sits BELOW the elbow. Measured on a bent arm, across every seed
value, the elbow moves 0.000 cm and the wrist moves 0.000 cm. The four
candidates are identical from the shoulder to the wrist and differ only in how
the hand is rotated about the forearm.

So the cold start's "best of four" has never been able to choose which side the
elbow goes. `{side}_uparm_twist`, at the shoulder, does select it: the same
values move the wrist by up to 44 cm.

**Measured and then dropped from the pack that found it**, and the numbers
here are corrected against `spikes/measure_seed_variety.py`, which is the
committed way to reproduce them:

| | >5 | >10 | >15 | >20 | >30 | worst | contact |
|---|---|---|---|---|---|---|---|
| the shipped four seeds | 112 | 8 | 0 | 0 | 0 | 12.4 | 38.58 |
| twenty, with humeral twist per side | 112 | 8 | 0 | 0 | 0 | 12.4 | 38.58 |

**Identical.** Not "nearly": every column, the worst step, and the contact mean
to two decimals. Wall time is 5.7 seconds against 5.8, which is noise — the
cold start is one frame out of ninety-eight, so sixteen extra candidates cost
nothing measurable. An earlier version of this entry said "one step at the
5 degree threshold, 0.02 cm, five times the cost". That measured the seed
change TOGETHER WITH a second change to the cold-start score, and it read the
cost as if the seed count were the running cost. Both are corrected here.

So the honest reason for dropping it is not that it is expensive. It is that
it fixes nothing that is currently broken, because the fault it was written for
turned out to be the waiting distance.

It is still recorded, because the search is nominal rather than real: four
candidates identical from the shoulder to the wrist is one trial wearing four
coats, and the next cold-start pathology will meet that wall. `pixi run seeds`
prints the comparison above and the parameter measurements behind it.

## The waiting hand's own history

Kept because the numbers are the evidence a coach is asked to bless.

Before the correction, `netball_hooks_outside_hand` waited with its free arm at
0.927 to 0.999 of full extension, mean 0.979, against 0.328 to 0.890 for every
other arm in the library. The waiting point sat 66.4 cm from that shoulder and
39.1 cm from the other, from one point 50.8 cm from the midpoint between them.

After it, that arm waits inside the library's own band and the drill's contact
elbow separation moves from 30.2 cm to 37.4, against the manual's 38.6.

**A coach may still rule that a facing-away wait belongs nearer full stretch.**
The dial is `ready` in the technique file, the evidence of what 0.999 looked
like is above, and the drill is one of the eight in the review pack.

## Two callers still measure the reach from the midpoint

`toward` places a point at a fixed distance from the MIDPOINT of the shoulders.
`within_every_shoulder` makes that a real reach guarantee, and only
`ready_point` wraps it. Two callers do not:

- `possession.py`, the released follow-through's aim point;
- `possession.py`, the hand target that follows it out.

**Both are reach-and-release contexts, and extending through the ball is what
the manual asks for there**, so a point at the limit of her reach is the
intent rather than a fault. That is the reason they are left alone.

**But the same geometry applies, and this records it as a decision rather than
leaving it as an assumption.** A turned athlete releasing the ball would put
one shoulder further from that point than the midpoint is, exactly as the
waiting case did, and could overshoot her reach on that side.

**It is latent, not active.** Measured at the release frames, all four
releasing drills are square: the shoulder line is within 0.1 degrees of facing
forward, so the midpoint and the shoulders agree and the approximation is
currently exact. The hands reach 0.905 to 0.952 of the arm there, which is the
intended extension.

A drill that both turns and releases would make it active. There is none today.


## The mean elbow separation agreed with the manual by mixing two populations

`ELBOW_POLE_ANGLE_DEGREES` is defined as the angle that puts the mean elbow
separation at contact on the manual's 38.6 cm. Across the whole library it did:
38.58 cm, which is 0.02 cm off. **No drill in that population was at it.**

The 38.6 cm figure is read from photographs of a snatch at contact with the arm
at 0.85 to 0.90 of full extension. That is already recorded above, under "How
wide the elbows sit with the ball at the chest". Six drills put both hands on
the ball at contact and averaged 36.57 cm. Two put one hand on it, so their
other elbow is not on the ball at all, and they averaged 44.60. The two groups
averaged to the target.

It surfaced on 2026-08-30 when the free-hand fix moved one population and left
the other alone. The whole-library mean jumped to 41.68 cm. The six two-handed
drills moved by 0.03.

**The gap is not new and the fix did not cause it.** On the population the
photographs describe, the angle gave 36.57 cm before that change and 36.54
after. A five-point sweep puts the angle that would close the gap at about
37.3 degrees, against 31.3 today.

**Marius ruled on 2026-08-30: record the gap, defer the angle.** The retune
waits for the coach-morning data, because it moves every drill and the
library's look must not change before a second coach has seen it.
`test_elbow_pole.py` now measures the evidenced population, records 36.5, and
states in its own docstring that it no longer proves the read-off claim.

This is the sixth instance of the project's recurring fault class and the first
of a new shape. The others spend a quantity measured in one regime on another.
This one is a CALIBRATION whose agreement with its evidence was an artefact of
the population it was averaged over. When you meet a calibrated constant here,
ask what population the agreement is computed over, and whether every member of
it is the thing the evidence describes.

## A free hand with no post-contact key would rest at the contact point

`resting_point` in `possession.py` puts the hand that is not on the ball at the
last post-contact key, which is where the ball is going. Two fallbacks sit
behind it. A technique with no post-contact key at all falls back to
`ready_point`, which is the behaviour this replaced. A technique whose only key
is the contact offset would rest the free hand out at the contact point.

**No drill trips either.** Every technique in the library that leaves a hand
free authors at least one key past contact, and the two that do author an
identical chest key at across 0, up 0.10171, ahead 0.55938 torso lengths.

It is recorded rather than guarded. A guard for a case no drill reaches cannot
be tested against a real drill, and an untestable guard is exactly what "A
comment is not a test" above is about. A drill authored with a free hand and no
chest key would make it active. There is none today.

## RESOLVED: the cold start resolved the leg's redundancy differently

**Closed by the backward sweep.** Frame zero was the only frame solved without
a neighbour to start from. It now gets one: the drill is solved forward as
before, then walked back from the last frame, every earlier frame re-solved
from its successor. No frame in the kept answer is a cold start.

On the outside-hand hooks the right knee now opens at 49.9 against the 48 the
drill settles at, and its worst step falls from 9.54 degrees to 2.03. The
record of the fault is kept below.

**The mechanism was proved, not inferred, after the free-hand pack shipped a
fix that passed its acceptance test by luck.** Two controls:

| build | knee at frame 0 | worst right-knee step |
|---|---|---|
| before | 34.1 | 9.54 at frame 6 |
| backward sweep | 49.9 | 2.03 at frame 47 |
| backward sweep, frame zero excluded | 34.1 | **15.43 at frame 0** |
| a second FORWARD sweep, same cost | 34.3 | 5.46 at frame 8 |

The third row is the confirmation: exclude frame zero and the whole
disagreement lands on the frame-zero boundary, which is where the explanation
says it should. The fourth is the refutation of "it is just more solving": the
same number of extra solves, in the same direction, leaves frame zero where it
was and the snap in place.

**What it costs.** The solve doubles, 11.2 to 22.0 milliseconds per frame.

**What it moves.** 38 measured values across the library, largest 5.34 degrees,
and no verdict flips. The signature is a left and a right knee moving in
opposite directions on every drill, by 0.5 to 4.8 degrees — the pelvis trading
one leg against the other, which is the redundancy this fault lives in.

`test_cold_start.py` states the rule as drift against target movement, which is
the pairing the cold start's own docstring used. It fails on the code before
this change and names the fault.

## The record of it

On `netball_hooks_outside_hand` the right knee opens at 34.1 degrees of flexion
against 50.0 before the free-hand fix. It holds 34 to 37 for six frames, steps
9.6 degrees between frames 6 and 7, and settles at about 47 for the rest of the
drill. The free hand's target barely moves across those frames.

**Nothing is broken in the pose.** Both feet read 0.00 cm off the floor
throughout and the pelvis holds 84.04 to 84.06 cm. With the foot planted and
the pelvis fixed, knee flexion is not fully determined — the hip can rotate and
reach the same foot from the same pelvis at a different knee angle. The solver
has freedom there and resolved it one way at the cold start and another once
the drill was running.

**It is the cold start, and it is the free-hand target that moves it.** Isolated
by building the two changes separately:

| build | right knee at frame 0 | worst right-knee step |
|---|---|---|
| main | 50.0 | 2.10 |
| the second solve pass alone | 50.0 | 1.06 |
| both changes | 34.1 | 9.54 |

The second pass alone leaves the opening pose alone and makes that channel
smoother. The free-hand target is what changes which pose the solve from rest
lands in.

**It is the same fault the cold start's own docstring already describes**, in a
new limb. That docstring says solving frame zero once from rest "left the
athlete in a different arm configuration from frame one, and the elbow moved 33
degrees over the first few frames while the target barely moved". The remedy
then was several seeds scored by `contact_miss`. The seeds vary only the forearm
twist and the score reads only hands, so neither can tell two leg poses apart.

**Scale, stated so it is not read as worse than it is.** No drill's worst
single-frame step moved by more than 0.56 degrees over eight angles, and the
library already carries steps of 4 to 19 degrees. The graded checkpoints at
`facing_away` barely moved: the left knee 50.6 to 51.9 and the trunk turn not at
all. The right knee is measured and reported there but is not a checkpoint.

A fix belongs in the cold start rather than here: frame zero is the only frame
not continuous with a neighbour, and a backward pass over the opening frames
would give it what every other frame has. That is a mechanism change and it is
not bundled into the free-hand pack.

## The term named continuity is a pull toward the rest pose

`possession_solve.py` and `movement_engine.py` both build a
`solver2.ModelParametersErrorFunction`, set its weight to 0.02, and call the
variable `continuity`. Neither ever calls `set_target_parameters`.

That class "penalizes the difference between the target model parameters and
the current model parameters". With no target set the target is zero, which is
the rest pose. Every other use of the same class in this repository names the
variable `prior`, which is what it is.

**Frame-to-frame continuity here comes entirely from the seed.** Each frame is
solved starting from the previous frame's answer. Nothing in the objective
prefers the previous pose.

**Five places said otherwise and all five are corrected as of this entry:** the
comment above `CONTINUITY_WEIGHT`; the first-frame comment in
`movement_engine.py`; the continuity paragraph in `spikes/README.md`; and two
sentences in the free-arm snap entry above. A sixth, in the follow-through
entry, listed the term among those resisting a branch change.

**Reread any historical snap reasoning that leans on this term.** Two of the
corrected sentences were load-bearing: "the continuity term carries that
faithfully" and "a term that is correct, opposed by continuity". A pull toward
rest can do neither. It cannot carry a bad pose forward and it cannot oppose a
correct term frame by frame. Wherever an explanation in this ledger turns on
continuity holding a pose, the mechanism is the seed and the explanation should
be checked rather than assumed to survive the rename.

**The behaviour is not changed here, and the variable is not renamed.** The
engine works: continuity does happen, by seeding, and every drill is graded on
what the code actually does. Only the description was wrong.

### What correcting the target would cost, measured but not applied

Setting the target to the previous frame was built and measured on 2026-08-30,
then deferred. The numbers are kept so the eventual change inherits them:

| | worst single-frame step, eight drills | values moved | verdicts flipped |
|---|---|---|---|
| target set to the previous frame | +0.10 in total | 35, at most 2.3 degrees | 0 |

**It is deferred for two reasons, and the first is the stronger.** The rest
prior is currently what lets a bad first frame ESCAPE, at the cost of a snap.
Making the prior frame-to-frame makes the solve more faithful to frame zero, so
a bad opening pose is carried further rather than repaired. The correction
belongs WITH a better cold start, never instead of one. Second, Marius's ruling
of 2026-08-30 holds the library's look still until a second coach has seen it,
and 35 moved values is a change to the look however small.

**It also does not fix the cold start, which is what it was first built for.**
Against the knee finding above it appeared to: the knee opened at 46.4 instead
of 34.1 and the 9.5 degree snap became 0.95. A control run — the old prior at
frame zero, the new one everywhere after — left the knee at 34.1 and moved the
snap to frame 9 at 6.15 degrees rather than removing it. The apparent fix was
an under-determined joint tipped across a basin boundary by the finger
parameters, which are the only part of the target that differs at frame zero.
Luck, not mechanism.

## The residual the cold-start test cannot see, and why it is excluded

`test_cold_start.py` compares the drift over a drill's opening window against
later windows whose hand target moved no further. A drill whose opening target
genuinely moves is excluded, because a pose that follows a moving target is
doing its job.

**That exclusion hides a real residual on `netball_hooks_jump_pull_in`.** Its
opening still drifts 5.65 degrees at the right knee over twelve frames, down
from 6.12 before the backward sweep. The test never looks, because the hand
target moves 2.15 cm over those frames and the rule only applies under 1 cm.

**The exclusion is right and the residual is real.** Both. A rule that failed
that drill would be measuring the drill rather than the solver, and would be
switched off the first time somebody read it. `netball_double_foot_landing` is
the clearer case: it drifts 26 degrees at the knee over its opening, which is
the landing.

So this is recorded here rather than tightened into the test. **It is a known
blind spot, not a gap somebody still has to find.** Anyone who rediscovers a
drifting opening on that drill has found this, not something new.

Closing it needs a discriminator the current one does not have: a way to say
how much of an opening's drift the target actually accounts for, rather than
whether the target moved at all. Nobody has built that.

## RESOLVED: the receiving hand no longer grips before it arrives

The queued finding read: "the job carries `grip.l` at the `contact` phase while
that hand is still 101 to 134 mm from the ball, so all five of its digits read
short." Measured on `a38c43d`, that state is gone.

`export_blender_job.py` emits a grip only for the hands `sides_at` reports, and
only once she is holding the ball. On both one-handed drills the `contact`
phase now emits `grip.r` alone:

| drill | phase | sides_at | left wrist to ball | right wrist to ball |
|---|---|---|---|---|
| one_hand_snatch | contact | `('r',)` | 49.0 cm | 15.2 cm |
| one_hand_snatch | join | `('l', 'r')` | 15.4 cm | 15.4 cm |
| hooks_outside_hand | contact | `('r',)` | 46.7 cm | 15.0 cm |
| hooks_outside_hand | gather | `('l', 'r')` | 15.4 cm | 15.5 cm |

**A hand is described as gripping only when it sits at the same standoff as
the hand that took the ball**, 15.2 to 15.7 cm from the centre. Two fixes closed
it between them: the `sides_at`-only export change, and the free-hand fix in
`c3aa388`, which turned the left hand's 49 cm at contact into a place it is
meant to be rather than a hand caught mid-flight.

## A retired lead: the 29.6-degree grip angle was three errors

Recorded so that nobody raises it again as an anomaly.

A measurement taken while chasing the above reported that at contact every
two-handed drill sits at 46 to 49 degrees between the ball-centre-to-wrist
direction and the ball's path, while the one-hand snatch's catching hand read
29.6. It looked like an outlier. It is not, and it was wrong three ways:

- **The wrong point.** It used the WRIST, which is about 15 cm from the ball
  centre and behind the palm. The contact point is on the surface.
- **The wrong axis.** It measured against the ball's VELOCITY. The grip is not
  built about the velocity. `grip.contacts` says so in its own docstring: "The
  catcher is used rather than the ball's own velocity because a grip is
  symmetric about the body that is taking the ball, not about the path it
  arrived on."
- **An inverted legend.** It was written up as "180 degrees means the hand
  meets the ball head on". The opposite is true: `contacts` places a hand at
  `centre + radius * outward` with `outward` built from `shoulders - centre`,
  and the ball flies toward the shoulders, so a hand on the arriving face reads
  NEAR ZERO.

Measured correctly, on the contact points, there is nothing to explain. The
half-spread is 45 degrees and the ball's velocity sits 22.5 degrees off `near`
on that drill, so the two contacts land at 66.5 and 24.9 — which is 45 plus and
minus 22.5. The two-handed drill, whose velocity is 8.9 degrees off `near`,
reads 45.7 on both hands against a half-spread of 45.

**The docstring predicted the error before it was made.** The lesson is not
about grips: an instrument aimed at a different axis from the one the design
uses will find an anomaly every time, and the anomaly will be the instrument.

## The second hand travels 14 cm out to meet the ball, and a coach must rule

Not a defect, and NOT changed here, because it lives in `spikes/movements/`.

Erin Burger's note on the one-hand snatch reads: "Other hand stays ready. Pull
the ball in from the hand that catch ball into other hand at chest. Don't want
other hand to go away from centre of body towards ball."

The free hand now waits at the chest, 11.9 cm ahead of her shoulders. The
carry's `join` key puts the ball at ahead 0.81364 torso lengths when the second
hand arrives, which is 35.6 cm ahead of her shoulders, so that hand goes out to
26.0 cm and then comes back to 12.0 as the ball reaches the chest. The hooks
drill is the same shape, 11.8 out to 25.1 and back to 12.0.

**It is smooth, and an earlier reading of it was wrong.** A first pass compared
the median over the whole pre-join window against the peak and reported a jump
at the join frame. The hand in fact starts moving at about frame 45 and ramps:
1.5 to 2.5 cm per frame on the way out over thirteen frames, 0.5 to 0.7 on the
way back over thirty-nine. The step at the join frame itself is 0.18 cm.

So the question is not whether the movement is broken. It is whether 14 cm out
and back is what the coach means by "don't want other hand to go away from
centre of body towards ball". If it is not, the change is the `join` and
`gather` keys at ahead 0.81364 and 0.79330, and that is a key-retune: it goes
to Marius with this evidence before anybody touches it.
