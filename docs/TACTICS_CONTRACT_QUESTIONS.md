# Five questions on the clip contract, answered where the evidence answers them

Written 2026-09-04 against `braven-movement` main at `cc2c20a` and
`braven-tactics` main at `987e2e2`. Every number below names the file and the
commit it was read from. Nothing here changes code, and nothing was written into
`braven-tactics`.

What each of the five turns out to be:

| | question | what it is |
|---|---|---|
| 1 | variants | **a decision**, framed here in three options and not taken |
| 2 | the release vocabulary | **a coach question**, and it gates the lob |
| 3 | truncation | **answered by the code**, and the answer is "nothing reads it" |
| 4 | `generatedFrom` | **a proposal**, for a gap with no field at all |
| 5 | the ball anchor | **a proposal**, for a residual on a design that is right |

This document has been through one independent review, which found three
blocking errors and ten smaller ones. Every correction is kept visible in the
section it belongs to rather than quietly folded in, because two of the three
were wrong in a way that is easy to repeat.

**The single most useful fact in this document, because four of the five
questions depend on it:** a clip loses fields at TWO places between the exporter
and the board, and the first of the two is an allowlist that silently drops ten.
Section 0 establishes this, and the later sections lean on it.

---

## 0. What survives the journey from the exporter to the board

There are three stages, not two.

| stage | fields | where |
|---|---|---|
| the exporter writes | **23** | `spikes/export_tactics_clip.py`, `cc2c20a` |
| `clips.json` carries | **13** | `public/figures/clips.json`, live on production |
| Tactics reads | **4** | `src/engine/clips.ts`, `987e2e2` |

### Stage one: the exporter writes 23

    schemaVersion  clipId  class  sport  technique  movementId  skill  source
    graded  stride  seconds  hit  hitPhase  inPlace  rootTravelM
    travelsUnderItsOwnPower  framesPerSecond  contactFrame  releaseFrame
    phases  ballRadiusM  ball  frames

### Stage two: an allowlist in Tactics drops ten of them

`tools/add-technique-clip.mjs` on `braven-tactics` `987e2e2` does not copy the
clip. It builds a new object field by field:

```js
set[clip.clipId] = {
  // What the player reads. Nothing below this line is read at play time.
  stride: 0, seconds: clip.seconds, hit: clip.hit, frames: clip.frames,
  // What a coach reads, and what says this is a technique rather than a capture.
  movementId: ..., skill: ..., graded: ..., inPlace: ..., rootTravelM: ...,
  hitPhase: ..., phases: ..., ballRadiusM: ..., ball: ...,
}
```

**Nine exported fields are dropped here and never reach the file:**

    schemaVersion  class  sport  technique  source
    travelsUnderItsOwnPower  framesPerSecond  contactFrame  releaseFrame

A tenth, `clipId`, is not dropped. It becomes the key of the object, so it
survives as the name of the clip rather than as a field inside it. That is why
23 − 13 = 10 while only nine fields are lost.

I confirmed the count against the shipped file rather than against the tool. The
clip `catch.netball.two-hand-snatch` has exactly thirteen keys.

**There is a second allowlist inside the first, and it is easy to miss.**
`phases` is not copied either. It is rebuilt entry by entry:

```js
phases: (clip.phases ?? []).map((p) => ({ name: p.name, at: p.at, cues: p.cues })),
```

so a phase's `frame` and `checkpoints` are dropped even though `phases` itself
survives. **A field can therefore be lost at three depths**: never exported,
dropped by the outer allowlist, or dropped by this inner one. Any proposal that
adds something inside `phases` has to change this line as well.

**This is the fact that matters most in this document.** A new field on the
exporter does NOT arrive at the board. It stops here, silently, because the
allowlist is written as a literal and an unlisted field is simply not mentioned.
Sections 3, 4 and 5 each propose a field, and each proposal must change this
tool as well as the exporter, or the field goes nowhere.

