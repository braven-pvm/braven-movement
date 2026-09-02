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

## No units-correct distance measures, and three cues already want them

Raised 2026-09-02 by the content lane while authoring `netball_overhead_pass`.
An open row, not a defect in anything shipped: nothing today reads a height,
and no band sits where one would be needed.

**TWO measures are missing, and both are lengths.**

**A HEIGHT.** How high the ball or the wrist is, in centimetres, with its unit
declared. It must be read AT THE FRAME THAT IS
GRADED: the crown reference `c_head_null` sits at 163.45 cm at frame 0 of
`netball_overhead_pass` and at 164.80 at its lift frame, and a first draft of
that drill's floor used the frame-0 figure and overstated its clearance by
1.35 cm. The manual's overhead cue is "Pull the
ball up into the air above your head", which is a height, and the drill grades
it on `leftShoulderElevationDegrees` instead.

**Why it was not simply added.** `segment_measures.MEASURE_UNITS` already
declares `footHeightGapCm` as `CENTIMETRES`, so the REGISTRY is not the gap. The
gap is the band: a checkpoint holds its bounds in `minimumDegrees` and
`maximumDegrees` whatever the measure is in, which is the entry above, "Centimetres
are stored in a field called degrees", with three occurrences. Adding a height
measure to a checkpoint today would make a fourth. The orchestrator ruled on
2026-09-02 that no centimetre value goes into a degrees field, and that the fix
is a units-correct band rather than a fourth instance.

**What the substitute costs, measured.** `leftShoulderElevationDegrees` reads
arm FOLD as well as height. Inputs: possession solve, grip `spreadDegrees` 90
with `faceBall`, ball radius 11.0 cm, lift phase 0.35, the carry's `ahead` swept
from 0.100 to 0.800 at a fixed `up` of 1.12 so the ball stays at 184.4 cm.

| where | fold range | shoulder elevation | spread |
|---|---|---|---|
| ball 184.4 cm | elbow 105.7 to 56.6 | 109.5, 107.7, 106.6, 114.8 | **8.2, non-monotonic** |
| ball 174.1 cm, near the crown line | elbow 123.5 and 81.1 | 87.3 and 91.0 | **3.7** |

**So the leak grows with height and is smallest where the band's floor sits.**
Near the crown line it is 3.7 degrees, under the 5 degree threshold, which is
why `netball_overhead_pass` ships on the substitute and says so beside its band.

Read that precisely rather than as "no verdict moves": the FLOOR ITSELF IS
UNCERTAIN BY 3.7 DEGREES because of the fold, so a drill reading within 3.7 of
its floor could fall either side depending on how the hands are placed. That is
smaller than the measurement threshold, and no drill sits there — the overhead
pass reads 107.7 against a floor of 91, a margin of 16.7. A future drill
authored close to the floor would need the pure measure. Above the crown the measure is impure, and **no band currently sits
there**, which is what makes this a row rather than a fault.

**IT ALSO READS HAND PLACEMENT, at a completely fixed ball.** Found by the
PR #60 reviewer and confirmed by the content lane on the same build. A grip
`spreadDegrees` of 60 against 120 reads 102.13 against 113.67, an 11.5 degree
spread. A ball radius of 8 against 14 cm reads 110.51 against 105.12, 5.4
degrees.

**That is safe for a technique file and would not be for a filmed athlete.** A
technique fixes the grip and the ball, so every drill in this library is
compared at one hand placement and the term cancels. A person filmed holding the
same ball at the same height with her hands differently placed would read up to
11.5 degrees apart on a checkpoint meant to be about height. Anyone pointing
this measure at a capture should read this row first.

**What a height measure would guard.** Discriminating height well above the
crown: a lob, whose cue is "as high as arm can go" rather than "above your
head", and any later band that had to separate two high positions. Refer to
`docs/LOB_AUTHORING_BRIEF.md`.

**A BALL POSITION AHEAD OF THE CHEST PLANE**, in centimetres, at the graded
phase, with its unit declared. This one has been wanted twice and refused twice.

The manual warns "Keep hands where they were with catch, don't pull ball back
behind head". A checkpoint for it was authored on `netball_chest_pass`,
mutation-tested and DELETED: moving the ball 13.2 cm shifted the largest
measured angle 5.1 degrees, at the threshold this project calls meaningless.

It was authored again on `netball_overhead_pass`, appeared to work, and was
DELETED FOR A WORSE REASON. Swept against its band, a 26 cm pull-back — the ball
well behind her head — PASSED at 114.99, and the whole range from 0 to 26 cm
moved the measure 7.7 degrees. The failure at 27.7 cm was a SOLVER BASIN FLIP:
across 26.8 to 27.2 the elbow's z ran +8.5 to −12.0, swinging 20.5 cm from in
front of the shoulder to behind it, while the wrist moved 0.2 cm and the ball did
not move at all. Refer to that drill's `pullBackNote`, and to
`docs/CLAVICLE_ARTEFACT.md` for the same shape in another drill.

**So the manual's own warning has NO instrument on either pass**, and an angle
cannot stand in for it. The cue is a DISTANCE and the engine grades ANGLES. Both
rows here are the same shape: the manual cues lengths, and a length needs a
measure whose unit says so.

**A caution for whoever builds them.** `netball_overhead_pass` was nearly
shipped with a checkpoint that passed a single mutation and measured nothing it
claimed. The proof method changed with it: a failing mutation is now a SWEEP of
at least three displacements, the measure must move progressively, and the joint
positions must move continuously at the crossing. A single-point failure beside a
joint discontinuity is a basin. That drill's `mutationNote` carries the eight
sweeps.

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


## FIVE coaching checkpoints now fail, and no number was changed to stop them

**It was four until PR #19 and the table below said four for two days.** The
content lane found the fifth as an undocumented failure, with two instruments,
before anyone recognised it as a deliberate flip. It is:

| drill | phase | measure | measured | band |
|---|---|---|---|---|
| 1 Hand Snatches to Other Hand | contact | `leftElbowFlexionDegrees` | 146.01 | 30 to 120 |

**146.01, not the 146.13 first written here.** Refer to "Five figures in this
file were stale" below.

That checkpoint read 89.64 and passed. The free-hand fix moved the waiting hand
to the chest, where the library holds a ball, and the elbow folds to 146.01.
**Erin Burger marked that same checkpoint NOT met**, so the engine moved from
disagreeing with her to agreeing with her, and the band is untouched. Refer to
`docs/COACH_REVIEW_2026-08-30.md`. A verdict that flips toward a coach is still
a verdict that flips, and it belonged in this table on the day.

## AND THE DIAGNOSIS BELOW IS SUPERSEDED: the bands were never wrong

