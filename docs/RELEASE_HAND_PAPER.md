# The release hand: what the engine does, what the manual asks, and a model

A paper for Marius, prepared by the movement lane on 2026-09-08 from `1c3d9d7`.
**It proposes a model and changes nothing.** No engine file is touched, and
`spikes/movements/` is gate 4 and untouched.

> **RULED 2026-09-08 BY MARIUS: MECHANICAL.** The release TIMING is the unit and
> the cosmetic hand sits on top of it afterwards. Section 9 records the ruling,
> its reason, and what the unit costs. **Question 1 below is answered; the other
> four are open.** Every withdrawal in this paper stands: they are what the
> ruling was made on.

Marius watched Erin's page v13 and found the one thing that differs: at launch
the athlete flicks her **wrist and her fingers** in the last moments of contact,
and the engine's hand stays flat through the release.

## 1. The engine's hand is not flat. It is frozen, and then it snaps

Measured on `1c3d9d7`, `netball_chest_pass`, 96 frames at 60 fps, the left hand.
The wrist angle is elbow–wrist–knuckle, so 180 is a straight line; the finger
angle is wrist–knuckle–tip, so 180 is a straight finger.

| frame | state | wrist | finger | wrist speed | nearest digit to the ball centre |
|---|---|---|---|---|---|
| 72 | carried | 128.97 | 119.90 | 35.6 cm/s | `l_thumb2` 11.06 |
| 73 | carried | 128.52 | 119.81 | 34.6 | `l_thumb2` 11.05 |
| 74 | carried | 128.07 | 119.76 | 34.0 | `l_thumb2` 11.04 |
| 75 | carried | 127.62 | 119.66 | 32.8 | `l_thumb2` 11.05 |
| **76** | **released** | 127.18 | **175.87** | 33.6 | **`l_thumb3` 10.30** |
| 77 | released | 122.72 | 175.87 | 245.5 | `l_thumb3` 16.22 |
| 78 | released | 117.92 | 175.87 | 212.9 | `l_thumb3` 22.75 |

Three things, and none of them is a flat hand.

**THE FINGERS DO NOT MOVE, AND THEN THEY SNAP OPEN IN ONE FRAME.** They hold
119.66 to 120.16 through every contact frame, then jump **56.2 degrees to
175.87 at the release frame**, and then never move again: 175.87 at every frame
after. That is `spread_fingers` resetting the digits once the ball is gone. So
what a viewer reads as "flat through the release" is a wrap that never changes
followed by a straightening that takes one frame.

**THE WRIST DRIFTS 3.04 DEGREES ACROSS THE LAST EIGHT CONTACT FRAMES**, 0.4 per
frame, in the direction of flexion, and then moves 23 degrees in the four frames
**after** the ball has gone. The engine's wrist does its travelling after the
release, where it can do nothing.

**THE HAND AND THE BALL BOTH JUMP AT THE RELEASE. THE BALL JUMPS FURTHER.**
All four passes, in centimetres per second. The ball column is a mean over the
three frames after release:

| drill | hand through contact | hand, frame after | ball after release |
|---|---|---|---|
| `chest_pass` | 32.8 to 36.4 | 245.7 | 602.0 |
| `overhead_pass` | 46.4 to 52.6 | 442.2 | 603.5 |
| `bounce_pass` | 34.0 to 35.4 | 302.2 | 604.3 |
| `one_hand_high_pass` | 63.3 to 78.6 | 349.1 | 621.2 |

**Against the HELD hand the ball leaves 8 to 18 times faster. Against the hand
one frame later it leaves 1.4 to 2.5 times faster.** An earlier draft printed
only the first of those and headed this block "an order of magnitude slower".
Both figures come from the same solve, and **the second is the fairer one**,
because it compares the ball's speed with the hand's at the same instant instead
of with the hand before it moved.

**The finding survives the correction and is narrowed by it.** The ball is still
not driven by the hand, because its speed is assigned from a constant. But the
gap is a factor of about two at the same instant, not an order of magnitude, and
a paper arguing from the larger number would have been arguing from a comparison
across the release.

### The engine's wrist beside the athlete's, in the same units

The comparison the clip cannot supply, because the clip carries no wrist at all
(below). This is the wrist joint's own speed **from the solve**, over the last
eight frames of contact, in **metres per second**:

**Both sides of the release**, because one side alone gives the wrong answer.
The working wrist's own speed from the solve, in metres per second:

The working wrist, in centimetres per second, **one column per instant**. The
peak column names the frame its number falls on, because which frame that is
turns out to be the whole finding:

| drill | working hand | held, last 8 | AT the release | one frame after | peak, and where |
|---|---|---|---|---|---|
| `chest_pass` | left | 33 to 36 | 33.6 | 245.5 | 2.45 m/s, one frame after |
| `overhead_pass` | left | 46 to 53 | 43.4 | 442.2 | 4.42 m/s, one frame after |
| `bounce_pass` | left | 34 to 35 | 35.4 | 302.3 | 3.02 m/s, one frame after |
| `one_hand_high_pass` | right | 63 to 79 | **561.4** | 349.1 | **5.61 m/s, AT the release** |
| **the filmed athlete** | near arm | | | | **2.5 to 5.4 m/s** |