### Stage three: the app reads 4 of the 13

```ts
export interface Clip {
  stride: number
  seconds: number
  hit: number
  frames: Frame[]
}
```

The loader validates nothing:

```ts
const p = fetch(url)
  .then((r) => (r.ok ? (r.json() as Promise<ClipSet>) : {}))
  .catch(() => ({}) as ClipSet)
```

`r.json() as Promise<ClipSet>` is a bare assertion. No schema check, no
rejection of an unknown field, no error. **Nine shipped fields sit in the
browser and are never read**, which the tool's own comment states: "Nothing
below this line is read at play time."

I searched for a consumer of each. Every `frame.ball` reference in
`src/engine/` is the board's OWN ball, off `frame.ball.holderId` and
`frame.ball.pos`, which comes from the project timeline. `techniqueBall.test.ts`
reads `capturedAction(...)!.pose` and not the clip's ball. **No code in
`braven-tactics`, in the app or in its tests, reads a clip's `ball` array.**

Three consequences run through the rest of this document.

1. Question 3's answer is "nothing", and section 3 explains why that is not
   reassuring.
2. No proposal in this document is free, and the cost is in a place none of them
   would obviously touch: a tool in the OTHER repository.
3. Any change that only ADDS a field cannot break Tactics. A change to `stride`,
   `seconds`, `hit` or `frames` is the only kind that can.

---

## 1. Variants: what a ball variant is to Tactics

### What exists on the engine side

`spikes/movements/` on `cc2c20a` holds fourteen ball files over eleven drills.
Three are variants, and all three sit on one drill:

    netball_two_hand_snatch_pull_in.high.ball.json
    netball_two_hand_snatch_pull_in.low.ball.json
    netball_two_hand_snatch_pull_in.wide.ball.json

`build_library.py` mentions `variant` twenty-one times and indexes a
`(movement, variant)` pair. `export_coach_animations.py` mentions it fourteen
times. **`export_tactics_clip.py` mentions it zero times, `clip_geometry.py`
zero, and the single occurrence in `verify_tactics_clip.py` is an unrelated note
about BLAS.** The Tactics side of the boundary has no notion of a variant.

**That is a decision and not an oversight**, and
`docs/KNOWN_ISSUES.md:2460-2470` records it under the heading "The exporter is
untouched, and that is deliberate": inventing a `(movement, variant)` key would
answer Marius's question by writing code rather than by asking him. A first
version of this section called it omission rather than decision, which
contradicted that entry.

`CLASSES` in `clip_geometry.py` is keyed by movement alone. So three of the four
balls cannot reach a clip, whatever a board asks for.

### The engine's own claim, and its own limit

`docs/KNOWN_ISSUES.md` on `cc2c20a` measures all four balls of
`netball_two_hand_snatch_pull_in` against that drill's eleven checkpoints, on
`2215713`:

- **Forty-three of the forty-four readings are within band.**
- **Seven** of the eleven checkpoints move by 0.02 degrees or less. An eighth,
  the left knee at `pull_in`, moves 1.63.
- The three that move meaningfully are **all at `contact`**, which is the one
  phase where the position of the ball IS the pose.
- The balls differ by up to **0.78 arm lengths in height and 0.60 across**.

So the library concluded, correctly for its own purpose, that a variant is the
same technique, and that per-variant bands would invent a difference that is not
there.

**That conclusion does not cross this boundary, and the same file says why.**

> The `wide` ball turns the athlete **45.97 degrees** where the other three turn
> 0.0, and **nothing grades a turn**.

### Why that matters here and not there

The library grades eleven checkpoints. **Tactics consumes the whole pose**, and
the third of its fifteen channels is `twist`. A turn of 45.97 degrees is
invisible to every checkpoint. It is also one of the largest things a viewer
would see.

So the two sides disagree, and each is right about its own question:

| | grades | sees the 45.97 degree turn |
|---|---|---|
| the library | eleven checkpoints | no |
| Tactics | fifteen pose channels | yes |