The four release failures were read here as bands authored against a solve
whose arm never extended. **They are not.** All four are WITHIN their own bands
at the moment the ball actually leaves her hands, and outside them only at the
frame they are graded on, which is phase 1.000 — the end of the follow-through.

Measured independently by this lane, with two instruments for "when does the
ball leave" that agree to eight thousandths of a phase: the technique file's
declared `release.atPhase`, and the SOLVED possession state's first `released`
frame.

| drill | graded at | ball leaves | band | at the graded frame | at the release |
|---|---|---|---|---|---|
| `deflect_high` send_on | 1.000 | 0.800 / 0.805 | 45 to 115 | 35.83 out | **98.71 in** |
| `hooks_jump_pull_in` release | 1.000 | 0.950 / 0.953 | 50 to 120 | 49.85 out | **99.25 in** |
| `two_hand_catch_chest` release | 1.000 | 0.920 / 0.928 | 55 to 115 | 41.04 out | **98.06 in** |
| `two_hand_snatch_straight_back` return | 1.000 | 0.900 / 0.907 | 45 to 105 | 41.00 out | **86.76 in** |

**Erin marked all three of her release cues MET**, which is consistent with a
coach judging the release and an engine grading the follow-through.

**Retiming would not create a blind phase, but the margin is thinner than
first printed.** Moved to the declared release, each of the four still differs
from the phase before it by **7.28 to 45.36 degrees**, against a 5.0 threshold.

| drill | as graded today | retimed to the release |
|---|---|---|
| `deflect_high` send_on | 70.16 | **7.28** |
| `two_hand_snatch_straight_back` return | 83.78 | 37.34 |
| `hooks_jump_pull_in` release | 91.48 | 42.08 |
| `two_hand_catch_chest` release | 103.34 | 45.36 |

**An earlier version of this said "21.46 to 45.49", and it was the wrong
measurement rather than a wrong tip.** It compared the two frames on EVERY
measured angle. `MovementDefinition.separation` — the rule this project already
has — compares them only on the measures THAT PHASE GRADES, which is the right
question: an angle no checkpoint reads cannot tell a coach two phases apart. On
the deflect the widest graded difference is 7.28 degrees where the widest
difference on any angle is 21.46.

The conclusion is unchanged and the comfort is not. Every drill clears the
threshold; the deflect clears it by 2.28 degrees, and the morning should hear
that rather than a figure three times too generous.

**Nothing is retimed here.** The question for the coach morning changes from
"should these bands be widened?" to "which frame is the release?", and that is
a better question with both lanes' instruments behind it. The content lane's
new pass anchors its release AT the release by the orchestrator's ruling, so
the library will hold both patterns until the morning decides.

## The record of the four, as it was diagnosed

The engine sends a released ball back to the passer at the speed it came in,
so the athlete now extends through the pass. She did not before: the ball
drifted out of her hands at 0.13 to 0.57 m/s and her arms stayed folded. At
the last frame the hand now reaches 0.93 to 0.95 of full extension, where it
used to sit at 0.70 to 0.75.

The same checkpoint fails on all four releasing drills:

| drill | phase | leftElbowFlexionDegrees | band | as first written |
|---|---|---|---|---|
| Deflects, High | send_on | 35.83 | 45 to 115 | 35.73 |
| Hooks, Jump and Pull In Ball | release | 49.85 | 50 to 120 | 49.98 |
| 2 Hands Catch | release | 41.04 | 55 to 115 | 41.05 |
| 2 Hand Snatches and Straight Back | return | 41.00 | 45 to 105 | 40.81 |

**The last column is what this table said until 2026-09-01, and every row of
it was stale.** The verdicts never changed and the point of the entry is
untouched: the same checkpoint still fails on all four. The figures are
corrected against two instruments that agree, the clip verifier and a direct
solve, and the old ones are kept beside them rather than deleted.

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

## RESOLVED: the pole's frame is now orthonormal

**Fixed by Gram-Schmidt.** `down` is kept and `out` is orthogonalised against
it, not the other way round, because `down` is where the angle is measured
FROM: orthogonalising `down` instead would silently redefine what zero means.

Swept over 576 reach directions, calling the solver's own `pole_target` rather
than a copy of it, the deviation from the elbow circle is **0.000000 cm**,
including on the family where the raw `out . down` reaches 0.991. Before, the
worst was 12.30 cm and the median 4.02.

**The feared consequence did not happen, and that is the finding.** This entry
said the angle would have to be re-read and every table depending on it
regenerated. The two-handed calibration mean moves from **36.58** to **36.43
cm**, which is inside the 0.5 cm the test records, so
`ELBOW_POLE_ANGLE_DEGREES` needs no re-read at all. One item leaves the coach
conversation rather than joining it.

Read that twice before taking it as good news. The angle was bisected through
the whole SOLVE rather than derived from the geometry, so it had already
absorbed the basis error. A calibration robust to a 12.30 cm geometry fault is
robust because it is loosely coupled to the geometry, which is not entirely a
compliment.

**What it does move**: 54 graded values, no verdicts flipped, worst
`hooks_outside_hand` facing_away left knee 51.13 to 35.40 and its pull_in trunk
lean 1.90 to 12.05. Those are a different pose rather than a defect: measured
across that drill the trunk lean's worst single-frame step is 0.12 degrees and
the knee's 0.33, both flat throughout. It is still a change to the library's
look and goes to Marius as one.

**And the largest move on that drill is not graded at all.** The RIGHT knee at
contact goes 50.3 to 74.2 degrees, about 24, and it is not a checkpoint on
`netball_hooks_outside_hand`, so no graded figure carries it. It is smoother
than before rather than rougher — its worst single-frame step falls from 2.03
degrees to 0.15, and it holds 72.9 to 75.0 across the whole drill. The look
record should carry the whole body, not only the parts a checkpoint happens to
name.

**On the hand-orientation rows**: 105 is the count above 0.05 degrees. At the
precision the receipts are written to, 177 rows move. Both are the same change
read at two thresholds, and the larger one is the honest headline.

**A reach in her coronal plane now correctly gets NO pole.** There `out` and
`down` collapse onto the same line once the reach axis is removed, so there is
no circle point to name and `pole_target` returns None. The skewed basis
emitted a point anyway. Verified directly rather than by sweep: six coronal
directions all return None, and one two hundredths off the plane still returns
a point, so it is the plane and not a region. A grid sweep MAY MISS IT ENTIRELY, and
whether it does depends on the grid: this lane's sampled at half-step offsets
and stepped over the plane, finding 0 of 576, while the reviewer's landed on it
and found 48 of 576. Neither count is a property of the code. Both are
properties of a grid, which is why the direct test is the one to trust.

