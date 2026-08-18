# The possession model

## The defect this fixes

Today a movement is a path for the hands. The ball is placed afterwards, at the
midpoint of the wrists, so it follows the athlete and can never be the reason she
moves. The ball intersects the wrists rather than sitting in the palms, because
the two were never related to each other.

The manual says the opposite, in every snatch drill on page 71:

> The passer can pass the ball **anywhere in workers arm span**.

The ball position is the variable. The athlete adapts. The engine encodes the
reverse.

## The principle

**A movement is a ball trajectory and a technique. The hands are solved, not
authored.**

One rule carries the whole model:

> Possession transfers at contact. Before contact the ball drives the athlete.
> After contact the athlete drives the ball.

Everything below follows from that sentence.

## Schema

A drill is three files. Two are new. The third already exists and does not
change.

### `<id>.ball.json` — where the ball goes, and when

Positions are in the athlete's own frame, in arm lengths, so a trajectory
authored on one body retargets to another. `across` is positive to the athlete's
left, matching MHR.

```json
{
  "movementId": "netball_two_hand_snatch_pull_in",
  "radiusFraction": 0.21,
  "arrival": { "atPhase": 0.55 },
  "keys": [
    { "atPhase": 0.0,  "across": 0.10, "up": 0.55, "ahead": 2.40 },
    { "atPhase": 0.55, "across": 0.10, "up": 0.42, "ahead": 0.88 }
  ]
}
```

Only the incoming flight is authored. After `arrival` the ball has no keys,
because the athlete carries it.

`radiusFraction` is the ball radius as a fraction of arm length, so a size 4 and
a size 5 are different drills without new geometry. A size 5 netball on a 53 cm
arm is about 0.21.

### `<id>.technique.json` — how she meets it

```json
{
  "movementId": "netball_two_hand_snatch_pull_in",
  "hands": "both",
  "grip": { "spreadDegrees": 62, "faceBall": true },
  "afterContact": [
    { "atPhase": 0.78, "across": 0.24, "up": 0.30, "ahead": 0.52 },
    { "atPhase": 1.0,  "across": 0.20, "up": 0.04, "ahead": 0.26 }
  ],
  "stance": { "hipDropFraction": 0.18, "turnDegrees": 0 }
}
```

`hands` is `both`, `left`, or `right`. A one-hand drill names which, and when the
second hand joins.

`spreadDegrees` is the angle between the two palms around the ball. It is the
only grip number a coach needs, and it is what makes ball size matter.

`afterContact` keys move **the ball**, not the hands. The pull-in becomes "bring
the ball to the chest", which is what the manual says, and the hands follow
because they are holding it.

### `<id>.json` — the coaching definition

Unchanged. Phases, checkpoints, bands, cues.

## Constraints

Three regimes, switched by the arrival phase.

### Before contact — the athlete reads the ball

- Hands are **not** targeted. A `ready` posture holds them in the athlete's span.
- The athlete may turn toward the ball. Trunk turn becomes derived, not authored:
  turn far enough that the ball is inside the reachable span, and no further.
- This is where "react to the front, in front of the shoulder" is measured, and
  it becomes a real assessment rather than a number I typed.

### At contact — hands on the ball

For each participating hand, replacing the wrist position target:

- **Palm centre on the ball surface**, at `radius` from the ball centre.
- **Palm normal pointing at the ball centre.** This is where "fingers up, thumbs
  in the middle" comes from, instead of the synthetic knuckle constraint added
  in `4d1b6fd`.
- Two hands sit `spreadDegrees` apart around the ball, symmetric about the
  approach direction.

The contact frame is not authored either. It is the first frame where the ball is
inside the athlete's reach. If she cannot reach it, the drill fails, and that is
a true result rather than a solver artefact.

### After contact — the athlete drives the ball

- Ball centre is targeted by `afterContact` keys.
- Hands stay on the ball surface under the same contact constraints.
- Release, where a drill has one, is the frame the hand constraints stop.

## What survives

The whole stack below the hands is unaffected, and none of it should be touched:

- phases, stance, hip drop, trunk turn, foot placement, root travel
- the frame-free measurement layer, validated against OpenSim
- joint limits at weight 200, and `check_joint_limits.py`
- scapular rhythm
- the coaching definitions, bands, cues, receipts and the noise rule
- the viewers, the library runner, all 85 tests

## What is replaced

- `across` / `up` / `ahead` hand keys in `*.motion.json`
- the derived ball in `export_viewer_data.py` and `export_mesh_viewer.py`
- the knuckle-direction constraint in `movement_engine.py`
- the hard-coded `contact_phase()` reading of a key named `contact`

## Milestones

Each one ends in something runnable and measurable. Do not start the next until
the current one is honest.

### 1. Ball trajectory and reach test

Load a `.ball.json`, place the ball per frame, and report for every frame whether
it lies inside the athlete's reachable span. No solving yet.

**Done when** the two-hand snatch reports the ball unreachable early in the
flight and reachable from its arrival phase onward.

### 2. Contact constraints

Palms on the surface, normals at the centre, two hands `spreadDegrees` apart.
Solve a single frame at the arrival phase.

**Done when** both palms sit within 1 cm of the ball surface, the ball does not
intersect the wrists, and joint limits stay clean.

### 3. Possession transfer

Run the full movement. Ball driven by its own keys before contact, by
`afterContact` keys after.

**Done when** the two-hand snatch runs end to end, the ball never jumps at the
handover frame, and per-frame joint jumps are no worse than today.

### 4. The proof: the same technique, three arrival points

Author **one** technique file and **three** ball files, placing the ball high,
central and wide within the arm span. Solve all three.

**Done when** all three produce a plausible catch with no new hand authoring.
This is the milestone that proves or kills the model. If the athlete cannot adapt
to a ball placed differently, the inversion has bought nothing.

### 5. Migrate the library

Convert the remaining seven drills. Retune the coaching bands against honest
anatomy, which is owed anyway after the scapular change.

**Done when** `build_library.py` is green and `check_joint_limits.py` passes.

## Open questions, to answer with evidence rather than opinion

1. **Does the athlete turn to the ball, or is turn authored?** Deriving it is
   more correct and matches the hooks drill, where the manual has her facing away
   until the ball arrives. Deriving it may also make the turn unstable. Milestone
   4 will show which.
2. **What happens when the ball is out of reach?** A failed catch is a real
   coaching outcome and the engine should be able to represent it, rather than
   stretching to reach.
3. **Do the fingers need to move?** All 104 finger parameters are frozen. Palms
   on a sphere may be enough for a POC, but "fingers up, thumbs in the middle" is
   a finger statement and the grip is where it will show.
4. **One ball or many?** Deflect drills have two workers and the ball leaves.
   Nothing in this design forbids a second trajectory after release, and nothing
   in it requires one yet.

## Why now

The eight movement files need retuning regardless, because the scapular rhythm
change in `a215a87` moved every measured angle. Rewriting keys that are about to
be rewritten anyway is the cheapest this change will ever be.