**A ball variant is the same technique to the grader and a different movement to
the board.** Any answer built on "the library already decided they are the same"
rests on a measurement that did not look at the channel Tactics reads.

### What a board can select today

`DEFAULT_TECHNIQUE` in `clips.ts` keys a drill as `<class>.<sport>`, and
`techniqueFor` resolves to one named technique for each class. No field on an
event could carry a variant, and no key shape could express one. A board author
cannot ask for a high ball, and cannot avoid one either.

### The decision, framed and not taken

**Option A. A variant is the same technique.** One clip for each drill, chosen
by the existing key. The board never names a ball.

- Cost: the exporter picks one ball, and the other three stay unreachable. This
  is today's behaviour, made deliberate.
- Risk: whichever ball is chosen, its turn is baked in. If the `wide` ball were
  ever chosen, every board playing that drill would show a 45.97 degree turn
  that no coach asked for.
- It fits the shape the contract already has, which is one clip for each
  `clipId`.

**Option B. A variant is a technique a board can name.** The clip id grows a
segment, and `CLASSES` becomes keyed by `(movement, variant)`.

- Cost: `clipId` changes shape, and that is the one part of the contract Tactics
  reads by name. `CLASSES`, the exporter, the gate and `DEFAULT_TECHNIQUE` all
  change. A board author gains a vocabulary they must learn.
- Gain: the three solvable balls stop being invisible, and a board can ask for
  the pass it wants.

**Option C. A variant is a property of the EVENT, not of the technique.** The
board says where the ball arrived, and the engine picks the variant.

- This is the only option that matches how the board already thinks. A release
  already carries a kind and a target.
- Cost: the largest of the three. It needs a model change in `ActorEvent` and a
  resolution rule. Neither exists.

**The shape the contract already has favours option A.** One `clipId`, one clip,
resolved by a table. Options B and C both change the key. That is an observation
about the contract as written. It is not a recommendation, because the reason to
prefer B or C is a coaching reason rather than a structural one.

**One measurement is missing before anybody decides.** Nobody has measured what
the four balls do to the fifteen POSE channels. The 45.97 degree figure is a
turn, read from the known issue. The other fourteen channels are unmeasured
across the variants. That read needs a solve, so it is not mine, and it is not
in this document.

---

## 2. `RELEASE_KINDS`: what the board can name against what the engine can grade

`ReleaseKind` in `src/core/types.ts` on `braven-tactics` `987e2e2` has seventeen
members:

    pass  chest-pass  bounce-pass  lob  shoulder-pass  offload  kick  punt
    grubber  chip  drop-kick  shot  torpedo  throw-in  tap  roll  drop

The engine has three `pass` drills in `CLASSES` on `cc2c20a`:

| engine technique | exports as | in `ReleaseKind` |
|---|---|---|
| `netball_chest_pass` | `pass.netball.chest-pass` | **yes** |
| `netball_bounce_pass` | `pass.netball.bounce-pass` | **yes** |
| `netball_overhead_pass` | `pass.netball.overhead-pass` | **no** |

### The high pass, and a search that proved nothing

A first version of this section stated that `one-hand-high-pass` has zero
occurrences anywhere in `spikes/` or `docs/`. **That was true of the spelling I
searched and false of the technique.** The repository writes it "1 Hand High",
and under its own spelling there are **seventeen** hits.

It is not unmentioned. `docs/LOB_AUTHORING_BRIEF.md:250-256` records it as an
open authoring question, and makes it a gate:

> **So the lob is a variant of the OVERHEAD or the 1 HAND HIGH pass, and neither
> is in the library.** Authoring the lob now requires authoring its parent
> first.

So the correct statement is stronger than the one it replaces. `1 Hand High` is
a manual technique with no engine drill and no place in `ReleaseKind`, it is a
recorded open question, and **the lob is blocked behind it**. The vocabulary
reconciliation is not tidiness. It gates a technique somebody wants.

