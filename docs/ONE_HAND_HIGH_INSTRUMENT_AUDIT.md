# The 1 hand high pass: what the manual cues, and what the engine can measure

Written 2026-09-04 by the content lane, BEFORE anything is authored, on the
orchestrator's instruction. Nothing in `spikes/movements/` is touched by this
document.

Measured on the engine at `46ed8a5`, the tip after PR #75 merged, in the
content-lane worktree, `pixi run --frozen`, `MKL_THREADING_LAYER=SEQUENTIAL`.
The manual is the *Netball Skills and Conditioning Manual, Level 1, 3rd
version*, by Niel du Plessis and Erin Burger, read at
`.assets/manual/202526 updated coaches manual.md`.

**Every length below is stated with the point it is measured FROM.** The bounce
pass pack had to be corrected twice for a span whose origin was not written
down, so this document names an origin beside every centimetre.

---

## The conclusion first

**THIS DRILL IS GRADEABLE ON THREE OF ITS FOUR CUE GROUPS, AND ITS DEFINING CUE
IS THE UNGRADEABLE ONE.** Step 1, *"Pull the ball up as high as arm can go"*, is
a HEIGHT, and the library still has no units-correct height measure. That is the
same gap the overhead pass shipped on a substitute for, and here the substitute
is worse rather than better, because this drill is defined by going HIGHER than
the overhead pass and the substitute's leak GROWS with height.

**Two structural facts follow from the drill being one-handed**, and only one of
them is new:

1. A one-handed technique carries a side by construction, so this drill can
   never enter the even population the knee-mirror guards read. That is
   correct behaviour, not a defect.
2. **The library already has two one-handed drills**, so the pattern for this
   is established and does not need inventing. Refer to "The one-handed
   question" below, which corrects a premise this audit was commissioned on.

**And one finding that is not about this drill at all**, found while checking
the release frame on the orchestrator's instruction: **at the release frame of
all three existing passes, the thumb swings 11.5 to 19.8 degrees in a single
frame and ends 0.70 cm inside the ball.** The receipt's hand-orientation rows
for a `release` phase are read at exactly that frame. Refer to "The release
frame" below. It is recorded, not fixed.

---

## The manual block, quoted with its lines

`#### **1 HAND HIGH PASS**` — heading at line **2670**, under image marker
`_page_80_`, so page **81** by the convention PR #74 sets out.

| line | text |
|---|---|
| 2672 | 1. Pull the ball up as high as arm can go |
| 2673 | 2. Give a small step, and with wrist and hands pass the ball |
| 2674 | 3. Keep hand behind the ball and fingers up |
| 2676 | *Focus on these things:* Don't move hand under ball (power moves under ball). Don't push the ball with arm. Don't give a too big step (shortening own 3ft). Don't wait too long to release, use momentum pull wide and release |

Line 2674 runs on into `Focus on these things:` in the extraction. That is a
layout artefact of the heading below it, not part of the cue.

**Three numbered steps and four warnings.** The warnings are as specific as the
steps here, which is unusual in this section, and two of them are gradeable in
principle. They are treated below.

---

## The parent question, which is why this drill was ruled next

The brief says the lob's step 2 is word for word this block's step 1. **It is,
and there is more than that.** Read the lob block at 2720 to 2726 against this
one:

| lob | text | where it comes from |
|---|---|---|
| step 1, line 2724 | Use one of the different passing types (1 Hand high/wide or double hand) | names its own parents |
| step 2, line **2725** | Pull the ball up as high as arm can go | **verbatim, this block's step 1 (2672)** |
| step 3, line **2726** | Keep hand behind the ball and fingers up | **verbatim, this block's step 3 (2674)** |

**TWO of the lob's three steps are verbatim from this block, not one.** The
third names its parents explicitly.

The overhead pass, which the library already has, shares **neither** verbatim:
its step 1 at 2663 reads *"Pull the ball up into the air above your head"*,
which is a different sentence and a different height.

**So the manual sanctions three parents for the lob — "1 Hand high", "1 Hand
wide", and "double hand" — and the library holds one of them today.** Authoring
this drill gives it a second, and the second is the one whose wording the lob
actually reuses.

### What separates it from the overhead pass, in centimetres

This is the question a coach will ask, so it is measured rather than asserted.
All heights are from the floor, on the reference athlete, at frame 0 of
`netball_overhead_pass`:

