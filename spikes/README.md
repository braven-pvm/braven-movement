# Spikes

## The proof of concept

[poc_engine.py](poc_engine.py) runs the whole engine on the netball catch, using
the repository's own hand-labelled data.

```text
config pixels -> constrained pose fit -> ISB measurement -> range check -> GLB + receipt
```

```bash
pixi run python poc_engine.py
```

```text
enabled parameters: 38 of 204
rest pixel errors:   head_base 71.4   left_elbow 175.5  left_wrist 310.6 ...
solve: 5.0 ms
fitted pixel errors: head_base 4.03   left_elbow 9.13   left_wrist 6.81 ...
measured: leftElbowFlexion 20.03   rightElbowFlexion 30.13
          leftShoulderElevation 70.98   rightShoulderElevation 82.97
anatomy: passed
```

The athlete fits the 8 labelled landmarks to between 3.8 and 11.6 pixels on a
769 by 665 frame, in **5.0 milliseconds**, with joint limits active throughout
and body proportions locked. Every measured angle is inside the clinical range.
It writes `poc-output/braven_poc_catch.json`, a receipt in the style this
repository already uses, plus a GLB.

The two arms report different angles, which is the point. An earlier version
reported the same angle for both, and that was a defect every time.

### What the fit taught us

Six failures happened before it converged. Each one is a rule worth keeping.

1. **MHR is Y-up and works in centimetres. The movement configuration is Z-up
   and works in metres.** Without the conversion the athlete stands 172 units
   tall in a scene scaled for 1.7, and every landmark misses by thousands of
   pixels. Any coordinate that crosses this boundary must be converted.
2. **`pymomentum` uses the same camera convention as computer vision**: X right,
   Y down, Z along the view direction. A sweep of all four sign combinations
   settled it. With the depth row negated the athlete falls behind the near clip
   and the solver never moves at all, which looks like convergence.
3. **The Gauss-Newton defaults are two iterations with no line search.** A
   projection residual is strongly non-linear, so the undamped step overshoots.
   Set `do_line_search = True`.
4. **Do not optimise 204 parameters for 8 landmarks.** That produced NaN. Enable
   only the parameters the landmarks observe.
5. **Name the enabled parameters exactly.** MHR calls the elbow parameter
   `l_elbow_bend`. A whitelist of "uparm", "lowarm", and "wrist" misses it, so
   the elbow freezes and the solver reaches the landmarks by moving the whole
   body instead. The fit still looked excellent at under 5 pixels, and both
   elbows still reported their rest angle of 34.53 degrees. A good residual is
   not evidence of a good pose.
6. **Lock the shape parameters.** Names such as `scale_uparms` and
   `arm_length_flexible` let the solver stretch the athlete's limbs to reach a
   pixel. That changes who the athlete is rather than how they move. Locking
   them raised the pixel error from 5 to 12, which is the honest number.

### What is proven, and what is not

Proven: the pose fit to 2D image landmarks, joint limits during the fit, locked
body proportions, the solve speed, frame-free measurement, the range check, the
receipt, and the GLB export.

Not proven: the legs never move, because the configuration has no leg landmarks,
so both knees report the rest angle. Axial rotation is not measured at all. The
`isb_angles.py` decomposition is validated against OpenSim but is not yet wired
to real bone orientations, so the pipeline uses the frame-free measures instead.

## Spike F: a simple movement

**Question.** Can the engine produce a movement, not only a pose?

**Answer. Yes, and faster than real time.**

[spike_f_movement.py](spike_f_movement.py) drives both hands along a netball
catch trajectory, solves all 24 frames under joint limits with body proportions
locked, and keeps the frames continuous with a pull toward the previous frame.

```text
frames: 24 at 24.0 fps
solve: 1.4 ms per frame, 0.033 s total
max hand target miss: 0.00 cm
largest elbow step between frames: 1.63 degrees
  start    left elbow   34.5  left shoulder   42.3
  contact  left elbow   45.7  left shoulder   58.1
  finish   left elbow   34.9  left shoulder   40.9
anatomy: passed
```

The whole movement solves in 33 milliseconds. A 24-frame movement at 24 frames
per second lasts one second, so the engine authors a movement about thirty times
faster than the movement takes to perform.

The largest elbow change between neighbouring frames is 1.63 degrees. That
number is the continuity test. Without the pull toward the previous frame, a
solver can jump between two equally valid answers to the same hand target, and
the movement flickers even though every single frame passes its checks.

It writes an animated GLB and a receipt that records every frame's angles.

## Spike G: the sport layer

**Question.** Can measured angles become something a coach would actually say?

