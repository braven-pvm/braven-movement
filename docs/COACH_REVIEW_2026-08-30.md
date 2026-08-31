# The first coach review, and what the instruments say about it

Erin Burger graded the library blind. Her review is stamped
2026-08-28T10:07:03Z, which is the morning the video spike shipped. This
document analyses it on 2026-08-30. An earlier draft gave the 30th as the date
she graded, which is the date of the analysis and not of the review.

She gave 68 marks across eight drills, 49 met and 19 not, and 8 notes in her
own words. She is an author of the manual the library is built from.

The engine and the coach agreed on 47 of 68 marks, which is 69.1 per cent.

The library holds 69 checkpoints. One went unmarked:
`netball_hooks_jump_pull_in`, gather, `leftKneeFlexionDegrees`. Every figure
here is out of 68, which is what she marked, not out of 69.

This document does three things. It records the free-hand defect her notes
found and the fix for it. It builds the evidence for the three release cues she
passed and the engine failed. It then says, mark by mark, whether an instrument
supports her, supports the engine, or supports neither.

No band was retuned. No file in `spikes/movements/` changed.

## 1. The free hand

Her notes say the same thing about both one-handed drills, unprompted:

> `netball_hooks_outside_hand`: "Hand closes to the passer reacts to the ball,
> touch and control ball to pull ball in to other hand and to chest."

> `netball_one_hand_snatch_to_other_hand`: "Other hand stays ready ... Don't
> want other hand to go away from centre of body towards ball."

Both sentences are about the hand that is NOT on the ball.

### What the engine did

The free hand's target was `ready_point`. That is the CATCHING hand's ready
position: aimed at the passer, at the full waiting distance, because that hand
has to meet the ball. The solver spent it on the free hand as well.

Measured from the solved skeleton, in her own axes:

| drill | free hand ahead of her chest | across sweep |
|---|---|---|
| `one_hand_snatch_to_other_hand` | 0.69 of full reach | 2.8 cm |
| `hooks_outside_hand` | 0.52 of full reach | 22.1 cm |

The hooks sweep is the worse of the two. The aim is at a passer she starts with
her back to. As she turns, that one fixed point in the world crosses her body,
and the free wrist travelled 22.1 cm from her right side to her left.

The solver reached its target every frame. The miss was a constant 15.2 cm on
both drills, which is the grip offset. So the target was wrong, not the solve.

### The fix

The free hand now waits at the last carry key, which is where the ball is
going. Both one-handed drills already author that key identically: across 0,
up 0.10171, ahead 0.55938 torso lengths. It is written in her own frame, so it
follows her turn instead of being crossed by it.

| drill | free hand ahead of her chest | across sweep |
|---|---|---|
| `one_hand_snatch_to_other_hand` | 0.23 of full reach | 3.6 cm |
| `hooks_outside_hand` | 0.22 of full reach | 3.6 cm |

Nothing in `spikes/movements/` changed. No technique file authors a free-hand
place at all, which is why this sat in the solver.

### Corroboration from a drill the fix does not touch

The library's own pose for a hand that holds the ball at the chest is 145.6 and
145.7 degrees of elbow flexion, at 0.30 of full reach. Those are the LEFT and
RIGHT hands of one drill, `two_hand_snatch_pull_in`, which this change does not
alter. The free hand now waits at 145.8 degrees and 0.30. The number was not
chosen. It fell out, and it matches to one decimal.

An earlier draft named `double_foot_landing` as a second drill giving the same
pair. It does not. It reads 142.8 and 142.9 at 0.32 of reach, because its chest
key is authored at ahead 0.58989 torso lengths rather than 0.55938. That is a
different key, so a different answer, and quoting it as the same number was
wrong. It is worth keeping for the opposite reason: a drill with a chest key
5 per cent further out sits 3 degrees further open, which is what a reader
should expect and is a second check that the pose follows the key.

### The solve needed a second pass

The figures in this section describe the intermediate build: the free-hand
target corrected, the second solve pass not yet added. They are the reason for
that pass. On the shipped tip the same frame moves the root 0.00 cm and no
joint more than 0.16, so a reader measuring the tip will not find them.

