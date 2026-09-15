# Capability and result: which document is which

Written 2026-09-09 by the content lane, **recounted on `40e1f2f`** after PR #99
merged and moved three documents from in flight onto main. **This document
classifies and proposes. It rewrites nothing.** A rewrite is a second unit, after Marius
rules on the classification.

Principle 4 of `.remember/PRINCIPLES.md` asks for two documents and never one:
capability is durable, result is per shoot or per build, and mixing them is why a
finding from a test recording keeps reading as a conclusion about the sport.

**This asks which of the two each document under `docs/` already is.**

---

## The count, stated because a count is a claim about a list

**`docs/` holds 28 markdown documents on `40e1f2f`, and 29 counting this one**,
which is on a branch and classifies itself below.

**7 capability. 4 result. 18 mixed.** 7 plus 4 plus 18 is 29.

**THE DANGEROUS CLASS IS THE MAJORITY**, and that is the finding rather than any
individual placement.

**A FIRST VERSION OF THIS DOCUMENT COUNTED 25**, which was correct on `a5d60da`
and wrong an hour later. PR #99 merged three documents I had listed separately as
in flight. **They are now folded into the tables below**, and this paragraph
stays because a count is only true of the tip it was taken on — which is the same
point the stamping rule makes.

---

## The rule used, so a reader can disagree with the rule rather than the verdict

- **CAPABILITY** if every sentence would still be true after a new shoot and a
  new build.
- **RESULT** if it describes what one shoot or one build produced.
- **MIXED** if it holds both, **so that a durable sentence and a per-shoot
  sentence cannot be cited apart.**

**Mixed is not a criticism of a document.** Most of the fifteen are mixed because
a finding and its method were written down together, which is the natural way to
write them. It is a statement that the document cannot be cited safely by
someone reading one section.

---

## Capability: 7

| document | why |
|---|---|
| `ARCHITECTURE.md` | what the system is and where its boundary sits |
| `DESIGN.md` | a candidate design, and it marks itself not agreed |
| `FILMING_GUIDE.md` | how to film. Principle 6 names it as iterative, second edition |
| `LICENSING.md` | licensing decisions |
| `REQUIREMENTS.md` | what the system must do |
| `TACTICS_CLIP_CONTRACT.md` | the boundary between two repositories |
| `COACH_REVIEW_SPEC_INTERFACE.md` | what a generator must refuse. It holds no figure of its own |

**`TACTICS_CLIP_CONTRACT.md` is the only document under `docs/` with no
commit-like reference anywhere in it.** That is what a capability document looks
like when it is doing its job.

## Result: 4

**All four carry the identity of what they measured.**

| document | what it measured | identity carried |
|---|---|---|
| `COACH_FIGURES_PACK_aa3f244.md` | library `2413f9d`, 11 drills, 144 stills | **in the filename AND the text**, with an archive digest |
| `COACH_REVIEW_2026-08-30.md` | the build of 2026-08-30 | in the filename and in a warning at the head |
| `FAN_AND_RELEASE_PACK.md` | the shipped library `2413f9d` | named, with the archive path |
| `HAND_MIRROR_EVIDENCE.md` | the fix at `fde5d5a` | named in its first line |

**No result document is missing its identity.** That is better than I expected
and it is worth saying plainly, because the risk this unit was set to find is not
where I would have guessed.

## Mixed: 18