**Answer. Yes, and this is the part no library supplies.**

[movement_definition.py](movement_definition.py) defines what a skill is. A
movement has phases. Each phase has checkpoints. A checkpoint is one measured
quantity, a target band, a coaching cue in plain language, and the reason it
matters. [movements/netball_two_hand_catch.json](movements/netball_two_hand_catch.json)
is the first definition: ready, reach, contact, pull-in.

Running [spike_f_movement.py](spike_f_movement.py) now ends like this:

```text
coaching (Two-hand catch, reach and pull-in): all checkpoints met
  [ready] Start with soft elbows, hands in front of the chest. Good.
  [reach] Reach to the ball early. Meet it, do not wait for it. Good.
  [contact] Take the ball with bent elbows so you can give with it. Good.
  [contact] Both hands work together. Match your hands. Good.
  [pull_in] Draw the ball in to your chest and secure it. Good.
```

When a checkpoint fails, the note reads "Needs more: 12 degrees against a target
of 30 to 75, off by 18." That is a coaching instruction with a number behind it,
which is the whole product.

### The rule that protects the coach

A checkpoint band narrower than 5 degrees is **rejected at construction**. The
noise study put the honest measurement threshold there, and clinical practice
treats smaller differences as meaningless. Without this rule the tool would
report measurement noise as a technique fault, which is worse than saying
nothing. A test covers it.

### Not coaching truth yet

The shipped bands are placeholders, and the definition says so in its `source`
field. A test asserts that it still says so. Replace them from the Netball Skills
and Conditioning Manual and a coach review before an athlete ever sees them.

## Visual acceptance

[render_contact_sheet.py](render_contact_sheet.py) writes
`poc-output/braven_catch_contact_sheet.svg`, a stick figure for each phase of the
movement with the measured elbow angle under it. No renderer and no extra
dependency.

This exists because of the repository rule that numeric limits never replace
human acceptance. A receipt full of passing angles proves nothing until a person
looks at the pose. The contact sheet is what a person looks at.

## Spike E: the frame-free measures

[segment_measures.py](segment_measures.py) measures joint angles from joint
centres alone. No synthesised landmark, no plane normal to flip, no Euler
sequence to hit gimbal lock. For a hinge such as the elbow it equals the ISB
flexion exactly. [test_segment_measures.py](test_segment_measures.py) covers it,
including a test that the two arms must report different angles, and a test that
a measure does not change when the whole body rotates.


Exploratory code that answers one question each. Nothing here is production code.
A spike graduates into the main tree only after its question has an answer.

Run the host-side spike tests with the repository Python:

```bash
python -m unittest discover -s spikes -p "test_*.py" -v
```

Run the OpenSim cross-check with the virtual environment interpreter, because it
needs the OpenSim wheel:

```bash
.venv/Scripts/python.exe spikes/opensim_crosscheck.py
```

## Spike C: the ISB measurement layer

**Question.** Can we report the joint angles that a sport scientist accepts, and
do they agree with an established biomechanics engine?

**Answer. Yes, exactly.**

[isb_angles.py](isb_angles.py) computes joint angles on International Society of
Biomechanics conventions. The elbow, the knee, and the hip use the ZXY sequence.
The shoulder uses the YXY sequence. The module depends only on the Python
standard library, so it runs unchanged in a test, in a solver loop, in Blender,
and on a server.

[opensim_crosscheck.py](opensim_crosscheck.py) builds a two-segment arm in
OpenSim 4.6, sweeps the elbow from 0 to 145 degrees, reads only the landmark
positions, and rebuilds the angle. The difference is 0.000000 degrees at every
tested angle.

### The landmark accuracy budget

The same script perturbs every landmark with Gaussian noise, then measures the
angle error over 400 samples at 110 degrees of elbow flexion.

| Landmark noise | Mean angle error | 95th percentile | Samples over 5 degrees |
|---|---|---|---|
| 2 mm | 0.59 degrees | 1.51 degrees | 0.0 % |
| 5 mm | 1.53 degrees | 3.89 degrees | 1.2 % |
| 10 mm | 4.17 degrees | 10.23 degrees | 26.0 % |
| 20 mm | 28.19 degrees | 225.64 degrees | 65.0 % |
| 40 mm | 67.70 degrees | 254.01 degrees | 85.5 % |

Three conclusions follow.

1. **The landmark budget is 5 mm.** Clinical practice treats a difference under
   5 degrees as not meaningful. Only 2 mm and 5 mm noise stay inside that band.
