# The coach morning: what to ask, and the evidence behind each question

Every figure here was re-measured on `ac240b2` with a clean tree. Where an
older document gives a different number, both are shown with the build each was
read on. Nothing in this document changes any code.

The questions are for Erin and Marius. They are written to be answerable by a
coach watching the athlete, not by reading a number. Where the engine has an
opinion it is stated as a measurement and never as a recommendation.

Eight items carry evidence. Three carry none, and say so.

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
| at 31.3, today | **36.40 cm** | 28.89 | 40.29 |
| at 37.3, previewed | **38.45 cm** | 30.63 | 42.41 |

The manual says 38.6. At 31.3 the gap is 2.20 cm. At 37.3 it is **0.15 cm**.

**A correction to how this question has been framed.** It has been asked as
"which of two populations does 38.6 describe". THE SECOND POPULATION IS NOT A
POPULATION. It is two drills:

| drill | elbow width at contact |
|---|---|
| `hooks_outside_hand` | 19.01 cm |
| `one_hand_snatch_to_other_hand` | 59.96 cm |

They sit 40.95 cm apart, with a standard deviation of 28.96 cm. Their mean of
39.48 cm describes neither drill: it lies about 20 cm from each. The six
two-handed drills are a real group by comparison, spread 11.40 cm with a
standard deviation of 4.08.

So the choice is not between two populations. It is whether 38.6 describes the
drills that put both hands on the ball, and the one-handed pair belongs outside
that comparison rather than weighed against it.

**A warning about the preview.** On `hooks_outside_hand` the 37.3 preview moves
the elbow width by 37.91 cm. That is the FREE arm relocating rather than the
elbow width changing, and it would dominate anything a person watched on that
drill. The comparison drill is `deflect_high`, where both hands are on the ball
and nothing else moves.

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

| drill | at contact | furthest out | back to | travel |
|---|---|---|---|---|
| `one_hand_snatch_to_other_hand` | 17.6 cm | 32.1 cm | 17.6 cm | **14.5 cm** |
| `hooks_outside_hand` | 13.1 cm | 22.5 cm | 13.0 cm | **9.4 cm** |

**An older reading, kept beside this one.** `docs/KNOWN_ISSUES.md` records the
same movement as 11.9 out to 26.0 and back to 12.0 on the first drill, and 11.8
to 25.1 to 12.0 on the second. Those were read on an earlier build. The travel
is close on the first drill and smaller on the second, and the hand now sits
further forward at contact on both. The two readings may also project "ahead of
the shoulders" slightly differently, so compare the shapes rather than the
decimals.

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

## 7. Should a drill in the library start turned away?

**The question.** Should the library hold a drill where the athlete begins with
her back or her shoulder to the passer?

**Why it is being asked, and it is new.** Until the hand fix shipped,
`hooks_outside_hand` began 48.23 degrees turned. It now begins at 15.44, and
nothing else comes close:

| drill | how far turned while a hand still waits |
|---|---|
| `hooks_outside_hand` | 15.44 degrees |
| `deflect_high` | 0.78 |
| `one_hand_snatch_to_other_hand` | 0.53 |
| the other five | 0.05 or less |

The athlete had been turning her shoulders 48 degrees to compensate for a hand
whose fingers closed wrongly. With the hand corrected she stands nearly square.

**What it cost.** A guard existed to make sure the engine's reach rule was
tested on a turned athlete, because that rule is only wrong when she is turned.
The library can no longer supply that case, so the rule is now pinned on a
hand-built figure instead. That works, and it means the library itself no
longer covers a shape netball actually contains.

**Not settled.** Whether a turned drill belongs in the library on coaching
grounds. This is content rather than a defect.

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

## Three items with no engine evidence

These are on the agenda and this document has nothing to add to them.

- **A second grader.** The provisional bands were set against one coach's
  marks. Whether a second coach agrees is not something the engine can measure.
- **Vocabulary conflicts.** The manual and the engine use some words
  differently. Nothing here resolves that.
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
