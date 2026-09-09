# The Tactics animation system, read from its code

Written 2026-09-09 for the character and animation lane, against `braven-tactics`
main at `6c341d2` and `braven-movement` main at `13148a7`. It answers four
questions about the far side of the clip boundary.

**Every claim names the file it comes from.** Where a statement is an inference
rather than a reading, the text says so. **Nothing in `braven-tactics` was
changed**, and neither the clip contract nor the exporter was touched.

**One thing this document deliberately does not do.** It states what the far side
would have to accept for a richer animation. It does not propose a shape for
that, because the shape is a decision Marius has not taken. Refer to section 8 of
`docs/TACTICS_CONTRACT_QUESTIONS.md`.

---

## 1. The one sentence that matters most

**Tactics does not animate a body. It animates a position on a field, and then
computes a body from it.**

`ActorState` in `src/core/types.ts` is the whole of what one player is at one
instant:

```ts
export interface ActorState {
  actorId: string
  pos: Vec2
  facing: number
  /** metres/second */
  speed: number
  gait: Gait
  hasBall: boolean
  activeEvents: ActorEvent[]
  gaze?: Gaze
}
```

There is no pose in it, no joint, and no skeleton. A frame of the timeline says
where a player is, how fast, which gait, whether she holds the ball, and what she
is in the middle of doing. **The body is derived from those facts every frame.**

A clip is one input to that derivation. It is not the animation.

---

## 2. What Tactics does with a clip today

### 2.1 The chain, file by file

| step | file | what happens |
|---|---|---|
| 1 | `src/engine/clips.ts` | `loadClips` fetches `/figures/clips.json` |
| 2 | `src/engine/clips.ts` | `capturedPose` samples a stride; `capturedAction` samples an action |
| 3 | `src/engine/tokens.ts` | both are passed into `pose({...})` beside the written inputs |
| 4 | `src/engine/pose.ts` | `pose()` composes one `Pose` |
| 5 | `src/engine/figure.ts` or `src/engine/skinned.ts` | `applyPose` or `applySkinnedPose` puts that `Pose` on a body |

The junction is `src/engine/tokens.ts`, and its own comment states the rule:

> One pose, either body. The whole point of `Pose` being a plain description of a
> moment is that it does not know what is drawing it.

### 2.2 A clip frame is fifteen numbers, and it becomes a `Pose`

`blend` in `src/engine/clips.ts` reads a frame by index:

```ts
const v = (k: number) => mix(a[k] ?? 0, b[k] ?? 0, w)
return {
  bob: v(0), lean: v(1), twist: v(2),
  leg: { left: { upper: v(3), lower: v(4), out: v(11) },
         right: { upper: v(5), lower: v(6), out: v(12) } },
  arm: { left: { upper: v(7), lower: v(8), out: v(13) },
         right: { upper: v(9), lower: v(10), out: v(14) } },
}
```

`Frame` is `number[]`, not a fixed-length tuple. **A channel a clip does not
carry reads as zero, never as an error.**

### 2.3 A capture replaces one layer, and everything else is laid over it

From `src/engine/pose.ts`:

> A capture replaces the stride and nothing else. Everything below this line —
> the carry, the action, the jump, the head — is laid on top of whichever stride
> it was.

The order of composition is fixed:

1. the stride, written or captured;
2. `withBall`, if she is carrying;
3. `withAction`, which is where an action capture enters;
4. `withCatchHands`, which solves both arms onto the ball;
5. `withAir`, for a jumper or a lifter;
6. `withGaze`, the head only;
7. `withScrum`, which overrules everything.

An action capture is used **instead of** the written action rather than mixed
with it, and one thing is taken back:

```ts
return input.gait === 'static' ? laid : { ...laid, leg: base.leg }
```

**A captured action keeps its own legs only when the player is standing still.**
While she is covering ground the legs come from the stride. The comment records
the reason: a catch captured from a standing goalkeeper stopped a receiver's legs
and she slid the last few metres into the catch.

### 2.4 The sampling clock, which is the rule a new animation must obey

From `capturedPose` in `src/engine/clips.ts`:

- **A stride is sampled by DISTANCE.** `phase = wrap(distance / strideAt(clip))`.
- **A clip that goes nowhere is sampled on the play clock**, plus a per-player
  offset from a hash of the actor id, so fourteen idle players are not one puppet
  copied out.
- **The wall clock is forbidden.**

From `capturedAction`:

- An action is lined up on its moment, not on its own beginning:
  `at = clip.hit * clip.seconds + age`.
- It is windowed by `CAPTURE_LEAD` and `CAPTURE_FOLLOW` and eased in and out by
  a weight, so it appears and leaves without a step.

The reason is stated in `tokens.ts`: a scrubbed board, a quarter-speed replay and
a recorded video must all land on the same body.

### 2.5 Which clip plays

