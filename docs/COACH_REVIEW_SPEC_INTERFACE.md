# The coach review specification: the interface

Written 2026-09-09 by the content lane, on `a5d60da`. **A proposal for the video
lane to agree or amend before either of us builds anything**, as the orchestrator
instructed.

**The content lane owns this shape. The video lane owns the generator.** This
document defines what goes in. It does not say how the generator works, and it
names the places where the generator's owner should overrule me.

Written to `.remember/PRINCIPLES.md`, principle 6: the review document must be
generated from the footage, the build and a specification, so a new round costs
an afternoon.

---

## 1. The question that decides the shape

**Does the specification describe a PAGE, or a set of QUESTIONS from which a page
is one rendering?**

**It describes QUESTIONS. A page is one rendering.** I have direct evidence from
today rather than a preference.

**The same twenty items now exist in four forms**, and I wrote three of them this
morning:

| form | what it is for |
|---|---|
| `docs/COACH_MORNING_2026-09.md` | the record: what is asked and why |
| `docs/COACH_MORNING_RUNNING_ORDER.md` | a sequence for a person in a room |
| `docs/COACH_MORNING_PAGE_SPEC.md` | what a web page would hold |
| `erin_review.html` | the web page itself, covering seven of the twenty |

**Every one of those went out of step with the others today.** The page covers
seven of twenty. One agenda item recorded a ruling superseded four hours earlier
while another document in the same commit had it right. Two items existed in no
agenda at all, one of them the page's own first question.

**Four hand-maintained renderings of one set of questions is why.** If the
specification describes a page, the morning needs a separate document that can
drift from it, which is exactly what happened.

### The consequence that is easy to miss

**"Needs nothing but the room" is a RENDERING TARGET, not a kind of question.**
My earlier split called four items "nothing but the room" as though that were a
property of the item. It is not. It says only that the page rendering is not
worth building for them. **The question still exists, still has an answer key,
and still needs its answer recorded.**

So each question declares which renderings suit it, and the generator emits only
what a target asks for.

---

## 2. A question, as data

The unit is a QUESTION, not a section. Proposed fields, with the reason for each.

| field | what it holds | why |
|---|---|---|
| `key` | a stable identifier, never reused, never renamed | a coach's archived marks are stored under it |
| `serves` | the agenda item or items it answers | no question that answers nothing; no item that silently loses its home |
| `type` | one of the four in section 3 | the generator implements types, not one-off layouts |
| `artefacts` | references, never paths | refer to section 4 |
| `ask` | the text, in her language | |
| `answer` | the options, or a unit and a range | refer to section 5 |
| `basis` | what this question is measured on | refer to section 6 |
| `movesWith` | open work that will change its numbers | refer to section 7 |
| `renderings` | which targets this question suits | section 1's consequence |

**`serves` is the field I would defend hardest.** It is what stops the two faults
this project keeps meeting: a page section that answers no agenda item, and an
agenda item with no home. Both are then checkable rather than noticed by a person
reading two documents side by side, which is how both were found today.

---

## 3. Four types

Named from what the five-four-one split actually produced.

**`look`** — show an artefact, ask a closed question. Items 12, 13 and 15.
The artefact carries the argument; the text only frames it.

**`open_then_closed`** — ask an open question with a free text answer, and only
then a closed one. Item 16, and it is the type most easily destroyed by a later
editor who wants the page tidier.

**THE GENERATOR MUST NOT RENDER THE CLOSED HALF BEFORE THE OPEN HALF IS
ANSWERED.** If she sees the closed options first she will very likely agree with
them, and the answer records only that our own option was plausible. **That
belongs in the type, not in a comment**, or it will be reordered for layout.

**`number`** — ask for a value in a named unit, with the current value and the
band shown. Items 2, 3, 8 and 11 are all of this type: a band she sets, a speed
she sets, an angle she sets.

**`brief`** — no question. Item 14. It tells her something she needs before she
looks at something else. **A brief has no answer key and must not have one**, or
it will be counted as an unanswered question for ever.

### Where I may be wrong

**I am not sure `number` and `look` are different types.** Item 2 shows two
renders AND asks for an angle. It may be that every type is `look` plus an answer
shape, and that `look`, `number` and `brief` are one type with three answer
kinds. **The video lane should decide this**, because it falls on the generator's
side. My four names are a starting point and not a boundary.

---

## 4. Artefacts by reference, and the first refusal

**A question names what it needs. It never names a file.**

- a clip, by drill and moment: `clip(netball_bounce_pass, release)`
- a still, by drill, moment and build: `still(netball_double_foot_landing, land, <build>)`
- a player, by the dataset it reads
- a pair of renders, by the parameter and its two values

**REFUSAL 1: the generator refuses when an artefact does not resolve.** It must
not emit a section with a hole in it, and it must not silently drop the question,
because a dropped question leaves its agenda item homeless without saying so.

**This is worth more than it looks.** My page specification found that item 11
needs four variant clips that **cannot be exported today**, because the export
key does not exist and inventing it would answer an open contract question by
accident. Under this interface that is not a paragraph a person must read. It is
a refusal with a named cause, and the item stays visibly unanswered.

