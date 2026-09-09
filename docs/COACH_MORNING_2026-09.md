# The coach morning: what to ask, and the evidence behind each question

**Items 1 to 9 were re-measured on `ac240b2` with a clean tree. ITEM 6 IS THE
EXCEPTION AND ITS TABLE NAMES ITS OWN BUILD**, because one of its eight rows was
read on a pose that drill no longer holds. Items 10 and
above were added later, as each drill was authored, and **each names the commit
its own figures were read on, or says that it carries no figure** — item 18 is
the one that carries none — do not read the `ac240b2` line as covering
them. Where an older document gives a different number, both are shown with the
build each was read on. Nothing in this document changes any code.

**An earlier version of that sentence said each item states its own date AND
BUILD. Only one of the six did.** The dates were there and five of the six named
no commit at all, which is the second time a framing sentence in this document
has been disproved by the list beneath it. Every item from 10 onward now carries
a hash.

The questions are for Erin and Marius. They are written to be answerable by a
coach watching the athlete, not by reading a number. Where the engine has an
opinion it is stated as a measurement and never as a recommendation.

**Nineteen numbered items.** One, item 7, is STRUCK, because it was raised on a
measurement the solver read from a second solution for that drill. **Fifteen
carry engine measurements. Items 8, 10 and 18 do not**, and neither claims to: item
8 names the constant that follows from item 2's answer, item 10 compares two
written vocabularies, and item 18 asks for two angles that nothing sources.
Three further items at the end carry no evidence either, and say so.

**Items 10 to 15 were added as the pass family was authored** and are the newest
part of this agenda: the vocabulary mismatch, a band floor, **an item for two of
the four passes** — the bounce and the 1 hand high, the two with something a
coach must rule on — and two items about the family rather than any one drill.
**Item 16 is the first that is not about a pass**: it comes from the landing
drill and from the movement lane's ledger rather than from authoring.

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

**What the engine does.** Wrist to wrist at the first frame, on the engine's
solved skeleton, checked against archive `coach-figures-2413f9d`:

| drill | wrist to wrist | as this item read it on `ac240b2` |
|---|---|---|
| `deflect_high` | 18.29 cm | 18.29 |
| `hooks_jump_pull_in` | 19.83 cm | 19.83 |
| `double_foot_landing` | 19.91 cm | 19.91 |
| `two_hand_snatch_pull_in` | 20.08 cm | 20.08 |
| `two_hand_snatch_straight_back` | 20.08 cm | 20.08 |
| `two_hand_catch_chest` | 20.10 cm | 20.10 |
| `one_hand_snatch_to_other_hand` | 32.15 cm | 32.15 |
| `hooks_outside_hand` | **40.36 cm** | 45.68, **MOVED** |

**AMENDED 2026-09-09. SEVEN OF THE EIGHT ROWS REPRODUCE TO TWO DECIMAL PLACES AND
THE EIGHTH DOES NOT.** The eighth is `hooks_outside_hand`. All eight were re-read
rather than the one already known to be wrong, because a single corrected row
leaves seven unchecked rows from an earlier build under one heading.

**Seven right and one wrong names the mechanism. One wrong row alone could have
been anything.** That drill has two solved poses about 33 degrees apart. The turn
of the shoulder line at the first frame is 48.22 degrees on the engine and 45.48
on the rendered figure, and struck item 7 records 48.22 as the corrected pose and
15.44 as the pose the shipped parameter set reached. **Both bodies hold the
corrected pose and only this row was behind.**

**ITEM 7 WAS STRUCK FOR THAT POSE AND NOBODY RE-MEASURED THE OTHER ROWS READ ON
THE SAME DRILL.** This row carried a figure from it for a week.

**THIS MEASUREMENT HAS NO AXIS, WHICH IS WHY IT IS SETTLED.** Wrist to wrist is a
straight-line distance between two points, so it reads the same in her frame and
in the room's. **Item 5's figures are a component along an axis and they are not
settled**, which is a difference between the two items and not a difference in
how carefully each was measured.