| route | rule | file |
|---|---|---|
| gait | one clip for each gait, by name, in `FOR_GAIT` | `clips.ts` |
| idle | every key starting `idle`, dealt by a hash of the actor id | `clips.ts` |
| stock action | `FOR_ACTION`, four kinds only | `clips.ts` |
| engine technique | `<class>.<sport>.<technique>`, resolved by prefix on `<class>.<sport>.` | `clips.ts` |

**The first segment of a clip id is the CLASS, not the technique.** A default for
each class is named in `DEFAULT_TECHNIQUE`, and `techniqueSet.test.ts` fails
until a class with several techniques names one.

---

## 3. The animation system in its own terms

### 3.1 The document model

From `src/core/types.ts`:

- **`MotionKey`** is the keyframe. It carries `t`, `pos`, an optional `facing`,
  an `easing`, a `path` style, two Bezier control values `bend` and `bendAlong`,
  an optional `gait`, and an optional `hold`. **It carries no pose.**
- **`Track`** is one actor's `keys`, its optional `runs`, and its `events`.
- **`Run`** is a line a coach drew, which owns the seconds it covers, and sits
  beside the keys rather than being made of them.
- **`Timeline`** is `duration`, `fps`, the tracks, the ball events and the
  storyboards.
- **`ActorEvent`** is what a player does at a time. **`BallEvent`** is what
  happens to the ball.

### 3.2 What the system animates

A coach places a player at a time and a point, draws the line between, and marks
events on the way. The sampler turns that into `FrameState`, which is `t`, an
`ActorState` for each actor, and one `BallState`.

**So the authored animation is a path, a speed and a set of events.** The pose
layer in `src/engine/pose.ts` is a separate stage that reads those facts and
writes a body. A clip enters only at that second stage.

### 3.3 The body vocabulary

`Pose` in `src/engine/pose.ts` is the whole of it:

```
bob      rise and fall of the whole body, in metres
lean     lean at the waist, positive forward
twist    shoulders against the hips, in radians
arm      left and right, each { upper, lower, out? }
leg      left and right, each { upper, lower, out? }
head?    gaze, absent means looking where he is going
```

`LimbPose.lower` is **a bend and never a direction**: zero is straight, positive
is bent, and which way a knee or an elbow folds is applied where the pose meets
the rig. `LimbPose.out` is **positive outward on both sides**.

**The clip carries fifteen of these and not the head.** Gaze is always written,
never captured.

### 3.4 The two bodies, and the rig contract

The same `Pose` drives either:

- **A drawn figure**, `src/engine/figure.ts`, built from primitives.
- **A skinned mesh**, `src/engine/skinned.ts`, loaded from a GLB.

`figureUrlFor` in `skinned.ts` loads one of two assets:

    public/figures/athlete-m.glb
    public/figures/athlete-f.glb

`BONES` in `skinned.ts` is, in its own words, "the whole of what the app asks of
a character":

    root      pelvis
    waist spine_01    spine spine_02    chest spine_03
    neck_01   Head
    clavicle_l  clavicle_r
    armL  upperarm_l  lowerarm_l  hand_l
    armR  upperarm_r  lowerarm_r  hand_r
    legL  thigh_l     calf_l      foot_l
    legR  thigh_r     calf_r      foot_r

Four facts about that list matter to a character lane:

1. **The names are the Unreal Engine mannequin's**, chosen because most humanoid
   rigs export against them, so a later swap is a file change and not a rewrite.
2. **The trunk has to be three bones.** The file records what happened with two:
   a man asked to fold to seventy degrees folded to thirty.
3. **The pose is retargeted by DIRECTION, not by angle.** The code works out
   where each limb should point and turns the bone from its bind pose to there,
   so any bind pose is acceptable.
4. **Everything else in the asset is ignored.**

### 3.5 The hand bone exists and is never posed

`hand_l` and `hand_r` are in `BONES`. Searched across `skinned.ts`, the hand bone
is used **once**, at build time, to compute standing reach:

```ts
standingReach = s.y + s.distanceTo(fingertip(hand)) + opts.height * SHRUG
```

**It is never driven.** The hand holds its bind pose for the whole play. So the
far side already has the bone. What it does not have is a channel that carries a
value for it, or a rule for what that value means.

---

## 4. What Tactics does not use of what the clip already carries

`public/figures/clips.json` ships **thirteen** fields for each technique clip.
The `Clip` interface in `clips.ts` declares **four**. The other nine divide into
two groups, and the difference between them matters.

| field | read by |
|---|---|
| `stride` `seconds` `hit` `frames` | **the app** |
| `movementId` `skill` `graded` `inPlace` `hitPhase` | **tests only** |
| `rootTravelM` `phases` `ballRadiusM` `ball` | **nothing at all** |

