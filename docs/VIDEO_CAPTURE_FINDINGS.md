# What the proper shoot must do differently

Findings from session 1.0, the four-clip feasibility sample. Written for
planning the real shoot.

## The answer

**Can we get from phone video what the engine needs?**

Not yet from footage like this — but the reason is specific, cheap to fix, and
none of it is about the phones.

The pipeline runs end to end. Two camera views became **3,439 tracked frames
out of 3,665** in about 160 seconds, lifted into 3D, and turned into a joint
angle against time. **It recovers the right movement.** Laid beside the engine's own
curve for the nearest drill, one catch cycle of left elbow flexion reads:

| | before the catch | at the catch | pulling in |
|---|---|---|---|
| measured from the video | 60 to 75° | 58° | 122 to 131° |
| the engine's snatch pull-in | 89° | 80° | 113 to 145° |

Both dip as she reaches to meet the ball, then fold sharply to bring it in.

The video row reads one catch cycle from `elbow-curve-0.1.json`: the catch is at
9.13 s, the pull-in window is 9.2 to 9.6 s, and 131° is the raw peak at 9.37 s
across all 13 frames in that window. An earlier draft said "122 to 126" from a
printout sampling every third frame, which understated the peak by 5 degrees.

**The shape is right. The numbers are not.** Two independent readings of that
same elbow, from the same footage, disagree by a median of 21 degrees. Nothing
in the analysis fixes that, because the information needed is not in the
footage.

**The difference between a shape and a number is a calibration reference in
frame.** That, and a clap. Both cost nothing and neither was present.

## What to change, in order of consequence

### 1. A clap — audible AND visible in both frames

There is no clap in this material. In both views the athlete stands and talks
for the first eight seconds, hands at her sides. The first shared event of any
kind is her first ball catch.

Four audio methods were tried. All four failed, and the confidence measure is
what says so:

| method | set 0.1 | set 0.2 |
|---|---|---|
| raw waveform | −78.6 ms, p/s 1.08 | +633.7 ms, p/s 1.12 |
| energy envelope | −249.0 ms, p/s 1.08 | +184.0 ms, p/s 1.01 |
| spectral flux, first 12 s | −245.3 ms, p/s 1.35 | +3616.0 ms, p/s 1.27 |
| spectral flux, whole clip | +17962.7 ms, p/s 1.02 | +4325.3 ms, p/s 1.28 |

Peak-to-sidelobe near 1.0 means the best match is no better than the next best:
there is no peak, so the milliseconds beside it are not a measurement. Four
readings, four different answers.

Matching catches by eye instead gives an offset good to about **±150 ms**, which
is four to five frames.

**Instruction: after both cameras are rolling and before anyone speaks, clap
once, sharply, where both cameras can see the hands.** On any take longer than
about a minute, clap at **both ends** — the two phone clocks differ by 0.04
percent, which is 11 ms over 28 seconds and 120 ms over five minutes. Two
anchors measure the rate as well as the offset; one anchor cannot.

**And between the clap and the first repetition, nobody speaks.** The clap
makes the talking harmless, so this is insurance rather than a second rule: if
the clap is missed in one view, the fallback is correlation, and correlation is
what speech defeats. It costs a sentence of silence.

### 2. A calibration reference in frame

Two independent readings of the same elbow disagree by a median of 21 degrees
(90th 63°). Four explanations were raised and all four were refuted — the table
is further down, under the elbow angle.

**So the case for a calibration reference is not that it fixes a known cause.**
Nothing tested explains that 21 degrees. The case is that without a known
object in shot, the depth axis has to be scaled by matching a body length
between two cameras at unknown distances with unknown lenses, and there is no
way to check that scale at all — not to confirm it, and not to rule it out.

The deeper reason is comparison. A calibration reference makes a future
measurement **like-for-like**, and the absence of one is why this disagreement
was so hard to read: every candidate had to be tested against correlations too
weak to exclude a minor contributor.

**Instruction: put a rigid object of known size in both cameras' view for the
whole take.** A printed checkerboard is ideal. A metre rule taped to the floor,
or a marked pole, will do. It must not move and it must be visible throughout,
not just at the start.

### 3. Film the drills the library contains, with a passer

Both sets show the same thing: she stands still, **tosses the ball upward
herself**, catches it at head height, brings it in, and tosses again. She begins
holding the ball, and no passer appears in either view.

Every one of the engine's eight drills is fed by a passer. The ball's flight is
authored from a passer position and a catch point, and the whole model turns on
a ball arriving with a speed and direction the athlete must answer. A ball
tossed straight up arrives slowly, vertically, and at a moment she chose.

**A perfect two-camera capture of a self-toss still grades nothing.**

**Instruction: film the drills by name, with a passer feeding the ball as the
manual describes.**

### 4. One drill per clip

Set 0.1 runs a single drill for 28 seconds, eight of them spent talking before
any movement.