| document | the durable half | the per-shoot or per-build half |
|---|---|---|
| `KNOWN_ISSUES.md` | the rules of method, the fault classes | every measured row, per build |
| `HANDOFF_RENDERING.md` | the procedure for the next run | what this shoot produced |
| `VIDEO_CAPTURE_FINDINGS.md` | "what to change", "method notes for whoever runs this next" | "what was measured, and how well" |
| `WRIST_AND_PACE.md` | what this footage cannot resolve; the pace has no author | what Marius saw on this build |
| `BALL_SPEED_PROVENANCE.md` | the constant has no source | what it costs on today's drills |
| `BOUNCE_PASS_INSTRUMENT_AUDIT.md` | which measures exist and which cue each can read | the flight figures |
| `ONE_HAND_HIGH_INSTRUMENT_AUDIT.md` | the same instrument survey | the reach and sweep figures |
| `CLAVICLE_ARTEFACT.md` | how a solver basin misleads | which builds it misled |
| `RELEASE_SEAM.md` | the mechanism | the four hitches measured |
| `RELEASE_TIMING_COST.md` | why an anchor in the wrong place costs | what it costs on these four drills |
| `SEAM_SWEEP.md` | the question asked of every boundary | the answers on this library |
| `REFERENCE_CURVE_WIDENING.md` | the design | that it landed, and what the columns hold |
| `LOB_AUTHORING_BRIEF.md` | how a lob's ball file should be authored | the measured apex figures |
| `TACTICS_CONTRACT_QUESTIONS.md` | six questions about the contract | "today's gap read, with its inputs" |
| `COACH_MORNING_2026-09.md` | the twenty-one questions and why each is asked | every figure quoted under them |
| `COACH_MORNING_RUNNING_ORDER.md` | the order and its dependencies | the three hours, and which artefacts exist today |
| `COACH_MORNING_PAGE_SPEC.md` | the five section specifications | "can be built today", which is true of one tip |
| **`CAPABILITY_AND_RESULT.md`** | **the rule and the stamping proposal** | **every count in it, including this one** |

**Several of these announce their own mixing in their first lines**, which is the
honest form of the fault rather than a hidden one. `VIDEO_CAPTURE_FINDINGS.md`
and `HANDOFF_RENDERING.md` both open with a warning that the source files were
renamed after much of the document was written.

---

## One stamping rule

**IDENTITY ATTACHES TO THE HEADING THAT OWNS THE FIGURES, NOT TO THE DOCUMENT.**

Every heading that states a figure names what that figure was read on: a build
commit, a footage sha256, a receipt path, or "nothing measured". **A document
whose headings all name the same thing may hoist it to the head** and say so.

### Why the heading and not the document

**A document-level stamp is a lie for half the sections of a mixed document**, and
eighteen of twenty-nine are mixed. Stamping `KNOWN_ISSUES.md` with one build would
be false on nearly four thousand lines.

**The heading is also the smallest unit anyone cites.** Every cross-reference in
this repository points at a document and a heading, so the identity arrives with
the citation rather than being left behind.

### It is not a new invention. One document already does it

`docs/BOUNCE_PASS_INSTRUMENT_AUDIT.md` carries this at its head:

> **TWO BUILDS APPEAR IN THIS DOCUMENT AND THE SPLIT IS DELIBERATE.** The
> instrument survey below is from `32663a9` and is unchanged, because
> `MEASURE_UNITS` has not moved since. **Every FLIGHT figure was re-measured on
> the engine at `eaecbb2`.**

**That was written because the document could not be cited safely without it**,
and it was written by hand after a review found figures from three builds in one
pack. **The rule is that paragraph, generalised.**

### What it costs, honestly

**Fifteen documents need it and one of them is 3952 lines.** This is not an
afternoon. The proposal is therefore an ORDER rather than a sweep:

1. **The four result documents already comply.** Nothing to do.
2. **The six capability documents need one line each** saying they are durable
   and hold no per-shoot figure. **That is the cheapest and it is also the one
   that protects most**, because a capability document quoted as a result is the
   fault principle 4 names.
3. **The mixed documents, worst first by how often they are cited.**

**AND `KNOWN_ISSUES.md` NEEDS ITS OWN DECISION RATHER THAN A PLACE IN THAT
QUEUE.** A first version of this section put it last, on the reasoning that its
rows already name their builds individually and the unstamped ones are the
exception. **I counted, and that is false.**