`pole_target` now lives outside `elbow_poles` so the guard calls the same code
the solver calls. The measurement that first found the 12.30 cm reimplemented
the basis in a script, which is a second copy of the thing under test.

The guard lost a clause from its name. It was
`test_the_target_is_on_the_elbow_circle_where_the_basis_is_orthogonal`, and its
reaches ran along one axis, where `out . down` is exactly zero and the flaw
vanishes. Its directions are now deliberately oblique, and a second test
asserts they are — otherwise a later edit could make them axis-aligned again
and the guard would pass for the old reason.

## The record of it

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

## RESOLVED: the snap check now sees a stall, and does not see a turn

**The instrument is rebuilt and lives in `snap_report.py`**, stdlib only, so a
test of it runs wherever the tests run. It used to sit in `possession_solve.py`
behind a solver import, which is why an instrument this wrong went this long
with no test at all.

Three faults, two recorded here before and one found while fixing them:

- **It divided by the MEAN of two neighbours**, breakdown point zero. Now the
  MEDIAN over three steps either side, excluding the frame itself.
- **It could not see a stall.** Its skip-gate exempted any frame whose
  neighbours were under 0.2 degrees, which is a snap out of stillness, and its
  significance gate required the STEP to be large, which a stall never is. The
  ratio is now symmetric and a frame is judged when EITHER its step or its
  neighbourhood is meaningful.
- **A stall test with no further condition flags every TURNING POINT.** An
  angle that reverses has a step through zero at the reversal. The first
  version of the fix scored 32.75 on `netball_double_foot_landing` for an elbow
  that simply stopped folding and began to open. The discriminator is the SIGN
  of the steps either side, and at an edge the one neighbour that exists
  decides — a version that returned "same direction" wherever a neighbour was
  missing reported the jump hooks' last-frame reversal as a stall of 7.74.

**`SNAP_RATIO` stays at 3.0 and was NOT recalibrated.** The entry said to
recalibrate once the denominator was robust. Having made it robust, the honest
reading is that 3.0 separates real hitches from ordinary movement, which is
what a threshold is for. Moving it to make today's library pass would be tuning
the threshold to the answer.

**So four rows now read over threshold, and they are findings rather than a
broken build.** Nothing in the test suite gates on `SNAP_RATIO`; `proof.py` and
`retarget.py` are reports.

| drill | ratio | kind | where |
|---|---|---|---|
| `two_hand_snatch_straight_back` | 9.42 | stall | right elbow, frame 88 |
| `two_hand_catch_chest` | 8.52 | stall | left elbow, frame 90 |
| `deflect_high` | 7.72 | stall | left elbow, frame 70 |
| `hooks_jump_pull_in` | 3.30 | stall | right elbow, frame 102 |

Two are one-frame pauses in the middle of a monotonic movement — the chest
catch runs -4.15, then -0.96, then -12.06 degrees per frame. One, the deflect,
is a different shape: the elbow is nearly still for six frames and then launches
at 10 to 13 degrees per frame, and the statistic names the last quiet frame
rather than the first fast one. Both frames are honest names for a change that
happens between them.

**AND THE HITCH THIS ENTRY RECORDED IS GONE.** It read "on the `wide` variant of
`netball_two_hand_snatch_pull_in` the elbow steps 8.50, then 0.19 at the contact
frame, then 4.41". Measured now, those steps read 11.36, 8.28, 3.92 — no stall.
Some later pack closed it, and nobody noticed because the instrument that would
have said so was the broken one.

## The record of it

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

**SUPERSEDED IN PART on 2026-09-01 by the hand mirror fix (`fde5d5a`).** Every
figure in this entry — the 44.60 one-handed average, the 36.57 two-handed one
and the 37.3 degree sweep — was measured on a build whose right hand was
anti-mirrored.

**AND THAT SUPERSESSION WAS ITSELF WITHDRAWN on 2026-09-02.** It said the
one-handed drills "have since come DOWN to 39.49 against a two-handed 36.40,
so the two populations now differ by 3.09 cm where they differed by about 20",
and that "the deferral below was taken on two populations that no longer exist".
**None of that was true.** The 39.49 came from a second solver basin on one
drill; with the locked parameters pinned the one-handed drills read 54.83 and
59.96, and the two groups are about 21 cm apart as they always were. The
figures in the entry above are still old, and the reason they are old is the
build they were read on, NOT a change in the athlete. Refer to
`docs/CLAVICLE_ARTEFACT.md`.

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


## RESOLVED: an archive of a graded build now has to be made on purpose

Raised on 2026-08-31 when the receipts Erin Burger graded turned out to have
survived by luck: the live `poc-output/library/` was overwritten four times in
one session, and the set existed only because somebody had copied it aside for
an unrelated reason.

`build_stamp.py` closed half of it — a receipt can now name its build.
`archive_receipts.py` closes the other half, which is that a stamp makes an
archive self-describing and does not make one exist.

Run it BEFORE a grading pack goes out. It refuses a directory holding more than
one build, refuses to overwrite an existing archive, and refuses an empty
source; it allows a dirty-tree build and says so loudly. Refer to "Before a
grading pack goes out" in `spikes/README.md`.

**One defect worth keeping, because fixtures did not find it.** The first
version took every `netball_*.json` as a receipt. `proof.py` writes
`{movement}.proof.json` beside them, it carries no stamp, and the one-set check
therefore refused every real archive on the first attempt. Twelve tests against
hand-built fixtures all passed; running the script once on the real library
found it immediately. The fixtures were built from what the code expected to
see rather than from what the directory holds.

## The ball speed for the whole library is one undocumented constant

Raised on 2026-08-31, from a file-level audit that needed no solver. Measured
in `docs/BALL_SPEED_PROVENANCE.md`.

The athlete returns the ball at the speed it was thrown at her, which
`possession.return_velocity` derives from the passer's flight. That reuse
works, and every drill in the library derives 600 cm/s from a flight that
`author_flight.DEFAULT_SPEED_CM` authored at 600 cm/s. Eight drills, flights
from 0.219 to 0.315 seconds, one speed.

**The agreement is a tautology.** It proves the derivation and says nothing
about the value. 600 cm/s has no coach, no measurement and no source, and its
own comment says a game pass is faster. Nothing grades it.

Two questions for the coach morning, neither of them a code change: is 6.00
m/s a drill feed, and should she return the ball at the pace it arrived. The
second is already marked PROVISIONAL in `return_velocity`.

The failure mode that docstring warns about — an early hold making her throw
harder — does NOT fire today. Every drill has a real parabola.

## The four contact hitches are one sub-frame timing defect

Raised on 2026-09-01. Proven in `docs/RELEASE_SEAM.md`, no solve required.

