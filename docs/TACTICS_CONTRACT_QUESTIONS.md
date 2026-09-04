# Five questions on the clip contract, answered where the evidence answers them

Written 2026-09-04 against `braven-movement` main at `cc2c20a` and
`braven-tactics` main at `987e2e2`. Every number below names the file and the
commit it was read from. Nothing here changes code, and nothing was written into
`braven-tactics`.

Two of the five questions turn out to have measured answers already in the
repository. Two are decisions for Marius, and this document frames them without
deciding them. One is a defect that nobody has named yet.

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

**Ten exported fields are dropped here and never reach the file:**

    schemaVersion  class  sport  technique  source
    travelsUnderItsOwnPower  framesPerSecond  contactFrame  releaseFrame
    clipId (kept, but as the object key rather than as a field)

I confirmed this against the live file rather than against the tool. The clip
`catch.netball.two-hand-snatch` on production has exactly thirteen keys.

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
about BLAS.** The Tactics side of the boundary has no notion of a variant, by
omission rather than by decision.

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

`one-hand-high-pass` has **zero occurrences anywhere in `spikes/` or `docs/`** on
`cc2c20a`. It is absent from the engine as well as from the vocabulary, so it is
not a mismatch between the two. It is a manual technique that nobody has
authored.

### What the vocabulary change would cost Tactics

Adding `overhead-pass` to `ReleaseKind` is a one-line type change. The cost sits
entirely in what must move with it:

1. **`actionShapeOf` must map it.** Every release kind resolves to a shape, and
   an unmapped kind reaches the pose with no shape.
2. **`isKick` must answer for it.** The code asks `isKick` rather than keeping a
   second list, and `docs/animation-demand.md` records what happened when two
   lists disagreed: a netball goal shoot came out as a drop kick at the ring.
3. **Every stored project keeps working**, because the change only adds a
   member. No saved board can contain the new kind.
4. **The board author gains a name with a real capture behind it**, which is the
   point of the change.

That is a small change. **Its size is not the reason to be careful.** The
vocabulary and the manual disagree in a way this repository has already
recorded: the manual teaches eight passes, the vocabulary names four, the two
overlap on `lob` and `bounce-pass`, and `shoulder-pass` has zero occurrences in
the manual. Adding one member to a list that is already out of step with the
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
- The release sits at **0.80 of a 1.60 s clip**, which leaves **0.32 s of
  flight**.
- The floor is reached **1.84 times later than the clip has left, short by
  0.268 s**.

The other two passes complete inside their clips, at frames 93 and 94 of 95.

**`bounce-pass` is the first truncated clip whose class name a board can already
select.** `overhead-pass` is truncated in theory only, because no board can ask
for it. That difference is the whole finding. Until now, truncation was a
property of clips nobody could reach.

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

This is the defect nobody has named on this side of the boundary.

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

### The inconsistency, stated plainly

    the SIZE of the ball      ballRadiusM, absolute metres
    the POSITION of the ball  arm lengths from a landmark the clip does not send

A consumer can draw the ball at the right size and cannot place it, unless it
assumes an arm length and a shoulder midpoint of its own. Any such assumption
describes the DRAWN figure, while the numbers describe the SOLVED body. Where
the two differ, the ball is wrong by that difference, and nothing reports it.

### Why this is familiar

This is the same shape as the defect in the Blender job, which anchored the ball
to a shoulder midpoint it never transmitted. The parallel is not a coincidence.
Somebody who has the body in hand does not notice that the recipient will not.

### What keeps it from being live today

Tactics does not read the ball channel. Refer to section 0. **The defect is
real, it is latent, and it would surface on the first day anybody used the
channel.** That is also the day it would be hardest to diagnose, because the ball
would be nearly right.

### What the fix costs

One field, and it can ride with `generatedFrom`:

```json
"anchor": { "landmark": "shoulderMidpoint", "armLengthM": 0.61 }
```

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
| method | join on `(phase, measure)`, compare `engineDegrees` |
| clips compared | the 8 that `braven-tactics` consumes |
| readings compared | 198 |

**Result:**

| measure | value |
|---|---|
| median movement | **2.52 degrees** |
| worst movement | **136.13 degrees** |
| readings over 15 degrees | **34** |

Worst and median for each clip:

| clip | worst | median | worst at |
|---|---|---|---|
| `block.netball.deflect-high` | 31.12 | 2.63 | ready / left shoulder elevation |
| `catch.netball.hooks-jump` | 17.29 | 3.57 | pull_in / right shoulder elevation |
| `catch.netball.hooks-outside-hand` | 136.13 | 4.81 | facing_away / left elbow flexion |
| `catch.netball.one-hand-snatch` | 65.60 | 1.47 | reach / left elbow flexion |
| `catch.netball.two-hand-chest` | 20.49 | 2.32 | pull_in / right shoulder elevation |
| `catch.netball.two-hand-snatch` | 21.76 | 1.85 | pull_in / right shoulder elevation |
| `catch.netball.two-hand-snatch-back` | 14.24 | 2.62 | control / right shoulder elevation |
| `land.netball.double-foot` | 21.47 | 4.45 | absorb / right shoulder elevation |

**The reading is a change in the pose and not a change in the measurement.**
Measure names are identical across both builds. Phase names are identical. Frame
counts and durations are unchanged on all eight. Root travel, which carries no
convention, changed on **six of the eight**.

**Read the history carefully, because it is not monotonic:**

| against | n | median | worst | over 15 |
|---|---|---|---|---|
| `ac240b2` | 198 | 1.84 | 140.13 | 37 |
| `aa3f244` | 198 | 2.52 | 136.13 | 34 |
| `cc2c20a` | 198 | 2.52 | 136.13 | 34 |

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
  vocabulary.** That is a coach question, and it is on the coach agenda.
- **Whether the 0.05 degree miss on the low ball is a band error or a real
  miss.** `docs/KNOWN_ISSUES.md` states that 0.05 degrees cannot separate the two
  readings, and that it must not be reported as a failure on its own.
- **Whether the eight live clips should be restaged.** That is Marius's open
  decision. Section 6 is the number it needs.