### What the vocabulary change would cost Tactics

Adding `overhead-pass` to `ReleaseKind` is a one-line type change. Two things a
first version of this section listed as costs are **not** costs, and the code
says so:

- **`actionShapeOf` needs no change.** `pose.ts:275-283` ends with
  `return 'throw'` for everything out of the hands that is not a catch, a kick
  or a shot. A new hand kind is already handled.
- **`isKick` needs no change.** `kicks.ts:174` answers it as
  `kickShape(kind, 10) !== null`, which is false for a kind it does not know.
  This is the single-definition design working as intended, and it is the reason
  the code asks `isKick` rather than keeping a second list.

**What the change does force**, none of which is in the engine's gift:

1. **`RELEASE_KINDS`** and its compile-time `Exact<>` guard,
   `contract/vocabulary.ts:164`.
2. **`THROW_WORDS: Record<ReleaseKind, string>`**, `scene/vocabulary.ts:534`,
   which is exhaustive by type and will not compile with a member missing.
   `hang.test.ts:152` reads it.
3. **The netball `throws` ring**, `sports/netball.ts:259-263`, which today lists
   only `pass`, `lob` and `bounce-pass`. A kind absent here cannot be authored
   on a netball board whatever the type says.
4. **The tool's third copy of `CLASSES`**, in `add-technique-clip.mjs`.

That last one deserves its own note: `CLASSES` now exists in three places, in
two repositories, and nothing compares them.

**Every stored project keeps working**, because the change only adds a member.
No saved board can contain the new kind.

That is a small change. **Its size is not the reason to be careful.** The
vocabulary and the manual disagree in a way this repository has already
recorded in `docs/COACH_MORNING_2026-09.md:325`: the manual teaches eight
passes, the vocabulary names four, the two overlap on `lob` and `bounce-pass`,
and `shoulder-pass` has zero occurrences in the manual. Adding one member to a list that is already out of step with the
source of truth corrects one name and leaves the disagreement in place. **The
vocabulary is a coach question before it is a typing question**, and it belongs
on the coach agenda rather than in a pull request.

---

## 3. Truncation: the bounce pass, and why "nothing happens" is the wrong comfort

### What Tactics does with `ball[]` past the last frame

**Nothing. It does nothing with `ball[]` at any frame.** Section 0 establishes
it. The `Clip` interface declares no `ball` field, the loader validates nothing,
and no code in the app or in its tests reads a clip's ball array.

So the truncation is invisible today, and it cannot produce a wrong drawing on
any board. That is a fact about the consumer, and not about the clip.

### Why the bounce pass changes the order of this question

`5d60dd2` on `cc2c20a` added `netball_bounce_pass` to `CLASSES` as
`("pass", "bounce-pass", "release")`. From
`docs/BOUNCE_PASS_INSTRUMENT_AUDIT.md` on the same commit:

- The engine **has no floor**. There is no floor term, no bounce and no
  restitution in `possession.py`, `ball_track.py` or `possession_solve.py`.
- The ball reaches the ground at **0.584 s**, 400.0 cm from her chest.

The audit then states the release at "0.80 of a 1.60 s clip", leaving 0.32 s of
flight, and the floor reached "1.84 times longer than the clip has left, short
by 0.268 s".

**Those three figures do not close against each other, and they do not match the
baseline.** I repeated them from the audit in a first version of this section
without checking them, which is the same fault the audit itself is about.

From `spikes/clip-baseline.json` at `cc2c20a`:

| quantity | audit | baseline |
|---|---|---|
| clip length | 1.60 s | 1.6000 s |
| release, as a fraction | 0.80 | **0.7920** |
| flight left in the clip | 0.32 s | **0.3328 s** |
| shortfall against 0.584 s | 0.268 s | **0.2512 s** |
| ratio, floor to flight left | 1.84 | **1.755** |

