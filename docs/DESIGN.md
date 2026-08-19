# Design — Braven Movement

Written 2026-08-19, at the end of the spike phase.

## 1. What this is

A movement engine for a high performance sport laboratory. It does three
things, in the order they earn their keep:

1. Produces the figures for coaching manuals, from movements graded against a
   coaches manual rather than drawn by hand.
2. Measures a real athlete performing a skill, and grades that against the
   same definition.
3. Serves the wider laboratory: rehabilitation, conditioning, and the
   instruments already in the building.

The first is content. The second is the reason the engine has to be right.

## 2. The two decisions this design rests on

**Analysis of real athletes is core, not an addition.** The domain model is
built around a real person from the start. An authored movement is not the
centre of the system; it is the reference a person is measured against.

**Physics goes as far as inverse dynamics.** Segment masses and inertias,
centre of mass, ground reaction and joint moments. Not muscle-driven forward
dynamics, which is a separate project built on top of this one.

Both were settled deliberately. Retrofitting either would mean a schema change
and a foundation change respectively.

## 3. The core model

> The engine solves a **Performance** from **Constraints**, on a stated
> **Anatomy**. A **Definition** grades a Performance and produces an
> **Assessment**.

Constraints come from two places and the engine does not care which:

| Source | Constraints | Produces |
|---|---|---|
| Authoring | motion keys, technique, object track | a reference Performance |
| Capture | landmarks from video or markers, camera calibration | a measured Performance |

This is the load-bearing idea, and it is the reason the spike work is not
wasted. **A comparison is only meaningful if the reference and the measurement
pass through the same anatomy.** Compare a raw capture against an idealised
drawing and the difference contains the measurement pipeline's own errors.
Solve both through the same skeleton, the same joint limits and the same ISB
angle definitions, and what is left is the athlete.

Everything below follows from that sentence.

## 4. Domain model

Names in **bold** exist today. The rest are new.

**Athlete** — a real person. Name or identifier, sex, date of birth, and the
measurements taken on a date: standing height, mass, and segment lengths where
they were measured rather than inferred. The current `Athlete` type is a
synthetic body built from MHR identity parameters; it becomes **Body**, and an
Athlete has one. A Body can also exist without an Athlete, which is what the
reference athlete and the squad are.

**Session** — one athlete, one date, one place, and the captures taken. This is
where "has she improved" lives.

**Capture** — the raw input to a measured Performance. The source file, the
camera calibration, the frame rate, and the landmark data extracted from it.
Kept because a Performance must be reproducible from its input.

**Performance** — the solved motion. Per-frame joint transforms, the Body it
was solved on, and its **provenance**: authored or captured, and from what.
Today the solve returns a dictionary. It becomes a type, because everything
downstream needs to know where the numbers came from. Refer to section 6.

**MovementDefinition** — unchanged. Phases, checkpoints, angle bands, cues.
The rubric. It grades a Performance whatever its provenance.

**MovementAssessment** — unchanged in shape, extended to carry the Performance
it graded and therefore the provenance.

**Technique** — unchanged. Grip spread, whether palms face the object, and the
anatomical limits a technique respects.

**ObjectTrack** — today `ball_track`, and today a sphere. The possession model
already generalises to any object a person holds, but the sphere is written
into three files. Generalising it is not urgent and it is not free; it is
listed here so it is a decision rather than a discovery.

## 5. The physics layer

Four things, each depending on the one before it.

**A mass model.** Segment masses, centre of mass positions and radii of
gyration, from published anthropometric tables scaled to this athlete's
measured height and mass. De Leva's adjustment of Zatsiorsky is the usual
choice and is sex-specific, which matters here. This is a per-Body property and
is measured or inferred once, not per movement.

**Centre of mass.** Per frame, from the segment masses and the solved joint
transforms. Immediately useful on its own: balance, whether a landing is
controlled, where the mass is over the base of support.

**Ground reaction.** From the acceleration of the centre of mass, by Newton's
second law. Distributing it between two feet needs either a contact model or a
measurement, and the laboratory has the measurement.

**Joint moments.** Newton-Euler inverse dynamics, working inward from the
distal segments. This is what turns "her knee is at 40 degrees" into "her knee
is carrying this much".

All four need clean second derivatives of position, and differentiating noisy
motion is the classic way to produce confident nonsense. The filtering policy
is part of this design and not an implementation detail: a low pass filter with
its cut-off chosen by residual analysis, recorded on the Performance, and
reported with every derived quantity.

## 6. What the physics may and may not claim

This is the most important paragraph in this document.

**On a captured Performance, the derived quantities are an estimate of what
happened.** They can be wrong, they have error bars, and they can be validated
against the force plates.

**On an authored Performance they are not.** An authored movement is four to
six keys interpolated to sixty frames a second. Its accelerations are a
property of the interpolation, not of an athlete. Joint moments computed from
it would be fiction with three decimal places.

