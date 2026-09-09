# The ten items with no home: what each one needs

Written 2026-09-09 by the content lane, on `13148a7`. **This document specifies.
It does not build.** The video lane owns Erin's page and is preparing v14.

`docs/COACH_MORNING_RUNNING_ORDER.md` found that the page's eight questions cover
seven of the agenda's twenty items, and that **ten live items have no home on
it**. Every one was added since 2 September. This document says what each of the
ten needs.

**The ten are still ten after items 17 and 18 were added.** Item 17 is the page's
own existing first question. Item 18 is a render set that does not exist yet.
Neither adds to the homeless count.

---

## The answer in one table

| item | what it needs | worth the page? |
|---|---|---|
| 11, the band floor | **a page section, and it is BLOCKED** | yes, when unblocked |
| 12, the bounce with no bounce | **a page section** | **yes, strongly** |
| 13, the one hand high pass | **a page section** | **yes** |
| 15, clips stopping short | **a page section**, sharing 12's clip | **yes** |
| 16, the landing's foot gap | **a page section** | **yes** |
| B, vocabulary conflicts | a written question | no |
| 10, which passes the board needs | nothing but the room | no |
| 14, one-handed determinacy | nothing but the room | no |
| A, a second grader | nothing but the room | no |
| C, two manual titles | nothing but the room | no |

**Five of the ten are worth a page section. Four need nothing but the room. One
is a written question.**

**Four of the five have their clip already.** `spikes/clip-baseline.json` carries
twelve exported clips, and they include all four passes and the landing. **Items
12, 13, 15 and 16 can be built today.**

---

## The five page sections, specified

Each follows the page's existing pattern: a short explanation in her language,
the artefact, one question, then named options including one that lets her say
she cannot tell.

**Item 16 is the one exception and it is deliberate.** It asks two questions, an
open one before a closed one, for the reason given in its own section. **Do not
make it match the others.**

### Item 12: the bounce pass has no bounce

**Artefact:** `pass.netball.bounce-pass`, the exported clip. **The clip is the
evidence.** She watches the ball leave on a correct path and the clip end while
the ball is still descending.

**Explanation:** the engine has no floor, so a released ball keeps going in one
unbroken curve. The drill shows the throw of a bounce pass honestly and is
silent about the bounce.

**Question:** is a drill that teaches the THROW useful to you while the bounce is
absent, or does it wait for the floor?

**Options:** useful now / it should wait / useful with a warning on it / cannot
tell.

**Why it earns a page section:** this is the one item where watching costs less
than reading. A sentence saying "the ball does not land" is weaker than seeing it
not land.

### Item 13: the one hand high pass's ungraded cue

**Artefact:** `pass.netball.one-hand-high-pass`, the exported clip.

**Explanation:** the manual's first instruction for this pass is *"Pull the ball
up as high as arm can go"*. That is a height, and the engine has no measure for a
height, so **the cue the drill is named for is not graded**. Everything else in
the drill grades cleanly. For her information and not graded: the ball reaches
199.95 cm, her crown is at 163.4, and the overhead pass reaches 184.4.

**Question:** is a drill whose defining cue is ungraded useful to you, when
everything else in it grades cleanly?

**Options:** useful / not until the height is measured / useful if the gap is
stated on it / cannot tell.

### Item 15: every pass clip stops before the ball arrives

**Artefact:** the same bounce clip as item 12, plus one of the chest or overhead
clips for contrast. **Put this section immediately after item 12** so the clip is
already in her eye.

**Explanation:** all four pass clips hold the same amount of flight after the
ball leaves. On three the ball reaches its target before the clip ends, with one
frame to spare on the overhead pass. On the bounce pass it never does.

**Question:** should a pass clip carry the flight all the way to the catch, or
only the release and the follow-through?

**Options:** to the catch / release and follow-through is enough / it depends on
what the clip is for / cannot tell.

### Item 16: the landing's foot-height gap

**Artefact:** `land.netball.double-foot`, the exported clip.

**Explanation:** this drill is the only one graded on a distance rather than an
angle. It measures how far apart her two feet are in height. Over the whole clip
that distance never exceeds 1.22 cm, and the three graded readings are 0.00, 0.00
and 0.01 against bands six to fourteen centimetres wide.

**ASK THE OPEN QUESTION FIRST, AND DO NOT SHOW THE OPTIONS UNTIL SHE HAS
ANSWERED IT.** The order is the specification here, not a preference.

**First, a free text field and one question:** when you watch a landing, what are
you looking at?

**Only then, a second question:** is the height difference between her two feet
part of it?

**Options for the second:** yes, that is one of the things / no / only on some
landings / cannot tell.

**WHY THIS ORDER AND NOT THE TIDIER ONE. If she is shown "a foot-height gap" as
an option before she has said what she watches, she will very likely agree with
it**, and we will have learnt nothing except that our own option is plausible.
That is anchoring, and it would make the item look answered while answering
nothing.

**A second reason, weaker but real:** if she names something the engine has no
measure for, that is the item's real output, and a multiple choice throws it
away.

**Do not reorder these two questions for tidiness.** A later reader will be
tempted to put the closed question first because it renders better. That
destroys the item.

### Item 11: the band floor missed by 0.05 degrees — SPECIFIED BUT BLOCKED

**Artefact:** four clips of `netball_two_hand_snatch_pull_in`, one per ball —
plain, high, low and wide.

**THOSE CLIPS DO NOT EXIST AND CANNOT BE EXPORTED TODAY.** The ledger records
why: `CLASSES` is keyed by movement, so a variant clip needs a `(movement,
variant)` key, and **inventing that key would answer the clip contract's open
question by accident** — is a high-ball snatch the same technique to Tactics, or
a different one a board can name?

**So this section is blocked by a decision, not by work.** It becomes buildable
the moment Marius answers the variant question, and not before.

**If it is built:** show the four balls, give the four readings at contact
(66.05, 81.63, **49.95**, 70.03) against a floor of 50.0, and ask whether the
floor is slightly high for a genuinely low ball, or the low ball asks for
something the technique cannot give.

**Do not ask her to see 0.05 degrees.** She cannot, and the page should say so.
The clips are there to let her judge the LOW BALL, not the margin.

---

## The one written question

### Item B: vocabulary conflicts

**Not a page section.** It is two lists of words, and a page renders lists no
better than a sheet of paper does.

**Send it as a written question before the morning**, with both lists set out,
so she arrives having read them. It pairs with item 10, which is Marius's
decision after she has spoken.

---

## The four that need nothing but the room

**None of these is improved by a page section, and building one would cost the
video lane time for no gain.**

- **Item 10, which passes the board needs.** A decision Marius takes AFTER her
  answers to items 12 and 13. Asking it on a page before those answers exist
  would invite an answer to the wrong question.
- **Item 14, the one-handed determinacy.** A briefing, not a question. It tells
  her that on one-handed drills the numbers are less able to see a wrong pose, so
  her eye matters more there. There is nothing to look at: the finding is about
  how the solver behaves, not about how the athlete looks.
- **Item A, a second grader.** A question about people.
- **Item C, the two manual titles.** Record-keeping.

---

## What this specification does not settle

**Whether the page should grow at all.** It is held until Marius is happy with
it, and adding five sections to a held page is his call and the orchestrator's,
not this lane's. This document says what the five would contain if the answer is
yes.

**The order the sections appear in.** The running order puts all five in block 3,
where the order within the block does not matter. Item 15 is the exception: it
should follow item 12 directly, because it reuses that clip.
