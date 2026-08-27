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

## Three coaching phases cannot fail

`build_library.py` reports these in every receipt under `phaseSeparation`, and
flags the movement rather than calling it ok.

| drill | phase | its measures move |
|---|---|---|
| Double Foot Landing | land | 0.33 |
| 1 Hand Snatches to Other Hand | reach | 0.21 |
| 2 Hand Snatches and Pull In | react | 0.17 |

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

