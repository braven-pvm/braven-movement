# The wrist and the pace: two properties of the movement nothing authors

Marius watched the chest-catch player beside the real footage and reported two
things: that the animation "feels like 80% speed", and that the "wrist
action/flick is missing — subtle but clearly lacking".

Both are readings of quantities the engine never set on purpose. Neither is a
tuning question, and neither has a fix in this document.

Measured on `02b25cd`. The video figures come from the video lane on the same
sample session.

---

## 1. The wrist moves, and it cannot matter

**The expectation was that the wrist would read zero.** It does not, and the
instrument was checked before that was believed.

### The instrument was proved first

A measure that reads zero on a real flick would report "no flick" on every
input. So a flick was PLANTED into the solved motion — 40 degrees of wrist
rotation over the six frames ending at the release — and the same measure was
asked to see it.

| | bend range over the release window | peak rate |
|---|---|---|
| the shipped solve | 42.91 to 61.74 degrees | 193.3 deg/s |
| with a flick planted | 15.37 to 61.74 degrees | **1736.5 deg/s** |

The instrument reads the planted flick at nine times the shipped rate. A zero
from it would have meant something. **It did not read zero.**

### What the shipped solve actually does

The hand bends against the forearm through every release, on every drill and
both hands:

| drill | side | range | peak rate | peaks at |
|---|---|---|---|---|
| `deflect_high` | l | 24.46 deg | 225.0 deg/s | **2 frames after release** |
| `deflect_high` | r | 22.19 | 342.8 | **4 after** |
| `hooks_jump_pull_in` | l | 32.79 | 299.1 | **3 after** |
| `hooks_jump_pull_in` | r | 32.81 | 299.0 | **3 after** |
| `two_hand_catch_chest` | l | 34.66 | 310.4 | **3 after** |
| `two_hand_catch_chest` | r | 34.67 | 310.4 | **3 after** |
| `two_hand_snatch_straight_back` | l | 24.97 | 224.7 | **2 after** |
| `two_hand_snatch_straight_back` | r | 25.01 | 224.7 | **2 after** |

**Twenty-two to thirty-five degrees of wrist movement. It is not a still hand.**

### The finding is the timing, not the amount

**Every one of those peaks falls AFTER the ball has left**, by two to four
frames — 48 to 96 milliseconds.

A flick drives the ball. It has to reach its greatest speed at or before the
moment the ball goes, because after that the hand cannot influence anything.
The engine's wrist reaches its greatest speed once the ball is already gone.
That is a follow-through.

### And it could not be a flick, whatever it did

The ball's outgoing velocity comes from `return_velocity`, whose four inputs
are the ball track, the stance frame taken at phase 0, the ball's carried
position, and the frame timing. **No property of the hand enters it.** The
carried position follows her chest, not her wrist.

So no wrist motion of any size or timing could change how the ball leaves.
**A flick is not merely unauthored here. It cannot be expressed.** The hand
moves; the ball does not know.

That is why it reads as missing to a coach while the hand is visibly moving:
what is absent is not the motion but its consequence.

### What is not settled

- **Whether a coach wants a flick modelled at all.** The manual's cue for this
  drill is "with wrist and hands pass the ball", and the ledger already records
  that cue as having NO instrument. This is that gap, measured.
- **What it would take.** Making the hand drive the ball is engine work on the
  possession model, not a weight and not a key. It is not proposed here.

---

## 2. The pace has no author

**The engine takes 2.24 times the athlete's time** on the stretch from ball
contact to the deepest point of the hold, where her elbows are most folded.

| | measurement |
|---|---|
| engine, from its own authored landmarks | contact phase 0.55 at frame 53 to pull_in phase 1.0 at frame 97, at 60 fps: **0.7275 s** |
| athlete, three strip-proved repetitions | 0.295, 0.400, 0.325 s, median **0.325 s** |
| ratio | **2.24x her time**, range 1.82 to 2.47 |

The engine plays that stretch at about 45 per cent of her speed. Marius said
80 per cent; the direction is right and he understated it.

**NOT CLAIMED: the reach.** Ready to contact reads 1.08 and 2.02 on two
repetitions. Two readings a factor of two apart are not a measurement.

### Where the pace comes from

`frames` and `framesPerSecond` are read straight out of each motion file. Both
are TYPED. Nothing derives them and nothing measures them.

| drill | frames | seconds |
|---|---|---|
| `deflect_high` | 88 | 1.450 |
| `double_foot_landing` | 110 | 1.817 |
| `hooks_jump_pull_in` | 108 | 1.783 |
| the other five | 98 | 1.617 |

Every drill runs at 60 frames per second, and **that** choice is documented. A
`rateNote` in each motion file explains 60 rather than 24, because at 24 a real
pass crosses the reachable span in two frames. It ends:

> Nothing about the movement changes with the rate; there were not enough
> frames to hold it.

So the RATE was a resolution decision, and the note explicitly disclaims any
effect on pace.

**THE FRAME COUNT, WHICH IS THE PACE, HAS NO NOTE ANYWHERE.** Not in the motion
files, not in the documents, not in the code. Five of the eight drills share 98
frames exactly, which reads as one default rather than eight judgements about
how long each drill takes.

Nothing in the repository would have contradicted a coach who said the movement
is slow, because nothing ever set its speed on purpose.

---

## Both findings are the same shape

A property of the movement that nothing authors and nothing grades.

The ball speed is the third of them: one constant, 600 cm/s, with no source,
which at the manual's own 7 m produces a ball peaking at 302 cm when a netball
goalpost is 305.

In each case the engine is not wrong so much as silent. It made a choice
nobody recorded, and a coach is reading the choice.

## Provenance

Measured on `02b25cd` with a clean tree. The wrist figures come from the solved
joint positions rather than from parameters, so they do not assume which
parameter a flick would live in. The planted-flick control is in the record
because a zero from an unchecked instrument would have been worthless. The
video figures are the video lane's, on matched stretches, and the engine side
of the ratio is read from the engine's own authored landmarks.