The declared release phase is authored as a round number and never lands on a
frame. The last carry key sits at that phase, and the release frame is the
first frame past it, 24 to 65 per cent of a frame late. On that one frame the
carry has already stopped at its key AND the flight measures its elapsed time
from the frame, so it has not started. The ball moves the fraction of a carry
step that fits before the key, and nothing else.

Predicting the step as the carry truncated at the key reproduces all four
measurements to 0.000000 cm.

**The leading hypothesis was refuted by the same measurement.** The chest
contributes exactly 0.0000 cm on three of the four drills. Only
`hooks_jump_pull_in` has a chest term, 0.33 cm, because it is the drill that
JUMPS: its chest rises 20.02 cm while it turns 0.00 degrees. It does not
affect the mechanism.

**This corrects what was first published here.** The claim was that the drill
turns, and it does not. The drill that turns is `hooks_outside_hand`, 4 to 48
degrees, and it never releases the ball, so it was never in that table. The
error was found on 2026-09-01 by reading `trunkTurnDegrees` while widening the
reference curves — a measure that had no curve when the seam was written.

The change this implies is to time the flight from the release key rather than
the release frame. It turns the stall into a ramp on all four drills and moves
the following frame by less than 0.04 cm. **Not made.** The graded values must
be measured first, and that needs a solve.

## The sub-frame defect is at the athlete's release only

Raised on 2026-09-01. Swept in `docs/SEAM_SWEEP.md`, no solve required.

Three regime boundaries exist. Contact is clean on all eight drills, and the
incoming pass is clean on all eight. Only the athlete's release is affected,
on the four drills that release the ball.

**Contact is clean structurally, not by luck.** It is chosen by a distance
test on frames, so no authored phase falls between two frames, and the carry's
first key is the flight's own position at that frame. **The arm constants are
calibrated at contact, and contact is unaffected.**

**The incoming pass is clean because it is sampled by phase.** Its release key
misses a frame boundary by 11 to 85 per cent and loses nothing, because the
flight answers where the ball is at a phase.

THE PRINCIPLE: a regime sampled as a function of phase is immune; a regime
integrated forward from a frame index is not. The outgoing flight measures its
elapsed time from the release frame rather than the key. The same physical
event is handled both ways in one file, and the correct pattern sits a few
lines from the defective one.

## Five figures in this file were stale, and the artefact beside them was not

Raised on 2026-09-01, from the two-records question: this file recorded the
one-hand-snatch contact elbow as 146.13 and the clip pipeline read 146.01.

**There is no divergence between two pipelines.** A direct solve, the clip
export and the clip baseline all read 146.01. The figure in the prose was
simply old.

**It was stale on arrival.** `2d82299`, the pole basis orthogonalisation,
moved that checkpoint from 146.13 to 146.01 at 17:50 and updated
`clip-baseline.json` in the same commit. `1df5e52` wrote 146.13 into this file
at 19:39, an hour and three quarters later. The number was copied from an
earlier reading rather than measured when it was written.

Four more were found by the same check, in the table of failing release
checkpoints: 35.73, 49.98, 41.05 and 40.81 against 35.83, 49.85, 41.04 and
41.00. All four corrected, with the old values kept beside them. No verdict
changed and no conclusion in this file depended on the third decimal.

**THE ARTEFACT WAS CORRECT THE WHOLE TIME.** `clip-baseline.json` matched the
engine exactly, because it is regenerated by the commit that moves it and a
gate reads it every run. The prose had neither. That is
"unmeasured is the risk" wearing documentation instead of code: a number under
an instrument stays true, and a number copied into a sentence goes stale in
silence.

**What to do about it is a convention, not a test.** A figure in prose should
name the build it was read on, the way the evidence documents in `docs/` now
do — "Measured on `9cf25a4`". A reader can then tell whether a number is
current instead of assuming it. Checking every figure in this file
automatically was considered and rejected: it would need a solve per assertion
and would break on every deliberate change, which is how a guard becomes noise
and then gets deleted.


## CLOSED: the right hand now opens the way the left one does

Marius ruled on 2026-09-01 that the fix ships, calling it a bug. Shipped in
`fde5d5a`. The six pieces of evidence are in `docs/HAND_MIRROR_EVIDENCE.md`,
which carries the closure and the measured cost.

Both hands now fan 14.37 cm and every fingertip is the reflection of its
opposite. The shipped fix was proved byte-identical to the previewed one on
all eight drills, worst difference 0.0000000000, against a capture taken
before the source changed.

**47 of 69 graded values moved and no verdict flipped.** The failing set is
unchanged in drill and phase; its figures on this build are 35.78, 49.98,
146.01, 40.89 and 40.86, and they name `fde5d5a`.

**THREE THINGS THIS OPENED, all recorded rather than absorbed.**

1. **WITHDRAWN 2026-09-02: "her ready stance changed".** This entry said
   `hooks_outside_hand` starts 15.44 degrees turned where it started 48.23, and
   that she had been turning her shoulders 48 degrees to compensate for the
   broken hand. **She had not.** That drill has two solved poses about 33
   degrees apart, and the parameter set that shipped reached the other one. She
   stands at 48.22 degrees under the correction. Refer to `docs/CLAVICLE_ARTEFACT.md`. The claim was relayed to
   Marius and to the rendering lane and is withdrawn to both.
2. **WITHDRAWN 2026-09-02: the library-content gap.** There was no gap. The
   drill turns 48.22 degrees while a hand waits, so the real library exercises
   the waiting-hand rule as it always did. The inverted clause has been
   restored to its original form and the hand-built fixture is kept as belt and
   braces. The coach-agenda item is STRUCK.
3. **WITHDRAWN 2026-09-02: the populations converged.** They never converged.
   The 3.09 cm reading was the same artefact: `hooks_outside_hand`'s contact
   elbow width read 19.01 cm under a distorted clavicle and reads 54.83 once it
   is pinned. The two populations are 20.96 cm apart, as they were before, and
   the deferred pole-angle question keeps its original two-population form.

**The mirror preview variant is retired.** `preview_variants` is coach-facing,
and a variant rendering the shipped build while a page labels it the
alternative is the byte-identical failure that module was already caught
committing once. The regression is guarded closer to the rig instead.


## The docs-wide stale-figure sweep, and what it could not reach

Run on 2026-09-02 against `ac240b2`. The item was logged as "unclaimed, not
clean" after five stale figures were found in this file by following one
question. This is the wider pass.

**The corpus.** 16 documents, 5113 lines, 1130 decimal figures.

Re-measuring 1130 figures is not possible and would not be useful: most sit
inside an entry describing a past event, and are correct as the record of what
was read then. So the sweep checked every class that HAS a current source of
truth, and says plainly what it left alone.

### What was checked, and what it found