The engine's reference curves are indexed by PHASE, running 0 to 1 across ONE
movement — that is stated in `reference-curves.json`'s own note. A clip holding
two drills cannot be phase-matched to either curve, because there is no single
movement for the phase to run across. This is not a tidiness preference: it is
what makes a comparison against the engine possible at all.

**Instruction: start a clip, clap, do one drill, stop. Then start the next
clip.**

### 5. A 90-degree camera pair cannot see one side of the body

Usable readings from the two views together, set 0.1:

| landmark | left | right |
|---|---|---|
| wrist | 731 | **28** |
| ankle | 199 | **14** |

The side camera sees her in profile, so the far limb is occluded almost
entirely. No analysis recovers a joint the cameras never saw.

**Instruction: pick one.** A third camera on the far side; or two takes with the
athlete turned around between them; or choose drills where the near arm is the
working one, and say which arm each clip is for.

### 6. Cameras within about four metres

The pose model's own card puts people further than about 4 metres out of scope.

**Instruction: keep both cameras inside 4 metres of the athlete.**

### 7. Nobody else in frame

The model tracks one person. A second person entering frame is a tracking
hazard, and one enters the right edge of `side 0.2` late in the clip.

**Instruction: clear the background. One person in shot.**

### 8. Whole body in frame, throughout

`front 0.1` crops her feet for part of the clip. Ankle readings drop to 199 of
730 frames as a result.

**Instruction: frame for the whole body including the feet, and check it after
the first repetition rather than at the end.**

### 9. Do not stop a camera while the drill is still running

`front 0.1` is camera handling from 26.0 s and dark from 26.267 s. Its usable
content ends at **25.7 s**, measured per frame.

The pose model does not save you here: it detects a body through **26.133 s**,
past the usable end, because a smeared body is still body-shaped.

**Instruction: let the camera run for three seconds after the last repetition,
then stop it.**

### 10. Constant frame rate, or document it

The front cameras run at exactly 30.000 fps. The side cameras run at 30.012,
which is variable and drifts 11 to 13 ms over a clip — about a third of a frame.
Small here, free to avoid.

**Instruction: lock the frame rate if the phone allows it. 60 fps is better than
30 for a fast catch, if both phones can hold it. If a phone cannot lock its
rate, write down the phone model and the camera setting used, per take** — the
analysis can measure the drift afterwards, but only if it knows which clip came
from which camera and at what setting.

### 11. Camera originals, not messaging transcodes

These files are 1.4 to 1.8 Mbps and 576p-class. They have been through a
messaging app.

**Instruction: transfer the original files off the phones — cable, AirDrop, or a
file-sharing link, not a chat app.**

## What was measured, and how well

### Two-view agreement

On 735 frame pairs and 5,088 landmark readings, comparing the height of each
landmark as the front camera sees it against the side camera's answer for the
same landmark:

| landmark | readings | median | 90th |
|---|---|---|---|
| left shoulder | 735 | 14.2 mm | 39.8 mm |
| right shoulder | 735 | 17.3 mm | 46.0 mm |
| left knee | 442 | 13.4 mm | 27.2 mm |
| left elbow | 734 | 65.8 mm | 193.7 mm |
| left ankle | 199 | 90.2 mm | 125.5 mm |
| left wrist | 731 | 140.9 mm | 336.4 mm |
| both hips | 735 | 3.7 mm | 8.5 mm |

**The hips are the vertical origin of both views, so their 3.7 mm is nearly
circular and is not a measure of accuracy.** It is the most quotable number here
and it means the least. Read the shoulders and the knees.

### The elbow angle: nothing tested explains the disagreement

Two independent readings of the same left elbow — one from the 3D lift, one
from the side view alone — differ by a **median of 21.2 degrees**, 90th 63.0.
This is measured on 730 frames, five fewer than the residual table's 735,
because it additionally requires shoulder, elbow and wrist all visible in
**both** views rather than one landmark at a time.

**It is a symmetric spread, not a constant offset.** The signed median is
+1.6 degrees. Those two point at different causes and only the second would
suggest a fixable bias.

**About 5.0 degrees of it is geometry rather than error.** A 3D angle and a
side-view 2D angle are not the same quantity: the side camera cannot see the
across axis, so it reads the arm projected into its own plane. That floor was
isolated by taking the same 3D and dropping `across` — no second instrument
enters, so nothing else can be blamed. It is about a quarter of the 21.

**Four explanations were raised and all four were refuted**, two by each lane,
and each lane killed one of its own:

| candidate | test | verdict |
|---|---|---|
| sync uncertainty | does not grow with speed above 1 m/s | refuted |
| projection alignment | correlation +0.088, flat across every band | refuted |
| depth scale error | banding is U-shaped, not monotonic rising | refuted |
| camera foreshortening | banding also U-shaped | refuted |

**Nothing tested explains the 21 degrees.** No fifth candidate is offered here:
a report that ends on an untested hypothesis reads as an explanation, and there
is not one.