With the free hand near her chest, frame 12 of the outside-hand hooks stopped
converging. Both wrists ended 24.1 and 32.5 cm from the points they were asked
for, against about 15.5 cm on either side of that frame. The root moved 13.5
cm, the right foot 46.2 and the left 9.4, and the left shoulder elevation went
19.4 to 114.8 degrees and back in one frame. That frame then seeded the next,
and the right wrist never recovered: its miss sat at 22.7 cm for the rest of
the drill instead of returning to 15.2.

An earlier draft said "both feet about 50". That came from a list of the
twelve joints that moved most, which held four right-side foot joints between
46 and 57 cm and no left-side one. The collapse was asymmetric and the pair
above is the honest reading.

The residual says unconverged, not a second valid pose. Frame zero already
solves twice per seed, so every frame now uses that same helper. This removes a
special case rather than adding one.

### The test

`test_free_hand.py` states the rule as a sign about the midline of her own
chest. Her left hand belongs on her left. There is no threshold and no tuned
constant, so nothing can be nudged to make a drill pass. On the code before the
fix it fails, and it names the fault:

    netball_hooks_outside_hand: the waiting l hand reaches -15.1 cm across her
    chest, on the wrong side of her own midline. Its range over the wait is
    -15.1 to 7.1 cm. A hand that waits does not travel across her.

`test_waiting_hand.py` already asks whether a waiting hand is further out than
a reaching one, and it passed throughout. The free hand sat at 0.69 of full
extension and the reaching hand goes to 0.89. That test is not hollow. It is
not tight enough. A hand can be inside every reach limit and still be in the
wrong place.

## 2. The three release cues

She passed three cues the engine failed. All three are the same measure at the
same kind of phase, and all three fall BELOW the band:

| drill | phase | measured | band | outside by |
|---|---|---|---|---|
| `hooks_jump_pull_in` | release | 49.97 | 50 to 120 | 0.03 |
| `two_hand_snatch_straight_back` | return | 40.85 | 45 to 105 | 4.15 |
| `two_hand_catch_chest` | release | 40.85 | 55 to 115 | 14.15 |

The engine reads elbow flexion as 180 degrees minus the included angle, so a
straight arm is zero. A value of 40.85 is an included angle of 139 degrees,
which is a nearly straight arm. That is what an arm looks like at the end of a
pass. Two of the three drills give the identical number.

The first is a band edge and not a disagreement about technique. It misses by
three hundredths of a degree.

**THIS SECTION'S REMEDY IS SUPERSEDED, and the finding is better than the one
it replaces.** It said a band that agrees with her needs a lower bound at or
below 40.85. That is the wrong repair, because the bands were never wrong.

All four release checkpoints are WITHIN their own bands at the moment the ball
actually leaves her hands. They are outside only at the frame they are graded
on, phase 1.000, which is the end of the follow-through. At the release the
same elbows read 98.71, 99.25, 98.06 and 86.76 degrees.

The content lane found it and this lane verified it independently, with two
instruments for "when does the ball leave" that agree to eight thousandths of a
phase: the technique file's declared `release.atPhase`, and the solved
possession state's first `released` frame.

So Erin was judging the release and the engine was grading the follow-through,
which is exactly why she marked all three of her release cues MET. **The
question for the morning is not "should these bands move?" but "which frame is
the release?"** Nothing is retimed without her word and Marius's. Retiming leaves no blind phase, and the margin is worth knowing: each retimed
phase still differs from the one before it by 7.28 to 45.36 degrees against a
5.0 threshold. The deflect is the thin one at 7.28. An earlier version of this
document said 21.46 to 45.49, which measured every angle rather than only the
measures the phase grades — refer to `docs/KNOWN_ISSUES.md`, where the table
and the correction are.

The receipts say the bands are provisional and that no coach set them. This is
the first coach reading of them. The bands are unchanged here, and setting them
is Erin's and Marius's decision.

## 3. Every disagreement, and what an instrument says

Twenty-one marks disagreed on the code before the fix. The free-hand fix
resolved one of them, so twenty remain.

The resolved one is `one_hand_snatch_to_other_hand`, contact,
`leftElbowFlexionDegrees`. It measured 89.64 against a band of 30 to 120 and
the engine said met. Erin said not. After the fix it measures 146.13, the
engine says above, and the two agree. The band is untouched.