| the ledger, counted | |
|---|---|
| `##` headings | 76 |
| `###` headings | 100 |
| **sections in total** | **176** |
| lines carrying any build-naming phrase | **41** |
| lines with the strict "measured on `<sha>`" form | **15** |

**Fewer than a quarter of its sections name what they were read on.** So the
ledger is not the document that mostly complies. **It is the largest unstamped
surface in the repository, and it is also the most cited.**

That combination is why it needs a decision rather than a queue position: it is
both the highest value to stamp and the most expensive, and the choice between
stamping its 176 headings and splitting it into rules and findings changes the
cost by an order of magnitude. **Refer to the last section: that choice is
Marius's and this document does not take it.**

---

## A second rule, and it is for CAPABILITY documents: the tense

**THE STAMPING RULE ABOVE ASKS NOTHING OF A CAPABILITY DOCUMENT**, because a
capability document holds no per-build figure. **It can still be false, and in
exactly the way a result document can.**

`docs/COACH_REVIEW_SPEC_INTERFACE.md` merged on 2026-09-09 saying, in the present
tense, that the render receipt "now carries `solveParameters`" and that
`render_receipt.refuse_unverifiable_pair` refuses a pair it cannot read.
**Neither is on main.** Both are on a gated branch. The document is not wrong
about the machinery. **It is wrong about which build has it**, and the word "now"
is what makes that a claim rather than a plan.

**THE RULE, AND BOTH HALVES MATTER:**

> **A document may not use the present tense for code that is not on main, and
> TEXT RECEIVED FROM ANOTHER LANE IS REWRITTEN INTO THIS DOCUMENT'S TENSE BEFORE
> IT IS COMMITTED.**

**The second half is the one that catches the fault.** The rendering lane wrote
"the render receipt NOW carries `solveParameters`" and it was TRUE, of its own
branch, where the code is. This lane committed that text into a document on main,
where "now" means main, **and the sentence became false in transit.**

**TEXT HANDED BETWEEN LANES CARRIES THE SENDER'S TENSE**, because the sender is
standing on the branch that makes it true. **Neither lane wrote a false sentence
and a false sentence is on main.**

### Why a rule and not a stamp, and the measurement that decided it

**A per-claim build stamp was the other candidate, and it was measured and
rejected rather than argued away.**

`scripts/docs_present_tense_audit.py` reads every backticked span under `docs/`,
keeps those shaped like code identifiers, and checks each against every tracked
non-document file at a named commit. **On `b011d39`:**

| | |
|---|---|
| backticked spans | 3636 |
| distinct identifiers kept | **513** |
| identifiers that resolve | **462**, or 90.1% |
| identifiers that do not | 51 |
| **faults, after reading the sentence for all 51** | **3** |

**The three sit in two documents.** Two are the one sentence above. The third is
`docs/KNOWN_ISSUES.md` citing a test as
`test_the_target_is_on_the_elbow_circle_where_the_basis_is_orthogonal`, where the
method is `test_the_target_is_on_the_elbow_circle`. **A reader who searches for
the cited name finds nothing and concludes the citation is invented**, which is
the harsher of the two readings available.

**THE OTHER FORTY-EIGHT ARE CORRECT, AND A HEADER IS WHY.** The documents most
exposed to this declare their tense in their opening lines:

| document | what it says of itself | identifiers absent | faults |
|---|---|---|---|
| `RELEASE_HAND_PAPER.md` | "It proposes a model and changes nothing" | 12 | 0 |
| `TACTICS_CLIP_CONTRACT.md` and its questions | "the boundary between the two products" | 15 | 0 |
| `WHAT_BETTER_ANIMATION_MEANS.md` | "Untracked, so no clone has it" | 1 | 0 |

**Twenty-eight identifiers absent from the code, and not one is a fault, because
the document said what it was.** A per-claim stamp would have added twenty-eight
stamps and prevented nothing.

### The instrument was wrong twice, and both counts are in it

