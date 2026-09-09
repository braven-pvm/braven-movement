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

The unit is a QUESTION, not a section. **There is no `type` field**: section 3
replaced four types with one type and an ordered answer list, so the shape a
question takes is carried by its answer list rather than by a name.

| field | what it holds | why |
|---|---|---|
| `key` | a stable identifier, never reused, never renamed | a coach's archived marks are stored under it |
| `serves` | the agenda item or items it answers | no question that answers nothing; no item that silently loses its home |
| `artefacts` | references, never paths | refer to section 4 |
| `ask` | the text, in her language | |
| `answer` | an ORDERED LIST of parts, each with a kind | refer to section 3 |
| `gated` | whether a part may be shown before the one before it is answered | the anti-anchoring rule, as data |
| `basis` | what this question is measured on | refer to section 6 |
| `movesWith` | open work that will change its numbers | refer to section 7 |
| `renderings` | which targets this question suits | section 1's consequence |

**`serves` is the field I would defend hardest.** It is what stops the two faults
this project keeps meeting: a page section that answers no agenda item, and an
agenda item with no home. Both are then checkable rather than noticed by a person
reading two documents side by side, which is how both were found today.

---

## 3. One type, with an ordered answer list

**AGREED WITH THE VIDEO LANE, 2026-09-09, and this is their shape rather than
mine.** I proposed four types. The orchestrator proposed one type with three
parts. **The video lane proposed one type with an ordered ANSWER LIST, which is
better than either.**

A question is: **artefacts to show, text to ask, and a list of answer parts, each
with a kind.** The kinds are a choice, a number with its unit, free text, and
none.

| what I called a type | what it is |
|---|---|
| `look` | artefacts + `[choice]` |
| `number` | artefacts + `[number]` |
| `brief` | artefacts + `[]` |
| `open_then_closed` | artefacts + `[text, choice]`, **gated** |

**Three things follow that four types do not give.**

- **Item 2 needs no new type.** It shows two renders AND asks for an angle, which
  is artefacts + `[number]`. Under four types it was a hybrid that forced a
  fourth.
- **A brief's answer list is empty, so it CANNOT have an answer key.** That stops
  being a rule a person must keep and becomes a property of the data.
- **THE ANTI-ANCHORING RULE GENERALISES.** A question declares its answer list
  **gated**, and no rendering may present part n+1 before part n is answered.
  **That is the same rule for a survey, a room and a page**, and a machine can
  check it. My version was a rule about one type that a generator had to
  remember to honour.

**Why this falls on the generator's side, in their words:** a type is a thing
they implement, an answer kind is a thing they render. Four types means four
layouts. One type with four answer kinds means one layout and four widgets.

**I withdraw my four names.** They came from sorting ten items by what each needs
in a room, which is a rendering question, and I turned that answer into types.

---

## 4. Artefacts by reference, and the first refusal

**A question names what it needs. It never names a file.**

**AGREED WITH THE VIDEO LANE, AND THE LIST SPLITS BY LANE.** Every form carries
the lane that resolves it, because two forms with one name is the fault this
project counts most often.

**The video lane resolves these:**

- `clip_footage(shoot, pair, moment)` — cut by frame index from each camera's own
  frame list, both views, equal lengths
- `still_footage(shoot, pair, moment)` — at a frame index, with the digest pinned
- `measurement(shoot, quantity)` — from the footage manifest

**These belong to the character and render lane and NEITHER OF US MAY PROMISE
THEM:**

- `still_render(drill, moment, build)` — a render still, which is what my first
  draft called `still` and is a different thing from a footage still
- `player(dataset)`
- `render_pair(parameter, value_a, value_b)`

**A THIRD LANE IS NEEDED TO CLOSE THIS INTERFACE, and that is a finding rather
than an obstacle.**

**Five of the twenty-one questions need render artefacts: items 2, 4, 13, 17 and
18.** Four of them are the missing renders the running order identifies as the
reason a morning date is hard to set. Neither the content lane nor the video lane
owns them.

**THE FIFTH IS ITEM 13, ADDED TO THIS LIST ON 2026-09-09, AND IT IS DIFFERENT IN
KIND.** The other four are renders nobody has made yet. **Item 13's drill cannot
be posed on this rig at all**, so its artefact is not merely unmade and no date
can be given for it. **A generator that treats the five alike will report the
wrong reason for the one that cannot be satisfied.**

**The engine also resolves one form**, which needs no lane agreement because it
reads the tree:

- `clip_engine(drill, moment)` — an exported clip from `clip-baseline.json`

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
and the prose is generated from the reference or checked against it.