The audit's own arithmetic does not close either: 0.584 − 0.32 is 0.264 and not
0.268, and 0.584 ÷ 0.32 is 1.83 and not 1.84. Both printed figures need a flight
of about 0.317 s, which appears nowhere.

**I am not calling the audit wrong.** It may have measured on a commit before
`hit` settled at 0.7920, and I have not looked. What I can say is that the two
documents must not both be quoted, and that whoever owns the audit should
reconcile them.

**The conclusion survives on either set of numbers, which is why it is safe to
state.** The clip has 0.33 s of flight at most and the ball needs 0.584 s. It
ends with the ball in the air by any measurement.

The other two passes complete inside their clips, at frames 93 and 94 of 95.
They share the bounce pass's length and release fraction exactly, so what
separates them is the flight each ball needs and not the shape of the clip.

**A first version of this section argued that `bounce-pass` is the first
truncated clip a board can already select, because `bounce-pass` is in
`ReleaseKind` and `overhead-pass` is not. That argument is wrong, and the
resolution code was in my hand while I wrote it.**

`techniqueChosenFor` in `clips.ts:218-226` matches on a prefix:

```ts
Object.keys(clips).filter((k) => k.startsWith(`${kind}.${sport}.`))
```

`kind` is the release event's own kind, put on the blip by `blips.ts:132` as
`e.kind` and passed through `tokens.ts:595`. The clips are exported with the
CLASS in the first segment, so a bounce pass is `pass.netball.bounce-pass`.

Therefore:

- A `bounce-pass` event looks for `bounce-pass.netball.` and **finds nothing**.
- A plain `pass` event looks for `pass.netball.` and **finds both passes**.

**Membership of `ReleaseKind` by the technique segment plays no part in
resolution at all.** The first segment does the work, and it is the class.

### What is actually true, and it is worse

**No pass clip is in Tactics.** `clips.json` at `987e2e2` holds eight technique
clips, all `catch`, `block` and `land`. Zero begin with `pass.`. All three engine
passes are unspliced, so nothing resolves today by any route.

And there is a trap waiting in the splice. `DEFAULT_TECHNIQUE` has entries for
`catch.netball`, `block.netball` and `land.netball`, and **none for
`pass.netball`**. If the passes were spliced as they stand, a plain `pass` event
would find two clips, find no default, and fall to "take the first rather than
dealing at random" — which sorts `pass.netball.bounce-pass` before
`pass.netball.chest-pass`.

**Every ordinary netball pass would be drawn as a bounce pass**, and the bounce
pass is the one clip of the three whose ball data stops before the ball lands.

That is the same defect class that `6e01e82` fixed for catches, where six drills
were dealt at random and one player received three different drills in one play.
It is not fixed in general. It was fixed for the three classes that had clips.

**So the truncation fact and the proposal below both stand. The ordering
argument does not, and the finding that replaces it is that splicing the passes
without naming a default is a live trap.**

### The answer this evidence supports

**A release clip must not be required to carry the full flight, and it must
declare where its ball data stops.**

The reasons are measured rather than preferred:

1. **The engine cannot produce the full flight for a bounce pass.** It has no
   floor. A contract that demanded the flight to the catch would make one of
   three merged pass techniques unexportable. It would be a rule the supplier
   cannot satisfy.
2. **The consumer does not want it.** Tactics computes ball flight from its own
   timeline. The board already knows where the ball goes, at what time, and to
   whom. A second copy in the clip is a second source of truth for a fact the
   board owns, and section 12 of the contract already records what happens when
   the body and the ball model disagree about one ball.
3. **What the clip uniquely knows is the release**, which is the part the board
   cannot compute: where the ball sat in her hands on each frame up to the
   moment it left.

So the useful shape is the opposite of the question as posed. The clip should
carry the ball up to the release and a little past it, and say so. It should not
carry a flight it cannot finish and leave the consumer to discover the end.

