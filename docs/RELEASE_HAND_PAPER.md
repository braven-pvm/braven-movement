# The release hand: what the engine does, what the manual asks, and a model

A paper for Marius, prepared by the movement lane on 2026-09-08 from `1c3d9d7`.
**It proposes a model and changes nothing.** No engine file is touched, and
`spikes/movements/` is gate 4 and untouched.

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

**THE HAND IS AN ORDER OF MAGNITUDE SLOWER THAN THE BALL IT RELEASES.** Over
the last eight contact frames, all four passes:

| drill | hand speed through contact | ball speed after release |
|---|---|---|
| `chest_pass` | 32.8 to 36.4 cm/s | 602.0 cm/s |
| `overhead_pass` | 46.4 to 52.6 | 603.5 |
| `bounce_pass` | 34.0 to 35.4 | 604.3 |
| `one_hand_high_pass` | 63.3 to 78.6 | 621.2 |

**The ball leaves 8 to 18 times faster than the hand that released it.**

### The engine's wrist beside the athlete's, in the same units

The comparison the clip cannot supply, because the clip carries no wrist at all
(below). This is the wrist joint's own speed **from the solve**, over the last
eight frames of contact, in **metres per second**:

| | wrist through contact | the filmed athlete |
|---|---|---|
| `chest_pass` | **0.33 to 0.36 m/s** | |
| `overhead_pass` | 0.46 to 0.53 | |
| `bounce_pass` | 0.34 to 0.35 | |
| `one_hand_high_pass` | 0.63 to 0.79 | |
| | | **3.4 to 4.3 m/s through the throw** |

**The engine's wrist runs at a fifth to a thirteenth of the filmed hand.** No
forward-kinematics rebuild is involved: these are the solved joint positions,
differenced frame to frame at the track's own rate.

**A flick added to a wrist travelling at a tenth of the filmed speed will not
reach that band**, and the gap is a statement about the whole arm's timing
through the last frames of contact rather than about the wrist alone.

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

**The third reading bounds the channel.** A hand channel fed by today's solve
would transmit a constant and a post-release swing, and neither is the flick
Marius asked about, so the channel is worth adding only together with a release
model that puts something in it.

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
- **The hand SPEED is measurable**: about **3.4 to 4.3 m/s through the throw**,
  with that lane's pack to follow and the engine's release beside it.
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

Second, and larger: the engine's hand runs at **0.33 to 0.79 m/s** through
contact against the footage's **3.4 to 4.3 m/s**. That is a factor of five to
thirteen, and it is a statement about the whole arm's timing, not about the
wrist. **A wrist flick added to a hand travelling at a tenth of the filmed speed
will not reach that band**, and this paper does not pretend otherwise.

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
| `flickWindowFrames` | N, the contact frames the flick occupies | **the footage**: the only source with a timescale. 30 fps and a 3.4–4.3 m/s hand bound it; the engine runs at 60, so N is read off the footage and doubled, and the paper states that doubling |
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

## 9. Mechanical or cosmetic: the choice, and what each costs

A release model that only bends a flat hand would leave the video lane's
finding untouched. So the paper must say how the launch speed would be
delivered, or say plainly that it stays assigned. Both are stated; neither is
chosen here.

### If the launch stays ASSIGNED and the hand motion is cosmetic

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

### If the launch is to be DELIVERED by the arm and hand

**What it costs.** It is not this unit. The ball's speed today comes from
`author_flight.DEFAULT_SPEED_CM = 600`, a constant with no provenance already on
the coach agenda. Delivering it from the body means the possession model stops
assigning a velocity and starts reading one, which changes: how a release is
authored; how every existing flight was calibrated, since all eight techniques
derive 600 from the same constant; and the whole library's ball trajectories,
because a hand-driven speed will not land on 600.

**And the arm cannot deliver it as it stands.** At 0.33 to 0.79 m/s the hand
carries a small fraction of the energy a 6 m/s ball needs, so the unit would
have to change the ARM's motion through contact and not only the wrist's. That
is the finding the wrist table above points at.

**If the answer is mechanical, the unit starts at the arm's timing through
contact, and not at the digits.**

**What it is worth**: a ball whose speed a coach can change by changing
technique, which is the thing the engine cannot do today, and the only route to
grading "power" at all.

### This lane's reading

**The two are not alternatives at the same scale.** The cosmetic model is one
unit and it is the one Marius described. The mechanical model is a rework of the
ball's launch and belongs on the agenda beside the 600's provenance, not inside
a hand unit.

**The recommendation is the cosmetic model, built so it cannot be mistaken for
the other**: the hand moves, the ledger and the drill files say in terms that
the ball's launch is assigned and the hand does not drive it, and a guard holds
that. If Marius wants the mechanism, this paper is the wrong size for it and the
right first step is the 600.

## Questions for Marius, in order

1. **Is the flick to be cosmetic or mechanical?** If the ball's speed is to come
   from the hand, that is a change to the possession model and a much larger
   unit than this one. If it is to look right, this model is the shape.
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