| class | checked | wrong |
|---|---|---|
| code constants cited by name in prose | 10 citations of 4 constants | **0** |
| bands quoted beside a measure name | 13 | **0** |
| the five failing checkpoints against `clip-baseline.json` | 5 | **0** |
| the open-defect figures in `REQUIREMENTS.md` | 2 | **2** |
| documents carrying figures with NO build named | 16 documents | **2** |
| a sample re-measured from the unstamped coach review | 7 | **7 moved** |

### The two that were wrong, and they were the ones presented as CURRENT

`docs/REQUIREMENTS.md` lists two open anatomy defects. Both figures were stale,
and both understated the defect:

- **The elbows.** Recorded as 27.3 cm against the reference photographs' 38.6,
  a gap of 11.3 cm. On `ac240b2` the six drills that put both hands on the ball
  average **36.40 cm**, a gap of **2.20**. The defect is four times smaller than
  the document claimed. The 27.3 figure predates the elbow pole becoming an
  angle.
- **The joint limit.** Recorded as one frame at 0.715 degrees. On `ac240b2`
  `netball_hooks_outside_hand` breaches on **98 of its 98 frames, worst 2.3355
  degrees on `l_clavicle_rx`**.

**The mirror fix did not cause the joint-limit breach**, and that was measured
rather than assumed: across that change the same drill breached 98 of 98 frames
before it too, worst 0.4990 degrees on `l_clavicle_rz`. The breach is older
than the fix. The fix made the worst overshoot 4.7 times larger and moved it to
a different axis. No other drill in the library breaches at all.

**Nothing in the test suite reads it.** `check_joint_limits.py` is a separate
task and it exits 1 today while the suite passes 564 tests. A defect recorded
as rare and small, which is neither, and which no gate reports.

### The class that matters more than any single figure

Two documents carry figures and name no build: `REQUIREMENTS.md`, corrected
above, and `COACH_REVIEW_2026-08-30.md`, which holds **113 figures** and is the
document the coach morning most depends on.

That review is NOT rewritten. Erin's marks and her words are the record of a
real event. What it lacked was the build its engine figures were read against,
and it now carries that as a header. Seven of its rows name a drill, a phase, a
measure and a value, which is enough to re-measure. **All seven moved**, by 0.02
to 0.47 degrees. No verdict or argument in it changes. The point is that not
one was unchanged: three fixes have landed since it was written, and small
universal drift is what that looks like.

### What this sweep did NOT do

- **It did not re-measure the other 1100 figures.** Most name no drill, phase
  and measure together, so there is nothing to re-measure them against without
  guessing what they meant.
- **It did not check `HANDOFF_RENDERING.md`'s 197 figures** beyond the stamp
  test. They belong to another lane's instruments.
- **It did not verify Erin's marks**, which are not engine readings.
- **It found no wrong band and no wrong constant**, which is a real result and
  not an absence of effort: those two classes are mechanically checkable and
  they are clean.


## The joint limits were exceeded on a parameter the model had locked

Raised 2026-09-02 by the docs-wide sweep, ruled a DEFECT rather than a judgement
call, and fixed. Measured in `docs/CLAVICLE_ARTEFACT.md`.

Four parameters have a range of ZERO WIDTH — the model says they must be
exactly zero — and all four were enabled for the solver: `l_clavicle_rx`,
`r_clavicle_rx`, `l_foot_lean1`, `r_foot_lean1`.

**The limit term is soft**, so a locked parameter left enabled sits wherever
the other terms drag it. On `netball_hooks_outside_hand` the left clavicle sat
2.34 degrees outside a range of zero on all 98 frames. **No other drill moved
that parameter at all**: their `l_clavicle_rx` maximum is 0.000006 degrees.

**A CORRECTION.** An earlier version of this entry said the other drills pulled
the same parameter 0.06 to 0.10 degrees. They do not. Those figures are
`clavicle_RZ`, a different axis with a real range, read off the limits table.
Two axes of one joint were conflated.

**The fix removes freedom rather than adding a constraint**, and touches no
weight: those four are excluded from the enabled set. `check_joint_limits` now
passes at exit 0 with a worst overshoot of 0.1033 across the library. 42 graded
values move, no verdict flips, and the largest change to any grip is 2 mm.

**THE MECHANISM FIRST PUBLISHED FOR THIS WAS WRONG.** It said the solver had
absorbed the athlete's turn into a clavicle rotation the body cannot make. A
control refutes it: excluding an UNRELATED axis with a real range, `head_twist`,
undoes the stance change identically, and in those solves the still-enabled
`l_clavicle_rx` sits at 0.0000 degrees. A 2.34 degree rotation cannot hold a 33
degree turn. Refer to the entry below on the two basins.

**IT ALSO REVERSED FOUR PUBLISHED FINDINGS**, three of which had left this
repository. The stance change, the population convergence, the "one-handed
drills are not a population" claim and the library-content gap were all read
from the second basin. Refer to `docs/CLAVICLE_ARTEFACT.md` for the three-state
table that settles it and for the corrected cost of the hand-mirror fix. Its
reported largest graded move of 23.16 degrees belongs to the basin change; the
3.09 that replaced it is a bistable knee, and the fix's largest move away from
the knee channel is 0.17 degrees.

**Two guards found it**, and both had been read as reporting something about the
athlete: the elbow-pole tripwire and the turned-drill clause in
`test_waiting_hand.py`. They went red when the axis was pinned, and reading why
is what produced the finding.

**Nothing in the gate read `check_joint_limits`.** It exited 1 while the suite
passed and the clip gate passed. That is now a suite row in
`test_locked_parameters.py`.

**How long, precisely, because two breaches are easy to conflate.** The 0.499
degree breach on `l_clavicle_rz` — a real axis — was present at `716b3eb`,
along with one frame of `two_hand_catch_chest` at 0.251 degrees on
`r_thumb2_rz`. The 2.34 degree breach on the LOCKED axis dates from `ac240b2`
at 14:04 on 1 September: **one day, not weeks.**


## One drill has two solved poses 33 degrees apart

Found 2026-09-02 by the review of the locked-parameter fix, and it is the
finding the fix uncovered rather than the fix's own subject.

`netball_hooks_outside_hand` reaches either of two solutions. They differ by
about 33 degrees of ready-stance shoulder turn — 48.22 against 15.44 — and by
about 36 cm of elbow width at contact. **Which one the solver reaches is decided
by the COMPOSITION of the enabled parameter set, not by any one parameter in
it.**

Excluding the locked clavicle pair reaches the 48 degree pose. So does
excluding `head_twist`, which is an unrelated axis with a real range. So does
excluding either foot alone. The exact 54-parameter set that shipped as
`ac240b2` is the only one measured that reaches the 15 degree pose.