**The concrete proposal**: a clip declares the frame at which its ball data stops
being meaningful. `releaseFrame` is already exported, and it already carries
exactly this information for a pass. What is missing is the contract saying that
`ball` is authoritative only as far as `releaseFrame`, and that a consumer must
not read past it.

**That proposal does not work as written, and section 0 says why.**
`releaseFrame` is one of the ten fields the allowlist in
`tools/add-technique-clip.mjs` drops. It is exported, and it does not reach
`clips.json`. So the field that would declare the boundary is already being
thrown away at the boundary.

The proposal therefore has two parts, and the second is the one that is easy to
miss:

1. State in the contract that `ball` is authoritative only as far as
   `releaseFrame`.
2. **Add `releaseFrame` to the allowlist in `tools/add-technique-clip.mjs`**, in
   `braven-tactics`. Without this, part 1 describes a field the consumer never
   receives.

Neither part costs the running app anything today, because the app reads none of
it. Together they cost whoever wires the ball up later the difference between a
documented boundary and a silent one.

**A note on how this was nearly got wrong.** The first draft of this section
proposed part 1 alone, on the belief that an exported field reaches the file.
Counting the fields on the live clip rather than in the exporter is what caught
it. The same mistake is available to every proposal below.

---

## 4. `generatedFrom`: a clip cannot be traced to the build a coach graded

### The gap

A clip carries `movementId`, `skill` and `graded`. It carries **no engine
build**, and there is no field for one. I established this on 2026-09-04 by
trying to answer "which build do the live clips come from", and finding that the
file could not answer it. The answer had to be reconstructed from a commit
message.

The reconstruction: the live `clips.json` on production is a byte match
(`sha256 2b2f528a...8da66d`) for `braven-tactics` `6e01e82`, and matches no other
version in that repository's history. The message on that commit names the
build: "Exported fresh from movement main f0172cf".

**A commit message is not provenance.** It is not on the artefact, it does not
survive a copy, and a consumer holding the file cannot read it.

### Why it matters more here than in most places

Comparability is per build. The marks a coach gives are scored against the build
she graded. If a receipt can name its build and a clip cannot, then the two
halves of one evidence chain have different traceability, and the half the coach
actually looked at is the weaker one.

### The proposal

Each clip carries a `generatedFrom` object, the way a receipt does:

```json
"generatedFrom": {
  "engineCommit": "f0172cf",
  "baseline": "spikes/clip-baseline.json",
  "movementId": "netball_two_hand_snatch_pull_in",
  "variant": null
}
```

`variant` is present and null, so that the field does not change shape if
question 1 is answered as option B or option C.

**Cost, stated correctly.** The running app costs nothing: it validates nothing,
already ignores nine shipped fields, and would ignore a tenth. But the field
must be added to the allowlist in `tools/add-technique-clip.mjs`, or it stops at
the boundary exactly as `releaseFrame` does. Refer to section 0.

So this is a two-repository change, and it is still the cheapest of the
proposals here. It is also the only one that makes a past mistake impossible to
repeat.

---

## 5. The ball anchor: the clip is anchored to a landmark it never sends

**A first version of this section called it "the defect nobody has named". That
was wrong, and the contract I wrote names it.**
`docs/TACTICS_CLIP_CONTRACT.md:376-391` gives the landmark, the unit, and the
reason:

> The offset is in arm lengths for the same reason everything else is: the
> athlete this was solved on is not the size of the body it will be drawn on.

That is a deliberate design and it is the right one. The residual is narrower,
and it survives the correction. Refer to "the residual" below.

`export_tactics_clip.py` on `cc2c20a`, at the `ball` field:

```
# One entry per frame: forward, up and lateral from the shoulder midpoint
# in arm lengths, then whether she has it. Refer to `read_ball`.
"ball": ball,
```

So the position of the ball is expressed:

- **relative to the shoulder midpoint**, and
- **in arm lengths**.

I searched the exporter for either quantity. **Zero occurrences** of arm length,
height, stature, or a shoulder-midpoint landmark, under any spelling. Neither
appears among the twenty-three exported fields, and so neither can appear among
the thirteen that ship.