| landmark | height |
|---|---|
| chest, `c_spine3`, the stance anchor | 126.32 cm |
| shoulder, `r_uparm` | 132.87 cm |
| crown, `c_head_null` | 163.45 cm |
| **wrist, arm straight up** | **185.55 cm** |

Segment lengths behind those: upper arm 25.68 cm, forearm 27.00 cm. The
engine's arm length is 52.68 cm, which is upper plus forearm exactly.

**CORRECTED AFTER AUTHORING, AND THE CORRECTION IS WORTH READING.** A first
version of this table carried a fingertip row of 198.79 cm and used it in the
construction below. **That row is withdrawn** and the construction below is
rebuilt on the wrist. **A fingertip height is not a reach figure.** The
wrist-to-fingertip distance is read along whatever direction the fingers happen
to point, so it depends on the grip pose: 13.24 cm here, **6.83 cm on
`netball_one_hand_high_pass`** at its own frame 0. A construction whose input
moves 6.4 cm between two drills of the same athlete is not a skeletal limit.
The WRIST figure is one, because shoulder plus two segment lengths does not
depend on the hand.

**And these are `netball_overhead_pass`'s landmarks, not every drill's.** The
frame-0 pose differs between drills: the authored drill reads chest 125.99,
shoulder 131.32, straight-arm wrist 184.00. Refer to that drill's `reachNote`
for its own figures.

**Where the overhead pass actually puts the ball**, by ball CENTRE:

| phase | frame | ball centre |
|---|---|---|
| ready | 0 | 132.72 cm |
| **lift** | 33 | **184.41 cm** — its highest |
| step | 55 | 181.08 cm |
| release | 76 | 180.42 cm |

**A held ball centres 15.15 cm from the wrist**, measured on that drill at
frames 74 and 75 while `holdingTheBall` is true. So a straight overhead arm
holding the ball would centre it near **200.7 cm** — 185.55 plus 15.15 — **IF
the hand stays aligned with the forearm**, which is an assumption about hand
orientation and not a solved pose. Stated as a construction, with its
assumption, because the last time this library reused a reach figure across two
drills it published a lob's geometry under a straight pass's label.

**On that construction the drill has about 16 cm of headroom above the overhead
pass**, 200.7 against 184.41. That is the difference the coach is being asked
about, and **nothing in the engine measures it.**

### The construction was tested, and it held

**Added after authoring.** A construction is a prediction, and this one was
checkable as soon as the drill existed. Predicted **200.7 cm**; the authored
drill's ball centre peaks at **199.95 cm**, which is **0.75 cm low**. The
assumption behind it — that the hand stays aligned with the forearm — is
therefore good to about a centimetre at full extension on this athlete.

The wrist prediction is the one that moved more, and in the direction the note
warned about: the frame-0 construction gives 184.00 cm on the authored drill,
and the wrist actually reaches **185.27 cm**, **1.27 cm higher**, because the
shoulder itself rises when the arm goes overhead. **A frame-0 reach
construction is a LOWER BOUND, not a ceiling**, and that is now written into
the drill's own `reachNote` rather than left here.

---

## The instruments that exist

`segment_measures.MEASURE_UNITS` declares **nine** measures: `trunkLeanDegrees`,
`trunkTurnDegrees`, left and right `ElbowFlexionDegrees`,
`ShoulderElevationDegrees` and `KneeFlexionDegrees`, all in degrees, plus
`footHeightGapCm` in centimetres. **Eight of the nine are angles.** Unchanged
since the bounce pass audit.

`spikes/hand_orientation.py` additionally reports `thumbToBallDegrees`,
`thumbUpDegrees` and `fingerUpDegrees` per hand into every receipt, and declares
itself **report-only**. It is absent from `MEASURE_UNITS`, so no checkpoint can
read it.

---

## Cue by cue