Therefore: **a derived physical quantity is reported only where provenance
allows it.** The engine refuses to report joint moments and ground reaction on
an authored Performance rather than labelling them and hoping the label is
read. Centre of mass position is allowed on both, because position does not
depend on differentiation; its velocity and acceleration are not.

This is why Performance carries provenance, and it is the reason that type
exists at all.

## 7. Lanes and boundaries

**This lane** owns movement, anatomy, physics, authoring and capture.

**The rendering and modelling lane** owns the athlete a person looks at and
every picture. It is handed over in `docs/HANDOFF_RENDERING.md`. The boundary
is one JSON job file per movement, carrying reach in arm lengths, stance in leg
lengths and the grip on the object. That lane never needs the solver.

A third boundary will be needed when capture arrives: the landmark extractor
should be replaceable without touching the solver, because that field moves
quickly and whatever is best today will not be best in a year.

## 8. What survives and what is deleted

**The crown jewels, and the reason not to start again:** the joint limits, the
ISB angle layer cross-checked against OpenSim, the possession model, the
body-relative unit discipline, and the coaching definitions with their bands.

**Load-bearing today:** `movement_engine`, `motion_track`, `ball_track`,
`possession`, `possession_solve`, `contact_solve`, `movement_definition`,
`technique`, `segment_measures`, `isb_angles`, `grip`, `finger_wrap`,
`athlete`.

**Delete.** Nothing imports these and they have been superseded:
`poc_engine` (464 lines), `retarget`, `author_flight`, `spike_a_mhr_ik`,
`spike_h_roundtrip`, `spike_i_camera_placement`, `render_photo_fit`.

**Retire when the manual page moves to Blender:** `smplx_body`,
`smplx_retarget`, `render_figure`, `export_figure_check`. This also removes the
SMPL-X research licence from the product path, which is recorded as a
commercial blocker in `LICENCE-RISK.md`.

**Keep, and fold into capture:** `fit_from_photo`, `multi_camera_fit`,
`verify_capture_pipeline`. They are partial and they are the right starting
point.

**Leave `spikes/` behind.** The directory is named for what it was. Load-bearing
code moves into a package with a name.

## 9. How this gets validated

A laboratory sells credibility, so validation is a feature and not a chore.

1. **Joint angles against OpenSim.** Exists. Keep it running.
2. **Centre of mass against a static measurement.** Standing centre of mass
   height as a fraction of stature is well documented. Cheap, and it catches a
   wrong mass model immediately.
3. **Computed ground reaction against the force plates**, on the same trial.
   This is the strongest claim available and the instrument is already in the
   building. Nothing else on this list is worth as much.
4. **Joint angles against a marker-based system**, if the laboratory has one,
   to bound the capture pipeline's own error.
5. **Coaching agreement.** A skills coach grades a set of performances blind,
   and their grades are compared against the engine's assessment. Measures
   whether the bands mean anything.

Items 3 and 5 are what turn this from a tool into an instrument.

## 10. Milestones

Each is finished when it can be demonstrated and measured, not when the code
compiles.

1. **Types before features.** Performance becomes a type with provenance.
   Athlete becomes a real person and the synthetic body becomes Body. Session
   and Capture exist as records even before capture works.
   *Done when* the eight drills solve to Performances and grade exactly as
   they do now.

2. **Mass and centre of mass.** The mass model, per-Body, and centre of mass
   per frame.
   *Done when* standing centre of mass height matches the published fraction
   of stature for the reference athlete.

3. **Capture, one drill, one athlete.** Video in, landmarks out, solved through
   the same anatomy, graded by the same definition.
   *Done when* an athlete's own catch is graded against the manual's bands.

4. **Inverse dynamics.** Ground reaction and joint moments on captured
   performances, refused on authored ones.
   *Done when* computed ground reaction is compared against a force plate
   trial and the disagreement is stated as a number.

5. **Two sessions, one athlete.** The same drill, weeks apart, compared.
   *Done when* a coach can see what changed.

Milestone 1 is a refactor and it is not optional. Everything after it depends
on knowing where a number came from.

## 11. Open questions

- **Does the anatomy stay on MHR?** MHR is Apache-2.0 and the joint limits and
  ISB layer are built on it, which makes it the most valuable thing here. For a
  laboratory publishing results, an OpenSim-based skeleton is easier to defend
  to a reviewer. This is a deliberate decision to make, not to drift into.
- **Which landmark extractor**, and how is its error bounded.
- **How is an athlete measured** in practice: which segment lengths are taken
  by hand, and which are inferred.
- **Two known anatomy defects remain.** The elbows sit 27.3 cm apart against
  38.6 cm in the reference photographs, which needs a term on the upper arm's
  orientation. And `netball_hooks_outside_hand` exceeds a joint limit on one
  frame by 0.715 degrees.
