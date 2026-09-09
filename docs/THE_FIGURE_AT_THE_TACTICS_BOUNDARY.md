# The figure at the Tactics boundary

Stage 1, item 6 of the character and animation lane, and it is deliberately
short. Written 2026-09-09 against `5d0406e`.

**The contract lane read the Tactics side and I have not read it twice.** Their
document is `docs/TACTICS_ANIMATION_FOR_CLARK.md` at `efced78` on
`lane/tactics-side-for-clark`. Everything about what Tactics animates, the body
vocabulary and the six requirements is theirs, and this file does not repeat it.

This file does the one thing their section 6 named as character-lane work, and
then reports what that work turned up.

## 1. Their reading still holds

**MEASURED.** The contract lane read `braven-tactics` at `6c341d2`. The checkout
on this machine is at `409d986`. `git diff 6c341d2 409d986 -- src/engine/skinned.ts`
is empty, so the file their rig contract comes from is byte-identical at both
commits. Their reading of `BONES` is current.

## 2. The item they could not verify, verified

Their section 6 says:

> I did not open either GLB. The bone names above are what the code asks for,
> not what the shipped assets contain. **A character lane should confirm the
> assets satisfy `BONES` before treating that list as met.**

`scripts/tactics_rig_check.py` confirms it. It reads the wanted names out of
`src/engine/skinned.ts` and the node names out of each GLB. **Neither list is
retyped into this repository**, because a copied list is a second source of
truth for a contract this repository does not own, and it would stop agreeing
with the far side without anybody noticing.

    21 bones are asked for by braven-tactics/src/engine/skinned.ts

    athlete-f.glb      69 named nodes, 21 of 21 wanted   SATISFIES
    athlete-m.glb      69 named nodes, 21 of 21 wanted   SATISFIES

**Both shipped figures satisfy the contract.** Each carries 69 named nodes
against the 21 asked for, which matches their fact 4: everything else in the
asset is ignored.

## 3. And the character THIS lane would deliver does not

**MEASURED.** The same check, run on an animated GLB exported by this
repository's own renderer:

    netball_chest_pass.glb   68 named nodes, 19 of 21 wanted
    MISSING: root, Head

**Both misses are the case of one letter, and they miss in opposite
directions.** Tactics asks for `root` and MPFB exports `Root`. Tactics asks for
`Head` and MPFB exports `head`. Nineteen other names, including every limb bone,
match exactly, because MPFB's `game_engine` rig and the Tactics contract are both
Unreal mannequin naming.

**The lookup is exact.** `skinned.ts` builds `bone[o.name] = o` and reads
`bone[BONES.head]`. A JavaScript object key is case-sensitive, so `head` is not
found by `Head`.

**The two misses do not cost the same.**

- **`root` costs nothing there today.** `BONES.root` is declared and is not read
  anywhere in `skinned.ts`. It is part of the contract and nothing consumes it.
- **`Head` costs the head.** `BONES.head` is read three times, and one of them
  is the line that turns it: `turn(rig, b[BONES.head], (p.head?.yaw ?? 0) -
  twist, ...)`. **Nothing would throw.** `turnBy` opens with
  `if (!bone || !bind) return`, so the head would simply hold its bind pose for
  the whole play, and no error would say so. A second function returns early on
  the same absence.

**This is a requirement, not a live defect.** Nothing sends the MPFB athlete to
Tactics today; Tactics ships its own two figures and both satisfy the contract.
The finding is about the MVP: **a character this lane delivers to Tactics must
carry the exact names, case included, or the head silently stops turning.**

That matters more here than it would elsewhere, because this renderer turns the
head on purpose. `orient_head_to_ball` is called in `pose_phase` and again in the
reference generator. The one joint this lane deliberately aims is the one the far
side would silently drop.

## 4. What I did not do

- **I did not change anything in `braven-tactics`.** The naming could be fixed on
  either side and the choice is not mine. The far side could match
  case-insensitively, or an exporter here could rename two bones. Both are
  changes to somebody else's file.
- **I did not check any node outside the 21.** The shipped figures carry 69
  named nodes each and the MPFB export carries 68. The contract is 21 names, and
  the far side's own statement is that everything else in the asset is ignored.
- **I did not verify that a renamed export actually drives correctly in
  Tactics.** Carrying the name is necessary and this check does not show it is
  sufficient. Bind pose, scale and axis are the far side's retarget problem and
  their fact 3 says any bind pose is acceptable, which I have not tested.
- **I did not read the Tactics animation system.** That is the contract lane's
  document and it is not repeated here.

## 5. The evidence

`tests/test_tactics_rig_check.py`, 15 tests. They build a glTF container and a
`skinned.ts` in a temporary directory rather than read the sibling checkout, so
**none of them skips** on a machine without `braven-tactics`.

Seven mutations, each killed by a named test:

| mutation | killed by |
|---|---|
| nothing is ever missing | `test_a_missing_bone_is_named` and two others |
| report only the first missing bone | `test_every_bone_missing_is_reported_and_not_just_the_first` |
| match a bone name case-insensitively | `test_a_near_miss_name_does_not_satisfy_the_contract` |
| read the KEYS of `BONES` instead of the values | `test_it_reads_the_values_and_not_the_keys` and one other |
| scan the whole source instead of the `BONES` block | `test_a_quoted_phrase_outside_the_block_is_not_a_bone` |
| accept any file as a glTF container | `test_a_file_that_is_not_a_glb_refuses` |
| accept any first chunk type | `test_a_first_chunk_that_is_not_json_refuses` |

**The case-insensitive mutation is the one that matters.** It is killed by the
test written before section 3 was measured, and section 3 is exactly the case it
describes. The guard was not written to fit the finding.

## 6. How to reproduce

    python scripts/tactics_rig_check.py --tactics <path to braven-tactics>

It reads two repositories and writes to neither.