Six of the eight hold their hands about 20 cm apart. The manual's cue for the
snatch asks for the arm span to be shown.

**THIS TABLE IS THE ENGINE AND THE COACH LOOKS AT THE FIGURE.** The two bodies do
not hold the same pose at the ready frame, and the gap is not small on any row.
**That measurement belongs to the rendering lane and it is in
`docs/TWO_BODIES_PAPER.md`, which is not on main.** It is named here so that this
table is not read as a description of what she will be shown.

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

Added 2026-09-02 by the content lane, with the first two passes authored, in `fcb7ca1`. Its content is two written vocabularies rather than engine figures, so the commit is where the item was added rather than where a number was read.

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
- **AND SO IS `1 hand high`, ADDED 2026-09-04.** It is authored and exported as
  `pass.netball.one-hand-high-pass` and is not in the list either. **Two of the
  four authored passes can now be watched but not selected**, which is the same
  question at twice the size.

**What is asked.** Not a code question. Which passes should the engine author
next, and should the vocabulary change to name them? The engine can hold a
technique the board cannot ask for, and does today, so nothing is broken while
this is open. It only decides where the content lane spends its time.

**Why it is worth a clip rather than an argument.** The overhead pass exists and
can be watched. So can the chest pass, which IS in the vocabulary. Comparing the
two against the manual is a better basis for the decision than comparing two
lists.

**One consequence for the lob, and it has moved since this item was written.**
The lob is a ball-file variant of a pass that lifts the ball overhead, and two
of its three manual steps are word for word the 1 HAND HIGH pass's, not the
overhead's. **When this was written the library did not have that pass. It does
now**, so the lob's most literal parent exists. What has not changed is that
NEITHER candidate parent is in the vocabulary. Refer to
`docs/LOB_AUTHORING_BRIEF.md` and to item 13.

## 11. One band floor, missed by five hundredths of a degree

Added 2026-09-02 with the ball variants, in `3f95fd1`. (The date was missing
from this item and is filled in from the commit that added it, so the note at
the head of this document — that every item from 10 onward states its own build
— is true of all of them.)

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

Added 2026-09-02 with `netball_bounce_pass`, the library's eleventh drill. **Figures read on `431bf3a`**, that drill's pack as it merged.

**What she can see.** The throw: the ball taken to the side, the knees bent, the
arm driving down and forward, the release low, the follow-through. Graded on six
checkpoints.

**What is missing from it, and why she should be told before she watches.** The
engine has no floor. The ball leaves her hands on a path aimed at the right spot
on the court and then keeps going in a straight parabola; the clip ends 0.267 s
before it would land. (That is 19 frame intervals of flight at 60 frames a
second, from the release frame to the last frame. Refer to item 15, which is
about the whole pass family rather than this drill.) So **the drill shows a bounce pass with no bounce.**

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
UPWARD to reach the floor: it needs **+95.15 cm/s** of vertical, and the throw
is only downward above **734 cm/s**. **A bounce pass is driven at the floor, not
lobbed at it.** The speed was left at 600 rather than invented afresh.

(The figures are computed over the flight's span, **350.3 cm**, from a release
at 111.7 cm to the point the engine itself aims at. **They were +95.37, 735 and
350.5 until 2026-09-07**, and those came from a floor point reconstructed by
hand as "the chest at frame 0 plus the authored offset" rather than read from
the engine. The engine's own aim point is 0.27 cm away from that
reconstruction, which is enough to move all three. Refer to the correction
under item 15.)

## 13. The one hand high pass, and the cue it does not grade

Added 2026-09-04 with `netball_one_hand_high_pass`, the library's twelfth drill,
its fourth pass and **its first one-handed pass**. **Figures read on `6228b3d`**, that drill's pack as it merged.

**What she can see.** The ball taken up on one arm to the top of its reach, a
step, the release, and the arm coming through. Graded on five checkpoints: four
on the RIGHT arm, because the right is the working arm, and the fifth the same
left-knee stance reading every drill in the library carries.

