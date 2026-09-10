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

Two poses, settled one at a time. This is the stills route.

```bash
blender -b --python-exit-code 9 -P blender_cloth_skirt_probe.py -- --job spikes/poc-output/netball_double_foot_landing.job.json --output <directory> --phase land --phase absorb
```

One bake over the whole drill, with the body moving under the skirt. The job
must carry frames, so export it with `--every=N` first.

```bash
blender -b --python-exit-code 9 -P blender_cloth_skirt_probe.py -- --job spikes/poc-output/netball_double_foot_landing.job.json --output <directory> --animate --view side
```

**One value per run, and `--skirt KEY=VALUE` puts it in the command line and in
the receipt.** Editing six values between two renders produced a worse skirt
that could not be attributed to any of them, and three one-variable runs then
answered the same question in an afternoon.

```bash
blender -b --python-exit-code 9 -P blender_cloth_skirt_probe.py -- --job spikes/poc-output/netball_double_foot_landing.job.json --output <directory> --animate --no-movie --skirt waistDropM=0.030
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

### 1.5 What the animate mode does differently, and why each difference exists

1. **Poses and keys every frame of the job**, then holds the first pose for a
   pre-roll. The skirt falls onto a body that is not moving, and only then does
   the movement play. **Every later pose is reached with momentum**, which is
   the one thing a per-pose settle cannot produce, because a settle is the
   definition of no motion.
2. **Carries the waistband on the pelvis with an ARMATURE modifier**, added
   BEFORE the cloth one. Refer to section 4.3: a pin holds a vertex to the
   modifier stack's input, not to the body.
3. **Bakes once**, over the whole scene range, and times every frame separately
   from every render.
4. **Measures the hem on every frame**: its radius, its height below the pelvis,
   the pelvis's own travel and the lower foot's height. **The question a bake
   exists to answer is whether the hem lifts on the jump, and my eye has been
   wrong about this garment twice.**
5. **Refuses the clip** if the point cache does not answer a jump backwards.

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

### 2.3 Against the reference, and the knob that would move each difference

**There is no reference photograph in this repository and there will not be
one.** The images are third-party and for internal review only. So the
comparison is made against the kit described in words, which names the knob and
is more useful than a picture would have been.

**The reference, a one-piece SPAR Proteas netball dress:** a fitted sleeveless
bodice with racer shoulders; a SHORT A-line skirt sitting at upper to mid thigh,
well above the knee, fitted at the hip and flaring only in its lower half,
attached FLAT under the bodice hem with no separate waistband visible; a clean
hem with slight movement, neither full nor gathered.

**The three differences a coach would name, worst last:**

| | this skirt | the reference | the knob |
|---|---|---|---|
| **length** | mid-thigh, approaching the knee | stops higher | `lengthM`, now 0.310 |
| **fullness** | flares earlier and wider | flares less and later | `flarePower`, now 2.4, wants MORE; and `hemRadiusM`, now 0.255 |
| **the waist** | a visible rolled band of its own | the skirt meets the bodice flat, no band at all | **not a parameter** |

**The waistband is the largest difference and it is the one that is not a
number.** `waistDropM` tucks the band higher, but the reference has no band to
tuck: its skirt is attached under the bodice hem. That is a construction change
— pinning the top ring to the bodice rather than building a band of its own —
and it is the next thing this route should do.

**The other two are one line each.** That is the whole argument for the
parameter list: two of the three named faults are a number, and the person
changing them does not have to be the person who wrote the file.

### 2.4 What is still broken

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
- **CORRECTED. This bullet used to read "No colour or material. The skirt is
  white default, deliberately".** It was true when it was written and it stopped
  being true one commit later, at `b878f27`. The skirt now wears the same fabric
  material as the bodice, through `make_fabric_material`, so the two routes are
  compared on SHAPE and not on shading. **Giving it that material was the single
  largest improvement of the day, larger than any shape change**, and the
  paragraph that listed the omission as deliberate was quietly carrying the
  biggest cue in the complaint that started this work. Colour is still the paint
  lane's and is not set here.

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

### Cons

**THE FIRST CON IS WITHDRAWN. It said this, and it was wrong by a factor of
about 57:**

> **18 seconds per pose, and it is PER POSE.** For stills that is free. For a 60
> fps animation it is prohibitive: a cloth simulation must settle for every pose
> it is asked about.

**The error was not in the measurement, it was in the method I priced.** I
measured a settle from a fresh lathe onto a static pose, which is the cost of
ONE STILL, and then multiplied it by a frame count. That is not how an animation
is made. The natural method is ONE CONTINUOUS BAKE over the drill's frames with
the body moving under the skirt, and it was never measured until the orchestrator
asked for it. Refer to section 4.2 for the numbers. **The whole 55-frame clip
costs less cloth time than one still did**, because a still pays for its own
settle and a clip spends one pre-roll on every frame it renders.

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

### 4.1 Per pose, which is the cost of a still

Measured on this machine, per pose, as printed by the script.

| resolution | settle | result |
|---|---|---|
| 56 x 12 | **3 s** | too coarse to fold at all |
| 72 x 32 | **27 s** | corrugated, ribbed like a lampshade |
| 72 x 24 | **10 s** | good drape, circular band |
| 72 x 24 + raycast band | **18 s** | good drape, fitted band — **shipped** |

**Resolution buys folds and costs seconds, and the useful setting was not the
highest one.** The raycast band roughly doubles the cost and is worth it.

**These are all PER POSE, and that is a still's price, not an animation's.** The
sentence that used to close this section said a 60 fps second of animation
"would cost about eighteen minutes". It multiplied a still's price by a frame
count, and section 4.2 is what it should have measured.

### 4.2 One continuous bake, which is the cost of a clip

`netball_double_foot_landing`, 55 frames at 30 fps, one cloth simulation over
all of them with the body moving underneath, behind a 30-frame pre-roll. The
same shape and the same cloth settings as the shipped stills.

| what | seconds |
|---|---|
| the whole bake, 84 scene frames | **23.3** |
| the pre-roll, 29 frames | 6.0 |
| **the drill itself, 55 frames** | **17.3** |
| **per frame of the drill** | **0.314** (worst 0.335) |
| the rig alone, no skirt, same frames | 0.010 per frame |
| the six sheet renders, excluded from every figure above | 196.9 |

**ONE STILL COSTS 18 SECONDS. THE WHOLE CLIP'S CLOTH COSTS 17.3.** A still pays
for a 45-frame settle that serves one frame. A clip pays for one pre-roll and
then spends 0.314 s on each frame it keeps.

**Priced the way section 3 priced it, one second of animation costs 9.4 s of
cloth at 30 fps and about 19 s at 60 fps. The withdrawn con said eighteen
minutes.**

**The rig control matters more than it looks.** Stepping this armature and its
meshes with no skirt costs 0.010 s a frame, so the cloth is 0.30 of the 0.314
and the figure is a cloth cost, not a scene cost.

### 4.3 Two guards, because both failures produce a plausible picture

**A pinned vertex is pinned to the modifier stack's INPUT, not to the body.** In
a still the waistband holds because nothing moves. In an animation the skirt
stays where it was built while the athlete leaves it. The fix is an ARMATURE
modifier before the cloth one, with every vertex weighted to the pelvis, and the
mesh has to be UN-POSED first or the pose is applied twice. **A wrong transform
leaves a skirt somewhere near a hip, on a figure, and no measurement in the
script would refuse it**, so the run prints the largest distance between a
vertex as built and the same vertex after the armature runs. It is 0.0000 mm.

**The movie renders the frame range a second time, from the start.** If the
point cache does not answer a jump backwards, the solver restarts from wherever
it is and **the clip is of a different simulation from the sheet**. One frame's
vertices are read during the bake and read again after a jump backwards. The
drift is 0.0000 mm, and the clip is refused if it is not.

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
- **I did not put the render beside a reference photograph**, because there is
  none in this repository and there will not be: the images are third-party and
  internal only. The comparison is made against the kit described in words in
  section 2.3 instead, which names the parameter behind each difference. **That
  is the criterion that would have caught the blanket**, and it is now run.
- **I did not test another drill or another sport.** The claim is about this
  landing.
- **I did not message the character lane**, as instructed.