**The five in the middle are not waste.** `technique.test.ts` and
`techniqueSet.test.ts` assert that a shipped clip is what it says it is: that it
is graded, that it stays in place, that its moment is the contact. They are the
reason a bad clip does not reach a board silently.

**The four at the bottom have no reader anywhere.** I searched `src/` for
`clip.phases`, `clip.ball`, `clip.ballRadiusM` and `clip.rootTravelM`, and then
checked each of the four test files that import `clips.json`. None of them
touches those fields. Every `ball` match in `src/engine/` is the board's own ball
off `frame.ball`, which comes from the project timeline.

**So a clip carries a complete per-frame ball track that nothing reads.** The
splice tool `tools/add-technique-clip.mjs` says why it is carried:

> Where the ball is on every frame, which nothing reads yet. Carried because the
> alternative is a second trip to Braven Movement the day somebody fixes the
> thing it is for.

That is a deliberate cost, taken once, against a known future need. It is not an
oversight, and it is the only one of the four with a stated reason.

---

## 5. What a richer animation would require at the boundary

Stated as requirements on the far side. **No shape is proposed here.**

### R1. It must be expressible as a `Pose`, or `Pose` must grow

Everything that reaches a body goes through `Pose`. A quality that cannot be
written as `bob`, `lean`, `twist`, four limbs of `upper`, `lower` and `out`, or a
head, cannot reach either body today. **This is the real boundary.** The clip
format is downstream of it.

### R2. A new channel must be APPENDED, never inserted

`blend` reads by index and a missing channel reads as zero. Two consequences:

- **Appending costs the far side nothing.** An old clip reads the new channel as
  zero, which is the neutral value. This migration has already happened once:
  the four `out` channels sit at indices 11 to 14, appended after the eleven
  rather than placed beside their own limbs.
- **Inserting in the middle would be silent and severe.** Every later channel
  shifts by one, the `?? 0` means nothing throws, and the board draws a wrong
  joint on every limb with no error anywhere.

### R3. Any new bone must be added to `BONES` and driven in `applySkinnedPose`

`BONES` is the whole contract with a character asset. A quality that needs a
joint the app does not drive needs an entry there, a retarget rule beside the
others, and the equivalent on the drawn figure in `figure.ts`, because **both
bodies take the same `Pose` and neither may fall behind the other**.

### R4. It must be samplable by distance or by phase, never by a clock

A stride must remain periodic in distance and an action must remain anchored to
its moment. A quality that only makes sense against elapsed time would break the
guarantee that a scrub, a replay and a recording show the same body.

### R5. It must degrade to the written pose

Every capture in this system is optional. `pose()` has a complete written answer
for every gait and every action, and a clip replaces it when one is present.
**A new quality must have a written default**, or every drill without a clip
draws a body missing something.

### R6. A per-frame quantity must survive two allowlists

A field added to the exporter does not arrive at the board. It is dropped by the
literal in `tools/add-technique-clip.mjs`, and anything inside `phases` is
dropped a second time by the map that rebuilds each entry. Refer to section 0 of
`docs/TACTICS_CONTRACT_QUESTIONS.md`.

---

## 6. What I did not verify

- **I did not run the Tactics suite**, and no claim here rests on a test result.
  Every statement is read from source at `6c341d2`.
- **I did not open either GLB.** The bone names above are what the code asks for,
  not what the shipped assets contain. **A character lane should confirm the
  assets satisfy `BONES` before treating that list as met.**
- **I did not trace `Viewport.tsx` or `SceneManager.ts` below the point where a
  `Pose` is applied.** Camera, selection and drawing are outside what was asked.
- **I did not read `src/scene/run.ts`**, which turns keys into a sampled path. I
  read the types it produces and not the sampler itself.
- **The composition order in 2.3 is read from one expression** in `pose.ts`. I
  did not test that the order is observable in a rendered frame.

## 7. Files read

    braven-tactics @ 6c341d2
      src/core/types.ts          ActorState, MotionKey, Track, Timeline, FrameState
      src/engine/clips.ts        loadClips, blend, capturedPose, capturedAction,
                                 Clip, Frame, FOR_GAIT, DEFAULT_TECHNIQUE
      src/engine/pose.ts         Pose, LimbPose, PoseInput, the composition order
      src/engine/tokens.ts       the junction, and which body is driven
      src/engine/skinned.ts      BONES, figureUrlFor, the hand bone, the retarget
      src/engine/figure.ts       applyPose, named only
      tools/add-technique-clip.mjs   the allowlist and the ball comment
      public/figures/clips.json      the thirteen shipped fields
      src/engine/technique.test.ts, techniqueSet.test.ts, techniqueBall.test.ts,
      float.test.ts                  the readers of the middle five

    braven-movement @ 13148a7
      docs/TACTICS_CONTRACT_QUESTIONS.md   sections 0 and 8