| manual cue | instrument | verdict |
|---|---|---|
| 1. "Pull the ball up as high as arm can go" | **NONE that reads it directly.** It is a height. The nearest proxy is `rightShoulderElevationDegrees`, which the overhead pass ships on and which **also reads arm fold and hand placement**. | **substitute only, and the leak grows with height** |
| 2a. "Give a small step" | **NONE.** Step length has no measure. Recorded already on all three passes. | cannot grade |
| 2b. "with wrist and hands pass the ball" | **YES.** `rightElbowFlexionDegrees`. Both other passes grade this exact cue on the elbow. | gradeable |
| 3a. "Keep hand behind the ball" | **REPORT ONLY.** `thumbToBallDegrees` states it and is not in `MEASURE_UNITS`. **And at a release phase the report is read on a corrupt frame** — refer below. | cannot grade |
| 3b. "fingers up" | **REPORT ONLY.** `fingerUpDegrees`, same status. | cannot grade |
| warning: "Don't push the ball with arm" | **PLAUSIBLY GRADEABLE** on `rightElbowFlexionDegrees` — an arm push is an elbow that extends through the release. Needs a sweep before it is believed. | candidate |
| warning: "Don't give a too big step" | **NONE.** Same missing step length as 2a. | cannot grade |
| warning: "Don't move hand under ball" | **REPORT ONLY**, `thumbToBallDegrees` again. | cannot grade |
| warning: "Don't wait too long to release" | **YES, indirectly.** The release phase is authored, and the follow-through shoulder sweep on the bounce pass showed the release phase is a lever that moves a shoulder measure 31.4 degrees. | gradeable if a coach sets a band |

**Three of the four warnings land on gaps this library has already recorded.**
That is not a new finding; it is the same two missing length measures and the
same report-only hand module, meeting a fourth drill.

### Do the two missing length measures bite here? Yes, and harder

The ledger row is *"No units-correct distance measures, and five cues already
want them"*. **This drill adds two more**, and one of them is its defining cue.

The height gap bites worse here than anywhere so far. The ledger row records
that `ShoulderElevationDegrees` leaks arm fold, and **that the leak grows with
height**: 8.2 degrees of spread with the ball at 184.4 cm, 3.7 degrees near the
crown line at 174.1 cm. **This drill is defined by putting the ball ABOVE
184.4 cm.** So it would ship on the substitute exactly where the substitute is
least pure, and its band floor would carry more than the 3.7 degrees of
uncertainty the overhead pass reasoned about.

**That is a decision for the orchestrator and not for this lane**, and it is the
main thing this audit was written to surface. The options as I see them:

1. Author it on the substitute anyway, with the leak stated beside the band and
   a wider floor, as the overhead pass did.
2. Author it with **no height checkpoint at all**, grading only the elbow and
   the knee, and record the defining cue as a gap — the choice the bounce pass
   made for two of its five steps.
3. Hold the drill until a units-correct height measure and a units-correct band
   exist.

**This lane's recommendation is option 2.** The bounce pass established that
recording a gap is better than grading a proxy, this library has twice withdrawn
a checkpoint authored on a weak instrument, and the substitute is at its worst
precisely here. Option 1 puts a number in front of a coach that is partly about
where her hands are.

---

## The one-handed question, and a correction to the brief

**The brief says the tripwire population has never met a one-handed drill. It
has, twice.**

| drill | `hands` |
|---|---|
| `netball_hooks_outside_hand` | `right` |
| `netball_one_hand_snatch_to_other_hand` | `right` |

Every other drill in the library is `both`. So this would be the library's
**first one-handed PASS**, which is what makes it new, but not its first
one-handed drill.

**The mechanism the brief describes is exactly right.**
`technique.carries_no_side()` returns `False` on the first line for anything but
`hands == "both"`, so a one-handed technique is uneven **by construction** and
`movement_carries_no_side()` excludes it. That is at
`spikes/technique.py:135`.

**And the pattern for handling it is already written down.**
`test_waiting_hand.py` has `test_the_even_population_is_what_it_claims`, which
asserts the even set equals the keys of `KNEE_GAP_CEILING_DEGREES` **and** names
four drills that must read uneven, including both one-handed ones. So a new
one-handed drill has an established home: it goes in the named-uneven list and
NOT in the ceiling dictionary.

**The precedent for which side to grade is also set.** Both existing one-handed
drills grade `right*` measures for the working arm and `left*` for the other.
**All three existing passes grade `left*`.** So this drill must break the
passes' convention and follow the one-handed one — an easy thing to get wrong by
copying the nearest pass, and the reason it is written here before authoring
starts.

### What a one-handed pass must be registered in

Four places, none optional:

