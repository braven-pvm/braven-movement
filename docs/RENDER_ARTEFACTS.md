# Which render artefacts exist, and which a coach in a room can use

`docs/COACH_MORNING_RUNNING_ORDER.md` recommends holding the morning date until
items 2, 4, 17 and 18 have renders. This answers whether each one exists.

**ONE OF THE FOUR EXISTS.** The recommendation is confirmed for items 2, 4 and
18, and item 17 can come off the blocking list.

Read on 2026-09-09 by `scripts/render_artefact_inventory.py`, which reads the
disk and hard-codes no answer.

| item | what it asks for | usable in a room | where | build |
|---|---|---|---|---|
| 17, corrected right hand | a render of the corrected hand at a catch | **YES** | `.assets/archives/coach-figures-2413f9d/` | `2413f9d` |
| 2, elbow width 31.3 against 37.3 | two renders side by side | **NO** | nothing at 37.3 exists | none |
| 4, the finger clip | a clip at full speed, then slowed | **NO** | 16 clips exist and none is usable | none |
| 18, the release angles | rendered candidates to choose from | **NO** | nothing, and nothing to render yet | none |

## The three rules that decide a row, and why the answer is not a file count

1. **EXISTS MEANS A PERSON IN A ROOM CAN LOOK AT IT.** A dataset a page can play
   is not a still a coach can mark. A player draws a skeleton from numbers. A
   still render is a picture of the athlete the manual prints.
2. **AN ARTEFACT MUST NAME ITS BUILD.** A coach's mark is scored against the
   build she graded, per `.remember/PRINCIPLES.md`. An unstamped render cannot be
   scored at all, however good the picture is.
3. **AN ARTEFACT MUST BE TRACEABLE TO A SOLVE.** A receipt records `jobSha256`.
   When the job no longer hashes to that, the picture is tied to no solve.

## What is archived

    coach-figures-2413f9d             11 receipts   144 stills   1 stamp   0 unstamped
    coach-figures-aa3f244             10 receipts   129 stills   1 stamp   0 unstamped
    rerender-hand-mirror-2026-09-02   16 receipts   200 stills   0 stamps  16 unstamped

Both `coach-figures` sets are clean on every receipt: none was rendered from a
dirty tree. The rerender set is entirely unstamped, and its own `PROVENANCE.md`
says so, because it predates the build stamp.

## Item 17, YES

144 stills at 1080 by 1350, three views per phase, 11 drills, 48 phases, 209 MB.
A person can look at them today and no export step stands in the way. The catch
is `netball_two_hand_catch_chest.contact.{front,quarter,side}.png`.

**THE HAND FIX IS IN THAT BUILD, CHECKED RATHER THAN ASSUMED.**
`git merge-base --is-ancestor fde5d5a 2413f9d` returns true. The fix is dated
2026-09-01 and the build 2026-09-07.

**A BEFORE SET EXISTS**, at
`.assets/archives/rerender-hand-mirror-2026-09-02/pre-fix-31aug/`, 99 stills
under the same file names, so the pair lines up by name. **It is unstamped**, so
it is context and not a graded artefact. The question "does the corrected hand
look right" needs the AFTER only, and the AFTER is stamped.

**THE PAGE IS NOT THE ARTEFACT, WHICH IS WHY THIS ROW IS YES.** The archive
stills exist independently of Erin's page, so the page hold does not reach them.

## Item 2, NO, and a defect in this lane's receipt sits under it

No render at 37.3 exists in any archive or in any worktree's `out/`. Every one
was swept for a pole variant and none was found.

**WHAT IS ON ERIN'S PAGE IS NOT A RENDER.** `index.html` embeds `const ANIM=`,
528 KB of bone data for four datasets: `chest`, `snatch`, `deflect` and
`deflectPole`. The page contains no `<img>`, no `data:image` and no base64. Those
players draw a skeleton from numbers, so they are `player(dataset)` and not
`render_pair`. The page's dominant build hash is `02b25cd`, not `2413f9d`.

**THE DEFECT. No render receipt records the parameter that produced the
picture.** The whole key set was walked and there is no pole, dial, variant or
parameter key in any of the three archives. So
`render_pair(parameter, value_a, value_b)` cannot be verified from a receipt
today, even after somebody renders the pair, because the receipt could not say
which value drew which picture. **This lane owns that and it must be fixed
before the form means anything.**

