# The movement-parameter register: what a row holds, and why

This file records decisions the orchestrator ratified on 2026-09-09. It does
not propose anything new. It exists because six columns were earned in one
morning, across four lanes, and a design held only in message history is a
design that drifts.

Read `.remember/PRINCIPLES.md` first. Principle 8 is this register's charter.

The register answers one question about every number in this repository that
makes a claim about human movement: **where did this number come from?**

The inclusion test, and a committed reason for every number left out, live in
`scripts/register_inclusion.py`.

---

## The rule the whole schema serves

**A rationale is not a source.**

Every one of the 94 graded checkpoints in the library carries a non-empty
`why`. Not one is blank. Thirty-six of them contain no digit, no quotation mark
and no file reference anywhere. One reads:

> "A locked arm cannot redirect a ball. A collapsed one cannot control it."

The band is 20.0 to 100.0. That sentence is correct coaching. It justifies that
a bound must exist. It derives neither 20.0 nor 100.0.

A reader who opens those files calls them unusually well documented. That
reader is right about the prose and wrong about the numbers. **Rich rationale
is the best camouflage an unsourced number has**, because no comment invites
the question and a paragraph closes it.

So `rationale` and `source` are separate columns. They are never merged.
Merging them is how this stayed invisible.

---

## A row

| column | what it holds |
|---|---|
| `id` | a stable identifier for the row, so a parent can name it |
| `file`, `line`, `name` | where the number lives, read from the code |
| `value` | the number |
| `unitDeclared` | the unit the code declares, never inferred from the name |
| `unitImplied` | the unit a reader would guess from the name or the value |
| `unitEvidence` | the site that PROVES the unit |
| `frame` | what the value is relative to, and what it moves with |
| `claim` | what it says about a person, in plain words |
| `rationale` | why a bound of this kind must exist |
| `sourceKind` | refer to the table below |
| `derivedFrom` | `{ parent, operation }`, empty only for a genuine source |
| `rootSource` | computed by following `derivedFrom` to its end |
| `regime` | where the quantity was measured, beside where it is spent |
| `reachedBy` | the function that reads it, and whether the library calls it |
| `existsInCode` | false for a number named only in prose |
| `whatWouldChangeIt` | a coach's ruling, a shoot, a literature value, a solve |
| `dependants` | what breaks if it moves, so the cost of a change is visible |
| `tip` | the commit the row was read on |

---

## `sourceKind`

| kind | meaning |
|---|---|
| `MANUAL` | a quoted line from the coaches manual, with its page |
| `COACH` | a ruling by a named coach, against a named build |
| `MEASURED` | an instrument produced it, and the instrument and build are named |
| `LITERATURE` | a paper, with its citation AND its population |
| `DERIVED` | it comes from another row. `derivedFrom` names the parent |
| `AUTHOR_INTENT` | a comment states what the number is FOR, and cites nothing |
| `NONE` | nothing states where the value came from |

**`AUTHOR_INTENT` is not `NONE`, and the difference is practical.**
`author_flight.DEFAULT_SPEED_CM = 600.0` carries this comment above it:

> `# A drill feed. A game pass is faster, and the flight gets shorter with it.`

A number that says what it is for can be put to a coach in one sentence. A
number that says nothing cannot even be put to her. `docs/KNOWN_ISSUES.md`
already holds both halves in one sentence and has no word for the distinction.

---

## `sourceScope`: a source can prove less than it appears to

Three states a row can be in, and they are independent:

| state | example |
|---|---|
| unsourced, correctly described | `author_flight.DEFAULT_SPEED_CM = 600.0` |
| unsourced AND wrongly described | `release@0.80` in three of five files |
| **sourced, for a claim narrower than its use** | `contact_solve.TWIST_SEEDS` |

The third is the commonest and the hardest to see. `TWIST_SEEDS` is not
unsourced. Its comment gives a mechanism, a cost of 20 ms, and a named failure
it removes: from rest the hand "rolled the wrong way round and jammed against
the pronation limit with the palm facing away", and several seeds remove that
entirely.

**That is a claim about a LIMIT JAM. It is not a claim about basin stability.**
The movement lane's sweeps on 2026-09-09 measured the library still crossing
basins with the seeds in place, on parameters the seeds do not touch: the
overhead pass's step knee reads 0.00 degrees at one spacing, +8.40 at the next,
0.00 at the third and +8.30 at the fourth. **A reader who filed that comment as
evidence of a stable solve would be reading a scoped claim as a general one.**

So a row records what its source proves, not only that it has one. This is the
repository's arm-constants fault class, recorded sixteen times: a quantity
measured in one regime and spent in another. **The register may be the first
place it becomes visible before it is spent.**

---

## `rootSource`, and why a chain needs following