**THE CUE THE DRILL IS NAMED FOR IS NOT GRADED, and she should be told before
she watches.** The manual's step 1 is *"Pull the ball up as high as arm can
go"*. That is a height, and nothing in the engine reads a height in
centimetres. **No angle was substituted for it.** The nearest available proxy
reads arm fold and hand placement as well as height, and it is least trustworthy
exactly where this drill lives, above the crown. So the cue is recorded as a
gap.

**The number she is not being shown, in case she wants it.** The ball reaches
**199.95 cm** at its highest. Her crown is at 163.4 cm and her shoulder at
131.3. The overhead pass peaks at 184.4 cm, so this drill carries the ball
**15.5 cm higher** — which is the difference between the manual's two
sentences, *"as high as arm can go"* and *"into the air above your head"*. Those
figures are measured and reported; none of them is graded.

**A question for her.** Is a drill whose defining cue is ungraded useful to
her, when everything else in it grades cleanly? The alternative was to grade
step 1 on the proxy and tell her the number is partly about where her hands
are. The engine work to measure height properly is queued.

**A second question, about a name.** Braven Tactics' clip vocabulary has four
pass names: `chest-pass`, `shoulder-pass`, `lob` and `bounce-pass`. This drill
is exported as `one-hand-high-pass`, which is **not** in that list, so no board
can select it. **It was deliberately NOT filed under `shoulder-pass`**, the one
unclaimed slot: this drill releases the ball **59.3 cm above the shoulder**,
against 47.6 for the overhead pass and 9.6 for the chest pass, and a pass
released nearly 60 cm over the shoulder is not a shoulder pass. (Those three
are the ball centre at the release frame measured against the shoulder **as it
stands at frame 0**. Against the shoulder at the release frame itself, which
rises as the arm goes up, they are 51.9, 39.8 and 6.3. The ordering and the
conclusion are the same either way; the inputs are stated because a height
without its reference point is what this project keeps having to correct.)
**Does `shoulder-pass` instead name the manual's 1 HAND LOW WIDE or 1 HAND WIDE
block?** Neither is authored yet, so the slot can still be given to whichever
she means.

**One thing this drill settles that was open.** The lob needed a parent. The
manual's lob block reuses **two of this block's three steps word for word**,
and its own step 1 names its permitted parents as *"1 Hand high/wide or double
hand"*. The library now holds two of the three, including the one whose wording
the lob actually copies. **Which parent the lob rides is still hers to decide**
and stays open in `docs/LOB_AUTHORING_BRIEF.md`; this drill only removes the
reason the question could not be asked.

## 14. The one-handed pass is harder for the engine to place than a two-handed one

Added 2026-09-04 with `netball_one_hand_high_pass`. **Figures read on `6228b3d`**, the same pack, and the table below is the one in `docs/KNOWN_ISSUES.md`. **This is not a question
about her coaching. It is a warning about how much to trust one frame of one
drill**, and it is here because she is the person who will look at the pose.

**What was measured.** The same experiment on all four passes: take the key that
says where the ball is at the release, move it through the same nine positions,
and count how far the body jumps between one position and the next.

| drill | hands | jumps over 5 cm | largest jump |
|---|---|---|---|
| **1 hand high** | **one** | **4** | **21.9 cm** |
| overhead | two | 1 | 7.5 cm |
| bounce | two | 2 | 7.0 cm |
| chest | two | 1 | 5.2 cm |

**The one-handed drill jumps two to four times as often, and its largest jump is
three times the worst of the others.** A "jump" means the solved body moved to a
noticeably different pose for a very small change in what was asked of it.

**Why it may matter to her.** The pose she is shown is one of several the engine
could have produced for the same instruction. On the two-handed passes those
alternatives are close together. On this one they are not.

**What was done about it.** The shipped pose was checked rather than assumed: it
sits in a region where the same small changes move the graded angle by half a
degree in total. **One checkpoint was authored and then deleted** because no
stable way could be found to make it fail, and a checkpoint that cannot fail is
not a check.