### Refusal 2: a caption that describes what the clip does not contain

**This nearly shipped today and was found by eye.** The generator can check it:
an artefact reference names a moment, the clip's own manifest declares which
moments it contains, and the two must agree.

**So a caption never states a moment in prose.** It states it in the reference,
and the prose is generated from the reference or checked against it. **A moment a
clip does not contain becomes impossible rather than caught.**

---

## 5. The answer, its options and its unit

**REFUSAL 3: a `number` question must name its unit, and the unit must be the
measure's own.**

Today's page has a box that asked for degrees under a question about
centimetres. The engine already knows the answer: `segment_measures.MEASURE_UNITS`
declares each measure's unit, and `unit_of` refuses a measure it does not know
rather than defaulting to degrees. **A question that cites a measure must cite it
by that key**, and the generator asks the engine for the unit rather than
trusting the specification's prose.

**Every closed question must offer a way to decline.** "Cannot tell from this" is
not a courtesy. A coach forced to choose gives an answer that reads as data and
is not.

### Refusal 4, and this one needs care

**A question must not ask about a quantity as though it were graded when it is
not.** The generator can check a cited measure against the receipt's declared
measures.

**CHECK AGAINST THE RECEIPT, NEVER AGAINST THE CLIP. I got this wrong in a first
draft of this document and measured it before sending.** On
`netball_double_foot_landing` the two disagree in both directions:

| source | measures it names |
|---|---|
| the receipt, from `assess().to_receipt()` | `footHeightGapCm`, `trunkLeanDegrees`, `leftKneeFlexionDegrees`, `leftShoulderElevationDegrees`, `rightKneeFlexionDegrees` |
| the clip's `rows` in `clip-baseline.json` | both elbows, both knees, both shoulders |

**A generator checking the clip would refuse item 16**, whose measure the drill
grades three times, **and would accept a question about `leftElbowFlexionDegrees`**,
which that drill does not grade at all.

**They are not the same list because they answer different questions.** The
clip's rows are a fidelity check: did the exported channel keep the engine's
value? The receipt is the grading record: what was measured against a band.
**Neither is a substitute for the other**, and only the receipt can answer "is
this quantity graded".

**And the library's only centimetre measure is the one the clip omits.** Anyone
building this check against the clip would find the units question invisible.

**But the check must not forbid the question.** Items 12, 13, 15 and 16 all ask
about cues the engine cannot see, and those are among the most valuable questions
on the agenda. **The fault is not asking about an ungraded cue. The fault is
asking as though it were graded.**

So a question citing a measure that no receipt declares must carry
`ungraded: true` with a reason, and the generator refuses only when the flag is
absent. **The flag is then visible in every rendering**, which is what item 13
spends three paragraphs doing by hand today.

---

## 6. Provenance, and principle 4

Principle 4 asks for capability and result to be separate documents. **Inside one
question the same split holds**, and `basis` carries it:

- **`build`** — a question about what the ENGINE does. It carries the commit.
- **`footage`** — a question about what THIS SHOOT showed. It carries the
  footage hash, and principle 2 means its wording must say "on this recording",
  not "in netball".
- **`manual`** — a question about what the source teaches. It carries the manual
  line.
- **`none`** — a question from coaching alone. Item A is one.

**A question may carry more than one**, and item 2 is about to need two: the
rendering lane is measuring a gap between the skeleton's elbow width and the
rendered athlete's. If that holds, item 2's `basis` is a build AND a render, and
the room must know which body her number governs.

**The generator refuses a `footage` basis without a hash.** That is principle 2
made structural: a finding from one shoot cannot be written as a finding about
the sport, because the field that would say which shoot is required.

---

## 7. `movesWith`, and why a specification needs it

**Seven of the twenty items will move when the release retiming lands.** Today
that is a paragraph in a running order that a reader must remember.

`movesWith` names the open work. The generator can then do two things a person
does badly: **mark those questions in every rendering**, and **refuse to publish
a page whose questions move with work that has landed since the page was built**.

**The second is the valuable one.** A page built before a retiming and read after
it shows a coach numbers that are no longer true, and nothing today would catch
that.

---

## 8. What I need from the video lane

1. **Agree or reject "questions, not a page".** Everything else follows from it.
2. **Rule on section 3's uncertainty**: four types, or one type with three answer
   kinds? It falls on the generator's side.
3. **Say which refusals you can implement cheaply.** I have proposed five. If
   any is expensive, I would rather drop it than have it half-built: a refusal
   that sometimes fires is worse than none, because it is trusted.
4. **Name the artefact reference forms you can resolve.** I have guessed four in
   section 4 and I do not know what your manifests carry.

## 9. What this interface does not settle

**Where the specification lives, and in what format.** It is a data file and I
have deliberately not proposed JSON or anything else, because the generator reads
it and its owner should choose.

**Whether the existing page is regenerated or left alone.** It is held until
Marius is happy with it. Regenerating it is a bigger decision than this interface.

**The generator's own tests.** They belong with the generator.