### Supports her, outright: 5 marks

The three release cues above, and these two:

| drill | phase | measure | measured | band |
|---|---|---|---|---|
| `double_foot_landing` | flight | `footHeightGapCm` | 0.00 | 0 to 14 |
| `double_foot_landing` | absorb | `footHeightGapCm` | 0.01 | 0 to 6 |

`footHeightGapCm` is a magnitude, so it is never below zero, so a band whose
lower bound is zero cannot fail. These are two of the five cannot-fail phases
already recorded in `docs/KNOWN_ISSUES.md`.

The measurement is also unnaturally exact. Over 110 frames the gap is at most
1.22 cm, and 60 of those frames read under 0.05 cm. Feet in flight are not
level to a hundredth of a centimetre.

### Supports her objection, but no checkpoint measures it: 7 marks

These are the marks where an instrument confirms the thing she describes, and
the checkpoint she marked measures something else. Every measured value here
sits strictly inside its band, and none is near an edge.

| drill | phase | measure | what her note is about |
|---|---|---|---|
| `hooks_outside_hand` | facing_away | `trunkTurnDegrees` | the hands |
| `hooks_outside_hand` | facing_away | `leftKneeFlexionDegrees` | the hands |
| `hooks_outside_hand` | contact | `trunkTurnDegrees` | the hands |
| `hooks_outside_hand` | contact | `rightShoulderElevationDegrees` | the hands |
| `hooks_outside_hand` | gather | `trunkTurnDegrees` | the hands |
| `one_hand_snatch_to_other_hand` | pull_in | `trunkLeanDegrees` | the free hand |
| `two_hand_snatch_pull_in` | ready | `leftKneeFlexionDegrees` | the arm span |

The first six are the free-hand defect of section 1. Her note on the hooks is
entirely about the hands, and not one of the five checkpoints she was given
measures where a hand is.

The seventh is separate and still open. Her note reads:

> "Ball will be placed off line (not to body) where arms can reach - that's why
> they show arm span at start of drill."

At the ready phase of that drill the engine puts her wrists 20.1 cm apart, with
the arms at 0.71 of full reach. That is hands together in front of her. Her own
wingspan would put the wrists about 145 cm apart. The engine does not show the
arm span, and no checkpoint asks whether it does.

**This is the finding that matters most for the next review. A coach can only
mark the checkpoints she is given.** When the pose is wrong in a way no
checkpoint measures, she marks down whichever checkpoint is nearest, and the
value under that checkpoint is fine. Reading those marks as band disagreements
would have retuned five correct trunk turns and hidden a hand in the wrong
place.

### Supports the engine: 1 mark

| drill | phase | measure | measured | band |
|---|---|---|---|---|
| `deflect_high` | contact | `leftElbowFlexionDegrees` | 98.60 | 20 to 100 |

Her note asks the hand to reach, touch, control and cushion. The engine
cushions. Left elbow flexion runs 127.7, 119.3, 107.7, then 91.3 at contact,
then 98.6, 106.3, 113.9, 121.0. The arm straightens to meet the ball and folds
after it, which is what a cushion is.

### Supports neither: 7 marks

No instrument in this project answers these yet. They are listed so that they
are not mistaken for agreement.

| drill | phase | measure | measured | band | what is missing |
|---|---|---|---|---|---|
| `two_hand_catch_chest` | pull_in | `trunkLeanDegrees` | 2.00 | 0 to 12 | no grip measure |
| `two_hand_snatch_pull_in` | contact | `leftElbowFlexionDegrees` | 75.78 | 40 to 110 | no reach threshold |
| `two_hand_snatch_pull_in` | contact | `rightElbowFlexionDegrees` | 75.78 | 40 to 110 | no reach threshold |
| `two_hand_snatch_straight_back` | control | `trunkLeanDegrees` | 2.00 | 0 to 12 | no return-height measure |
| `two_hand_snatch_straight_back` | return | `leftShoulderElevationDegrees` | 79.03 | 30 to 100 | no return-height measure |
| `hooks_jump_pull_in` | contact | `leftElbowFlexionDegrees` | 77.52 | 45 to 100 | no grip measure |
| `deflect_high` | ready | `leftKneeFlexionDegrees` | 47.09 | 15 to 65 | not tested |