**The release frame has its own column so that no column can hide the one drill
whose big number is in a different one.** An earlier version of this table
carried that 561.4 only as prose inside a peak cell, and a reader comparing the
"one frame after" column down the page would have seen 245.5, 442.2, 302.3 and
349.1 and missed the exception entirely. The video lane found the same fault in
its own table on the same morning: **prose inside a cell does not survive a
reader who is scanning a column.**

**THE COMPARISON IS GOOD TO THE ORDER AND TO THE OVERLAP OF THE RANGES, AND NO
FURTHER.** The video lane states the resolution of its own instrument and this
paper repeats it in the same place as the numbers rather than under them: one
athlete, twelve releases, 30 fps footage, two scales whose frame-by-frame ratio
runs 0.21 to 3.05 about a median of 1.30. **The width of the band, 2.5 to 5.4,
IS that instrument's honest resolution.** These are solved joints at 60 fps and
share no arithmetic with it. That two such instruments land this close is a good
sign, and it is coincidence at the second decimal. **No sentence in this paper
rests on a gap of a few hundredths of a metre per second**, and an earlier draft
that said "0.04 below the floor" was making a claim its evidence cannot carry.

### Three of the four are not slow. They are LATE. The fourth is FAST.

**This is a correction, and the correction is the finding.** An earlier draft of
this paper compared the held column alone against the athlete's band, concluded
the engine's wrist runs "at a third to a sixteenth of the filmed hand", and
called that a statement about the arm's timing. **The held column is one side of
the release.**

**THE LATE THREE.** On the chest, overhead and bounce passes the wrist
multiplies its speed by 7.4 to 10.5 times in the single frame AFTER the release,
reaching 2.45, 4.42 and 3.02 m/s against a band that starts at 2.5. **The
engine's arm reaches an athlete's release speed and reaches it one frame after
the ball has gone.** That is a different fault from the one the earlier draft
named, and a smaller one to fix, because the motion exists and is misplaced in
time rather than missing.

**THE FAST ONE, AND A SENTENCE COVERING ALL FOUR WOULD BE WRONG IN THE ENGINE'S
FAVOUR.** `one_hand_high_pass` reaches **5.61 m/s in the release frame itself**
and then slows. It does not sit inside her band: it **overshoots** it. It is the
one drill whose hand is fast at the moment the ball leaves and the one drill
that goes too far. **Three late and one fast is a different finding from four
late**, and this paper states it as two findings on the video lane's caution.

**And the overshoot is against a ceiling that is not even one-handed.** That
lane reports its fastest release, 5.39 on the image scale, is a TWO-HANDED one
(run 0.2, release 646); the athlete's one-handed releases are not the fastest in
its set. So the engine's one-handed drill exceeds her fastest release of any
kind, in the category where she is slower.

**None of this is new to the repository, which is the uncomfortable part.**
`docs/KNOWN_ISSUES.md` has recorded it since before this paper began, under "The
hands are not already moving": the right wrist runs 0.55 cm per frame before the
chest pass release and 4.09 after it, a step of 7.4, and 10.2 on the overhead.
Worse, **section 1's own close-up table above prints 245.5 cm/s at frame 77**.
This paper published the refutation of its own sentence, in its own figure, and
did not read it. The video lane sent the correction; the independent review of
`1ec0dfd` found it first.

**The athlete's figures are the video lane's, cited and not re-derived here**,
and they carry their inputs: twelve releases across both runs, the near arm,
crisp releases only, one slow held repetition excluded and declared. **The band
is quoted across both scales and never as one column**, on that lane's own
instruction: its two scales disagree by about 30 per cent at the median, and the
per-scale figures an earlier draft of this paper quoted took their low end from
a release marked `soft`.

**So the question a flick has to answer changes.** It is no longer whether a
wrist at a sixteenth of her speed can reach her band. It is **whether the speed
the arm already produces can be moved to the side of the release where it would
act on the ball.**

### How far the hand travels, on all four passes

**Measured for the contract lane's sixth question**, which has to size a hand
channel by what a hand actually does. Degrees, from the solve. A span is a
maximum minus a minimum inside its window, so it can exceed the first-to-last
difference when the angle turns around.

| drill | side | wrist, last 8 held frames | wrist, 4 frames after release | finger, before -> at release |
|---|---|---|---|---|
| `chest_pass` | l | 130.66 to 127.62, span **3.04** | 127.18 to 104.06, span **23.11** | 119.66 to 175.87 |
| `overhead_pass` | l | 129.35 to 128.28, span **1.07** | 128.22 to 114.13, span **14.09** | 119.09 to 175.87 |
| `bounce_pass` | l | 117.77 to 112.22, span **5.55** | 111.39 to 104.99, span **8.93** | 119.20 to 175.87 |
| `one_hand_high_pass` | r | 107.68 to 102.97, span **4.71** | 111.30 to 110.48, span **0.82** | 133.04 to 175.87 |