**AND THE VIDEO LANE STRENGTHENED THIS, BECAUSE MY VERSION WOULD NOT HAVE CAUGHT
THEIR OWN DEFECT.** Their caption named a pull-in that the clip does not contain.
A manifest declaring which moments a clip contains **does not help when the
person writing the manifest declares the wrong one**, which is what happened: the
section was cut under a label and the label was believed.

**The check must be against evidence, not against a label.** The moment must be a
**named event in the event ledger**, read on the pictures under a stated rule,
and **the clip's frame window must contain that event's frame**.

**That turns a label match into an evidence match**, and a caption can then name
no moment that no ledger event supports. **This is their amendment and it is
better than what I wrote.**

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

**ASK THE DEFINITION, NOT THE RECEIPT AND NEVER THE CLIP.** The video lane found
a cheaper route than mine and I ran it before agreeing:
**`MovementDefinition.graded_measures()`** returns the graded measures **from the
definition alone, with no solver run and no receipt file**. On
`netball_double_foot_landing` it returns exactly the five the receipt declares.
Its own docstring says what it is for: several consumers pick their own list of
measures and none was ever reconciled with what the coaching layer grades.

**The finding below stands unchanged. The definition is simply a cheaper way to
ask the same question.**

**CHECK AGAINST THE GRADING RECORD, NEVER AGAINST THE CLIP. I got this wrong in a
first draft of this document and measured it before sending.** On
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

### What "landed" means, which the video lane asked me to define

**`movesWith` names work in a form a machine can resolve, or it names nothing.**
Three forms, and the third is the honest one:

| form | resolved by | when it counts as landed |
|---|---|---|
| `pr(<number>)` | the forge | the pull request is merged |
| `commit(<sha>)` | `git merge-base --is-ancestor <sha> main` | it is an ancestor of main |
| `ruling(<heading>, <date>)` | **nothing. It cannot be resolved.** | **never** |

**AN UNRESOLVABLE `movesWith` IS TREATED AS STILL MOVING, NEVER AS LANDED.** That
is the safe direction and it must be the default. Work that has been ruled but
not started has no pull request and no commit, and a generator that read "no
reference found" as "nothing is moving" would publish exactly the numbers this
field exists to protect.

**The release retiming is a `ruling` today.** It is ruled and in progress, so it
has no merged reference, so every question that moves with it stays marked. That
is correct, and it is the case the design must not get wrong.

---

## 7a. Two rules from the video lane, both from defects of the last two days

**Both are theirs and both are adopted.**

**A FIGURE THAT APPEARS TWICE IS GENERATED ONCE.** A mutation that changed a
number on a printable card and left the same number in the page's prose passed
all 94 of their tests. **A coach follows the card.** So a figure has one source in
the specification and every rendering derives from it; a figure written twice is
a defect the generator refuses rather than a discrepancy a reader may notice.

**THE GENERATOR REFUSES A FIGURE THAT IS NOT IN THE MERGED TREE.** They kept a
four-drill table off the page yesterday because those figures were real, measured
and not on main. **A coach's mark is scored against a build**, so the page must
quote what is merged. This is the same rule as `movesWith` seen from the other
end: one refuses a figure whose work has moved, the other refuses a figure whose
work has not arrived.

---

## 8. Agreed with the video lane, 2026-09-09

**All four questions are answered and nothing is outstanding between us.**

1. **Questions, not a page.** Agreed.
2. **One type with an ordered answer list**, which is their shape and better than
   both mine and the orchestrator's. Refer to section 3.
3. **All five refusals are implementable.** Two are cheaper than I thought:
   refusal 3 is free, and refusal 4 has a cheaper route through the definition.
   **They strengthened refusal 2**, because my version would not have caught the
   defect it was written for.
4. **The artefact forms split by lane**, and **a third lane is needed to close
   the interface**. Refer to section 4.

**What each of us gave the other.** They took my `serves` field, the questions
-not-a-page decision and the receipt-not-clip finding. I took their answer-list
shape, their evidence-match version of refusal 2, their cheaper route to refusal
4, their two rules in section 7a, and JSON.

**Neither of us has built anything.**

## 9. What this interface does not settle

**Where the specification lives, and in what format — SETTLED.** The video lane
proposes **JSON**, because every artefact on their side is already JSON with a
schema and a refusal, and because a specification a test can parse is one a test
can check `serves` against in both directions. **Agreed.** I had left it to them
and they chose for a reason that improves my own field.

**Whether the existing page is regenerated or left alone.** It is held until
Marius is happy with it. Regenerating it is a bigger decision than this interface.

**The generator's own tests.** They belong with the generator.
