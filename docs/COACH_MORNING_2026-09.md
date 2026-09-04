# The coach morning: what to ask, and the evidence behind each question

Every figure here was re-measured on `ac240b2` with a clean tree. Where an
older document gives a different number, both are shown with the build each was
read on. Nothing in this document changes any code.

The questions are for Erin and Marius. They are written to be answerable by a
coach watching the athlete, not by reading a number. Where the engine has an
opinion it is stated as a measurement and never as a recommendation.

Seven items carry evidence. One is STRUCK, because it was raised on a
measurement the solver read from a second solution for that drill. Three carry
no engine evidence, and say so.

**One section of item 2 is withdrawn, and the withdrawal is written out rather
than tidied away.** The elbow-width question is unchanged; what was wrong was a
claim about how it had been framed. Refer to `docs/CLAVICLE_ARTEFACT.md`.

---

## 1. Which frame is the release?

**The question.** When she passes the ball back, which moment should the engine
be graded on: the instant the ball leaves her hand, or the end of the
follow-through?

**Why it is being asked.** Four checkpoints fail today. All four are inside
their bands at the moment the ball leaves, and outside only at the frame where
they are graded.

| drill | phase | graded at | reading there | at the ball's departure | band |
|---|---|---|---|---|---|
| `deflect_high` | send_on | frame 87 | **35.78 OUT** | frame 70, **98.72 in** | 45 to 115 |
| `hooks_jump_pull_in` | release | frame 107 | **49.98 OUT** | frame 102, **99.29 in** | 50 to 120 |
| `two_hand_catch_chest` | release | frame 97 | **40.89 OUT** | frame 90, **98.02 in** | 55 to 115 |
| `two_hand_snatch_straight_back` | return | frame 97 | **40.86 OUT** | frame 88, **86.75 in** | 45 to 105 |

The measure is `leftElbowFlexionDegrees`, in which a straight arm is zero. The
graded frame is 5 to 17 frames after the ball has gone.

**Three independent findings point at the same place.**

1. The reading above: in band at the pass, out of band at the follow-through.
2. No evidence gathered so far names a band as the fault. The bands were the
   first suspect and the investigation moved off them; that is weaker than a
   proof they are right, and it is stated as the weaker thing.
3. A separate timing defect was found and measured. Correcting it makes the
   follow-through more physically correct, and makes the graded reading WORSE
   on all four. That is what an anchor in the wrong place does. Refer to
   `docs/RELEASE_TIMING_COST.md`.

**Not settled.** Whether a coach grades a pass at the ball's release or at the
end of the arm's travel. That is a coaching judgement and the engine has no
view on it. If the anchor moves, item 9 must be decided with it, because each
changes the other's evidence.

---

## 2. How wide should the elbows sit when she takes the ball?

**The question.** Watch the two previews side by side. Which elbow width looks
like the athlete in the manual's photographs?

**What the dial does.** One number sets it, `ELBOW_POLE_ANGLE_DEGREES`, at 31.3
today. The manual's figure, read from photographs, is 38.6 cm between the
elbows at contact.

On the six drills that put BOTH hands on the ball:

| | mean | narrowest | widest |
|---|---|---|---|
| at 31.3, today | **36.43 cm** | 28.90 | 40.37 |
| at 37.3, previewed | **38.42 cm** | 30.57 | 42.37 |

The manual says 38.6. At 31.3 the gap is 2.17 cm. At 37.3 it is **0.18 cm**.

Every cell in this table is read on one build, with the locked parameters
pinned, and the whole row was re-measured rather than the mean alone. An
earlier version mixed two builds: it read 36.40 and 38.45 for the means, and
then kept 30.63 and 42.41 from the older build after the means were
corrected.

**WITHDRAWN, 2026-09-02.** This section said:

> **A correction to how this question has been framed.** It has been asked as
> "which of two populations does 38.6 describe". THE SECOND POPULATION IS NOT A
> POPULATION. It is two drills:
>
> | drill | elbow width at contact |
> |---|---|
> | `hooks_outside_hand` | 19.01 cm |
> | `one_hand_snatch_to_other_hand` | 59.96 cm |
>
> They sit 40.95 cm apart, with a standard deviation of 28.96 cm. Their mean of
> 39.48 cm describes neither drill: it lies about 20 cm from each. The six
> two-handed drills are a real group by comparison, spread 11.40 cm with a
> standard deviation of 4.08.
>
> So the choice is not between two populations. It is whether 38.6 describes
> the drills that put both hands on the ball, and the one-handed pair belongs
> outside that comparison rather than weighed against it.

**That was wrong.** `hooks_outside_hand` read 19.01 cm because the solver had
reached a second solution for that drill — one of two, about 33 degrees apart
in stance — and the parameter set that shipped was the only one measured that
reaches it. Refer to `docs/CLAVICLE_ARTEFACT.md`.