**Three readings a hand channel would have to carry, and one that it must not.**

1. **The hand does most of its moving after the ball has gone.** On the chest
   pass the wrist turns 3.04 degrees through the last eight frames of contact
   and 23.11 degrees in the four frames after release, which is seven times as
   much once the ball can no longer be affected. The overhead pass is the same
   shape at 1.07 against 14.09.
2. **The one-hand-high pass is the exception and it goes the other way**: 4.71
   degrees during contact and 0.82 after. It is also the only one of the four
   the engine solves RIGHT-handed, which this script measures rather than
   assumes.
3. **The finger lands on 175.87 degrees in all four passes.** One value, to two
   decimals, across four different techniques and both working hands. That is
   not four measurements agreeing. It is one constant, and it is the clearest
   evidence in this paper that the digits are not solved at all after the ball
   leaves: they fall to the same rest value every time.

**The third reading bounds the channel, and the other two do not generalise.**
An earlier draft of this paper said a channel would carry "a constant and a
post-release swing". That smoothed the table above and it is corrected here.

- **The swing is not on every pass**: 23.11, 14.09 and 8.93 degrees on the
  chest, overhead and bounce passes, against **0.82 on one-hand-high**, which
  has effectively none.
- **The grip before release is not one value either**: 119.66, 119.09 and 119.20
  on the three left-handed passes, and **133.04** on the right-handed one.
- **The constant has no exception**: 175.87 on all four, both hands.

**So the conclusion rests on the constant alone**, which is the only reading that
holds across four techniques and both working hands: the digits are not solved
after release. A hand channel fed by today's solve would carry that constant, and
a swing on three passes out of four. Neither is the flick Marius asked about, so
the channel is worth adding only together with a release model that puts
something in it.

### Two measurements of "the fingers", and they agree

**Two merged documents say opposite-sounding things about the same frame of the
same drill, and both are right.** They measure different quantities under one
word, which is the fault this ledger has counted more often than any other, so
the reconciliation is written here rather than left to the next reader.

| document | quantity | instrument | chest pass, frame 75 to 76 |
|---|---|---|---|
| this paper | how BENT the finger is | angle wrist-knuckle-tip at the middle finger, `scripts/release_hand.py` | 119.66 to **175.87**, a change of 56.21 deg |
| `ONE_HAND_HIGH_INSTRUMENT_AUDIT.md` | which WAY the hand points | `fingerUpDegrees`, the ray wrist-to-knuckle against world up, `spikes/hand_orientation.py` | 5.87 to **5.98**, a change of 0.11 deg |

**A finger can hold its direction while its bend opens**, because the two
measures share only one point. The ray from the wrist to the knuckle can be
fixed while the segment from the knuckle to the tip straightens. That is exactly
what happens here: the knuckle stays put and the finger unrolls.

**The audit's own definition of `fingerUpDegrees` says so before either of us
measured anything**: it must not "conflate curl with orientation. 'Fingers up'
is about which way the hand points."

**The audit's third figure is this unit's, not the audit's.** At that same frame
the thumb swings 11.5 to 19.8 degrees and its tip ends **0.70 to 0.72 cm inside
the ball**, and the receipt's hand-orientation rows for a release phase are read
at exactly that frame. **It is the frame this unit retimes and the frame option B
changes**, so the corrupt reading is not a separate defect to be scheduled. It
is a consequence of where the release frame sits, and it moves when the release
moves.

### The video lane found the same thing from the other end

Cited from that lane's pack and log, not re-derived here: **in every shipped
clip the ball is ASSIGNED its flight velocity at the release frame** — on the
chest pass **0.46 m/s while held and 8.88 the next frame**, a step of 6 to 19
times in ONE frame across all eight techniques. Nothing accelerates the ball,
and the flick Marius saw is the last part of a throw the engine does not perform
at all.

**Two lanes, two instruments, one conclusion**, which is worth more than either
alone: that lane read the exported clips, this one read the solve.

**THE TWO SETS OF NUMBERS WERE NOT THE SAME QUANTITY, AND NOW THEY ARE
RECONCILED.** An earlier draft of this paper reported the disagreement and
declined to explain it. The orchestrator supplied the explanation and this lane
then reproduced it, which is why the paragraph now states a result instead of a
puzzle.

**The clip does not carry the ball in metres.** `clip_geometry.read_ball`
carries it from the SHOULDER MIDPOINT and in ARM LENGTHS, and it recomputes the
divisor every frame from that frame's own left arm. So one ball has three
speeds, and only one of them is what either lane published:

| step | world | from the shoulders | the clip's own channel | that channel x 0.77 m |
|---|---|---|---|---|
| 75 -> 76 | 0.33 m/s | 0.31 m/s | 0.585 arm/s | **0.45** |
| 76 -> 77 | 6.03 m/s | 6.07 m/s | 11.530 arm/s | **8.88** |