**A guess at the reason, and it is only a guess.** Two hands on the ball hold
both arms and the trunk between them. One hand leaves the other arm and the
trunk with nothing asked of them, so the engine has more equally good answers to
choose from. **Nothing has tested that.** It is engine work and **it waits on a
ruling**, which is what `docs/KNOWN_ISSUES.md` says of it: constraining the
solve "belongs to the movement lane and needs a ruling first". An earlier
version of this line said the work was queued, which promised more than the
ledger does.

**What is asked of her.** Only this: when a one-handed pose looks slightly wrong
to her, say so even if the numbers are inside their bands. On this family the
numbers are less able to see a wrong pose than usual.

---

## 15. Every pass clip stops before the ball arrives

Added 2026-09-04, **read on `56e70a3`** and re-measured since on `b214bc4` with the same result. **A question about the clips a board plays, not about her
grading**, and it applies to the whole pass family rather than to one drill.

**All four pass clips are built the same way**: 96 frames at 60 a second, 1.60
seconds long, with the ball leaving her hand at frame 76. That leaves **19
frame intervals, 0.3167 seconds, of flight** in every one of them. The four are
the chest, overhead, bounce and 1 hand high passes.

**On three of them the ball reaches its target before the clip ends. On the
bounce pass it never does.** Measured against a last frame of 95:

| clip | ball reaches its target | exact crossing | margin |
|---|---|---|---|
| 1 hand high | frame 91 | 90.94 | 4 frames |
| chest | frame 93 | 92.09 | 2 frames |
| overhead | frame 94 | 93.67 | **1 frame** |
| **bounce** | **never** | — | **0.267 s short of the court** |

**That 0.267 s with its inputs, because a time without them is what this
document keeps having to correct.** The ball leaves at frame 76 with **350.3 cm**
still to travel, and at the library's 600 cm/s that takes **0.5838 s**. The clip
holds 0.3167 s. The difference is **0.2671 s**.

**AND THE INPUT ITSELF WAS WRONG UNTIL 2026-09-07, WHICH IS THE POINT OF WRITING
INPUTS DOWN.** This document said 350.5 cm and 0.268 s. Both came from a floor
point I reconstructed by hand — the chest joint at frame 0 plus the authored
offset — instead of the point the engine actually aims at. **The engine's own
aim point sits 0.27 cm from that reconstruction**, and it is the one the ball
flies to. Read from the engine, the span is 350.3 cm and the shortfall 0.2671 s.

The reconstruction was never checked against the engine because it looked like
arithmetic rather than a measurement. **It was a measurement**, and a
hand-rebuilt one. The figures above are now read from
`possession._launch_toward`, which is where the engine states its own target.
Nothing a coach is asked changes: the clip still ends a quarter of a second
before the ball arrives.

**"Reaches its target" means the first WHOLE FRAME at or past it**, because a
clip plays frames and not fractions. The middle column is where the ball
actually crosses, between frames. The chest pass crosses at 92.09 and is
reported at 93; that is the convention and not a rounding error.

**So a board playing the bounce pass shows a throw and a ball that never lands**
— the point item 12 makes about that drill. What is new here is that **the
margin on the others is between one and four frames**, which is thin rather than
comfortable, and that a change to when she releases would move all four clips
together. The overhead pass has a single frame in hand.

**The question, and it is one for the manual rather than for the engine.**
Should a pass clip carry the flight all the way to the catch, or only the
release and the follow-through? A coach teaching a pass may only need the
release. A board showing a play may need the ball to arrive.

**Nothing is being proposed.** The engine can make the clip longer or move the
release earlier; both change what every pass clip contains, so the choice is
hers and Marius's rather than the content lane's.

## 16. The landing's own cue may be graded by an instrument that cannot see it

Added 2026-09-07 from the movement lane's ledger row, which was measured on
`b214bc4` and reached main in `ad7e65d`. **The cue is real. The instrument
cannot see it yet.** That is the whole item, and she should know it before she
watches that drill.