**A chain that terminates in NONE is unsourced however many hops it has. A
chain that terminates in a measurement is sourced however deep it runs.**

The authored carry offset arrived from the contract lane as one triple in four
ball files, filed as wholly unsourced. Following it:

1. `netball_chest_pass.ball.json` holds `across 0.0, up 0.12, ahead 0.55`.
2. Its own note converts it from a parent, divided by 1.017053. The arithmetic
   is exact: 0.120004 and 0.550001.
3. The note points at the parent drill's `.ball.json`, which has no such key
   and every note in it empty. The values live in that drill's
   `.technique.json` instead.
4. `netball_two_hand_snatch_pull_in.technique.json` records a measured sweep:
   "0.40 gives 153 degrees of elbow flexion, 0.50 gives 149, and 0.55 gives
   145", chosen because an earlier draft passed the limit at
   `spikes/isb_angles.py:241`.

So `ahead 0.55` is sourced three hops deep. `up 0.12` has no derivation below
the conversion. **One row, filed as wholly unsourced, is half sourced and half
not, and neither half is visible without following the chain.**

---

## The rule above the rules

The movement lane found the general form, after four instances in one morning:

> **The thing that answers the question sits one level away from where the
> question was asked.**

| the question | where the answer was |
|---|---|
| where did this release key come from? | the file's `source`, one level up |
| where is the carry authored? | the technique file, not the ball file |
| is this code on the library path? | the function, not the module |
| what population do these limits describe? | the comment, not the field |

Four different levels and one shape. Two lanes made two of these while telling
each other to check the source rather than the message. **It is not ignorance
of the rule that causes it. It is that a read stops at the level the question
named.**

So a read that fails to find something states which levels it read. The rules
below are the specific forms this took.

---

## The five rules that produce a row, and the defect that bought each

A rule with its defect attached is followed. A rule without one is a slogan.

### 1. A generated number is not a witness

`netball_two_hand_catch_chest.ball.json` records `ahead 4.0` at its release
key. That looks like an independent sighting of
`author_flight.DEFAULT_PASSER_AHEAD = 4.0`. It is not. `author_flight.py`
builds the release point at `chest[2] + passer_ahead * arm_cm` and converts
every key back with `(world - chest) / arm_cm`, so the release component
reduces to `passer_ahead` exactly. **No value of the constant could have made
the two disagree.**

Eleven derived launch speeds are one constant seen eleven times. Four files
holding the ball radius 11.0 are one authoring seen four times. **A register
that counts sightings reports a library as well grounded because one number
appears in fifteen places.**

*The defect: this lane offered that release key as an independent witness one
paragraph after writing the rule against it. The movement lane refuted it.*

### 2. A file that names a parent makes its numbers children

The trigger is a named PARENT, in the file's `source` or in any key's note. It
is not a named generator, and it is not satisfied by a file declaring what did
NOT author it.

Of the 15 ball files, 10 name `author_flight.py` as their generator, 4 declare
"Authored by hand, NOT by author_flight.py", and 1 cites a manual page. **The
four that deny the generator are the four passes, and the chest pass's own key
note then derives its numbers from another file.** A file can be downstream
while declaring that no generator touched it.

The row-level read cannot find this. The release key's note field is EMPTY and
its provenance sits one level up, in the file's `source`.

**"Declares a generator" and "is downstream" are independent properties.** A
file can declare a generator and be a source for some of its keys. A file can
deny every generator and still be downstream. Test for the parent. Do not test
for the declaration.

*The defect: this lane asserted fifteen where the list says ten, on a day it
quoted "a count is a claim about a list" at three lanes.*

### 3. `derivedFrom` carries the operation, not only the parent

"Copied from X" and "X divided by a torso-to-arm ratio" are different rows. A
duplicate needs collapsing, so the register stops counting one source twice. A
unit conversion needs CHECKING, because a unit conversion is where this
project's numbers go wrong. The conversion above was verified to five places
only because the note stated it.

### 4. A row carries the unit's EVIDENCE, not the unit

`unitDeclared` and `unitImplied` can both be filled by a person who read the
name. `DEFAULT_PASSER_AHEAD = 4.0` is 4.0 ARM LENGTHS. The evidence is the
multiplication at `author_flight.py:123`, and the recorded `passerAheadCm:
210.7` against a 52.68 cm rest arm, which tests the unit through a different
quantity.

*The defect: the movement lane published that constant as metres inside the
document tracing that exact fault class. A drill file's own note saved it.*

### 5. A value without its frame is half a value

`0.12` and `0.55` mean nothing without "arm lengths, from her chest anchor, in
her own frame". The offset is constant in her frame and moving in the world,
so the ball is pinned to her and travels 0.36 to 1.60 cm per frame.

