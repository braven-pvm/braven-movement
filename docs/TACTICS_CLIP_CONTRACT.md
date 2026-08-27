# The technique clip contract — Braven Movement to Braven Tactics

Written 2026-08-27.

Braven Movement solves a netball technique on a validated anatomy and grades it
against the coaches manual. Braven Tactics is the court planning application: a
coach choreographs a play, and every player on the board is drawn from the
playhead. This document is the boundary between the two products.

It is the third boundary this repository has. The first is the Blender job file
in `docs/HANDOFF_RENDERING.md`. The second is the capture path, which does not
exist yet. This one is the same shape as the first: one file per movement, and
the consuming side never needs the solver.

## 1. The finding that shaped this contract

The brief for this work said that Tactics plays no animation clips and has no
animation mixer. That was true when it was written and it is not true now.

Tactics already has a complete capture path, and it is a good one:

- `src/engine/clips.ts` loads a clip set and samples it.
- `tools/make-clips.mjs` reads a motion capture file into the application's own
  `Pose` type.
- `src/engine/pose.ts` accepts a sampled capture on two inputs, `captured` for a
  stride and `actionCapture` for a one-shot action.
- `public/figures/clips.json` ships eighteen clips today, one of which is a
  catch.

So the work is not to build a clip path. It is to put a **graded netball
technique** where a bought library clip is standing in. The clip that plays a
catch today is a goalkeeper's, from a general animation pack, and no coach
approved it.

**This changes the deliverable and it is recorded here rather than smoothed
over.** The primary rendition below is not a rigged animation file, because the
consuming application does not want one.

## 2. The two renditions

A clip crosses this boundary in one of two forms. A consumer declares which it
wants.

| Rendition | What it is | Who wants it |
|---|---|---|
| `pose` | The application's own body description, one frame at a time | Braven Tactics, today |
| `rig` | A skeletal animation on a named bone set | Blender, and anything that needs a real skeleton |

**`pose` is the default and it is what is built.** It is written by
`spikes/export_tactics_clip.py`.

**`rig` is specified here and is not built.** It is written down so that the
decision to defer it is a decision. Refer to section 9.

### Why the pose rendition is the right primary

A pose names no skeleton. It says how far each limb is swung, how far it is
carried away from the midline, how far each lower joint is bent, how far the
trunk leans, how far the shoulders are turned against the hips, and how far the
body sits off the floor. Nothing in that description knows what is drawing it.

Three things follow, and each of them matters:

- The retarget happens once, at export, and it is a measurement rather than a
  transfer. No bind pose has to be guessed at either end.
- The same clip drives a bought character and a body built from cylinders.
  Tactics draws both, and neither knows about the other.
- It is small. Fifteen numbers a frame against sixty-five quaternions.

## 3. The movement class taxonomy

A class is the name a board already uses for the thing that happens. The names
are not invented here. They are taken from `ACTOR_EVENT_TYPES` and
`RELEASE_KINDS` in `src/contract/vocabulary.ts` in Braven Tactics.

**A class that is not in that vocabulary can never be selected**, because a
board only asks for a clip when an event fires, and an event carries one of
those names.

| Class | What it covers | Netball techniques today |
|---|---|---|
| `catch` | Any ball taken into the hands: a pass gathered, a rebound claimed, an interception | Six |
| `block` | A ball touched but not taken: a deflect, a tip | One |
| `land` | Coming down, off one foot or two | One |
| `shot` | Up at the ring | None yet |
| `pass` | The ball leaving the hands. Also `chest-pass`, `shoulder-pass`, `lob`, `bounce-pass` | None yet |
| `pivot` | Turning on a planted foot | None yet |
| `jump` | Leaving the ground | None yet |

The eight drills in the library map as follows.

| Movement | Class | Technique | Moment |
|---|---|---|---|
| `netball_two_hand_snatch_pull_in` | `catch` | `two-hand-snatch` | `contact` |
| `netball_two_hand_snatch_straight_back` | `catch` | `two-hand-snatch-back` | `contact` |
| `netball_two_hand_catch_chest` | `catch` | `two-hand-chest` | `contact` |
| `netball_one_hand_snatch_to_other_hand` | `catch` | `one-hand-snatch` | `contact` |
| `netball_hooks_jump_pull_in` | `catch` | `hooks-jump` | `contact` |
| `netball_hooks_outside_hand` | `catch` | `hooks-outside-hand` | `contact` |
| `netball_deflect_high` | `block` | `deflect-high` | `contact` |
| `netball_double_foot_landing` | `land` | `double-foot` | `land` |