**What the drill grades.** `netball_double_foot_landing` is the only drill in
the library with a checkpoint measured in CENTIMETRES rather than degrees. It
reads `footHeightGapCm` — how far apart the two feet are in height — at three
phases, against bands of 0 to 14 cm, 0 to 6 and 0 to 6.

**What the engine actually sees.** Over all 110 frames of that drill the gap
spans **0.00 to 1.22 cm**. The three graded readings are **0.00, 0.00 and
0.01 cm**. The bands are six to fourteen centimetres wide and the readings are
hundredths of one.

**And the whole observed range sits below the measure's own noise.** The
movement lane's noise study propagates **1.45 cm** of error into this measure
from the landmarks it is built on. The drill never produces a gap that large.

Two consequences, and the ledger is careful that they are different:

- **On the solved skeleton** the number is exact and the bands are never
  approached. All three read `within`, at every phase, every time.
- **On a filmed athlete** the same column would be **indistinguishable from
  noise**, because the range the movement produces is smaller than the error the
  measurement carries.

**What is NOT claimed, and the ledger says so in capitals.** Nobody has run a
sweep to find out whether those three checkpoints CAN fail under any lever. The
row records that the question has never been asked of the library's only length
checkpoints, and that the reading above is the reason to ask it. **Owner: the
movement lane**, queued behind the height measure item 13 waits on.

**The question for her.** Landing is the skill whose coaching is most about what
the feet and knees do, and this drill grades more below-the-hips checkpoints
than any other. **Is a foot-height gap the thing she would look at**, or is she
watching something the engine has no measure for at all — the timing of the two
feet, the width of the base, where the weight goes? If the cue is right and only
the instrument is weak, that is engine work. If the cue is not what she watches,
the checkpoint is measuring the wrong thing well.

**TWO THINGS WERE WRONG UNTIL THIS WEEK, AND THEY ARE DIFFERENT THINGS.** Both
were fixed in `ad7e65d`, both were real in the code, and **neither was ever
printed for this drill** — but for two separate reasons, which is why they are
listed apart rather than as one.

- **The feedback a coach reads named every figure in degrees**, whatever its
  unit. On this drill it would have said *"Needs less: 17 degrees against a
  target of 0 to 14"* about a distance between two feet in centimetres. **It
  never fired here because it only speaks when a reading falls OUTSIDE its
  band, and all three of these read within, always.**
- **The warning that a band is too narrow to mean anything used a degrees
  threshold on centimetre bands.** **It never fired here because it only speaks
  for a band narrower than the floor, and these three are 14, 6 and 6 cm wide
  against a floor of 2 cm.**

So one was silenced by the readings and the other by the bands, and a drill that
differed in either respect would have shown a coach a length wearing an angle's
unit. **That substitution is the fault the ledger row above exists to track**,
which is why both are recorded here rather than left as fixed code.

## 17. The hand that was posed wrongly, and whether the fix reads right

Added 2026-09-09 by the content lane. **Figures read on `fde5d5a`**, the commit
that fixed it. **This item is on Erin's page as its FIRST question and has never
been on this agenda.** It is added here because the morning needs it and no
agenda document carried it.

**What was wrong.** The model's right hand was anti-mirrored. Its fingertips
bunched to about the width of two fingers while the left hand opened a full
hand-span. **It is the likely reason the thumbs looked wrong to her** when she
said they should not be.

**What the fix did, measured.** On the corrected build the right hand opens like
the left: at the chest catch **the two hands match to the decimal**.

**Why it is a LOOK item and not a closed defect.** The measurement says the two
hands now agree. It does not say the catch looks right to a coach. **That is her
eye and nothing else can supply it.** The page puts a corrected catch in a player
she can turn, zoom and step frame by frame, and asks one question: do the right
hand's fingertips spread like the left's, and does the catch look right?

