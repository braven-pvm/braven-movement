# Two receipts, and a second asset list

Written 2026-09-09 by the character and animation lane, against main `59a91c6`,
after PR #105 gave the movement render receipt a licence per asset.
**AMENDED the same day against main `a02d9b4`**, after the orchestrator tried
to replicate this document's own measurement and could not. Option D gained a
cost, and the section "Two claims, and only one of them is unreachable" is new.

**This document proposes no change and makes no recommendation.** Section 1 is a
requirement for the rendering lane, in the pattern the clip contract uses.
Section 2 is a question for Marius with its options and their costs. Both exist
because this lane is the only one that has now read both receipts.

## 1. A requirement: the generator's asset list and the licence table are two lists

**The state.** `create_athlete` selects seven assets by seven literal
`asset_path(...)` calls, at `blender_mpfb_reference_catch.py:1102` to `1108`.
`asset_licences.SELECTED_MPFB_ASSETS` holds the same seven names again, because a
licence has to be recorded against something. **They are two lists of one thing,
and two lists of one thing drift.**

**What holds them together today.**
`tests/test_asset_licences.py::test_the_generator_selects_exactly_the_licensed_assets`
reads the `asset_path` calls out of the generator's SYNTAX and compares the set
with the table. It is proved failing on an asset added and on an asset removed.
It is a guard against drift and it is not a cure for it.

**THE REQUIREMENT, and it is the rendering lane's file and the rendering lane's
call.** If `create_athlete` ever reads its asset names FROM
`asset_licences.SELECTED_MPFB_ASSETS` rather than repeating them, the two lists
become one, the drift becomes impossible rather than detected, and the AST guard
can be deleted. **The cost is a change to that lane's generator and a new import
in it. The benefit is one list instead of a guard.** This lane is not asking for
it, has not written it, and will not: the same rule that keeps a clip channel out
of this lane's hands keeps this out of it too.

**One caution if it is ever done.** The guard must be deleted in the same change
that removes the second list, and not before. A guard left in place against a
list that no longer exists is a test asserting that a thing equals itself.

## 2. A question: two receipts record a licence at two granularities

Both receipts describe the same athlete built from the same assets. **They record
her licence differently, and neither is wrong for its own generator.**

### What each one records

**The reference-catch receipt**, `blender_mpfb_reference_catch.py:1673` onward:

    "licence": config.licence,          <- "CC0", ONE value for the whole output
    "publishable": config.publishable,
    "source": { "assets": [ {"path": ..., "sha256": ...} ] }   <- NO licence per asset

**The movement render receipt**, after PR #105:

    "sourceAssets": [ {"path": ..., "sha256": ..., "licence": ..., "licenceSource": ...} ]
                                        <- a licence PER ASSET, with its source sentence
                                        <- and NO top-level licence or publishable

So one receipt answers "may this be published?" in one field and says nothing
per asset. The other answers per asset and says nothing about publication.

### Where each one refuses

**They also refuse in different places, and that is the larger difference.**

- The reference receipt is validated AFTER the fact.
  `reference_pose_contract.py:71` raises unless `licence` equals `CC0`, reading a
  receipt that has already been written.
- The movement receipt cannot be written wrong. `Studio.__init__` refuses an
  undetermined asset as soon as the athlete is built, **before any figure is
  drawn**, so the false receipt is unwritable rather than caught.

### THE FINDING THAT MAKES THIS WORTH ASKING ABOUT

**Three different things in this repository are written as the string `CC0`, and
they carry three different strengths of evidence.**

| where | what it is | what backs it |
|---|---|---|
| `config/reference_catch.v1.json` `"licence": "CC0"` | a DECLARATION, typed into a config, covering the whole output | whoever typed it |
| `asset_licences.py` | a TRANSCRIPTION of `docs/LICENSING.md`, per asset | a test that both sentences are still verbatim in that document |
| each MPFB asset's own file header | the ASSET'S OWN STATEMENT: "This asset was explicitly released as CC0 in september 2020" | the asset, per file |

**MEASURED: 78 of 78 installed MPFB assets declare CC0 in their own headers** —
20 clothes, 23 skins, 12 eyebrows, 10 hair, 6 teeth, 4 eyelashes, 2 eyes, 1
tongue. Refer to `docs/WHERE_A_BETTER_CHARACTER_COMES_FROM.md` section 3.