**The word "population" is not a claim two points can carry, in either
direction**, and the withdrawn paragraph's standard deviation of 28.96 was the
same error as the 3.63 that first replaced it. What the measurement supports:

> Two one-handed drills sit 5.13 cm apart, at **54.83 and 59.96 cm**. Each is
> 18.4 to 23.5 cm above the two-handed mean of 36.43, and 14.5 to 19.6 cm above
> that group's widest member at 40.37.

The question keeps its original form: does 38.6 describe the drills that put
both hands on the ball, or the two that put one?

| population | drills | mean elbow width at contact |
|---|---|---|
| both hands on the ball | 6 | **36.43 cm** |
| one hand on the ball | 2 | **57.39 cm** |

**A warning about the preview.** On `hooks_outside_hand` the 37.3 preview moves
the elbow width by 37.91 cm. That is the FREE arm relocating rather than the
elbow width changing, and it would dominate anything a person watched on that
drill. The comparison drill is `deflect_high`, where both hands are on the ball
and nothing else moves.

**The guard that this section said it had dissolved was right.**
`test_elbow_pole.py` holds a tripwire on the distance between the two means.
This document argued its premise had dissolved, because one side was not a
population. It had not. That guard, together with the turned-drill clause in
`test_waiting_hand.py`, is what FOUND the artefact: both went red when the
locked axis was pinned, and reading why is what produced
`docs/CLAVICLE_ARTEFACT.md`.

Leaving it untouched was the right call for the wrong reason. It now records
the whole history, artefact included: about 8 cm, then about 20, then 3.09 as
an artefact reading, then 20.96.

**Not settled.** Everything. The 0.15 cm agreement is the engine matching a
figure read off a photograph. No coach has yet said the wider elbow looks
right, and a number agreeing with a number is not a coach agreeing with a pose.

---

## 3. How fast should the ball arrive, and how fast should she send it back?

**The two questions.** Is 6.0 metres per second a drill feed? And should she
return the ball at the pace it arrived?

**What the engine does.** Every ball in the library is fed at one speed. All
eleven ball files carry a horizontal launch speed between 599.3 and 600.4
centimetres per second, because one constant authored them all:
`author_flight.DEFAULT_SPEED_CM = 600.0`.

That constant has no coach, no measurement and no source. Its own comment says
"A drill feed. A game pass is faster", so the engine already claims to feed
below match pace and nobody has agreed to that.

She then returns the ball at the speed it arrived, because the outgoing throw
derives its speed from the incoming flight. That reading of the manual's cues
is marked PROVISIONAL in the code, and no coach has confirmed it.

**Not settled.** Both questions. Refer to `docs/BALL_SPEED_PROVENANCE.md`.

---

## 4. Do her fingers close too fast when she takes the ball?

**The question.** Watch the catch at quarter speed. Does the hand close like a
hand?

**What the engine does.** The fingers change by up to **89.95 degrees in a
single frame**, and it happens at the contact frame on every drill in the
library.

| drill | worst one-frame change | where |
|---|---|---|
| seven of the eight | 89.95 degrees | the contact frame |
| `hooks_outside_hand` | 88.18 degrees | the contact frame |

At 60 frames per second that is one sixtieth of a second from open to closed.

**Not settled.** Whether it reads acceptably to a person watching. If it does
not, the change is a ramp on the curl, which is a look change rather than a
defect.

---

## 5. Does the second hand travel too far to meet the ball?

**The question.** Erin's note asks that the other hand does not go away from
the centre of the body towards the ball. Watch the second hand join. Does it go
too far?

**What the engine does.** On the two drills where one hand takes the ball and
the other joins, the free hand goes out ahead of her shoulders and comes back:

Measured from the midpoint of her two upper-arm joints, which is the origin
`docs/KNOWN_ISSUES.md` used, so the two readings can be compared at all:

| drill | at contact | furthest out | back to | travel |
|---|---|---|---|---|
| `one_hand_snatch_to_other_hand` | 11.85 cm | 25.97 cm | 12.07 cm | **14.12 cm** |
| `hooks_outside_hand` | 3.43 cm | 14.33 cm | 3.48 cm | **10.90 cm** |

**WATCH THE TRAVEL, NOT THE HEIGHT ABOVE ZERO.** "Ahead of her shoulders" needs
an origin, and the number changes completely with the choice while the movement
does not. On the first drill, across four defensible origins, the contact
reading ranges from 7.46 to 20.66 cm and the travel stays between 14.12 and
14.67. The travel is the movement. The level is a choice of where to measure
from.

