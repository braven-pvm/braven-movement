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

## Four coaching phases cannot fail

`build_library.py` reports these in every receipt under `phaseSeparation`, and
flags the movement rather than calling it ok.

| drill | phase | its measures move | was |
|---|---|---|---|
| Double Foot Landing | **flight** | **1.97** | **5.70, so it could fail** |
| Double Foot Landing | land | 0.16 | 0.33 |
| 1 Hand Snatches to Other Hand | reach | 0.15 | 0.21 |
| 2 Hand Snatches and Pull In | react | 0.00 | 0.17 |

**The flight row is new, and the elbow pole pack caused it.** Its measure is
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
those two frames, and it does so despite the continuity term, the elbow poles
and the upper arm aim term, all of which run on released frames.

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

## The free arm starts 46 degrees off and snaps through 41 frames later

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
solve leaves the elbow almost straight out to her side, the continuity term
carries that faithfully, and the pole wins abruptly rather than gradually.

The trunk goes with it. The shoulder line jerks −2.26 degrees at that frame
against a steady +0.85 either side, and this drill has no authored turn at all,
so that rotation is entirely emergent.

**This is a snap-through, not a mode flip:** a term that is correct, opposed by
continuity, winning all at once. The fix belongs at frame 0.

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