2. **Monocular video cannot measure.** The published error for single-camera 3D
   pose on real sport motion is about 65 mm, even after fine-tuning on sport
   data. That is three times worse than the 20 mm row, where this method already
   fails most of the time. Entry point A produces a starting pose, not a
   measurement. This repeats the published finding with our own numbers.
3. **Short landmark baselines are fragile.** The collapse between 10 mm and
   20 mm is structural, not statistical. The epicondyle and styloid offsets are
   only 30 to 40 mm, so noise of that scale flips the plane normal and the
   segment frame inverts. A production measurement layer must take segment
   orientation from bone frames, not from a small landmark triangle.

### What is not done

The cross-check covers the elbow, which is a pin joint. The shoulder uses the
YXY sequence and three degrees of freedom, so it needs its own cross-check
against an OpenSim ball joint. That is the next step for this spike.

## Spike A: MHR and the momentum solver

**Question.** Can we pose an MHR athlete to an end-effector target at
interactive speed?

**Answer. Yes, with a very large margin.**

[spike_a_mhr_ik.py](spike_a_mhr_ik.py) loads the MHR athlete, drags the left
hand to a target, solves with joint limits active, and measures the result with
the ISB layer.

```text
character: 127 joints, 204 model parameters
chain: l_uparm -> l_lowarm -> l_wrist
solve time: 1.1 ms per solve, averaged over 20
target miss: 0.10 mm
```

A coach interface at 60 frames per second has a 16 millisecond budget. One solve
costs 1.1 milliseconds on this CPU, with no GPU. There is roughly fifteen times
more headroom than an interactive interface needs.

### What the solver already provides

`pymomentum.solver2` contains most of the engine that the research proposed.
Nothing in this list has to be written.

| Need | Error function |
|---|---|
| A coach drags a hand or a foot | `PositionErrorFunction`, `OrientationErrorFunction` |
| Anatomical joint limits | `LimitErrorFunction` |
| Plausible completion of the rest of the body | `PosePriorErrorFunction` |
| Limbs must not pass through the body | `CollisionErrorFunction` |
| Feet stay on the ground | `FloorErrorFunction`, `HeightErrorFunction` |
| Fit a pose to 2D pixels from a camera | `CameraProjectionErrorFunction` |
| Smooth motion across frames | `AccelerationSequenceErrorFunction`, `JerkSequenceErrorFunction` |
| Balance and support | `support_polygon`, `support_contacts` in `geometry` |

`CameraProjectionErrorFunction` deserves attention. It fits a pose directly to
2D image landmarks, with joint limits and a pose prior active during the fit.
That is a stronger design for entry point A than trusting a monocular 3D lift,
and it is stronger than the hand-written pixel calibration in the repository
root.

### Environment notes, the hard way

- The package published on PyPI as `pymomentum` belongs to Momentum Teknoloji
  AS. It is **not** Meta's library, and pip installs it with no warning. Do not
  depend on it.
- Meta's `pymomentum-core` and `pymomentum-cpu` do not exist on PyPI. conda-forge
  is the only route.
- conda-forge win-64 builds need Python 3.12 or newer. [pixi.toml](pixi.toml)
  pins Python 3.12 with `pymomentum` 0.1.114 and `mhr` 1.0.1.
- Model assets come from the MHR GitHub release, 189.7 MB, extracted to
  `spikes/mhr-assets/`, which git ignores.

```bash
pixi run python spike_a_mhr_ik.py
```

### Open point

The spike synthesises the epicondyle and styloid landmarks with a fixed world
offset, so the reported carrying angle is not meaningful. This is the same
fragility the noise study exposed. The fix is to take segment frames from the
bone quaternions in the skeleton state, which MHR supplies directly, rather than
from a landmark triangle.

## Spike B: SAM 3D Body

**Status. Blocked twice.** It depends on MHR, so it inherits the blocker above.
It also needs a reference image, and `references/` holds only its README.

## Spike D: Kimodo

**Status. Not started.** This machine has no NVIDIA GPU, so diffusion sampling
runs on CPU. Judge feasibility before committing to a download.

## Licences, verified against the LICENSE files

| Component | Licence | Commercial use |
|---|---|---|
| MHR, code and weights | Apache 2.0 | Yes |
| SAM 3D Body | SAM licence | Yes, with acceptable-use limits |
| Kimodo code | Apache 2.0 | Yes |
| DPoser-X | MIT | Yes for the code. Its pose space is SMPL-X, which is not free. |
| WHAM | MIT for the code | Restricted in practice by SMPL and AMASS |
| GVHMR | Custom academic licence | **No.** Educational, research, and non-profit only. |