**What it also cost, which is why it is worth her minute.** A whole ledger entry
of elbow-width figures — the 44.60 one-handed average, the 36.57 two-handed one
and the 37.3 degree sweep — **was measured on the anti-mirrored build** and had
to be marked superseded. **Item 2 and item 8 are that entry's question.** If the
hand still looks wrong to her, those two items are being asked about a pose she
does not accept, and the order in `docs/COACH_MORNING_RUNNING_ORDER.md` puts this
item before both for that reason.

---

## 18. The two angles of the release hand, which nothing sources

Added 2026-09-09 by the content lane. **THIS ITEM NAMES NO BUILD BECAUSE IT
CARRIES NO ENGINE FIGURE**, which is the whole of its content: the two angles it
asks about are unsourced. Its source is `.remember/RELEASE_HAND_PAPER-f7af647.md`
at `f7af647`, **which is not on main** — refer to the last paragraph.

**This item exists because Marius answered two of three questions and the third
is hers.** It has never been on this agenda and it lives today only in the
orchestrator's state notes.

**What was already ruled, and the first ruling was WITHDRAWN the same
afternoon.** The order matters, because the paper this item cites still
recommends the first one.

1. **Marius first ruled the hand COSMETIC**, reluctantly, with his own debt note:
   the wrist and finger action is one of the key differentiators top athletes
   use.
2. **He was then told the premise of that ruling was wrong.** He had been given
   the engine's hand speed as about 0.3 m/s against the athlete's 2.5 to 5.4.
   **That figure was measured only BEFORE the release.** The frame after, the
   engine's hand reaches 2.46 on the chest pass, 3.02 on the bounce, 4.42 on the
   overhead and 5.61 on the one hand high. **The arm is not slow. It is LATE**:
   three of the four reach her speeds one frame after the ball has gone, and the
   fourth peaks at the release frame itself.
3. **He asked whether that made it mechanical.**
4. **The recommendation was mechanical on one condition**: it must land before
   Erin grades, because retiming moves the arm inside the last frames of contact,
   and that is the window her checkpoints measure. She must not grade a build we
   already intend to replace.
5. **He ruled it**, in his words: *"yes, I am holding back her page/feedback
   until I am happy with what we are giving her - so push ahead."*

**SO THE RULING IS MECHANICAL. Cosmetic is superseded.** He also ruled the
shape: **option B, ball-relative, at the release frame.**

**Two of those four speeds sit just outside her band, and that is not evidence
against any of this.** The chest pass's 2.46 is 0.04 below her 2.5 and the one
hand high's 5.61 is 0.21 above her 5.4. **The band's width is its resolution**,
so margins of that size carry no weight in either direction.

**What the correction does to THIS item.** Nothing to its question and everything
to its frame. The two angles are still unsourced and still hers. But she is no
longer choosing how a decorative hand looks beside a launch the engine assigns.
**She is choosing part of a release the engine will actually perform.**

**What is not ruled, and cannot be ruled by measurement.** The flick model takes
seven parameters. **Four are sourced** — the footage's timescale, the engine's
own start angles, the manual's end state and its aim. **Two are not:
`wristToDegrees` and `fingerToDegrees` are named and not filled.** No footage,
no manual line and no engine reading supplies them.

**So the two angles are a coaching judgement, and the proposal is that she makes
it by looking.** Render a small set of candidates, show her the hand at the
release frame in each, and let her choose. That is the orchestrator's
recommendation and it is why this is a morning item rather than an engine one.

**What she would be setting.** The receipt for that work carries two angles and a
wrist speed in centimetres per second, which is a new unit needing its own floor.
**The coach grades the angles.** The speed is the engine's business.

**It is the one morning item whose artefact does not exist and cannot yet be
made.** The candidates cannot be rendered until the movement lane's flick model
does, so this item is the last of the four missing renders to become possible.

**CITED FROM AN UNMERGED BRANCH AND LABELLED SO, AND ONE PART OF IT IS ALREADY
OUT OF DATE.** The parameter list above comes from
`.remember/RELEASE_HAND_PAPER-f7af647.md`, and `f7af647` is **not on main**.
**That paper recommends COSMETIC**, which the ruling above supersedes. So a
reader who meets only the word "mechanical" here cannot reconcile it with the
paper, which is why both rulings are written out in order.