The per-frame figures are the movement lane's, measured across all 76 held
frames of each of the four passes. They are cited to `15d9857` on
`lane/movement-release-hand`, which is **NOT merged into main**. This lane did
not re-derive them.

*The defect: three lanes guessed three different origins for one phrase in one
morning. The orchestrator read a carry path, the contract lane read a held
point, and the truth was neither.*

---

## `reachedBy`: a file is not on or off the path, its functions are

`solve_contact` is defined at `contact_solve.py:508` and called once, at 724,
inside that file's own `main()`. It is a spike entry point and the library does
not call it.

`ELBOW_POLE_ANGLE_DEGREES` is used at line 376, inside `elbow_poles`.
`UPPER_ARM_AIM_OUT` and `UPPER_ARM_AIM_DOWN` are used at 434, inside
`upper_arm_aim`. Both functions sit outside `solve_contact`.
`possession_solve.py` imports both by name at lines 35 and 36 and calls them at
304 and 308.

**So the 31.3 a coach is being asked to move to 37.3 is reached by every solve
the library performs.** "The module is not on the library path" and "these
constants are not reached" are different claims.

---

## What this register does NOT do

It changes no engine code. It produces documents and, later, proposals. A
parameter change is another lane's unit, with its own guards and its own sweep.

It does not re-derive another lane's measurement. It cites it.

---

## Open rows recorded on 2026-09-09

- **The AAOS limits: an incomplete citation, and NOT an unsourced number.**
  `spikes/isb_angles.py:240` holds eight joint limits and sixteen numbers, and
  `build_library.py` checks every drill against them. The two lines above the
  table read: "Clinical norms from the American Academy of Orthopaedic
  Surgeons. These are guidance for a healthy adult. An athlete population needs
  its own bands." **So the organisation is named in full and the population is
  stated, and the author already recorded the limitation this register would
  have raised.** What is missing is narrower: the organisation is not a
  publication, so there is no edition, no page and no way for a reader to check
  the sixteen numbers. `sourceKind: LITERATURE`, population STATED, citation
  INCOMPLETE.

  *This lane first reported the row as "four letters, no edition, no page, no
  population", to three lanes, and one of them repeated it. It had read the
  table and not the two lines above it. That is the third time in one morning
  this lane scoped a read to the thing named and missed what sat one line up.
  Refer to the habit section below: what was measured was "the dict entries say
  AAOS", and what was published was "there is no population".*
- **The secured-ball parent.** The torso-length values that four drills' carry
  geometry descends from. The parent drill's ball file has no key after its
  arrival at 0.45, so the values live somewhere not yet found. Whether they
  descend from the 600 or are an independent authoring is unknown and is not
  guessed. Raised by the movement lane.
- **The manual-cited ball file.** `netball_two_hand_snatch_pull_in` is the only
  ball file whose source names an authority outside this repository, at page
  71. It is the only one that could fail an audit in an interesting way,
  because a page citation can be checked. Nobody has checked it.
- **Pass speed as a coachable objective.** The manual names a faster pass as an
  objective in two drills and gives no number for it. A drill whose objective
  is a faster pass cannot be graded by an engine whose pass speed is one
  constant. This is a claim about the sport. It belongs to the research
  section. Raised by the movement lane.

---

## Attribution

The columns and rules above were earned by four lanes on 2026-09-09. The
movement lane earned rules 1, 3 and 4. The contract lane earned rule 5 and the
first chain. The footage lane established that a guard narrower than its
promise converts an unexamined area into a reassured one. The orchestrator
ratified each.

One pattern is worth more than any single rule. Not one of the four errors
recorded that morning was caught by the lane that made it. Every one was caught
by a lane that went to the SOURCE rather than to the MESSAGE. **An absence
claim must say what was READ, not what was looked for.**

---

## The habit under all of it: publish the claim you measured

The contract lane found the general form in its own three errors of that
morning, and it is the rule this register most needs:

| what it measured | what it published |
|---|---|
| "no citation in the five fields I printed" | "no citation in any of the four files" |
| "the offset is constant" | "the wrist is stationary" |
| "this function is not called" | "this module is not reached" |

Each time the narrow claim was the one it checked, and the wide one was the one
it wrote. **That is not three errors. It is one habit with three outputs**, and
this lane's own four fall into the same shape.

The third row cost the most. **The wide reading would have removed
`ELBOW_POLE_ANGLE_DEGREES` from this register**, and that constant is on the
coach agenda, where Erin is being asked to move it from 31.3 to 37.3. The
orchestrator had already dictated the broad version into a document about to
merge. The pull request is held until the sentence is narrowed.

So a row in this register states the claim that was measured. When a wider
claim follows from it, the wider claim is a separate row and it is marked as an
inference until somebody measures it.