**The comparison drill is `deflect_high`**, because both hands are on the ball
and nothing else moves. On `hooks_outside_hand` the 37.3 preview moves the elbow
width by 37.91 cm, and that is the free arm relocating rather than the width
changing.

**This lane cannot start it alone.** The pole is the movement lane's dial, so the
37.3 job has to come from them.

## Item 4, NO, and the near miss is the instructive part

**No archived build carries a clip.** `animation` is null on all 11 receipts of
`2413f9d` and on all 10 of `aa3f244`.

**SIXTEEN clips exist unarchived, and the count is broken down rather than
rounded**, because an earlier draft of this page said eight in one place and
fifteen in another:

    repo-onboarding-890149/out/coach-movies    8
    repo-onboarding-890149/out/anim-batch      2
    repo-onboarding-890149/out/batch-proof     2
    repo-onboarding-890149/out/fps-check       2
    repo-onboarding-890149/out/anim-check      1
    clark-lane-setup-3d9a52/out/animate        1

The fifteen in `repo-onboarding-890149` fail three ways at once:

    generatedFrom is null        UNSTAMPED, so no build can be named
    phases is []                 nothing in them checks against a phase
    jobSha256 does not match     the job that made them was overwritten

**The third ends it.** The job files in that worktree were hashed against what
the receipts recorded, on two drills, and both differ. Those clips are tied to no
solve.

One further clip sits at `clark-lane-setup-3d9a52/out/animate/`. It is stamped,
and the stamp says `treeWasClean: false` with two uncommitted files, so checking
that commit out does not rebuild the athlete that was drawn. It is 8 frames of
`netball_chest_pass` at 5 frames a second, which is a rig test and not a coach
artefact.

**AND ITEM 4 IS THE WORST QUESTION TO ASK OF A HALF-RATE CLIP.** It is about a
change of 89.95 degrees in ONE frame. The `coach-movies` clips hold 49 frames at
30 a second from a 98-frame 60 a second source, so every other frame is gone, and
that is exactly the evidence the question needs.

## Item 18, NO, and this lane is not the blocker

Nothing exists. Erin's page contains no mention of a release angle. The source
paper `.remember/RELEASE_HAND_PAPER-f7af647.md` is not on main, checked with
`git cat-file -e`. The agenda's own item 18 states that it carries no engine
figure.

**There is nothing to render because no candidate angles have been chosen.** A
`render_pair` needs two values and item 18 has none. That is upstream of this
lane.

## What this lane takes on

The receipt gap under item 2. A render receipt must record the parameter and the
value that produced it, or `render_pair` is unverifiable.
`docs/COACH_REVIEW_SPEC_INTERFACE.md` section 4 gives this lane that form, and
the form does not work until the receipt carries the value.

## The boundary of the worktree sweep, which this claim does not exceed

**A search across worktrees is exposed to a stale corpus.** A worktree behind
main may lack renders that a current tree would have produced, so an absence
found by sweeping them is an absence in the trees AS THEY STOOD, not in the
project.

Nine worktrees were swept on 2026-09-09, at these tips, and **none of them was
fetched or updated first**:

    agent-session-communication-c733cf   e63e2ca
    amazing-chatelet-ed2e1c              d6b93fd
    clark-lane-setup-3d9a52              29fdf70
    gracious-blackburn-7375ce            0d3bc18
    mystifying-ardinghelli-401eac        12cccbe
    project-onboarding-ba6479            312eb6d
    repo-onboarding-6c4df5               aec9300
    repo-onboarding-890149               e1674c6
    zealous-tereshkova-c7f926            79fa5c8

**This does not weaken the four rows above, and the reason is worth stating.**
The ARCHIVES are the authority for every one of them, and the archives do not
live in a worktree: they are at `.assets/archives`, outside every checkout. The
sweep only ever adds candidates, and every candidate it found was refused for a
reason that does not depend on how current its tree is.

## Instrument

    scripts/render_artefact_inventory.py

It reads the archives and every worktree's `out/`, and it names a fault rather
than counting files.