**Against the older reading in `docs/KNOWN_ISSUES.md`**, which records 11.9 out
to 26.0 and back to 12.0 on the first drill and 11.8 to 25.1 to 12.0 on the
second, both introduced in `1106617` on 2026-08-27:

- **The first drill has not moved.** 11.85 to 25.97 to 12.07 against 11.9 to
  26.0 to 12.0. The older reading reproduces on `ac240b2`.
- **The second drill has moved**, and it is the drill the hand fix changed most.
  Travel 10.90 cm against 13.3, and it sits closer in.

**A correction to an earlier draft of this document.** It gave 17.6 and 13.1 cm
at contact and said the hand now sits further forward on both drills. Those
figures came from a DIFFERENT ORIGIN — the trunk frame's own shoulder places
rather than the solved upper-arm joints — so the difference was in the
measurement and not in the athlete. One drill had not moved at all. Retracted
rather than corrected in place, because a coach could have repeated it.

The movement is smooth either way. The hand ramps out over about thirteen
frames and back over about thirty-nine.

**Not settled.** Whether travel of this size is what the cue forbids. If it is,
the change is to the `join` and `gather` keys, which is a key retune and goes
to Marius with this evidence before anybody touches it.

---

## 6. Is she showing her arm span while she waits?

**The question.** Watch the ready position. Is she showing the passer a target?

**What the engine does.** Wrist to wrist at the first frame:

| drill | wrist to wrist |
|---|---|
| `deflect_high` | 18.29 cm |
| `hooks_jump_pull_in` | 19.83 cm |
| `double_foot_landing` | 19.91 cm |
| `two_hand_snatch_pull_in` | 20.08 cm |
| `two_hand_snatch_straight_back` | 20.08 cm |
| `two_hand_catch_chest` | 20.10 cm |
| `one_hand_snatch_to_other_hand` | 32.15 cm |
| `hooks_outside_hand` | 45.68 cm |

Six of the eight hold their hands about 20 cm apart. The manual's cue for the
snatch asks for the arm span to be shown.

**Not settled.** Whether 20 cm is a shown arm span or a pair of hands held
together. No checkpoint grades this today, so nothing in the engine will notice
if the answer is no.

---

## 7. STRUCK. There is no library-content gap

**This item asked whether the library should hold a drill that begins turned
away from the passer. IT ALREADY DOES.** The question was raised on a
measurement that was wrong, and it is struck rather than reworded, because
there is nothing left to decide.

What it said: `hooks_outside_hand` had begun 48.23 degrees turned and now began
at 15.44, so the athlete had straightened up and the library had lost the only
shape that could exercise the engine's reach rule on a turned athlete.

**She never straightened up.** That drill has two solved poses about 33 degrees
apart in ready-stance turn, and the parameter set that shipped was the only one
measured that reaches the 15 degree pose. She stands at 48.22 degrees under the
correction, where her track always put her. The library holds what it always
held.

| drill | furthest turned at any frame before contact |
|---|---|
| `hooks_outside_hand` | **48.22 degrees** |
| `deflect_high` | 0.78 |
| `one_hand_snatch_to_other_hand` | 0.53 |
| the other five | 0.05 or less |

Refer to `docs/CLAVICLE_ARTEFACT.md`. **Nothing is asked of the coach here.**

---

## 8. The elbow dial's number

Item 2 is the question a coach answers by looking. This is the number that
follows from the answer: `ELBOW_POLE_ANGLE_DEGREES`, 31.3 today and 37.3
previewed. It needs no decision of its own. It is listed so that nobody is
surprised that answering item 2 sets a constant.

---

## 9. The release timing fix, which waits on item 1

A defect is found, measured and NOT fixed. The flight of the passed ball
measures its elapsed time from the release FRAME rather than from the release
KEY, so the ball is nearly stationary for a fraction of a frame at the moment
she throws it. Refer to `docs/RELEASE_SEAM.md`.

It is not a coaching question, because it has a determinate right answer. It is
here for two reasons. Correcting it moves what a person sees on every drill
that passes the ball back. And **it must be decided with item 1**: if the
anchor moves, the cost table for this fix is recomputed against a different
frame.

---

## 10. Which passes does the board need, and which does the manual teach?

Added 2026-09-02 by the content lane, with the first two passes authored.

**THE TWO LISTS DO NOT MATCH, AND NEITHER IS WRONG.**

The manual teaches eight passes: overhead, 1 hand high, 1 hand low wide, 1 hand
wide, bounce, underarm, lob and fake. Its syllabus lists a ninth, "Double hand
chest", in two practice plans and gives it no technique block.

Braven Tactics' `RELEASE_KINDS` names four: `chest-pass`, `shoulder-pass`, `lob`
and `bounce-pass`. A board can only ask for a clip whose class is in that list.

**They overlap on two: `lob` and `bounce-pass`.**