**The released frame reproduces the video lane's 8.88 exactly.** That lane
converted the arm-length channel with a filmed athlete's arm of 0.77 m. The
engine's arm is **52.68 cm** measured here at the release frame through the
exporter's own chain, so the conversion inflates every figure by
0.77 / 0.5268 = **1.462**, which is the factor the earlier draft observed and
could not name.

**The held frame lands one hundredth low: 0.45 here against their 0.46.** It is
not claimed as an exact reproduction. The channel is rounded to four decimals
before it is written, and over a single frame at 60 fps that rounding is worth
about a hundredth at this magnitude, so the residual is the size of the rounding
and no further claim is made about it.

**TWO DIFFERENT QUANTITIES IN THIS PAPER BOTH READ 0.33 m/s, and a reader has to
be told which is which.** The 0.33 in the table above is the BALL's centre while
it is still held. The 0.33 to 0.36 in section 1 is the WRIST joint, from
`scripts/release_hand.py`. They are not the same measurement and neither is
derived from the other.

**They agree because the ball is carried.** While the hand holds it, the ball
moves at the hand's speed, so the two readings SHOULD match, and they do. One
frame later the ball is at 6.03 m/s and the wrist is still at 0.36. **The ball
tracks the hand exactly while held, and then leaves it entirely.** That is the
authored launch seen from the ball's side rather than the hand's, and it is the
same finding measured a second way.

**So the two routes agree in the engine's own units**, and the agreement is
worth more than either reading alone: that lane read the exported clips through
the arm-length channel, this one read the solve in centimetres, and both say the
ball's speed appears in one frame from nothing. **When Tony's corrected column
lands, cite his figures and not these**; these exist to show the two are the
same measurement.

### And that is the finding under Marius's observation

