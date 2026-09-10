# The loose-garment route: Blender's own cloth simulation

Written 2026-09-10 against `braven-movement` main at `b011d39`, Blender 4.5.12
LTS. One of three route reports for Marius's comparison. This one covers the
part of a kit that must be geometry: **a loose skirt**, which cannot be painted
and is exactly the part that clips.

The instrument is `blender_cloth_skirt_probe.py`, committed beside this report.
Every number below is the value that file ships.

**The test is a LANDING.** `netball_double_foot_landing`, phases `land` and
`absorb`, three views each. That drill grades the knee, so the knee must stay
visible. A skirt that hangs correctly in a standing pose has answered nothing.

---

## Why the pipeline had never had a loose garment

MPFB garments are **proxies**. A proxy is fitted to the body by construction and
rides it. So it **can never clip, and it can never flare**. That is one fact and
not two, and it explains what both lanes found: the hand-modelled dress
converged on tight, because tight is what the format rewards.

Cloth simulation is a different mechanism entirely. A mesh, a collider, gravity.

---

## 1. Process

Somebody who has never done this can follow these steps.

### 1.1 What must exist first

1. **Blender 4.5** on the machine. Nothing is installed into it. No add-on, no
   asset, no licence.
2. **A job file for the drill**, written by the movement engine:

```bash
pixi run --frozen python -B spikes/export_blender_job.py netball_double_foot_landing
```

   It lands at `spikes/poc-output/<movement>.job.json`. **A stale job is refused
   by the renderer**, so regenerate rather than reuse.

### 1.2 The run

```bash
blender -b --python-exit-code 9 -P blender_cloth_skirt_probe.py -- --job spikes/poc-output/netball_double_foot_landing.job.json --output <directory> --phase land --phase absorb
```

### 1.3 What the script does, in order

1. **Builds the studio** by importing `Studio` from `blender_movement_render`.
   The athlete, the lighting, the cameras and the ball are the shipping ones, so
   the render is comparable with the coach pack rather than a lookalike.
2. **Poses one phase** with `pose_phase`, the same call the coach renders use.
3. **Measures the waistband.** One ray per radial segment, fired outward from
   the pelvis axis at the band height, against the posed body AND every worn
   garment. The nearest hit wins. The vertex sits `waistStandoffM` outside it.
4. **Builds the skirt** as a lathe: a fitted waist ring, a circular hem ring,
   and rings between whose radius opens as `fraction ** flarePower`. Every
   polygon is set to smooth.
5. **Pins the top two rings** into a vertex group named `pin`.
6. **Adds a `CLOTH` modifier** to the skirt and a `COLLISION` modifier to the
   body and to every garment.
7. **Settles**, by stepping the scene frame from 1 to `settleFrames`. Nothing is
   rendered until this finishes.
8. **Renders the three views** through `render_view`, the shipping function.
9. **Deletes the skirt** and repeats for the next phase.
10. **Writes a receipt** carrying both parameter blocks and the settle timings.

### 1.4 Three things the method requires, and a second skirt requires them too

- **A pin group.** A cloth object with no pinned vertices is a dropped sheet: it
  falls to the floor.
- **Built on the POSED pelvis, never the rest body.** Built at rest it begins
  interpenetrated, and a solver asked to resolve an initial interpenetration
  explodes rather than settles.
- **One skirt per pose.** A settled skirt carries the folds of the pose it
  settled on. Reusing it draws the landing's folds on the absorb.

---

## 2. Issues

### 2.1 What broke, and what each one taught

**The napkin.** The first render looked like folded paper and I nearly reported
a simulation fault. The simulation was already correct. **Flat-shaded quads give
every fold a hard facet.** One loop setting smooth normals fixed it. A picture
that looks like a physics failure can be a shading default.

**The blanket.** The first skirt passed my criteria and my criteria were wrong.
Marius: *"is that a blanket round her waist?"* **"No clipping and the knee is
visible" is satisfied by a barrel.** A 2:1 flare over 200 mm of length is a
short wide tube. The fix was a parameter that did not exist: `flarePower`, which
decides WHERE the widening happens. Below 1 it is a bell, at 1 a cone, above 1
an A-line.

**The corrugation.** Softening bending from 0.20 to 0.02 did not give drape. It
gave a ribbed lampshade. **Bending stiffness sets the SIZE of a fold, against
the ring spacing** — near-zero bending folds at the smallest scale the mesh
allows. Raising resolution without raising bending trades a stiff skirt for a
ribbed one. Twelve rings cannot fold at all; thirty-two at 0.02 corrugate;
twenty-four at 0.30 drape.

**The waist roll.** Pinned at a radius narrower than the hip, the fabric was
pushed outward and buckled into a roll. Compression stiffness resists that, and
it is not the same knob as bending. A single pinned ring is a pinned LINE, so
the band is pinned over two.

**The hoop, and it is the one worth reading.** The band still stood off the body
like a ring the skirt hung from, and **no parameter could have fixed it**. A
CIRCULAR BAND ON AN ELLIPTICAL HIP touches at the sides and gaps at the front
and back. Every setting described the ring's SIZE; the fault was its SHAPE.

### 2.2 The 0-of-72, which is this route's finding of the day

The fix for the hoop is to measure the band off the figure rather than assume a
circle. **The first measurement returned 0 hits out of 72 rays and said so.**

The cause: **MPFB DELETES THE BODY UNDER THE CLOTHES.** The human carries a mask
modifier named `Delete.female_casualsuit02`. At the hip there is no skin to hit.
Confirmed rather than assumed — a ray fired INWARD from outside the figure also
misses, so the region is genuinely gone rather than facing the wrong way.

