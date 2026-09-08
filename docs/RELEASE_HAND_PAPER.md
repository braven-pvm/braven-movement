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

## The instrument

Every figure in section 1 comes from one script, committed with this paper, and
re-runs from the repository. The manual quotations are line-cited above and can
be read at `references/202526 updated coaches manual/`.