- **`shoulder-pass` has ZERO occurrences in the manual.** Searched in full. The
  board can ask for a pass the manual never teaches.
- **`overhead` is absent from the vocabulary.** It is the manual's most fully
  documented pass, second in its syllabus, and it is now authored and exported
  as `pass.netball.overhead-pass`. **No board can select it.**

**What is asked.** Not a code question. Which passes should the engine author
next, and should the vocabulary change to name them? The engine can hold a
technique the board cannot ask for, and does today, so nothing is broken while
this is open. It only decides where the content lane spends its time.

**Why it is worth a clip rather than an argument.** The overhead pass exists and
can be watched. So can the chest pass, which IS in the vocabulary. Comparing the
two against the manual is a better basis for the decision than comparing two
lists.

**One consequence for the lob.** The lob is a ball-file variant of a pass that
lifts the ball overhead, and its own manual step is word for word the 1 HAND
HIGH pass's step, not the overhead's. So the lob rides a one-handed pass the
library does not have, or the overhead pass the board cannot select. Refer to
`docs/LOB_AUTHORING_BRIEF.md`.

## 11. One band floor, missed by five hundredths of a degree

`netball_two_hand_snatch_pull_in` has four balls. All four are now solved and
graded against the same eleven checkpoints, and one reading needs your ruling.

**At contact, left shoulder elevation, against a band of 50 to 140:**

| ball | reading | |
|---|---|---|
| the plain one | 66.05 | within |
| high | 81.63 | within |
| **low** | **49.95** | **misses the floor by 0.05** |
| wide | 70.03 | within |

The engine grades that as a miss, because it is one, and the receipt says 10 of
11 rather than 11 of 11.

**THE ENGINE CANNOT TELL YOU WHICH OF TWO THINGS IT MEANS**, and neither
reading is more likely than the other from here:

- the floor is slightly high for a genuinely low ball, or
- the low ball asks for something the technique cannot give.

**0.05 degrees cannot separate them.** This project treats five degrees as the
point where a difference means something, and this is a hundredth of that. The
band is yours; the measurement is all we have.

**What is NOT being asked.** Nothing about the other three balls, whose
readings sit 16 to 32 degrees inside the same band, and nothing about the
technique, which the other ten checkpoints show does not change with the ball.

## 12. The bounce pass exists, and its bounce does not

Added 2026-09-02 with `netball_bounce_pass`, the library's eleventh drill.

**What she can see.** The throw: the ball taken to the side, the knees bent, the
arm driving down and forward, the release low, the follow-through. Graded on six
checkpoints.

**What is missing from it, and why she should be told before she watches.** The
engine has no floor. The ball leaves her hands on a path aimed at the right spot
on the court and then keeps going in a straight parabola; the clip ends 0.264 s
before it would land. So **the drill shows a bounce pass with no bounce.**

**What was deliberately NOT graded.** Two of the manual's five steps — the
bounce point "approximately 1m in front of receiver" and "keep ball low" — have
no instrument, and no angle was substituted for them. This library has twice
authored a checkpoint for a manual cue and withdrawn it, so the two are recorded
as gaps instead.

**The question for her.** Is a drill that teaches the THROW of a bounce pass
useful to a coach while the bounce is absent, or does it wait for the floor? The
content is honest either way; the choice is whether an incomplete drill helps
more than it misleads.

**One number for the same conversation.** The library throws every pass at
600 cm/s, which has no source. On this drill that constant makes the ball travel
UPWARD to reach the floor: it needs +95.32 cm/s of vertical, and the throw is
only downward above 734 cm/s. **A bounce pass is driven at the floor, not lobbed
at it.** The speed was left at 600 rather than invented afresh. (The figures are
computed over the flight's true span, 350.5 cm from a release at 111.7 cm, which
is the floor point 4.00 m from her chest less the 49.5 cm the ball is already
ahead of it.)

## Three items with no engine evidence

These are on the agenda and this document has nothing to add to them.

- **A second grader.** The provisional bands were set against one coach's
  marks. Whether a second coach agrees is not something the engine can measure.
- **Vocabulary conflicts.** The manual and the engine use some words
  differently. Nothing here resolves that. The pass family's version of this is
  now item 10 above, with both lists written out.
- **Two manual titles.** The library cites a manual whose title appears in two
  forms. It is a record-keeping question.

---

## Provenance

Read on `ac240b2` with a clean tree, the tip that passed the suite at 564 tests
and passed the clip gate on the morning of 2026-09-02. The figures come from
one solve of each of the eight drills, plus one preview solve at 37.3 degrees.
Elbow width is elbow to elbow at the contact frame, which is the measure the
pole question has always used. Older figures, where they differ, are kept
beside the new ones with the build each was read on.