**A first version reported 129** and counted `.md` filenames, OCR page markers
and dotted paths whose last segment exists. **A second reported 75 and searched
file CONTENTS for a FILENAME.** A Python file does not contain its own name, so
seventy-six real test files were listed as missing.

**That second one is a HAYSTACK error rather than a NEEDLE error, and it fails in
the direction that manufactures work.** The script now refuses to report until
three known-present names are found in its haystack, and that refusal is
exercised rather than assumed.

**Both failed counts stay in the script**, because a number is worth what its
predecessors' failures show it survived.

### And the audit read this document's own count back to it

**The classification above covers 29 documents on `40e1f2f`. `docs/` holds 41 on
`b011d39`.** Twelve have been added since and none of them is classified.

**That is this document's own rule working rather than failing.** The count names
the tip it was taken on, so it is stale and not false, and a reader can see the
gap without measuring anything. **The tables are a snapshot and the rule is the
durable half**, which is the split the document argues for everywhere else.

**Naming the gap is not a commitment to close it.** Whether twelve more documents
are worth classifying is a decision, and this document does not take it.

### And a second rule, because the same sentence was wrong twice: check a correction before committing it

**A CORRECTION ARRIVES WITH THE SAME PROVENANCE PROBLEM AS THE CLAIM IT
CORRECTS.** On 2026-09-09 one sentence was wrong twice in a row, in the same way,
and the second attempt was written by the lane that had just been told about the
first.

The rendering lane sent replacement text saying its fifth refusal was dormant
because "the producer records exactly ONE parameter". **This lane checked instead
of committing, and the tree said the producer records NONE.** A second
replacement followed, and it described code sitting on two unmerged branches.

**Had either been committed in good faith, main would carry a second false
sentence behind the first**, and the record would show this lane putting it there
twice.

> **A correction is checked against the tree before it is committed, exactly as a
> claim is. A correction from a lane with more standing on the file is checked
> HARDER, not less**, because standing is what makes it easy to accept.

### The case that makes both rules necessary: one contract, two branches

**`solveParameters` has a READER on one branch and a PRODUCER on another.**

| tree | producer | reader | what the guard can do |
|---|---|---|---|
| main | absent | absent | the field does not exist |
| main and the rendering lane's branch | absent | present | **only refusal 1 can fire** |
| main and both branches | present, one key | present | **1 stays reachable**, 2, 3 and 4 become live on a NEW pair, 5 dormant at one key |

**REACHABILITY IS A PROPERTY OF THE MERGE AND NOT OF EITHER BRANCH.** Two lanes
answered correctly about their own trees and got different answers, and **a gate
on either branch alone cannot settle it.**

**So a document describing that contract is false on main, false on either branch
alone, and true only after both land.** That is why the tense rule says "not on
main" rather than "not written yet": **a thing can exist, twice, and still not be
true anywhere.**

**AND THE THIRD ROW WAS WRONG WHEN FIRST WRITTEN, WHICH IS THE POINT OF WRITING
IT AS THREE ROWS.** It said check 1 becomes unreachable after the merge. **The
archived receipts predate the field entirely**, so any pair drawn from them
refuses at check 1 whatever the producer records later.

    THREE archive sets, 37 receipts, counted RECURSIVELY:

      coach-figures-2413f9d                        11 receipts
      coach-figures-aa3f244                        10
      rerender-hand-mirror-2026-09-02               0 directly, 16 beneath
          pre-fix-31aug                             8      the last batch BEFORE
                                                                the 1 Sep hand fix
          interim-05e58cd                           8      an interim build, and
                                                                NOT the corrected
                                                                figures

    carrying `solveParameters`                      NONE, at any depth

**So the guard protects comparisons this project has not yet made, rather than
the ones already on disk.** A pair can only be assembled from two receipts
rendered after the producer lands.

**The row was REASONED and the archives were READ**, and the reading disagreed.
**A row about a tree that does not exist yet is a prediction**, and this one is
kept as three rows so the third can be checked when it becomes a statement about
main rather than carried forward as settled.