What differs inside that pose is not the clavicle. `spine_twist0` reads −11.56
degrees at frame zero there, against +51.57 — saturated at its own limit — in
every other state, and the root rotation is wound to 1030, 769 and 683 degrees.

**Nothing here is a defect with a fix attached.** Both poses satisfy the
solver's terms. The finding is the FRAGILITY: a drill whose look changes by 33
degrees depending on which parameters are enabled has no single answer, and
every measurement taken from it inherits that. It is the reason four published
findings had to be withdrawn.

**What it costs to leave alone**: any change to the enabled set — adding a
parameter, removing one, or a model update that changes a range — can move that
drill's look without touching a weight, a key or a band. Nothing would report
it, because the two-handed mean does not move and no verdict flips.


## The wrist moves after the ball has gone, and could not drive it anyway

Raised 2026-09-02 from Marius watching the chest-catch player beside the real
footage. Measured in `docs/WRIST_AND_PACE.md` on `02b25cd`.

The hand bends against the forearm by 22 to 35 degrees through every release,
so the wrist is NOT still. **Every one of those movements reaches its greatest
speed AFTER the ball has left**, by two to four frames. A flick drives the ball
and must peak at or before the release; this is a follow-through.

**And no wrist motion could drive it.** `return_velocity`'s inputs are the ball
track, the stance frame at phase 0, the ball's carried position and the frame
timing. No property of the hand enters, and the carried position follows her
chest rather than her wrist. **A flick cannot be expressed in the possession
model as it stands** — it is not an authoring gap.

The instrument was proved before the reading was believed: 40 degrees planted
on `wrist_rz` reads 2503.6 deg/s against the shipped 278.6, nine times over. It
did not read zero, and the first expectation — that the wrist would not move at
all — was wrong.

**THE CONTROL IS AXIS-DEPENDENT and this sentence must say so.** The same 40
degrees on `wrist_ry` reads no change at all on that hand, and an independent
run puts forward twist at 0.7 to 1.5 times. The measure sees FLEXION and is
nearly blind to PRONATION, so a thumbs-down chest-pass finish would read as
almost nothing. "A zero would have meant something" holds for flexion, the
primary component, and is WEAK for pronation.

**A RATE HERE IS A PLAIN ONE-FRAME DIFFERENCE OVER THE TRACK'S 1/60 SECOND
FRAME PERIOD.** An earlier version divided by `solve_movement`'s
`secondsPerFrame`, which holds `time.perf_counter()` over the frame count — the
SOLVER'S WALL-CLOCK COST, not a frame duration. Those rates were degrees per
second of computer time and moved between runs. The field's name invites that
reading and it caught me; anything else dividing by it is measuring the
machine.

The manual's cue for this drill is "with wrist and hands pass the ball", and
this file already records that cue as having no instrument. This is that gap,
measured.

## The pace has no author either

Same document, same day. The engine takes **2.24 times the athlete's time** on
the stretch from ball contact to the deepest point of the hold: 0.7275 s
against her median 0.325, from three strip-proved repetitions. It plays that
stretch at about 45 per cent of her speed.

`frames` and `framesPerSecond` are typed in each motion file and nothing
derives or measures them. The RATE is documented — a `rateNote` explains 60
rather than 24 and says "nothing about the movement changes with the rate" — so
the rate was a resolution decision that explicitly disclaims pace. **The frame
count, which IS the pace, carries no note anywhere**, and five of the eight
drills share 98 frames exactly.

That is the third property of the movement that nothing authors and nothing
grades. The other two are the wrist above and the ball speed, whose 600 cm/s
constant at the manual's own 7 m produces a ball peaking at 302 cm against a
305 cm goalpost.


## A basin flip now reports itself, on one drill

Added 2026-09-02 after the two-basin finding. `test_waiting_hand.py` records
every drill's ready-stance shoulder turn and pins it, so a change of basin
names the drill instead of arriving as four wrong findings.

Nothing reported the last flip for a day. It moved no verdict, and it moved no
aggregate — the two-handed contact mean read 36.40 to 36.43 through all of it —
so every gate watched a quantity the flip did not touch. Two guards eventually
caught it by accident, and both had first been re-pointed as though the library
had changed.

**It is a pin and not a fingerprint, deliberately.** A pose fingerprint would go
red on every legitimate change: the hand fix moved 46 graded values and the
locked-parameter fix 42. A guard that fires on all of those is noise within a
week and deleted within two. What discriminates is the GAP — drift here is
hundredths of a degree and a flip is 33 — so the tolerance is 2 degrees, far
above one and far below the other.

**ITS BLIND SPOT, WITHDRAWN 2026-09-02.** This entry said: "Seven of the eight
drills stand square, at 0.5 degrees or less, and would read near zero in EITHER
basin. This catches a flip on the drill we have seen and may miss one
elsewhere."

**The "may" was wrong and the reasoning behind it was wrong.** Those drills do
not stay near zero in either basin — their basins differ BELOW THE HIPS, where
this pin does not look. Refer to "The lower body has no stable solution" below.

**And the interval matters.** This pin shipped in PR #57 watching eight drills.
It never watched `netball_chest_pass`, because the stance was recorded after a
check that skips any drill whose contact frame is 0 — which is every drill that
STARTS with the ball. So from PR #57 until 2026-09-02 the guard stood over no
ball-in-hand drill at all, and nobody should read it as having done so.

The companion idea, a general bound on root winding, was investigated
separately and closed with no action.

Mutation-proven: handing the locked parameters back flips that drill to 15.44
and the pin reports it by name, with the 32.78 degree gap and a pointer to
`docs/CLAVICLE_ARTEFACT.md`.


## The root winding is not a defect, and the guard proposed for it would be wrong

Investigated 2026-09-02 and CLOSED WITH NO ACTION. Recorded so it is not raised
again.

The two-basin finding noted that in the retired basin (state B, measured on
`ac240b2` in `docs/CLAVICLE_ARTEFACT.md`) the root rotation was wound to 1030,
769 and 683 degrees. I proposed a general bound on root winding
as a companion guard, on the reasoning that nearly three full turns is not a
pose anybody wants. **Three measurements say otherwise** (all measured on
`7fb351c`, whose solve of this drill is identical on `cc43666`).

1. **The root rotations are unbounded by design.** They carry no recorded limit,
   which is correct for a free root.
2. **The pose repeats modulo 360.** Adding a full turn to any root rotation
   moves the skeleton by 0.00002 cm. A wound angle is the SAME POSE described
   differently.
3. **Nothing on the clip or coach boundary reads the raw angle.**
   `export_tactics_clip` states in its own docstring that every number it
   writes is read off the solved joint POSITIONS, and the coach animation and
   Blender job exporters read positions too, so a wound angle cannot reach the
   clip contract or a coach. (`build_library` does write the raw parameter
   track into a derived, uncommitted GLB; the limit checkers read the track
   for overshoot, which is inert for a limitless root.)