### The clip identifier

```
<class>.<sport>.<technique>
```

For example `catch.netball.two-hand-snatch`.

Three parts, in that order, because the consumer resolves them in that order: it
knows the class from the event, it knows the sport from the play, and the
technique is the choice that remains. A consumer with several techniques for one
class and sport picks one, and must pick the same one every time. Refer to
section 5.

A technique name must match `^[a-z][a-z0-9-]*$` and must not start with `idle`.
`idlesIn` in `engine/clips.ts` collects every clip whose key starts with `idle`
and deals them out as standing poses, so a technique named that way would be
given to a player who is doing nothing.

## 4. The clip file

One JSON file per movement, written to `spikes/poc-output/<movementId>.clip.json`.

```
schemaVersion            1
clipId                   "<class>.<sport>.<technique>"
class, sport, technique  the three parts, separately
movementId, skill        what produced it, and its coaching name
source                   the manual, the page, and what is provisional

stride                   metres of ground one loop covers. Zero for every
                         one-shot action, which is every clip today
seconds                  how long the clip runs
framesPerSecond          the rate it was solved at
hit                      where the moment is, 0 to 1
hitPhase                 which phase that moment is

ballRadiusM              absolute. A netball is a netball
ball[]                   one entry per frame. Refer to section 8

inPlace                  whether the root stays where it is
rootTravelM              how far the root goes, whether or not it stays
travelsUnderItsOwnPower  whether that travel is locomotion or noise
contactFrame             the frame the possession model says the ball is taken

phases[]                 name, at (0 to 1), frame, cues[]
frames[]                 fifteen numbers each. Refer to section 8
```

Everything past `frames` is metadata. A consumer that reads only `stride`,
`seconds`, `hit` and `frames` gets a correct animation, which is deliberate:
that is exactly the set `engine/clips.ts` reads today.

## 5. The sampling rule

**A clip is sampled by a phase derived from the playhead. Never by a running
clock.**

This is not a preference. A board is scrubbed as much as it is played, it runs
at a quarter speed and at double, and it is recorded to video. A clip advanced
by elapsed time would sprint through a slow motion replay, would put a different
body on the same second every time the playhead visited it, and would record
something to a file that nobody had watched.

So a consumer must obey all four of these.

1. **A locomotion clip is sampled against metres run**, as
   `phase = distance / stride`. A stride is periodic in distance, not in time,
   so a player who stops has legs that stop and the feet do not slide. No clip
   this repository writes is one of these today.

2. **A one-shot action clip is sampled against its own moment**, as
   `at = hit * seconds + age`, where `age` is the play time since the event was
   stamped. Negative before, positive after. The clip supplies nothing else that
   a clock could be read from.

3. **The play clock is permitted where neither applies.** A clip that covers no
   ground and is about no instant, such as a player standing and breathing, is
   played on the play clock. That is the playhead, not elapsed time, so every
   guarantee above still holds.

4. **The same frame in gives the same pose out, every time.** A consumer that
   chooses between techniques, or between variants, must choose from a pure
   function of the actor and the event, never from a random number and never
   from anything that changes between two visits to the same frame.

### The consequence a producer must respect

A consumer's window on an action is short. Tactics gives 0.9 s of wind-up and
0.5 s of follow-through, so about 1.4 s of a clip can ever be seen and the rest
is discarded from the ends. A technique whose meaning is in a longer
follow-through will lose it silently.

Measured on `catch.netball.two-hand-snatch`: the clip runs 1.633 s with the
moment at 0.87 s, so the first 0.03 s and the last 0.27 s never play. The elbow
reaches 140.5 degrees inside the window against 141.6 at the end, so nothing
coachable is lost. **This must be measured per technique and not assumed.**

## 6. Phase markers

Every clip declares the coaching phases of the movement it came from, at
normalised times from 0 to 1.