The ball's speed is **authored**, not imparted: `author_flight.DEFAULT_SPEED_CM
= 600` sets it, and the possession model releases the ball onto a parabola that
the hand plays no part in. So **a flick cannot change ball speed in this engine
as it stands, because the ball's speed does not come from the hand at all.**

Marius calls the flick "the direct mechanism for ball speed and late direction
change". In the engine that mechanism is **not connected**. Modelling the flick
makes the hand *look* right; it does not make the ball go faster, and this paper
must not let a later reader think it will.

**That is a decision for him, not for this lane**, and it is the first question
below.

### Chuck's finding is visible in the same table

`l_thumb2` sits 11.04 to 11.07 cm from the ball centre against a radius of
**11.0**, so the thumb rides the surface; at the release frame `l_thumb3` is at
**10.30 cm**, 0.7 cm **inside** the ball. `FAN_AND_RELEASE_PACK.md` records the
same thing across the library: with the shipped option A the wrist leaves the
ball in a single frame and **a coach sees the ball inside the fingers at the
moment of release on three of the five release phases**.

The flick and that intersection are the same frame and the same joint chain, so
they cannot be designed apart. Section 5 folds them together.

## 2. What the manual asks, quoted

**The manual gives the chest pass no technique block**, which its own drill file
already records: every other technique here quotes a numbered step from its own
block, and this one transfers its cues from the other pass blocks, each
checkpoint naming the block it came from. The same rule governs this paper.

The cue Marius is pointing at is in **every** pass block that has one:

> **"Give a small step, and with wrist and hands pass the ball"**
> — OVERHEAD PASS step 2, and verbatim in 1 HAND HIGH PASS, 1 HAND LOW WIDE
> PASS, 1 HAND WIDE PASS and 1/2 HAND BOUNCE PASS.

**The manual's stated mechanism for a pass is the wrist and the hands.** Not the
arm — it says so directly:

> **"Don't push the ball with arm."** — 1 HAND HIGH PASS
> **"Don't move hand under ball (power moves under ball)."** — 1 HAND HIGH PASS

That second warning is the only place the manual uses the word **power**, and it
attaches it to where the hand is. And on where the fingers point:

> **"Keep hand behind the ball and fingers up"** — 1 HAND HIGH PASS step 3,
> 1 HAND WIDE PASS step 3
> **"Keep hand behind the ball fingers will turn slightly to the side"**
> — 1 HAND LOW WIDE PASS step 3
> **"Player catch the ball the same every time with 2 hands and fingers up and
> thumbs behind in the middle of the ball"** — OVERHEAD PASS, opening line

**What the manual does NOT say**, and this matters for the parameters below: it
never says "snap", never says "flick", never gives a wrist angle, never gives a
timing, and never describes the follow-through of the fingers. The word
"straight" appears about wrists only in a **conditioning** context — "Keep
wrists straight inline with arm" at manual lines 1490 and 1518 — which is a
different exercise and must not be borrowed for a pass.

**So the manual supports the EXISTENCE and the SEQUENCE of a wrist-and-hand
release and supplies not one number for it.**

## 3. What the footage can and cannot support

Cited from the video lane's committed work, not re-derived here.

- **The hand ANGLE is not measurable.** The footage is 30 fps with the hand 15
  to 30 px. The video lane has measured that the wrist angle cannot be read from
  it.
- **The hand SPEED is measurable, and the band is 2.5 to 5.4 m/s.** Twelve
  releases across both runs on the near arm, **crisp releases only**, excluding
  the repetition where she holds the ball about a second before throwing.
  Source: `spikes/video-annotations/hand-speed/BAND.md` and
  `spikes/video_hand_speed.py`, PR #97, with the recordings pinned by sha256
  above the table and a test asserting the document equals the module's output.
- **Quote the range, never one column.** That lane's instrument produces no
  per-scale band, and its two scales disagree by about 30 per cent at the
  median. Two earlier drafts of this paper got this wrong in two different ways:
  the first cited 3.4 to 4.3 from a preliminary reading, and the second quoted
  per-scale figures of 3.3 to 5.4 and 2.5 to 3.9 whose low end came from a
  release marked `soft`. Crisp releases give 3.82 to 5.39 and 2.51 to 3.94, and
  the union of those is the band above.
- **An earlier draft also fitted a scale factor of 1.354 to 1.367 to two
  published endpoints, and that interval is withdrawn.** It assumed the extremes
  of two summary ranges are one release measured two ways, when they need not
  come from the same release at all, and it published an interval about a
  hundred times tighter than the frames beneath it, whose per-frame ratio runs
  0.21 to 3.05 about a median of 1.30.
- **That lane searched a null and put it at 0.06 to 0.10 m/s.** It is landmark
  scatter on a still arm, so it bounds the FOOTAGE column and says nothing about
  a solved joint, which has no landmark scatter to bound.
- **The pairing is by hash, never by name** — the files were relabelled on
  2026-09-07. The established pair is `f7faf38b` with `6e8f9fb2` at `side index
  = front index − 5`.
- **A constant frame offset is good to about a fifth of a frame** across a clip:
  the two cameras' periods differ by 11 microseconds, drifting ~6 ms over 450
  frames.

**Two consequences for this model.**

First, **no parameter of the flick may be inferred from the footage's angles**,
because the footage does not carry them. Only the speed can be checked against
it, and only as a band.

Second, and larger: **the engine's hand is late, not slow, and an earlier draft
of this paper said the opposite.** Through contact the wrist runs 0.33 to
0.79 m/s against her 2.5 to 5.4, which the earlier draft published as a factor
of three to sixteen. One frame after the release the same wrist is at 2.45 to
4.42 m/s on three of the four drills, and the fourth reaches 5.61 m/s in the
release frame itself. **The comparison was true of the frames it chose and false
of the next one.** An intermediate draft then wrote those two as one range,
"2.46 to 5.61 m/s one frame after the release", which is a range that exists at
no single instant: it is the same across-the-release fault committed inside the
correction for it.

**What that costs the model, and what it does not.** It does not weaken the
finding that the ball's speed is assigned: the ball still receives 6 m/s from a
constant, and the hand still does not drive it. It removes a different claim
entirely — that the arm is incapable of the speed. **The arm produces the speed
and produces it on the wrong side of the release**, so a mechanical model is a
question of moving motion that exists, rather than of creating motion that does
not.

**Where that speed comes from matters, and it is not a throw.** `possession.py`
eases the follow-through aim point out of the release with `out = 1 - (1 - t)^2`,
and an ease-out has its greatest slope at t = 0. The hand is fast after the
release because the follow-through starts at full speed, not because anything
threw the ball. Moving it earlier is not a retiming of a throw; it is making the
engine have one.

## 3b. The clip cannot carry a flick, whatever the animation does

Verified here from the exporter rather than taken on trust. A clip frame is
**fifteen positional numbers** (`export_tactics_clip.py:246-264`):

    bob, lean, twist,
    leg left upper/lower, leg right upper/lower,
    arm left upper/lower, arm right upper/lower,
    leg left out, leg right out, arm left out, arm right out

**There is no wrist, no hand and no finger among them**, confirmed against a
shipped clip: `netball_chest_pass.clip.json` carries fifteen bare numbers per
frame and no channel name matching wrist, hand, finger or thumb.

So a flick can be solved, rendered and graded, and **Tactics will not receive
it**. That is a contract question for Marius and this paper states it as one: a
sixteenth and seventeenth channel would be a change to the clip contract, which
is the boundary this lane deliberately does not cross alone.

**It also bounds what the unit can claim.** A flick reaches the coach's figure
and the receipt; it does not reach a board.

## 4. The proposed model

Over the last **N** frames of contact the wrist moves from extension toward
flexion while the fingers flex to push; at the release frame the fingers begin
to extend, and over the following frames they point at the target.

Written as the engine's other authored quantities are: phases of a normalised
progress through a named window, with the window anchored on the **release
frame** rather than on a clip fraction, because that is where the event is.

| parameter | what it sets | inferred FROM |
|---|---|---|
| `flickWindowFrames` | N, the contact frames the flick occupies | **the footage**: the only source with a timescale. 30 fps and a 2.5–5.4 m/s hand bound it; the engine runs at 60, so N is read off the footage and doubled, and the paper states that doubling |
| `wristFromDegrees` | the wrist angle at the window's start | **the engine's own solve**: it is where the wrist already is, 130.7 on the chest pass, so the flick starts from the shipped pose and does not move it |
| `wristToDegrees` | the wrist angle at the release frame | **NOT SOURCED. A coach must set it.** No manual number exists, the footage cannot read an angle, and biomechanics literature is not in this repository |
| `fingerFromDegrees` | the finger flexion at the window's start | **the engine's own solve**: 119.7, the grip the possession model already holds |
| `fingerToDegrees` | the finger flexion at the release frame | **NOT SOURCED. A coach must set it.** Same reason |
| `followThroughFrames` | how long after release the fingers take to point | **the manual**, weakly: "fingers up" and "hand behind the ball" describe an end state and give no duration. A number here is a coach's |
| `pointsAt` | what the extended fingers aim at | **the manual**: "Keep hand behind the ball and fingers up", and the ball's own launch target, which the engine already computes |

**Four of the seven have a source in this repository. Three do not, and they are
named rather than filled.** Two of those three are the angles the whole flick is
about. That is the honest position: the manual says the wrist and hands make the
pass and never says how far.

**Per pass kind, not one set.** The manual distinguishes them — "fingers up" for
the high and wide passes, "fingers will turn slightly to the side" for the low
wide, "keep ball low" for the bounce — so `pointsAt` at least is per drill, and
the angles may be. The parameters therefore live in each technique file, which
is **gate 4**: this model cannot be applied to a drill without Marius's ruling,
and the paper asks for the ruling rather than assuming it.

## 5. How the wrist-at-release decision folds in

`FAN_AND_RELEASE_PACK.md` puts two options on the table and this lane did not
choose between them. **The flick changes the arithmetic of that choice**, so it
should be decided once, here.

|  | option A, what ships | option B, ball-relative |
|---|---|---|
| chest pass, vertices inside | 190 at −20.27 mm | **0 at 0.00 mm** |
| bounce pass | 120 at −17.76 | 6 at −0.59 |
| overhead pass | 78 at −9.55 | 32 at −2.62 |
| the cost | the ball passes through the hand | the wrist sits 34 to 49 mm from where `arms` asked |

**The flick makes A worse and B cheaper.** A flick flexes the fingers *into* the
ball in the frames before release, so under option A — where the wrist leaves
the ball in one frame — the digits are driven further inside at exactly the
frames the flick occupies. Under option B the ball keeps deciding for that
frame, so a finger that flexes stays on the surface by construction.

**The recommendation is that the flick and option B are decided together**, and
that if the flick is built on option A it must carry a guard on the digit
intersection, because it will deepen the finding Chuck already recorded.

## 6. What the receipt would read, and what a coach would grade

**Two new measures**, both in the units they are measured in, both declared:

- `leftWristFlexionDegrees` / `rightWristFlexionDegrees` — the elbow–wrist–
  knuckle angle. Degrees.
- `leftFingerFlexionDegrees` / `rightFingerFlexionDegrees` — wrist–knuckle–tip
  at the middle finger. Degrees.

**And one rate, which is the quantity the footage can check:**

- `wristSpeedCmPerS` — the wrist's own speed. **Centimetres per second, a unit
  this engine does not yet have**, so `MEASURE_UNITS` gains it with its own band
  floor derived in its own regime. It must not borrow the degrees floor or the
  centimetre one; a speed is neither.

**What a coach grades**: the wrist and finger angles **at the release frame**,
and the change across the flick window. Not the speed — the speed is the
footage's check on the engine, and a band on it would be graded against a
figure the athlete's technique does not directly set.

**A caution this lane has earned.** `footHeightGapCm` spans 0.00 to 1.22 cm on
its own drill against bands of 0–14 and 0–6, so its three checkpoints have never
been shown able to fail. A flick checkpoint must be swept before it is banded,
or it joins them.

## 7. What a mutation sweep looks like

The lower body has taught this lane that every planted increment can land in a
different basin, and the height measure's own sweep found one **at the shipped
value**. So:

1. **A progressive sweep, spacing stated**, of `wristToDegrees` and
   `fingerToDegrees` separately, at least seven points each, run on a **copy** of
   `spikes/movements/` so gate 4 is untouched — the pattern
   `sweep_ball_height.py` already uses.
2. **Joint steps beside every point**, split into digits and body: the digits
   re-wrap the ball at every arm angle, so the largest single joint step is
   almost always a finger and says nothing about the body finding another
   solution.
3. **A fine sweep across the shipped value**, because the coarse one alone
   published a basin last time and the shipped value is exactly where it sat.
4. **The digit intersection printed at every point**, so a flick that improves
   the angle while driving the thumb further into the ball is visible rather
   than discovered later.
5. **The instrument refuses a flat sweep** — a span under a stated floor means
   the lever is not reaching the solve, not that the lever does nothing.

## 8. What this paper does not claim

- **It does not claim the flick will change ball speed.** The ball's speed is
  authored; the mechanism is not connected. That is question one for Marius.
- **It does not claim the engine's hand is wrong.** It is flat because nothing
  asked it to move, and no coach has been asked whether the difference matters
  at the size a manual figure is printed.
- **It supplies no angle.** Two of the model's seven parameters are the angles
  the flick is about and neither has a source; a number invented for them would
  be this ledger's own recurring fault in a new place.
- **It has not been swept.** Nothing here is proven able to fail.
- **It does not explain its own exception, and this lane owns the check.**
  `one_hand_high_pass` is the only one of the four whose wrist moves MORE through
  contact (4.71 degrees) than after release (0.82), and it is also the only one
  the engine solves RIGHT-handed. PR #46 (`ac240b2`, 2026-09-01) fixed a sign in
  `finger_wrap.spread_fingers` on exactly that hand. **No mechanism is
  established here and none is claimed.** That fix changed the finger SPREAD
  (`middle1_ry`, 0.18, negated on the right until then) and this paper measures
  wrist and finger FLEXION, which is a different quantity. The two are not
  independent either: a spread rotation on `middle1` moves `middle3` out of the
  flexion plane, so it can move the angle measured here. **The experiment is
  named**: solve the drill with the pre-#46 sign restored and see whether the
  exception follows the sign. Until that runs, this is a coincidence with a
  plausible route, and not a finding.
- **Half of that exception now has a simpler explanation, found while correcting
  section 1.** `one_hand_high_pass` is the only drill whose wrist peaks AT the
  release frame, 5.61 m/s, rather than one frame after it. Its post-release
  travel is small because the motion has already happened. **That accounts for
  the wrist half of the exception with no appeal to a sign at all**, and it
  demotes the PR #46 hypothesis to the second candidate. **The finger value is
  still unexplained** — 133.04 degrees before release against about 119 on the
  other three, on the one hand whose spread that fix changed — and the
  experiment named above still settles that half.
- **And the video lane has narrowed what that experiment must explain.** Its
  fastest measured release, 5.39 on the image scale, is a TWO-HANDED one, and
  the athlete's one-handed releases are not the fastest in its set. The engine's
  one-handed drill peaks at 5.61 AT the release frame. **So whatever the sign
  experiment settles has to explain a drill that is early AND fast, and fast in
  the category where the athlete is slower** — not merely a drill that behaves
  differently from the other three.

## 9. The ruling: MECHANICAL, and the unit it defines

**Marius ruled on 2026-09-08: mechanical.** The release timing is the unit. The
cosmetic hand sits on top of it afterwards. He is holding Erin's page until he
is satisfied with what she is given, so the constraint on this unit is that it
lands BEFORE she grades.

**THE REASON IS NOT THE SPEED, AND THIS PAPER HAD MISSED IT.** Both branches
below argue about whether the arm can produce an athlete's release speed.
Marius's reason is different and better: **retiming moves the arm inside the last
frames of contact, and that window is exactly what Erin's checkpoints measure.**
A cosmetic build shipped now would have her grade a build we already intend to
change. She grades once, against the build we mean to keep.

**That reason does not appear anywhere in the two branches below**, which
weighed figure quality against implementation cost and never asked which window
the coach's instrument reads. The sections are kept as written, because the
ruling was made against them and a superseded argument that is deleted cannot be
checked.

### The record: what the cosmetic branch would have cost

**What it costs.** The figure a coach sees becomes right and the mechanism stays
absent: the hand will move through the last frames of contact and the ball will
still receive 6 m/s from a constant at the release frame. Anyone reading the
engine afterwards — a coach, a later lane, a reviewer — may reasonably take the
moving hand as the cause of the speed, because that is what a moving hand means
everywhere else. **The engine would then look like it models a throw and not do
it**, which is a worse position than today, where the flat hand at least does
not imply the mechanism.

**What it needs**: one sentence in the drill files and the ledger saying the
hand does not drive the ball, and a guard that fails if a later change makes the
launch depend on the hand without a ruling.

**What it is worth**: Marius's own words are that the difference is small but
crucial for the FIGURE. A cosmetic flick delivers exactly that and nothing else,
at a cost measured in one unit of work.

### The record: what the mechanical branch was costed at

**What it costs.** It is not this unit. The ball's speed today comes from
`author_flight.DEFAULT_SPEED_CM = 600`, a constant with no provenance already on
the coach agenda. Delivering it from the body means the possession model stops
assigning a velocity and starts reading one, which changes: how a release is
authored; how every existing flight was calibrated, since all eight techniques
derive 600 from the same constant; and the whole library's ball trajectories,
because a hand-driven speed will not land on 600.

**And the arm does reach that speed. It reaches it one frame too late.** An
earlier draft of this section read the held frames alone and said "the arm
cannot deliver it as it stands". The same wrist runs at 2.45 to 4.42 m/s one
frame after the release on three drills, and at 5.61 m/s in the release frame
itself on the fourth, which overshoots the athlete's band rather than reaching
it. **That sentence is withdrawn, and this section had rested its cost estimate
on it.**

**What the correction changes: the mechanical option is smaller than this paper
first costed it.** Not small. The speed after the release comes from an ease-out
on a follow-through aim point, `out = 1 - (1 - t)^2` in `possession.py`, and not
from a throw, so the unit would have to make the engine throw rather than shift
an existing curve. But **the specific objection that the arm is incapable of the
speed is gone**, and with it the argument that the mechanical route needs a new
capability before it can even be considered.

**What the correction does not change.** The ball's launch is still assigned
from `author_flight.DEFAULT_SPEED_CM`, every existing flight is still calibrated
against that constant, and the 600 still has no provenance. Those remain the
mechanical option's real cost.

**If the answer is mechanical, the unit starts at the arm's timing through
contact, and not at the digits.**

**What it is worth**: a ball whose speed a coach can change by changing
technique, which is the thing the engine cannot do today, and the only route to
grading "power" at all.

### This lane's recommendation, and why it is superseded

**This paper recommended the cosmetic model. That recommendation is
superseded.** It is left here in full rather than deleted, because a
recommendation that is quietly removed cannot be checked against the ruling that
overrode it. It read:

> The two are not alternatives at the same scale. The cosmetic model is one unit
> and it is the one Marius described. The mechanical model is a rework of the
> ball's launch and belongs on the agenda beside the 600's provenance, not
> inside a hand unit. The recommendation is the cosmetic model, built so it
> cannot be mistaken for the other.

**Where it was wrong.** It weighed the two by size and by what a coach would
see, and it never asked WHICH FRAMES the coach's instrument reads. Erin's
checkpoints measure the last frames of contact. That is the same window a
retiming moves. So the cosmetic model is not the smaller unit at all once
grading is counted: it is a unit that would have to be graded twice.

**The one argument it made that survives is a cost, not a reason against.** A
hand that moves while the ball's speed is still assigned would look like a
throw the engine does not perform. Under this ruling that is not a risk to be
avoided by staying still; it is a state the unit must not stop in. **The launch
must stop being assigned in the same unit that makes the hand move**, or the
build in between is exactly the misleading one this paper warned about.

### What the mechanical unit is

Ordered, and the first three read before any code is written.

1. **The provenance of the authored 600.** `author_flight.DEFAULT_SPEED_CM` is
   one constant for the whole library. The bounce pass's own ball file already
   records that it has no coach, no measurement and no source, and that it is
   measurably wrong there: 600 cm/s needs a vertical of +95 cm/s, so the ball is
   thrown UPWARD at a floor below a release of 734 mm. What does the manual say
   about pass speed, if anything, and what would a derived launch replace it
   with. **The video lane is measuring the athlete's ball speed at release from
   the footage in parallel**, which would be the first real source this constant
   has ever had. This step leaves the slot for it and does not wait on it.
2. **What retiming moves in the graded window.** A measurement and not a build:
   on the chest pass, shift the hand's acceleration to before the release frame
   and report **which graded checkpoints move and by how much, per checkpoint**,
   against the shipped build. That number is the size of the unit, and it is
   what Erin would have to re-grade if this landed after her. Run the way the
   sweeps are run: on a copy, gate 4 untouched, joint steps beside every point,
   and a refusal on a flat result.
3. **Why one pass already times it correctly.** `one_hand_high_pass` peaks AT
   the release frame at 5.61 m/s, above the athlete's fastest one-handed
   release. **Either that is the template for the other three, or it is a defect
   that happens to flatter the engine.** Find out which and say which. It is the
   cheapest possible answer to "can the engine do this at all", and the engine
   may already contain it.

Then, on those three readings and Marius's word on the launch: the possession
model stops assigning the launch and derives it, the flights are re-calibrated,
the receipt rows, the guards, the sweep. **The cosmetic hand and its two angles
come last**, and they now belong at the coach morning where Erin picks them from
renders rather than in this paper.

## Questions for Marius, in order

1. **ANSWERED 2026-09-08: MECHANICAL.** The release timing is the unit; the
   cosmetic hand follows it. Marius's reason is that retiming moves the arm
   inside the window Erin's checkpoints measure, so a cosmetic build would make
   her grade a build we intend to change. Refer to section 9.
2. **The two angles.** `wristToDegrees` and `fingerToDegrees` have no source.
   A coach's judgment, or the unit waits for faster footage.
3. **Option A or option B at the release frame**, decided with the flick rather
   than before it.
4. **Gate 4**: the parameters live in the technique files, so the unit needs the
   ruling before any drill carries them.
5. **The clip contract.** Fifteen channels carry no hand. A flick reaches the
   coach's figure and the receipt and stops there unless the contract gains
   channels, which is a boundary this lane does not cross alone.

## The instrument

Every figure in section 1 comes from one script, committed with this paper, and
re-runs from the repository. The manual quotations are line-cited above and can
be read at `references/202526 updated coaches manual/`.