The fifteen pose channels cannot supply them. They are `bob`, `lean`, `twist`,
and four limbs of `upper`, `lower` and `out`. Every one is an angle or a
normalised offset. **None is a position, a length or a landmark.**

### The residual, stated narrowly

The contract's design is right and the contract's own §8 states the rule the
design rests on: a clip travels in units that do not depend on the body it was
solved on. The ball channel obeys that rule. **One field breaks it.**

    the SIZE of the ball      ballRadiusM, absolute metres, shipped
    the POSITION of the ball  arm lengths, and the arm length is NOT shipped

So the two halves of one ball are expressed against different standards, and
only one of them travels. A consumer holding the clip knows the NAME of the unit
its ball positions are written in and does not know its VALUE.

The consequence is narrow and real. To place the ball at all, a consumer must
supply an arm length. The only one available to it is the DRAWN figure's, while
the numbers describe the SOLVED body. Where those differ, the ball is wrong by
that ratio, and nothing reports it. `ballRadiusM` is exempt because a netball
really is one size on every body, which is the contract's stated reason for it.

**This is not an argument to change the unit**, and section "What the fix costs"
says so again. It is an argument that a unit must travel with the numbers
written in it.

### What keeps it from being live today

Tactics does not read the ball channel. Refer to section 0. **The residual is
real and it is latent**, and the mechanism, rather than a prediction about it,
is this: the error is a ratio between two arm lengths, so it scales the offset
rather than displacing it. A ball placed with the wrong arm length sits near the
hands and not beside them. That is the property that makes it hard to see, and
it is a fact about the arithmetic rather than a forecast about a future day.

### What the fix costs

One field, and it can ride with `generatedFrom`:

```json
"anchor": { "landmark": "shoulderMidpoint", "armLengthM": 0.52675 }
```

The value is not an example. `docs/BALL_SPEED_PROVENANCE.md:26` records
`arm_length_cm` as **52.675 cm**, recovered from each ball file with every file
agreeing. A first version of this section printed 0.61, which was invented, and
an invented number in a proposed provenance field is the exact failure the field
exists to prevent.

The clip then carries the unit its own numbers are written in. As with every
other proposal here, the field must also be added to the allowlist in
`tools/add-technique-clip.mjs`, or it never arrives. Section 0 says the consumer
cannot break on a field that is added.

**Do not fix this by changing the ball channel to metres.** The arm-length unit
is the right one: it is what makes a clip play correctly on figures of different
sizes, which is the whole reason the pose channels are angles. The defect is
that the unit is not transmitted, and not that the unit is wrong.

---

## 6. Today's gap read, with its inputs

**Question**: how far has the solve moved since the build the live clips came
from?

**Inputs, so that the number can be reproduced:**

| input | value |
|---|---|
| exported build | `f0172cf` |
| compared against | `cc2c20a`, `braven-movement` main, 2026-09-04 |
| instrument | `spikes/clip-baseline.json` at both commits |
| script | **`spikes/clip_gap_read.py`**, added with this document |
| command | `python spikes/clip_gap_read.py f0172cf cc2c20a` |
| method | join on `(phase, measure)`, compare `engineDegrees` |
| **median convention** | **the mean of the two middle values** |
| clips compared | the 8 that `braven-tactics` consumes |
| readings compared | 198 |

**The convention line is there because a first version of this document did not
have one, and needed one.** That version used an inline script which took the
LOWER of the two middle values for the summary and the UPPER for the per-clip
rows. Both are defensible, neither was stated, and the two cannot be compared
with each other. A reviewer reproduced every other figure and could not
reproduce the medians. The script now fixes one convention, in one place, and
names it. The medians below are therefore slightly different from the ones first
published, and the worst values and counts are unchanged.

**Result:**

| measure | value |
|---|---|
| median movement | **2.57 degrees** |
| worst movement | **136.13 degrees** |
| readings over 15 degrees | **34** |