```json
"phases": [
  { "name": "ready",   "at": 0.0,   "frame": 0,  "cues": ["Power position, ..."] },
  { "name": "react",   "at": 0.296, "frame": 29, "cues": ["React to the front, ..."] },
  { "name": "contact", "at": 0.541, "frame": 53, "cues": ["Snatch the ball ..."] },
  { "name": "pull_in", "at": 0.99,  "frame": 97, "cues": ["As soon as you catch it, ..."] }
]
```

The names come from the coaching definition and therefore from the manual. They
are not a fixed set across techniques, because a deflect has a `send_on` and a
landing has an `absorb`, and flattening those into one vocabulary would throw
away the thing a coach recognises.

### Why `hit` is declared and not derived

Tactics derives the moment a clip is about from its busiest frame, measured on
the legs. That is right for a kick and it is wrong for netball.

`netball_two_hand_snatch_pull_in` is coached with the feet still — the cue is
"the feet do not move, the arms do the work" — so the busiest leg frame in that
clip is solver noise. Deriving a moment from it would line the clip up at
random, and a catch would play its follow-through before the ball arrived.

So the clip declares the moment, by naming the phase it belongs to.

The declaration is checked rather than trusted. The clip also carries
`contactFrame`, which is what the possession model independently derives, and
the exporter prints the difference. On the six catches and the block the two
agree to within 0.03 s. On the landing they differ by 0.32 s, and **that
difference is correct**: she takes the ball in flight and lands a third of a
second later. A landing lined up on the catch would put her feet down before she
had come back to earth.

## 7. Root travel, and why a clip is in place

**A clip carries no root travel into the consumer.** The consumer owns where the
player is: in Tactics that is `evaluateFrame(project, t)`, and its first
invariant is that nothing keeps a second copy of a player's position. A clip
that moved the root would be that second copy.

So the travel is measured, stripped, and declared:

- `rootTravelM` — how far the root moved over the movement, in metres.
- `inPlace` — whether that is under 0.02 m, which is solver noise.
- `travelsUnderItsOwnPower` — whether the travel is locomotion rather than a
  wobble, tested against the athlete's own stance height rather than against a
  fixed number.

Seven of the eight clips are in place to within 1 mm.
`land.netball.double-foot` travels 0.369 m, which is a real approach and is
declared. A consumer must reconcile that against its own player track, and this
contract does not say how — that is the consumer's model of movement, not this
one's.

## 8. The frame

Fifteen numbers, in this order. The order is `tools/make-clips.mjs`'s and must
not be rearranged.

| Index | Name | Meaning |
|---|---|---|
| 0 | `bob` | Rise off the lowest point of the clip, in metres |
| 1 | `lean` | Trunk from vertical. Positive is forward |
| 2 | `twist` | Shoulders against hips. Positive brings the right shoulder forward |
| 3, 4 | left leg | Thigh swing, then knee bend |
| 5, 6 | right leg | Thigh swing, then knee bend |
| 7, 8 | left arm | Upper arm swing, then elbow bend |
| 9, 10 | right arm | Upper arm swing, then elbow bend |
| 11, 12 | leg sideways | Left, then right |
| 13, 14 | arm sideways | Left, then right |

Everything is radians except `bob`, which is metres.

Four conventions decide whether a clip is right or is mirrored, and each of them
is tested in `spikes/test_export_tactics_clip.py`.

1. **A swing is zero when the limb hangs straight down, and positive
   forward.** This is the inverse of the rotation the consumer applies.

2. **A lower joint is a magnitude, never a direction.** Zero is straight and
   positive is bent, for a knee and for an elbow alike. A knee folds the heel
   backwards and an elbow brings the hand forwards, and which way is anatomy
   rather than data. Signed, it comes out negative on every frame of a run and
   clamps to nothing, which is a sprinter on straight legs.

   **And it is measured in three dimensions, while the two above it are
   measured in a plane.** That split is the whole of why the format works. The
   consumer applies `upper` and `out` as rotations about two axes, so a reading
   taken in each of those planes is exactly what it wants. It applies `lower` as
   a bend at the joint, so that one must be the true angle between the two
   segments and nothing less.

   Getting this wrong is invisible. A bend read as the difference between two
   planar swings equals the true angle only while the limb stays in the plane of
   the run, and a netballer's arms do not: a high deflect goes overhead and out,
   a hooks catch goes behind the body. Measured against the engine's own ISB
   flexion on every phase of all eight drills, the difference of swings was wrong
   by up to 52.7 degrees and the angle between the segments is wrong by 0.0. The
   clip still loaded, still played and still interpolated in both cases.