If the paper changes before the morning, this item's account of what is sourced
changes with it. **Its account of the RULING has already changed once**, and the
sequence above is the record of that.

## 19. Which of the cues you teach are distances rather than shapes?

**The question, and it is for Erin.** The manual's cues are written in the words
a coach uses. Some name a SHAPE, such as how wide the elbows sit. Some name a
DISTANCE, such as how far the ball is from the chest. **Which of yours are
distances?**

**Why it is asked.** This engine grades angles. **A cue that names a distance has
no instrument here, and a checkpoint has been authored for one and withdrawn
twice.** Her answer sizes the gap, and no measurement in this repository can.

### Two experiments, and the second is the one that matters

**THE FIRST FAILED OPENLY.** A checkpoint for the manual's "don't pull ball back
behind head" was authored on `netball_chest_pass` and mutation-tested. Moving the
step key 13.2 cm, which is more than half a netball's diameter, moved every
measure this engine has by at most 5.1 degrees. **That is the threshold this
repository calls meaningless. It passed the mutation, so it was not a check, and
it was deleted rather than kept green.**

**THE SECOND LOOKED LIKE IT WORKED.** The same checkpoint was authored again on
`netball_overhead_pass`. Swept against its band, **a 26 cm pull-back, with the
ball well behind her head, PASSED at 114.99**, and the whole range from 0 to 26 cm
moved the measure 7.7 degrees. The failure at 27.7 cm was a SOLVER BASIN FLIP.
The elbow's z ran +8.5 to -12.0, swinging 20.5 cm from in front of the shoulder to
behind it, while the wrist moved 0.2 cm and the ball did not move at all.

**A GREEN CHECK THAT WOULD HAVE SHIPPED IS WORSE EVIDENCE ABOUT THE ENGINE THAN A
CHECK THAT PLAINLY DID NOTHING.** The first deletion suggests the answer is a
linear measure. **The second shows an angle measure that appeared to supply one
and did not.**

### Four drills, counted from the list rather than summarised

| drill | the cue, and what quantity it names |
|---|---|
| `netball_chest_pass` | "don't pull ball back behind head" — a DISTANCE. Checkpoint deleted |
| `netball_overhead_pass` | the same cue — checkpoint deleted for the worse reason above |
| `netball_bounce_pass` | "bounce approximately 1m in front of receiver" — a POSITION; "keep ball low" — a HEIGHT; "pull the ball to the side" — a LATERAL position |
| `netball_one_hand_high_pass` | "pull the ball up as high as arm can go" — a HEIGHT, and it is the sentence that drill exists for |

Refer to the row in `docs/KNOWN_ISSUES.md` that records both deletions and all
four drills. It states the pattern once: **the manual cues lengths, and a length
needs a measure whose unit says so.**

**THIS ITEM IS NOT A REQUEST FOR AN INSTRUMENT.** It asks which class of cue she
teaches in. Whether the engine should grow a linear measure is a separate
decision, and it belongs to Marius after her answer rather than before it.

**Not settled.** How much of her coaching is distance and how much is shape.
**That number does not exist and only she can supply it.**

---

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

**Items 1 to 9, EXCEPT ITEM 6**, were read on `ac240b2` with a clean tree, the
tip that passed
the suite at 564 tests and passed the clip gate on the morning of 2026-09-02.
Those figures come from one solve of each of the eight drills that existed then,
plus one preview solve at 37.3 degrees.

**Items 10 to 15 were added later and each carries its own date and build.**
They were written as the pass family was authored, on a library that has grown
from eight drills to twelve. **This paragraph does not cover them**, and an
earlier version of it implied that it did.
Elbow width is elbow to elbow at the contact frame, which is the measure the
pole question has always used. Older figures, where they differ, are kept
beside the new ones with the build each was read on.