Worst and median for each clip:

| clip | worst | median | worst at |
|---|---|---|---|
| `block.netball.deflect-high` | 31.12 | 2.53 | ready / left shoulder elevation |
| `catch.netball.hooks-jump` | 17.29 | 3.19 | pull_in / right shoulder elevation |
| `catch.netball.hooks-outside-hand` | 136.13 | 4.54 | facing_away / left elbow flexion |
| `catch.netball.one-hand-snatch` | 65.60 | 1.43 | reach / left elbow flexion |
| `catch.netball.two-hand-chest` | 20.49 | 2.14 | pull_in / right shoulder elevation |
| `catch.netball.two-hand-snatch` | 21.76 | 1.80 | pull_in / right shoulder elevation |
| `catch.netball.two-hand-snatch-back` | 14.24 | 2.57 | control / right shoulder elevation |
| `land.netball.double-foot` | 21.47 | 4.38 | absorb / right shoulder elevation |

**The reading is a change in the pose and not a change in the measurement.**
Measure names are identical across both builds. Phase names are identical. Frame
counts and durations are unchanged on all eight. Root travel, which carries no
convention, changed on **six of the eight**.

**Read the history carefully, because it is not monotonic:**

All three rows are re-read with `clip_gap_read.py` under the one convention, so
they can be compared with each other:

| against | n | median | worst | over 15 |
|---|---|---|---|---|
| `ac240b2` | 198 | 1.86 | 140.13 | 37 |
| `aa3f244` | 198 | 2.57 | 136.13 | 34 |
| `cc2c20a` | 198 | 2.57 | 136.13 | 34 |

The median rose between `ac240b2` and `aa3f244`, while the worst and the count
over 15 degrees both fell. **The gap neither simply grew nor simply shrank.**
Between `aa3f244` and `cc2c20a` the eight clips did not move at all. The hash of
the baseline file changed over that span only because `bounce-pass` was added to
it, which is why the figures were read again rather than recalled.

### One artefact this instrument caught

Root travel on `hooks-outside-hand` read 0.0011 m at `f0172cf`, 0.0225 m at
`ac240b2`, and 0.0009 m at `cc2c20a`. That excursion is the clavicle artefact
appearing and then being reversed. `ac240b2` carried four zero-width-limit
parameters enabled for the solver, and PR #53 (`02b25cd`, 2026-09-02) excluded
them. I verified that `02b25cd` sits inside the measured window, that
`docs/CLAVICLE_ARTEFACT.md` is on main, and that it names all four parameters.

**Root travel knows nothing about clavicles.** It is a cheap and independent
detector for a class of solver artefact that nothing else was watching, read
from a file diff in seconds. That is worth keeping.

---

## 7. What this document does not answer

Stated here so that nobody reads silence as a finding.

- **What the four balls do to the fifteen pose channels.** Only the turn is
  known, and it comes from the known issue. That read needs a solve.
- **Whether the eight passes in the manual should replace the four in the
  vocabulary.** That is a coach question, and it is on the coach agenda. Section
  2 adds one fact to it that was not there before: the lob is a variant of the
  overhead or the 1 Hand High pass, neither is in the library, and neither is in
  `ReleaseKind`. **The reconciliation is the lob's gate**, so it is not
  housekeeping that can wait indefinitely.

- **Whether the three engine passes should be spliced into Tactics.** Section 3
  says what must happen first: `DEFAULT_TECHNIQUE` has no `pass.netball` entry,
  and splicing without one makes every ordinary pass draw the bounce pass.
- **Whether the 0.05 degree miss on the low ball is a band error or a real
  miss.** `docs/KNOWN_ISSUES.md` states that 0.05 degrees cannot separate the two
  readings, and that it must not be reported as a failure on its own.
- **Whether the eight live clips should be restaged.** That is Marius's open
  decision. Section 6 is the number it needs.
