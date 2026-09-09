# RETRACTED. The carry HAS a path, and it is in the technique file

**THE FILENAME OF THIS DOCUMENT IS WRONG AND IS KEPT ONLY SO EXISTING CITATIONS
RESOLVE.** The claim it was written to make — that the carry has no authored
path — is false. It was published on 2026-09-09 and retracted the same morning.
Everything below is the correction.

Measured against `13148a7`. The instrument is `scripts/carry_path.py`.
`spikes/movements/` is gate 4 and untouched.

## What was claimed, and what is true

| claimed on 2026-09-09 | true |
|---|---|
| the carry has no authored path | **every drill authors one**, and the four passes author four keys each |
| the ball is pinned to her | **it is not**: it travels 22.6 to 110.6 cm relative to her body |
| every centimetre before release is her own motion | **backwards**: 83 to 100 per cent of it is the authored path |
| gate 4 asks how many numbers must be CREATED | **it asks how many change.** The keys exist |

## How the error was made, in two steps

**1. I read an engine value, but the WRONG engine value.** I measured
`ball.offset_at(phase)`, found one triple held at every phase, and reported it as
the carry. **`ball.offset_at` is the BALL file's FLIGHT offset.** The carry does
not use it. `possession.carry_path` builds the carried offsets from the
**TECHNIQUE file's `afterContact`**, passed at `possession_solve.py:198` as
`after_contact=method.after_contact`.

The wrong value was constant, and a constant agreed with the claim I had been
given and was checking. **A measurement that confirms the story is the one to
re-check, not the one to publish.**

**2. I talked myself out of the correct result.** The first version of the
instrument measured the ball against the shoulder midpoint and found it moving
0.28 cm per frame relative to her body. **That was the real carry path, detected
correctly.** I reasoned that the shoulder midpoint is not the engine's frame —
which is true — and replaced a right answer obtained by an imperfect route with
a wrong answer obtained by a clean-looking one. **The reasoning about the origin
was sound and the conclusion it licensed was false.**

## A CORRECTION CAN BE THE ERROR: the trap, named

**The next person to meet this will be somebody who thinks they are being
careful, so it is named here with its conditions rather than left as an
anecdote.**

1. **a result that CONTRADICTS the expected story** — the shoulder-midpoint
   instrument said the ball moves relative to her body, against two people
   telling me the carry was static;
2. **a plausible methodological objection to that result** — the shoulder
   midpoint is genuinely not the engine's frame, and that objection was TRUE;
3. **a replacement whose answer AGREES with what you were told** —
   `ball.offset_at` returned one constant triple.

**Condition 3 is the alarm, and it is the one that reads as success.** Three
sources agreeing is not corroboration when two of them are the same claim and
the third is measuring the wrong quantity.

**A measurement that confirms the story is the one to re-check, not the one to
publish.**

**And the write-up was the proof I had stopped checking.** The retracted version
of this document contained a section praising the catch of the imperfect route.
When you correct your own method, **re-run the old instrument beside the new one
and explain the difference before discarding either.**

**The root cause is a file-level version of this repository's most common
fault.** `ball.offset_at` is the FLIGHT offset in the ball file.
`carried_offsets` is the CARRY path in the technique file. **Two authored
things, two files, one word.** Say which file a number lives in before quoting
it: **the carry and the flight are separate authorings.**

## The authored path, read from the engine

`possession.carry_path` and `possession.sample_offsets`, on the technique loaded
by `load_technique`. Nothing is rebuilt.

| drill | held frames | travel relative to her | travel in the world | the path's share |
|---|---|---|---|---|
| `chest_pass` | 76 | 22.59 cm | 27.24 cm | **83%** |
| `overhead_pass` | 76 | 72.94 | 73.25 | **100%** |
| `bounce_pass` | 76 | 41.86 | 42.31 | **99%** |
| `one_hand_high_pass` | 76 | 110.60 | 120.24 | **92%** |

**The authored path is most of the ball's travel on every drill.** On the
overhead pass it is all of it.

## Gate 4, in its real shape

**A retiming is a retune of existing numbers, which is what the orchestrator said
before I contradicted it.** The numbers are these:

| drill | keys in the file | keys the engine uses | numbers |
|---|---|---|---|
| `chest_pass` | 4 | 3 | 12 |
| `overhead_pass` | 4 | 3 | 12 |
| `bounce_pass` | 4 | 3 | 12 |
| `one_hand_high_pass` | 4 | 3 | 12 |
| **total** | 16 | **12** | **48** |

Each used key carries four numbers: `atPhase`, `across`, `up`, `ahead`.

**AND EACH FILE CARRIES A KEY THE ENGINE IGNORES.** The `held` key at phase 0.00
is never used, because `carry_path` appends only keys **after** the contact
phase, and the passes arrive at 0.02. Four keys are authored, three are read.
That is a separate small finding and it is not a defect: `carry_path`'s docstring
says the author writes where the ball goes and never where it starts.

**What a retiming would change.** The release key sits at phase 0.80 on all
four. The acceleration is in the interval between `drive` (or `step`) and
`release`. Moving it earlier means moving an `atPhase`, an offset, or both.

## What each number would inherit, and what would need a source

| number | parent today |
|---|---|
| `ahead` at the held offset, 0.5594 | traced three hops to a measured elbow-flexion sweep against `RangeLimit(0.0, 150.0, "AAOS")`. Refer to the movement-science lane |
| `up` at the held offset, 0.1221 | **no derivation anywhere.** An open row |
| the secured-ball parent, in torso lengths | `netball_two_hand_catch_chest.technique.json`, `afterContact` `pull_in` at 0.76. Its own origin is **open and unguessed** |
| every `atPhase` | **no source.** They are authored phases |
| the `across` components | zero on the chest and overhead passes; non-zero only on `bounce_pass` and `one_hand_high_pass`, which are the two that move the ball sideways |

**So a retimed path would inherit a parent for one component, inherit an open row
for a second, and need a new source for the timing itself.** A path authored
without inheriting from the first would silently break a chain that currently
holds.

## What survives from the retracted version

The trace of `contact_solve`, which was a separate question: `solve_contact` has
one caller and it is that module's own `main()`, while `elbow_poles` and
`upper_arm_aim` are called from `possession_solve.py:304` and `:308`. **A file is
not on or off the library path. Its functions are.** That stands and is
unaffected.

The easing sweep and its null are also unaffected, because they vary a line that
runs after the release and measure graded checkpoints directly.