3. **Sideways is positive outward on both sides.** The side is supplied by the
   producer and the sign is not carried in the number, or one number would mean
   two things.

4. **Sideways is measured from the athlete's own neutral, not from her
   midline.** Every body has a resting splay, and the consumer's figure is built
   with its own. An absolute angle stacks the two, and every player stands in a
   straddle with her arms held out.

A limb angle also keeps counting past a half turn rather than wrapping. An arm
swung past vertical otherwise steps from +154 degrees to -103 in one frame, and
a consumer interpolating between stored frames turns ten degrees of arm into two
hundred and fifty seven degrees of windmill.

### The ball, alongside the pose

`ball[]` is one entry per frame, the same length as `frames[]`, and a consumer
that does not read it loses nothing.

| Index | Meaning |
|---|---|
| 0 | Forward from the shoulder midpoint, in arm lengths |
| 1 | Up from the shoulder midpoint, in arm lengths |
| 2 | Sideways from the shoulder midpoint, in arm lengths |
| 3 | 1 while she has it, 0 while she does not |

`ballRadiusM` is declared once for the clip, in metres, because a netball is a
netball on every body. The offset is in arm lengths for the same reason
everything else is: the athlete this was solved on is not the size of the body it
will be drawn on.

It is a separate array rather than four more channels on a frame. Inserting a
number into a positional fifteen would silently change every clip already
written, which is drift risk 2 in section 14.

Read section 12 for what it is for.

## 9. The rig rendition

Specified, not built. A consumer that needs a real skeleton receives a GLB.

**The bone set is the Unreal Engine mannequin's**, which is what Braven Tactics
names in `BONES` in `src/engine/skinned.ts`, and what the free character packs,
Mixamo's output and most commissioned work export against.

```
root
pelvis
spine_01, spine_02, spine_03
neck_01, Head
clavicle_l, clavicle_r
upperarm_l, lowerarm_l, hand_l
upperarm_r, lowerarm_r, hand_r
thigh_l, calf_l, foot_l
thigh_r, calf_r, foot_r
```

A reference skeleton is available inside
`F:\Repositories\braven-tactics\public\figures\athlete-f.glb`.

**The contract stops at the wrist.** No finger bones are named. A producer may
export them and a consumer must ignore them. Refer to section 10.

The axis conversion is the one every other boundary in this repository makes.
MHR is Y up, in centimetres, with the athlete's left at positive X and her front
at positive Z. glTF is Y up in metres. Blender is Z up in metres. Convert once,
at the boundary, and assert the athlete's left afterwards — a mirrored athlete
crosses the arms and twists the trunk, and it has happened twice in this
repository.

**Why it is deferred.** No consumer asks for it today, and an unused format
drifts. Build it when one does: the first likely caller is contact work, where
two bodies must agree on one pose and a fifteen number description of each of
them separately cannot express the bind.

## 10. What a consumer does with what it does not have

**A consumer ignores what its rig does not carry, and never fails on it.**

The named case is fingers. Braven Movement solves a grip: which fingers wrap the
ball, how far each joint bends, and where the palm faces. That is the most
carefully built part of the possession model. Braven Tactics has no finger bones
in its contract, so **none of it crosses in the pose rendition and it must not
be faked**.

The rule, in both directions:

- A **producer** may write a channel the contract does not name. It must not
  require it.
- A **consumer** meeting a bone, a channel or a metadata field it does not know
  ignores it silently. It does not warn, and it does not refuse the clip. A
  missing number reads as zero, which for every channel here is a neutral body.
- A **consumer** meeting a clip whose class it does not know does not play it.
  It falls back to whatever it drew before, which is a complete way to draw a
  player.

That last one is the reason `engine/clips.ts` returns null for a missing clip
rather than throwing. Techniques arrive one at a time and a board must keep
working while it has none of them.

## 11. What is lost, and what is kept

Written down so nobody claims otherwise later.