| registry | what this drill needs |
|---|---|
| `test_waiting_hand.py: STANCE_DEGREES` | a pin, measured at the tip and quoted beside it |
| `test_waiting_hand.py: KNEE_GAP_CEILING_DEGREES` | **no entry** — it is uneven |
| `test_waiting_hand.py`, the named-uneven list | **an entry**, so its side is asserted by name |
| `test_authored_launch.py: AUTHORS_A_LAUNCH` | an entry — a pass authors a launch |
| `spikes/clip_geometry.py: CLASSES` | `("pass", "one-hand-high-pass", "release")` |

---

## The release frame, measured on the orchestrator's instruction

The brief asked me to measure frames 75 to 78 and record rather than fix. **The
finding reproduces on all three existing passes, identically, on both hands.**

Distance from the ball CENTRE to each joint, ball radius **11.00 cm**, so a
figure below 11.00 means the joint is geometrically **inside the ball**:

`netball_bounce_pass`, left hand:

| frame | state | `thumb1` | `thumb3` | `index3` | `middle3` | `wrist` |
|---|---|---|---|---|---|---|
| 74 | carried | 12.54 | 11.74 | 11.69 | 11.69 | 15.15 |
| 75 | carried | 12.53 | 11.74 | 11.70 | 11.70 | 15.14 |
| **76** | **released** | 12.52 | **10.28** | 17.35 | 18.38 | 15.14 |
| 77 | released | 17.90 | 16.53 | 23.22 | 23.42 | 19.67 |
| 78 | released | 24.10 | 23.26 | 29.76 | 29.42 | 25.28 |

**Frame 76 is the FIRST released frame.** At it, and only at it, `thumb3` is
**0.72 cm inside the ball**. The chest and overhead passes give 10.30 cm, which
is 0.70 cm inside, at the same frame.

**Read the finger columns carefully — most of that jump is the BALL leaving,
not the fingers moving.** The ball is on its parabola from frame 76, so every
distance to its centre grows. The thumb tip is the one that goes the OTHER WAY.

**The hand-orientation report confirms it is the thumb that moves.** Comparing
frame 75, where she is holding, with frame 76, where she is not:

| drill | `thumbUpDegrees` 75 → 76 | move | `fingerUpDegrees` 75 → 76 |
|---|---|---|---|
| `netball_chest_pass` | 70.76 → 54.95 | **−15.81°** | 5.87 → 5.98 |
| `netball_overhead_pass` | 56.89 → 37.06 | **−19.83°** | 35.45 → 35.03 |
| `netball_bounce_pass` | 83.30 → 71.79 | **−11.51°** | 15.27 → 15.34 |

**The fingers hold their orientation to within 0.42 degrees while the thumb
swings 11.5 to 19.8 degrees in one frame.**

**Neither carrying drill shows it.** `netball_one_hand_snatch_to_other_hand` and
`netball_hooks_outside_hand` hold every distance flat between 11.68 and 13.28
across frames 74 to 79, and nothing goes inside the ball. So this is a property
of the RELEASE TRANSITION, not of the grip.

### Why it matters to this drill specifically

`hand_orientation.receipt_section` reads **the frame the grading reads**,
`round(atPhase * (frames - 1))`. A `release` phase at 0.80 of 96 frames is
frame 76. **So the hand rows a receipt shows for a release phase are taken at
exactly the frame where the thumb has swung and gone inside the ball**, with
`holdingTheBall` already `false`.

Manual cue 3 here is *"Keep hand behind the ball and fingers up"* and the
warning is *"Don't move hand under ball"*. **Those are precisely what this
module reports, and at the release phase the report is taken on that frame.**
The finger figure appears stable across it; the thumb figure does not.

**RECORDED, NOT FIXED**, as instructed. What this lane will do when authoring:
if a hand cue is reported at all, it will be reported at a phase where she is
**holding** the ball, and the release phase's hand rows will carry a note
pointing here. Whether the underlying pose should be fixed is engine work and
belongs to the movement lane.

---

## What I expect to author, subject to the ruling above

- **Four or five checkpoints**, all on the RIGHT arm for the working side.
- **`rightElbowFlexionDegrees`** at a ready phase, a lift phase and a release
  phase — the cue *"with wrist and hands pass the ball"* is the elbow, and the
  bounce pass proved the elbow sweeps cleanly on a carry lever.
- **`leftKneeFlexionDegrees`** at ready, as every drill in the library grades.
- **No height checkpoint**, per the recommendation above, with step 1 recorded
  as a gap in the definition and in the ledger row.
- **Every band PROVISIONAL**, and a coach must set them.

**Nothing is authored until the orchestrator rules on the height question.**
