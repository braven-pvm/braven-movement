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

- **The waist ROLL is gone. A CREASE remains, and it is not attributed.** The
  roll was `waistStandoffM` at 0.012 and it is a crease at 0.004. Refer to
  section 2.5. **Worst on `absorb.side`**, which is the view a coach reads the
  hip on. I first called `land.quarter` the worst panel and was wrong: I picked
  the view where the defect was most VISIBLE rather than the view where it most
  damaged the garment.

  **THE FIVE CANDIDATES THAT DID NOT MOVE IT ARE NAMED, so the next person does
  not spend the afternoon I spent.** The crease is present in all nine bakes,
  unchanged, under every one of these:

  1. `waistDropM` moved from −0.020 to +0.030, which put the pin on the hip.
  2. `fitToBodyFraction` raised from 0.05 to 0.20.
  3. `fitToBodyFraction` raised to 0.35, which fits nine rings instead of two.
  4. The band floor removed, so every ray's own hit decides its vertex.
  5. The whole panel rebuilt as an offset from the band's measured profile.

  `flarePower` at 1.5 is a sixth that changed the panel and not the crease.
  **A defect with its eliminated causes listed is worth more than a defect with
  a guessed one**, and none of these is the cause.
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

### 2.5 Nine bakes on one defect, and two of my own fixes are withdrawn

The thick rolled band at the top of the skirt is the towel cue Marius named.
Nine continuous bakes, one variable each, on the same drill and the same side
view. Every run wrote six panels, so the nine wrote 54. **I compared two of the
six from each run: `approach`, where she stands tallest, and `absorb`, the
deepest crouch. That is 18 of the 54, and the ranking below is a ranking of
those 18.** The six panels of the earlier quarter-view bake in section 4.2 were
looked at in full, and they are a separate set.

| run | one variable | result |
|---|---|---|
| control | `waistStandoffM` 0.012 | a rolled tube standing proud, shadow under it |
| drop | `waistDropM` +0.030 | **worse**: bigger gather, and the band fell below the bodice hem and opened a strip of bare body |
| **stand** | **`waistStandoffM` 0.004** | **the fix**: the roll becomes a crease and the panel sits under the bodice hem |
| fit20 | `fitToBodyFraction` 0.20 | no visible change |
| fit35 | `fitToBodyFraction` 0.35 | no visible change |
| hitwins | every ray's hit decides its vertex | **worse**: the band hugs, the gather below grows |
| profile | the panel built as an offset from the band's own profile | **worst of the nine** |
| final | the construction restored | reproduces `stand` exactly |
| **flare15** | **`flarePower` 1.5** | a fuller, smoother panel; the crease is untouched |

**THE TWO WITHDRAWN REBUILDS ARE THE USEFUL PART.** `waistRadiusM` reads as a
fallback and behaves as a floor, so a band whose 144 rays all hit was a circle
of 0.170 m on 139 of them. Removing that floor is the obvious fix and it made
the garment worse twice.

**A diagnostic settled it.** `report_clearance` casts the band's own rays at
five heights and decides no vertex:

| down the panel | rays that hit | mean radius | widest radius |
|---|---|---|---|
| 0.00 | 72 of 72 | 0.1384 m | 0.1704 m |
| 0.15 | 72 of 72 | 0.1411 m | 0.1808 m |
| 0.30 | 72 of 72 | 0.1374 m | 0.1836 m |
| 0.45 | 72 of 72 | 0.1151 m | 0.1963 m |
| 0.60 | 41 of 72 | 0.0339 m | 0.0780 m |

**The figure keeps widening below the pin.** A panel cut to a 0.1384 m waist
has to pass 0.1963 m at 45% down, and a sheet that cannot stretch gathers
instead. `waistRadiusM` is the clearance that lets it pass. **It was doing that
job under a fallback's name, and the name is what I trusted.**

The same table sets `flarePower`, and **that makes it the first parameter in
this file whose value comes from a measurement rather than from looking at a
render.** At 2.4 the cone is 0.1825 m at 45% down, **1.4 cm inside her thigh**,
so the collision had to push the panel out on every frame. 1.5 is the exponent
that meets 0.1963 m there.

**`report_clearance` is the deliverable from the two failures, not a
by-product.** It costs one ring of rays per height, decides no vertex, and it
would have saved both bakes had it existed first. The general form: **when a
constant and a measurement disagree, print the measurement beside the constant
before changing either.** I changed the code twice on the strength of a name.

**And a null result kept as a null result.** `fitToBodyFraction` stays at 0.05.
At 0.05 the measurement beats the clearance on 5 vertices of 1800; at 0.35 it
casts four and a half times the rays and beats it on 80, and the hem moves by at
most 2.9 mm. **The parameter moves the mesh and does not move the picture.**
That is not a proof that it is useless, so it stays at the cheap end rather than
being deleted.