On the shipped build (`7fb351c`) there is no winding to speak of: the root sits
between 119 and 182 degrees on the drill in question, with a largest
frame-to-frame step of 8.81 degrees.

**AND THE GUARD WOULD HAVE BEEN ACTIVELY HARMFUL.** Winding is what keeps an
angle CONTINUOUS from frame to frame. Forcing it into a bounded range would
introduce a jump wherever the value crossed the boundary, and the Tactics
player interpolates between the clip frames it is given — the same reason
`clip_geometry.unwrap()` deliberately lets limb angles count past a half turn.
A bound would have penalised the representation that makes interpolation
correct, in the name of tidiness.

The winding remains a true DESCRIPTION of that basin's parameters and it is
kept in `docs/CLAVICLE_ARTEFACT.md` as such. It is not evidence of a bad pose.


## The lower body has no stable solution

Added 2026-09-02. A pelvis pin was built for this and WITHDRAWN before it
shipped, because building it produced a larger finding than the one it was
meant to guard.

**THE MEASUREMENT.** Between the two configurations that shipped as `716b3eb`
and `ac240b2`, whose difference is the sign on one hand's finger spread, SIX of
the nine drills flipped their pelvis line, worst move 61.45 degrees. Both
states are reconstructed on one engine rather than checked out, which the
paragraph after the table sets out:

| drill | negation, locked free | mirror, locked free |
|---|---|---|
| `double_foot_landing` | −15.65 | 15.69 |
| `hooks_jump_pull_in` | −15.70 | 15.65 |
| `hooks_outside_hand` | 6.05 | −55.40 |
| `two_hand_catch_chest` | 15.66 | −15.66 |
| `two_hand_snatch_pull_in` | 15.67 | −15.66 |
| `two_hand_snatch_straight_back` | 15.67 | −15.67 |

**WHAT THAT TABLE WAS READ FROM, because a comparison without its inputs is not
reproducible.** The pelvis line is `l_upleg` to `r_upleg` in the ground plane,
read from the solved joint positions at FRAME 0.

**The two states are RECONSTRUCTED, not checked out.** Both were solved on the
engine and the definitions at `a775502`, with only two things swapped: the
`spread_fingers` body taken from `716b3eb`, and the enabled set left as it was
before the locked parameters were excluded. So the comparison isolates the hand
change on one engine; it is not two literal checkouts. That matters in one
direction only — `netball_chest_pass` did not exist at `716b3eb`, and it is not
one of the six.

**THE ENABLED SET WAS IDENTICAL ON BOTH SIDES.** This is not the parameter-set
sensitivity already recorded for `hooks_outside_hand`. It is an ordinary code
change — a sign on a finger — mirroring the lower body of six drills.

**THE UPPER BODY IS NOT AFFECTED ON THE EIGHT SQUARE DRILLS.** Across the same
transition their shoulder line moves by at most 0.056 degrees.

**IT IS AFFECTED ON THE NINTH, AND AN EARLIER VERSION OF THIS ROW DENIED IT.**
`hooks_outside_hand`'s shoulder line moves −48.234 to −15.442, **32.79
degrees**. That is the A→B basin change `docs/CLAVICLE_ARTEFACT.md` records and
PR #53 reversed. The claim "the upper body is not affected, at most 0.041
degrees" was read from the square drills and stated of all nine.

So the transition is not "a correct, ruled, shipped change" without
qualification. **The same code change flipped one drill ABOVE the hips and six
BELOW it. The one above was ruled on and reversed. The six below were never
ruled on.** The withdrawal survives the correction and does not depend on the
ninth drill: a pelvis pin would go red on six square drills for a change nobody
has decided anything about.

**WHY THE PIN WAS WITHDRAWN.** A pin on the pelvis with any workable tolerance
would have gone RED on six drills for a correct, ruled, shipped change. That is
the failure this project already names: a guard that fires on every legitimate
change is noise within a week and deleted within two.

**THE MAGNITUDE IS NEARLY STEADY, AND THAT IS NOT WHY IT IS NOT PINNED.**
Across the same transition |pelvis| moves 0.00 to 0.04 degrees on six drills,
**1.99 on `deflect_high`**, **1.06 on `one_hand_snatch_to_other_hand`**, and
49.35 on `hooks_outside_hand`, which goes 6.05 to 55.40. An earlier version of
this row called the magnitude unpinnable, citing the ninth drill. The six
square drills are steady enough to carry a pin.

The reason not to pin it is that the value being held IS THE DEFECT. A drill
that authors nothing asymmetric holds a hip line near 15.7 degrees with square
shoulders. A pin would record the fault as the specification. Refer to the
entry below, which measures the same population with an instrument that reads
zero when the drill is right.

**WHAT IT MEANS FOR EVERY LOWER-BODY NUMBER.** The bistable knee this file
already records and the 6.48 degree left-right knee gap on
`netball_hooks_jump_pull_in`, measured on `c4a7a37` and reached independently
from the graded checkpoints by the content lane, are the same thing seen
through two instruments: the lower body's solution is not
determined, so any figure read from it is a figure from whichever solution that
build happened to reach.

**WHICH CHECKPOINTS THIS GRADES, NAMED.** The library holds 75 graded
checkpoints. **SIXTEEN read a below-the-hips measure, and FIFTEEN of those move
between the two solutions:**

Both columns name the CONFIGURATION they were solved under, not a checkout.

| drill | phase | measure | negation, locked free | mirror, locked free |
|---|---|---|---|---|
| `hooks_outside_hand` | facing_away | left knee | 35.40 | **56.05** |
| `two_hand_snatch_pull_in` | pull_in | left knee | 52.28 | 56.21 |
| `two_hand_catch_chest` | ready | left knee | 49.32 | 52.56 |
| `two_hand_snatch_straight_back` | ready | left knee | 52.60 | 55.69 |
| `two_hand_snatch_pull_in` | ready | left knee | 52.60 | 55.68 |
| `hooks_jump_pull_in` | gather | left knee | 66.84 | 64.01 |
| `deflect_high` | ready | left knee | 46.79 | 45.04 |
| `chest_pass` | ready | left knee | 49.06 | 50.27 |
| `double_foot_landing` | absorb | left knee | 78.25 | 77.04 |
| `double_foot_landing` | absorb | right knee | 77.55 | 78.75 |
| `two_hand_snatch_pull_in` | ready | left knee | 52.60 | 55.68 |
| `double_foot_landing` | approach | left knee | 35.56 | 35.71 |
| `one_hand_snatch_to_other_hand` | ready | left knee | 55.21 | 55.09 |
| `chest_pass` | step | left knee | 59.43 | 59.39 |
| `double_foot_landing` | land | foot height gap | 0.01 | 0.00 |
| `double_foot_landing` | absorb | foot height gap | 0.01 | 0.00 |
| `double_foot_landing` | flight | foot height gap | 0.00 | 0.00 |