### A COUNT OF FILES UNDER A DIRECTORY MUST STATE ITS DEPTH

**Four lanes measured that one directory within ten minutes and produced four
different answers. None was careless and no two asked the same question.**

| reading | sets | receipts | what it actually asked |
|---|---|---|---|
| the orchestrator, first | 2 | 21 | enumerated to look, hard-coded to measure |
| the movement lane | 3 | 21 | a NON-recursive glob |
| this lane | **4** | 37 | recursive, but grouped one level too deep |
| the orchestrator, second, and the rendering lane | **3** | **37** | recursive, grouped at the top |

**The rerender holds ZERO receipts directly and SIXTEEN one level down.** So a
non-recursive count says 0 for it and a recursive one says 16, and a listing one
level deeper reports its two subdirectories as archive sets beside the others.
**The two readings differ by the entire disputed amount.**

**MY TOTAL WAS RIGHT AND MY SHAPE WAS WRONG, AND THE SHAPE IS WHAT A READER TAKES
AWAY.** Four independent archives of graded work is a different belief from two,
plus one pair of before-and-after states from a single repair.

**So "37 receipts in the archives" is not a claim until it says whether it
descended.** A count of files under a directory carries its depth the way a
figure carries its build and a line citation carries its tip. **It is the same
rule three times: a number without its scope is not yet a statement.**

**AND A FIFTH READING OF THE SAME DIRECTORY WAS WRONG IN THIS DOCUMENT UNTIL IT
WAS CHECKED.** A draft of the block above labelled the two nested states "the
state BEFORE a fix" and "the state AFTER it", **inferred from their names and
inverted.** The archive's own `PROVENANCE.md` says it:

> `pre-fix-31aug` — "the last full batch before the 1 Sep hand fix"
>
> `interim-05e58cd` — 8 receipts on `05e58cd`. **"NOT the corrected figures"**

**So they are not a before and an after at all.** One is the last batch before a
fix and the other is an interim build that is explicitly not the corrected
state. **A name is not a correspondence**, and `pre-fix` reads like an ordering
while `interim` reads like a stage, so guessing from the pair produces a
plausible sentence that is wrong twice over.

---

## This document is MIXED by its own rule

**It classifies itself, and the answer is the uncomfortable one.**

The rule and the stamping proposal are durable. **Every count in it is true of
one tip and no other** — 29 documents, 176 ledger headings, 41 build-naming
lines. The first version of this document proved that by being wrong within the
hour.

**So it carries the fault it describes**, and the honest response is not to
remove the counts but to stamp them, which is what the rule asks of every other
mixed document.

**Three of my four coach-morning documents are mixed too, by the same rule.** The
running order's three hours and its "four renders missing" are true of today; its
ordering and dependencies are durable. **I did not see that when I wrote them
this morning**, which is the ordinary way a document becomes mixed: a finding and
its method written down together, because that is the natural way to write them.

---

## What this document does not do

**It does not rewrite anything**, per the boundary set for this unit.

**It does not rule on whether a mixed document should be SPLIT or STAMPED.**
Splitting `KNOWN_ISSUES.md` into a rules document and a findings document is a
much larger decision than stamping its headings, and it is Marius's. The rule
above works either way: after a split, each half's headings still name what they
were read on.

**It covers documents under `docs/` and nothing else, and that boundary matters.**
The video lane measured the same fault outside this unit's scope this morning:
**the page's submission payload carries no build at all.** The build appears
eight times in the page's own text and in none of what leaves the browser, so an
answer is attributable to a build only by inferring it from a timestamp. **That
is the same fault this rule addresses, in a data payload rather than a
document.** It is theirs and they are routing it; it is named here only so a
reader does not think this rule already covers it.

**It classifies by reading, not by measurement.** Every verdict above is a
judgement against the stated rule, and the rule is written down so a reader can
disagree with the rule rather than with twenty-nine separate calls.