**The same word, three strengths, and nothing in a receipt says which one it
is.** That is the shape that becomes a defect: a reader who trusts the strongest
reading of `CC0` will trust the weakest one by the same name.

### The options, with their costs

**Option A. Leave them different.**
Cost: two conventions in one repository, and a reader must know which receipt
they hold before they know what its licence field means. Benefit: no work, and
each shape already fits its own generator. Risk: the next receipt picks whichever
it saw first.

**Option B. Give the reference receipt a licence per asset as well.**
Cost: a change to `blender_mpfb_reference_catch.py`, and `reference_pose_contract`
would need to decide whether it still validates the single field, the per-asset
ones, or both. Benefit: one shape across both receipts. Note: the config's
`licence` field would then be a declaration sitting beside per-asset transcriptions
of a different strength, unless it is also removed.

**Option C. Give the movement receipt a top-level `licence` and `publishable`
as well.**
Cost: small, and this lane's file. Benefit: a reader of either receipt can ask
"may this be published?" in one place. **Risk, and it is the reason this is not
free: a declared `CC0` would sit beside read `CC0`s under one word**, which is
exactly the confusion the finding above names.

**Option D. Read the licence from each asset's own header, in both receipts.**
Cost: a reader of a third-party file's comment block, in code, plus a decision
about what to do when an asset carries no such header. Benefit: the strongest
evidence available, per asset, and both `docs/LICENSING.md`'s determination and
this lane's table become derivable rather than declared. **Risk: it reads a
comment in a file this repository does not own, and a header can be edited or a
format can change.**

**AND A COST THIS TABLE DID NOT STATE, ADDED 2026-09-09 AFTER THE ORCHESTRATOR
TRIED TO REPLICATE THE MEASUREMENT AND COULD NOT. D's evidence base is
UNREACHABLE FROM A CLONE.** The 78 assets live only inside a Blender
installation, at
`.../Blender/4.5/extensions/.user/blender_org/mpfb/data`. They are not in
git, not under `.assets`, and a `find` for `*.mhclo` or `*.mhmat` anywhere under
`.assets` returns nothing. **Nobody without that installation can check the
evidence** — not another lane, not a reviewer, not a buyer's counsel. **And it is
unreplicable on the measuring machine too, once MPFB updates**, because the same
path would then name different bytes. That is `asset_licences.py`'s own opening
warning turned on the evidence rather than on the receipt.

**A REMEDY EXISTS AND IS NAMED HERE AS A REMEDY, NOT PROPOSED AS WORK.** If D
were ever chosen, the header STATEMENT would have to travel with the artefact:
the line itself, or a hash of it, copied into the receipt. **The receipt already
pins WHICH BYTES were licensed, by recording each asset's sha256. What it does
not pin is the sentence inside them.**

### Two claims, and only one of them is unreachable

**A reader of this document will otherwise conflate them, and the orchestrator
did so having read the file.** They are different claims with different
strengths and different reach.

| | what it rests on | who can check it |
|---|---|---|
| **the receipt's licence** | `docs/LICENSING.md`, quoted verbatim, **in git**, with `tests/test_asset_licences.py` re-reading the document and comparing word for word | **anyone with a clone**, and a test fails if the document changes |
| **the 78 of 78** | what the ASSETS say in their OWN headers. **Not what any receipt records** | **nobody**, without that Blender installation |

**They answer different questions.** `docs/LICENSING.md` answers "what has this
repository determined?". The headers answer "what do the assets say about
themselves?". **The second is stronger evidence and it is the one nobody can
reach.**

**So nothing that ships today rests on the unreachable measurement.** The merged
receipt's licence is replicable and pinned. The 78 of 78 is evidence for option D
and for option D alone, and it is measured, this lane's, and unreplicated.

### What is NOT being asked

- **No option is recommended here.** The lane that would do the work is named in
  each one, and the licence question is Marius's rather than any lane's.
- **The refusal placement is not in question.** Refusing at construction is
  better than validating afterwards for the reason PR #105 records — a receipt is
  a claim, so refusing early makes a false claim unwritable rather than caught —
  and nothing here proposes moving it.
- **Nothing here has been measured about whether a receipt is ever read for its
  licence.** `docs/LICENSING.md` says the current receipt "labels the selected
  MPFB-derived model output as CC0", so at least one document reads it. This lane
  has not traced every reader, and it says so rather than implying it has.