The last row is the sixteenth, and it is the ONE that does not move. Both feet
are off the ground in flight, so the gap between their heights is zero in every
solution. The other fifteen move.

**NO VERDICT FLIPS.** Every one of those stays on the same side of its band, so
no drill's pass or fail changes. **But the FIGURES move, by up to 20.65
degrees, and the figures are what a coach is shown.** A knee angle presented to
Erin is one of two answers, chosen by which solution that build reached, and
nothing on the page says so.

The landing drill is the one to look at first: `double_foot_landing` grades SIX
below-the-hips checkpoints, more than any other and more than a third of the
sixteen, and landing is the skill whose coaching is most about the knees. An
earlier version of this paragraph said four, having counted the knees and
missed the three foot-height gaps.

**WHAT IS NOT SETTLED.** Why the lower body is under-determined enough to
mirror, and whether it should be constrained so that it is not. That is engine
work on the solve rather than a guard, and it is NOT proposed here.

The candidates visible from here, named so the question has somewhere to start
and NOT as a diagnosis — none of these has been tested:

- **No lower-body target.** The solve places hands and holds the trunk. The
  legs are asked for a planted foot and a knee bend, and a mirrored pelvis can
  satisfy both.
- **The rest prior pulls toward rest rather than toward the previous frame**,
  which this file already records, so nothing carries a leg's choice forward
  from the frame before it.
- **The foot placement is a height and a plant**, not a left-right position, so
  swapping which leg is forward may cost the solve nothing.

Testing any of those is a separate piece of work and it needs a ruling first.

**A COUNT CORRECTED.** A draft of this entry said "five of the library's square
drills are bistable", taken from a relayed figure rather than measured. What is
measured is four flips under one parameter exclusion and six between the two
reconstructed configurations above. The relayed five is not used.

## Every square drill solves with one knee more bent than the other

**Six drills author nothing that distinguishes left from right, and not one of
them solves as a mirror.** The gap between the knees runs **3.78 to 6.48
degrees**, on every drill, in every solution measured. Nothing asks for it.

Measured on `c4a7a37`.

### The population comes from the files, not from a judgement

A drill is in when NOTHING in its authoring carries a side. Four fields do:
the hand offsets, the foot placements, `turn_degrees` (positive to the
athlete's left) and `root_across` (positive the same way).

| out of the population | what carries a side |
|---|---|
| `double_foot_landing` | feet: approach key asks left 0.150 ahead, right −0.163 |
| `hooks_outside_hand` | a right-hand override, and a 48 degree turn |
| `one_hand_snatch_to_other_hand` | a right-hand override on three keys |

The other six are in: `chest_pass`, `deflect_high`, `hooks_jump_pull_in`,
`two_hand_catch_chest`, `two_hand_snatch_pull_in`,
`two_hand_snatch_straight_back`.

**FIELD PRESENCE IS THE WRONG TEST, AND A FIRST VERSION OF THIS USED IT.**
`hooks_jump_pull_in` writes `footLeft` and `footRight` on all five keys with
IDENTICAL values, and `across` is mirrored per side in `foot_targets` — the
left foot takes `+across`, the right takes `−across`. So identical values mean
a symmetric stance, and the drill belongs in the population. Excluding it on
the presence of the fields dropped the worst member.

### The gap, across three solutions

| drill | negation | shipped mirror | mirror, locked pinned | spread |
|---|---|---|---|---|
| `hooks_jump_pull_in` | 5.78 | 5.81 | **6.48** | 0.70 |
| `deflect_high` | 3.79 | 5.82 | 3.78 | 2.04 |
| `chest_pass` | 4.45 | 4.56 | 4.31 | 0.25 |
| `two_hand_catch_chest` | 4.39 | 4.15 | 4.44 | 0.29 |
| `two_hand_snatch_straight_back` | 3.93 | 4.24 | 4.02 | 0.31 |
| `two_hand_snatch_pull_in` | 4.20 | 4.09 | 4.15 | 0.11 |

**THE 6.48 IS THE CONTENT LANE'S FIGURE.** It reported a 6.48 degree left-right
knee gap on a drill flagged `symmetric`, from the graded checkpoints. It is the
worst member of this population on the shipped build. The two readings are one
instrument at two thresholds, and neither lane knew that when it wrote its own.

### Why this is pinnable where the pelvis line was not

The entry above withdraws a pelvis pin because the pelvis line FLIPS between
solutions — six of nine drills, worst 61.45 degrees — so any pin on it goes red
for a correct change.

**Two mirrored solutions read the same |left − right|.** The magnitude survives
exactly the change that defeated the sign. Across the three states above each
drill moves by 0.11 to 0.70, and 2.04 on `deflect_high`. That is the whole
reason this quantity can carry a guard and the other cannot.

### The flag was reading the hands only

`MotionTrack.is_symmetric()` returned `all(key.left == key.right ...)`. Those
are HAND keys. `double_foot_landing` lands off one foot, its hands match, and
it was published to the library as **`symmetric: true`** — a split stance
declared as a mirror. The flag now reads all four side-carrying fields, and one
drill's published value changes with it. **A ONE-WORD NAME FOR TWO QUANTITIES,
which is the fault class this file already names three times.**

### What was landed

- `test_an_even_drill_solves_evenly` is an **expected failure**. `unittest`
  reports an expected failure that starts passing as a FAILURE, so the day the
  solver answers evenly the suite goes red and someone must come back and
  record what changed. A comment would have stayed true and told nobody.
- `test_no_even_drill_solves_more_crookedly_than_it_did` holds each drill under
  its worst measured state plus one degree. Nothing else reads the DIFFERENCE
  between the knees — the graded checkpoints read each knee against its own
  band, and both can drift together inside their bands while the gap widens.
- **A gap that merely SHRINKS does not pass.** Halving every measured value
  leaves the expected failure failing, which was verified as a mutation.

Four mutations were run: the threshold raised to say "fixed" gives an
unexpected success; a ceiling lowered gives a named failure; the flag reverted
to hands-only makes the population wrong on three tests; and the halved gap
above. The turn and step clauses of the flag change no drill in today's
library, so `test_motion_track.py` plants each of them into a square drill.

### What is not settled

Why the solver returns an uneven athlete for an even question. That is the same
open question as the entry above, and the candidates listed there are the
candidates here. **NOT PROPOSED: constraining the solve.** This entry adds an
instrument and changes no engine behaviour.