**Casting against the garments as well is the physically right answer and not a
workaround.** A netball skirt sits over the shorts, not on skin. With the body
and every garment as candidates and nearest-hit-wins, the fit is 72 of 72.

**The hit count is printed, and a run with zero warns.** That number is the only
reason this is not a second hoop wearing a measurement's name: a band fitted
from nothing falls back to the circle and LOOKS fitted. The count was added
before it was needed.

### 2.3 What is still broken

- **The waist roll is not gone, it is smaller.** The fabric still bunches where
  the fitted band meets the flare. **Worst on `absorb.side`**, where it reads as
  a towel rolled at the waist over a skirt below — and that is the view a coach
  reads the hip on. I first called `land.quarter` the worst panel and was wrong:
  I picked the view where the defect was most VISIBLE rather than the view where
  it most damaged the garment.
- **It is longer and fuller than a netball skirt.** It falls to mid-thigh and
  reads closer to a tennis skirt. The reference sits higher and flares lower.
  That is `lengthM` and `flarePower`, not a limit of the method.
- **A real netball dress has the skirt attached flat under the bodice hem.**
  This one has a visible band of its own.
- **No colour or material.** The skirt is white default, deliberately: the paint
  lane owns colour and two lanes on one artefact is what principle 5 forbids.

---

## 3. Pros and cons

### Pros

- **Real drape and flare, which nothing else on the table has.** A fitted proxy
  cannot flare at all. This is the only route that produces a garment with a
  silhouette of its own.
- **It resolves collision by simulation.** No iteration against clipping,
  because the solver does not let the fabric through. The eight-iteration
  problem does not exist here.
- **Free, and installed.** No licence, no new tool, no export step, no format
  conversion. It runs inside the renderer that already exists.
- **Parameterised.** A second skirt is a number list, not a modelling session.

### Cons, and the first one decides against it for animation

- **18 seconds per pose, and it is PER POSE.** For stills that is free. For a 60
  fps animation it is prohibitive: a cloth simulation must settle for every pose
  it is asked about.
- **Not deterministic across a re-pose.** Two renders of the same phase agree,
  but change the pose and the folds are different folds. A drill re-rendered
  after an engine change gets a differently creased skirt.
- **The shape needed five iterations** and four of the five faults were
  invisible to geometric criteria. **The method converges, but only against an
  eye.**
- **Untested on a fast trunk rotation**, where settling from a static build shape
  may not find the pose a moving skirt would.

---

## 4. Speed

Measured on this machine, per pose, as printed by the script.

| resolution | settle | result |
|---|---|---|
| 56 x 12 | **3 s** | too coarse to fold at all |
| 72 x 32 | **27 s** | corrugated, ribbed like a lampshade |
| 72 x 24 | **10 s** | good drape, circular band |
| 72 x 24 + raycast band | **18 s** | good drape, fitted band — **shipped** |

**Resolution buys folds and costs seconds, and the useful setting was not the
highest one.** The raycast band roughly doubles the cost and is worth it.

**The number that decides scaling is that all of these are PER POSE.** Two
phases of one drill cost 36 seconds. A second drill costs the same again. A 60
fps second of animation would cost about eighteen minutes.

---

## 5. Ease of use

### What is script and what is judgment

**Script:** everything in section 1. The build, the fit, the pinning, the cloth,
the settle, the render, the receipt. A second skirt needs no Blender GUI at all
and no mesh editing.

**Judgment:** the values. Nothing in the file knows what a netball skirt looks
like, and four of the five faults above were caught by eye rather than by a
check. **Somebody who is not me can make skirt two from these files**, and they
will need to look at the render and decide whether it is the garment.

**The honest limit:** this route replaces modelling with parameter choice. That
is a large saving and it is not zero work.

### The parameter list, with the values shipped

**The shape.** A hockey skirt is the first five of these changed.

| name | value | what it decides |
|---|---|---|
| `waistDropM` | −0.020 | band height; negative tucks it under the bodice |
| `waistRadiusM` | 0.170 | **fallback only** — used where a ray misses |
| `waistStandoffM` | 0.012 | how far outside the figure the band sits |
| `hemRadiusM` | 0.255 | **the flare**, which a fitted proxy cannot express |
| `lengthM` | 0.310 | waist to hem |
| `flarePower` | 2.4 | **where** the widening happens; 1 is a cone |
| `segments` | 72 | radial resolution |
| `rings` | 24 | vertical resolution, and the fold scale with bending |

**The cloth**, all Blender's own settings.

| name | value | note |
|---|---|---|
| `quality` | 10 | |
| `massKg` | 0.45 | heavier hangs; light plus stiff stands off |
| `tensionStiffness` | 8.0 | |
| `compressionStiffness` | 15.0 | resists the waist buckle |
| `shearStiffness` | 2.0 | |
| `bendingStiffness` | 0.30 | **the fold size**, against `rings` |
| `airDamping` | 1.0 | |
| `collisionDistanceM` | 0.004 | thicker reads as felt |
| `collisionQuality` | 5 | |
| `selfCollision` | True | |
| `selfDistanceM` | 0.006 | |
| `settleFrames` | 45 | the per-pose cost |

---

## 6. What I did not do

- **I did not paint anything.** The bodice, bib, letters and shorts belong to
  the parallel lane.
- **I did not price a commercial tool.** The hard stop was Blender first, and
  Blender produced a skirt.
- **I did not put the render beside a reference photograph.** There is no netball
  kit reference in this repository. That comparison is the criterion that would
  have caught the blanket, and it is still owed.
- **I did not test another drill or another sport.** The claim is about this
  landing.
- **I did not message the character lane**, as instructed.