**What that refutation is worth, stated honestly.** These are correlations
against a quantity whose median is 21 degrees with a wide spread. That gives
good power to refute an effect that DOMINATES and poor power to exclude one
contributing a few degrees. None of the four is ruled out as a minor
contributor, and this data cannot distinguish "small effect" from "none". The
case is bounded, not closed.

**A correlation quoted without the exact definition of both quantities is not a
measurement.** The two lanes computed the same refutation on identical frames
and got +0.023 and +0.140 — a six-fold difference, caused by one taking the
larger across-extent of the two arm SEGMENTS and the other the shoulder-to-wrist
span. Neither wrote the choice down. The refutation survives all four readings
taken, and the discrepancy is the sharper lesson: it is the same fault as a
number quoted without its instrument.

**One unexplained fact, recorded without a story.** Every banding either lane
has tried is U-shaped — worst at both extremes of the range, best in the
middle. Nobody can say why.

### Where the sync uncertainty bites

Agreement was measured, not predicted. On trunk landmarks in slow phases the two
cameras agree to **13 to 17 mm**. On the hands in fast phases they disagree by
**100 to 340 mm**, and that disagreement stops growing with speed above about
1 m/s — sync uncertainty bounds it rather than explaining it. The lift is usable
in stance, hold and ready; in fast phases it is illustrative and never a
measurement.

### Scale

Recovered from the athlete's own measurements rather than an anthropometric
table. Wingspan 1.82 m minus twice the 0.77 m one-arm reach leaves **0.280 m
across the shoulders**, visible in the front view every frame. The side view's
scale is tied to the front's by requiring the torso to be the same length in
both — one length seen twice, needing no assumptions about body proportions.

## Method notes for whoever runs this next

**Repetitive drills defeat whole-signal correlation, in any modality.** The
athlete throws and catches on a cycle of a second or two, so the signal is
nearly periodic and the correlation has many near-equal peaks. This held for
audio and for pixel motion alike. A unique event is not a convenience for this
method — it is a requirement, and that is what a clap is.

**"Detected" does not mean "usable".** The pose model finds a body in smeared
frames with high confidence. Detection answers *did the model find a body*;
frame quality answers *is this frame footage*. A consumer trusting detection
alone measures a blur with confidence.

**The elbow angle has two conventions and they are opposites.** The engine's
`elbow_flexion_degrees` in `spikes/segment_measures.py` is `180 − included
angle`, so a straight arm is **zero**. A video curve carrying the included angle
would be the opposite convention, and laying the two side by side compares
different quantities that both read in degrees. This was caught before it
published a number, by reading the definition rather than assuming it.

**Two readings of the same joint disagreed by ~20 degrees and neither was
averaged into the other.** Two hypotheses were tested and refuted: sync
(correlation +0.327, no growth above 1 m/s) and forearm foreshortening
(correlation +0.088, disagreement flat across every alignment band). The cause
remains unidentified, and the honest statement is that neither reading is a
measurement of that joint on this material.

## Artifacts

Computed at the time of writing. Any regeneration supersedes these.

| file | size | sha256, first 32 |
|---|---|---|
| `keypoints-front-0.1.json` | 10.0 MB | `d0f97642d08f473fda83b0d626512231` |
| `keypoints-side-0.1.json` | 10.9 MB | `b7a51d73971230d386b1e3a6900e80f8` |
| `keypoints-front-0.2.json` | 11.5 MB | `36bddb50cef6ecccec8eb4bdba6511f5` |
| `keypoints-side-0.2.json` | 11.4 MB | `0e2a1fdc9e623ab0bdfd5923f83b8315` |
| `lift-3d-0.1.json` | 1.0 MB | `209f878249bd26714f5fe87aa35d61dd` |
| `elbow-curve-0.1.json` | 0.1 MB | `e4f7bcfa057aa3e438149d0fda8f5c5c` |
| `reference-curves.json` | 0.1 MB | `30c75d10d013b7ed0dd1e9bcb5e7810b` |

All under `spikes/poc-output/video/`. **Their own `generatedFrom` stamps read
commit `a3efaf4` with `treeWasClean: false`, written 12:48 to 12:50 UTC** — the
extractor was uncommitted when it ran and was committed afterwards. An earlier
draft said "generated at commit e4f0983", which is a commit that did not exist
when these files were written. The stamps are the authority; quote them rather
than a commit chosen later. Set 0.2's
two views carry `"measured": false` in their sync block: only set 0.1 has a
measured offset between the cameras.

The tooling is `mediapipe` 1.0.1, Apache 2.0, with the
`pose_landmarker_heavy.task` bundle. The bundle itself carries no licence text
of any kind; its model card states Apache License, Version 2.0, and that is the
authority. The card also names 3D pose measurement in scope, and puts people
beyond 4 metres and multi-person scenes out of it.

## Working notes

The full working record, including the failures and two mistakes made and
corrected during the spike, is in `spikes/VIDEO_SPIKE_NOTES.md`.