**Lost in the pose rendition.** The wrist, the forearm roll, every finger, the
grip on the ball, the spine as three joints rather than one lean, and the sign
of a knee or an elbow bend. A pose is a fifteen number sketch of a body and this
is what a sketch costs.

**Shoulder elevation is not carried, and this is the loss consumers meet
first.** The engine measures it the ISB way, as a three dimensional angle of the
upper arm from the trunk. A pose has no such channel: `upper` is a swing in one
plane and `out` is a departure from the midline, and the consumer applies each
as a rotation about its own axis. So the two quantities are relatives rather
than the same number, and they part company as soon as the arm leaves the plane
of the run.

Measured on `netball_two_hand_snatch_pull_in`:

| Phase | ISB elevation | The clip's `upper` | Apart by |
|---|---|---|---|
| ready | 47.4° | 45.1° | 2.3° |
| react | 47.5° | 45.3° | 2.3° |
| contact | 64.2° | 62.0° | 2.2° |
| pull_in | 41.4° | 26.9° | **14.5°** |

The pull-in is where the arm carries 25 degrees off the midline, and that is
exactly the part `upper` cannot see.

**So a coaching checkpoint on shoulder elevation cannot be re-checked from a
clip.** It was checked at export, against the solve, and the verdict travels in
the clip's own `phases[].checkpoints`. A consumer that recomputes it from
`upper` will find a movement failing a band it passed. Assert on the elbow and
the knee, which a pose carries exactly, and read the shoulder rather than
measuring it.

`verify_tactics_clip.py` reports this comparison on every run and never asserts
on it, for the same reason.

**Kept.** The shape of the movement, frame by frame, on an anatomy with joint
limits that were enforced during the solve. The coaching phases, by name, with
their cues. The moment the movement is about. The grading provenance: which
movement, which manual, which page.

**The claim this supports.** A player on a tactics board is performing a
technique that a coaching definition graded. It is not a picture of a real
athlete, and the requirement in `docs/REQUIREMENTS.md` section 4 still holds
here: a figure is an illustration of a technique, and it is not evidence about a
person.

**The claim it does not support.** Nothing about the hands. A coach who wants to
see the grip looks at a manual figure rendered in Blender, where the grip
survives.

## 12. The open finding: a carried ball has no gather

Measured on the board, on 2026-08-27, and recorded here because it decides how
much of a catching technique a coach can actually see.

**From the instant the ball arrives, the technique's arms are replaced.**
Braven Tactics puts the hands wherever the model says the ball is, at full
weight, for as long as she holds it. Its model carries a ball at one fixed point
in front of the chest — `CARRY_OFFSET` 0.42 m, `CARRY_HEIGHT` 1.05 m — and that
point never moves. So the arms stop moving with it.

| | Technique | Drawn on the board |
|---|---|---|
| Elbow at the ready position | 75 degrees | 71 degrees |
| Elbow at contact | 79 degrees | 71 degrees |
| Elbow at the pull-in | 126 degrees | 71 degrees |
| Shoulder at contact | 61 degrees | 7 degrees |

The manual's contact checkpoint asks for 50 to 140 degrees of shoulder
elevation, and the drawn body shows 7. The pull-in checkpoint asks for 105 to
150 degrees of elbow, and the drawn body shows 71 for the whole movement.

**This is not a fault in the consumer's hand solver.** That is its first
invariant working: one definition of where the ball is, and nothing keeping a
second copy. A pose that folded her arms to her chest while the model drew the
ball 42 cm in front of them would be a ball floating beside a pair of hands,
which is the defect that solver was written to end.

**The disagreement is with the ball model, and the ball model has no answer.** A
netball catch has a gather. Measured on this technique, the ball travels from
0.93 arm lengths in front of the shoulder and 0.27 above it, in to 0.45 in front
and level — about 25 cm of travel on this athlete, over three quarters of a
second. A carry point with one offset and one height cannot express any of it.

**So the clip declares where the ball is on every frame.** That is the `ball[]`
channel in section 8. It is what a consumer needs in order to move the ball
instead of pinning it, and it is written whether or not anybody reads it yet.

**What is drawn correctly meanwhile.** Everything before the ball arrives, which
is the ready position and the reach, and the trunk and the legs throughout. That
is most of what a coach reads about a stance, and it is why the technique is
worth shipping while this is open.