### 2.6 The hem-lift test cannot run through this RENDERER, and the reason is not cloth

The reference photographs get their flare from a **flying hem**, so the test a
continuous bake exists for is whether the hem lifts on the jump and drops on the
landing. **It cannot be run through this renderer today.** Every bake prints the
same two lines:

    the pelvis moves 13.0 cm vertically, and the lower foot takes
    1 distinct height(s) over 55 frames

**The lower foot is at 0.0736 m on all 55 frames.** `pose_stance` in
`blender_movement_render.py` translates the pelvis every frame so that the lower
foot sits on a floor height read off the rig at rest, and `pose_phase` resets
the rig before each frame, so that height is the same constant every time. The
13 cm is the crouch going down and coming back up.

**`netball_double_foot_landing` has a phase named `flight`, and in every render
this repository makes, nothing in it leaves the ground.** It applies to every
drill, every still and the glTF export, not to this skirt.

**AN EARLIER VERSION OF THAT SENTENCE READ "and nothing in it leaves the
ground". THAT IS WITHDRAWN, AND IT IS A SCOPE ERROR OF THE USUAL SHAPE.** My
instrument reads the posed rig, which is the RENDER, and the render is flat by
construction. It is not evidence about the SOLVE. The rendering lane measured
the solve on the same drill and it has flight:

| phase | frame | lowest ankle | above the floor |
|---|---|---|---|
| approach | 0 | 0.0740 | 0.01 cm |
| **flight** | **54** | **0.2319** | **15.80 cm** |
| land | 89 | 0.0740 | 0.01 cm |
| absorb | 109 | 0.0739 | 0.00 cm |

**The solve carries 104 distinct heights over 110 frames and the renderer shows
one.** The four figures above are that lane's measurement and are not
re-measured here.

**The two lines they name ARE read here, because a mechanism is cheap to check
and a relayed one is a claim.** Both hold:

- `export_blender_job.py` stores the stance as
  `ankles[side] = (ankle - pelvis) / leg`, under the key
  `ankleFromPelvisInLegs`. **The ankle is relative to the pelvis and the
  pelvis's own world height is never written**, so no height survives the job
  file.
- `pose_stance` in `blender_movement_render.py` then reconstructs one:
  `floor = min(world_head(rig, f"foot_{side}").z ...)`, read off the rig after
  `pose_phase` has reset it, and the pelvis is translated to put the lower foot
  there.

**Two places, and the first one alone is enough**: a renderer cannot restore a
height that is not in its input.

So the finding is about the RENDERER and not about the engine. Whether it is a
defect or a deliberate simplification belongs to the rendering lane, whose file
it is. `pose_stance` says in its own docstring why it exists: the engine has no
floor constraint in the posing path and holds the ankle 48 to 62 degrees
plantarflexed, which drove the ball of the foot through the floor.

**One thing is unreconciled and is not mine to rule on.** The orchestrator read
the source footage for this drill frame by frame and reports no airborne phase
in it, and the rendering lane reports 15.80 cm of flight in the solve of the
same drill. Both statements reached me today from different lanes. They are
about different surfaces — the video and the solve — and I have not measured
either.

**What the hem does instead is measured.** The hem radius swings 1.5 cm and its
widest frame is `absorb`, the deepest crouch, where the thighs push the panel
out. That is the opposite of the reference, whose widest frame is airborne.

**THE TEST BECOMES RUNNABLE THE DAY THOSE TWO LINES CHANGE, AND THIS BAKE IS
WHAT WOULD SHOW IT.** Nothing in the cloth route has to change for it. Whether
to spend that day is Marius's call and not this route's.

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
| `waistRadiusM` | 0.170 | **hip clearance**, a floor under every vertex |
| `waistStandoffM` | 0.004 | how far outside the figure the band sits |
| `hemRadiusM` | 0.255 | **the flare**, which a fitted proxy cannot express |
| `lengthM` | 0.310 | waist to hem |
| `flarePower` | 1.5 | **where** the widening happens; 1 is a cone |
| `fitToBodyFraction` | 0.05 | how far down the panel is raycast, not left on the cone |
| `segments` | 72 | radial resolution |
| `rings` | 24 | vertical resolution, and the fold scale with bending |

**`fitToBodyFraction` was missing from this table** until 2026-09-10. The table
listed eight of the nine values and read as complete.

**`waistRadiusM` USED TO BE LISTED HERE AS "fallback only — used where a ray
misses". THAT IS WRONG AND THE ERROR COST TWO REBUILDS.** The panel radius is
`max(measured, cone)`, and at the top ring the cone IS `waistRadiusM`, so it is
a FLOOR under every vertex of the band and not a fallback at all. On this
athlete **144 of 144 rays hit and 139 of the results were below it**. Refer to
section 2.5.

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