Two of her notes ask for a grip the engine does not measure at all. On the
chest catch: "Thumbs shouldn't be up." On the jump hooks: "Fingers up, thumbs
in the middle." The engine measures trunk turn, trunk lean, elbow flexion,
shoulder elevation, knee flexion and foot height. It measures no hand
orientation, so it can neither pass nor fail a thumb.

One claim her notes make was tested and holds. She writes "Bring the ball to
your chest" on the chest catch. The engine does bring it: the left hand comes
to 0.29 of full reach at phase 0.76, which is exactly where the drill's
`pull_in` key sits, and the jump hooks reaches 0.33 at its own key at 0.82. The
library's chest is 0.30 of reach. That note is satisfied, so it does not
explain her mark.

## 4. The elbow pole: a mixing artefact, found and then deferred

`test_elbow_pole.py` checked that the mean elbow separation at contact, across
the library, is the manual's 38.6 cm. `ELBOW_POLE_ANGLE_DEGREES` is defined as
the angle that reproduces that figure. The free-hand fix moved the mean to
41.68 cm and the test failed.

The cause is the population, not the angle:

| population | before the fix | after the fix | drills |
|---|---|---|---|
| all eight | 38.58 | 41.68 | 8 |
| two-handed only | 36.57 | 36.54 | 6 |
| one-handed only | 44.60 | 57.13 | 2 |

`docs/KNOWN_ISSUES.md` already states what the 38.6 cm figure describes: "those
photographs are a snatch AT CONTACT, with the arm at 0.85 to 0.90 of full
extension." On a one-handed drill the free elbow is not on the ball at all, and
after the fix its arm is folded to 0.30 of reach. Averaging that elbow into a
figure read from a two-handed photograph mixes two populations.

**The agreement before the fix was a mixing artefact.** Six two-handed drills
at 36.57 and two one-handed drills at 44.60 average to 38.58, which is 0.02 cm
from the manual's figure, and no member of the population was at it. On the
population the photographs actually describe, the angle gave 36.57 before this
change and gives 36.54 after. The gap of about 2 cm existed already. The fix
did not create it. The fix exposed it.

The two readings pull the angle in opposite directions. From a five-point
sweep, with linear interpolation between the points:

| reading | angle that puts the mean on 38.6 |
|---|---|
| all eight drills | about 22.8 degrees |
| the six two-handed drills | about 37.3 degrees |

That is a 15-degree spread and it changes every drill in the library, so this
lane did not make the choice.

### The ruling

**Marius ruled on 2026-08-30: repopulate the test to the manual's own
population, and defer the angle.** `ELBOW_POLE_ANGLE_DEGREES` stays at 31.3.
The retune waits for the coach-morning data, because the library's look must
not change before a second coach has seen it.

`test_elbow_pole.py` now measures the drills that put both hands on the ball at
the contact frame, taken from the solve rather than from a field in a technique
file. It records 36.5 cm against the manual's 38.6, states the 2.1 cm gap and
the deferral in its own docstring, and says plainly that it no longer proves
the angle was read off the manual's figure. Two guards come with it: one
asserts that the population restriction excludes something, because a
restriction that excludes nothing is a comment, and one asserts that the two
populations have not converged, so the split stays justified.

The suite is green again on 282 tests. That is not the gap closing. It is the
gap being recorded where the next person will find it.

### One note for a reader of the checks

The whole solver suite, including this test, needs `pymomentum`, which lives in
the pixi environment. Continuous integration does not have it, so continuous
integration never ran this test and never saw it red. A green check on this
repository is not evidence about anything in this section. Run it with pixi.

## 5. A latent edge, recorded rather than guarded

The free hand now waits at the last post-contact key. A technique with NO
post-contact key at all would fall back to `ready_point`, which is the old
behaviour, and a technique whose only key is the contact offset would rest the
free hand out at the contact point.

No drill in the library trips this. Every technique that leaves a hand free
authors at least one key past contact, and both that do author an identical
chest key. It is written down here rather than guarded, because a guard for a
case no drill reaches cannot be tested against a real drill, and an untestable
guard is the thing this project keeps finding under a comment.

If a drill is ever authored with a free hand and no chest key, this is where
to look first.