The finding is held as a test rather than only as this paragraph:
`src/engine/techniqueBall.test.ts` in Braven Tactics fails the day any of the
four numbers above changes.

## 13. What Braven Tactics must change to consume this

Small, and each part is separable.

1. **Select a clip by class and sport, not by class alone.** `FOR_ACTION` in
   `engine/clips.ts` maps a kind to one clip name for every sport at once, so a
   netball technique dropped in under the name `catch` would also be played by a
   rugby player taking a high ball. Resolving `<class>.<sport>.<technique>` in
   that order fixes it, and gives the variant mechanism for free.

2. **Keep the fallback.** A sport with no technique for a class keeps the clip
   it has, and a class with no clip at all keeps the written pose. Both paths
   exist already.

3. **Nothing else.** The sampling, the blending over the stride, the easing at
   both ends of the window and the determinism are all built and tested.

## 14. Drift risks

- **The class vocabulary is copied, not shared.** The two repositories do not
  share a build, so `TACTICS_VOCABULARY` in
  `spikes/test_export_tactics_clip.py` is a hand copy of Tactics'
  `vocabulary.ts`. A value added there and not here is not caught by anything.
  A published contract package would fix it and does not exist.

- **The frame layout is positional.** Fifteen numbers with no names. Insert one
  in the middle and every clip already written becomes a different body, with no
  error anywhere. `schemaVersion` is the only guard and it must be bumped.

- **The athlete is not the player.** A clip is measured on the engine's athlete
  and drawn on the consumer's character. Angles carry across bodies and
  distances do not, which is why `bob` is the only absolute number in a frame
  and why nothing else in the format has a unit.

## 15. The pre-merge gate

**Run this before merging anything that touches a clip, the exporter, or the
solve it reads.**

```bash
cd spikes && "$USERPROFILE/.pixi/bin/pixi.exe" run python export_tactics_clip.py --all && "$USERPROFILE/.pixi/bin/pixi.exe" run python verify_tactics_clip.py --against clip-baseline.json
```

It exits non-zero when any asserted channel has left its solve, so it can gate a
merge by hand or by hook.

### Why this is not a job on a runner, and what is

An independent review found the hole this closes: with the bend reverted to the
old planar reading, **every unit test in both repositories still passed**. The
contact anchor missed it by 0.064 degrees, because this drill happens to be
nearly in the plane of the run at that one instant — the same geometry that
fooled a hand check earlier the same day. Only the verifier caught it, on seven
of the eight drills, worst 49.81 degrees. And nothing ran the verifier.

So the guard is split in two, by what a runner can actually hold.

**What CI now runs.** The engine-side suite, 234 tests, on every push. It used
to run only on a machine with the pixi environment on it, and the only thing
keeping it off a runner was a handful of module-level imports of `pymomentum`,
which is conda-forge only. The geometry those tests cover is arithmetic on joint
positions and needs no solver, so it now lives in `spikes/clip_geometry.py` with
nothing but numpy behind it. That is where a second anchor at the pull-in also
sits: the planar bypass shows a 10.4 degree gap there, against a 0.5 degree
tolerance.

**What CI cannot run, and the reason is not effort.** The verifier solves each
movement to compare the clip against it, and solving needs the character —
`spikes/mhr-assets/`, 4.5 GB, gitignored, and not something to put on a runner
on every push. Standing a pixi environment up in CI is the smaller half of that
problem; the asset is the larger half and it does not go away.

**So the verifier is a named command enforced by process**, listed here and on
the merge checklist, until somebody finds a way to make a runner hold it. That
is a weaker guarantee than a green check and it is written down as one rather
than described as equivalent.

## 16. Producing a clip

```bash
cd spikes && "$USERPROFILE/.pixi/bin/pixi.exe" run python export_tactics_clip.py netball_two_hand_snatch_pull_in
```

Every movement that has a class, a ball and a possession-ready technique:

```bash
cd spikes && "$USERPROFILE/.pixi/bin/pixi.exe" run python export_tactics_clip.py --all
```

The conventions, which are the part that can silently invert:

```bash
cd spikes && "$USERPROFILE/.pixi/bin/pixi.exe" run python -m unittest test_export_tactics_clip
```
