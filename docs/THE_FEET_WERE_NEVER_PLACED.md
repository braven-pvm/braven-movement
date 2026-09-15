# The renderer has never placed her feet

Measured 2026-09-14 by the rendering lane, against `320bd01`, with
`scripts/flight_probe.py` and the comparison described at the end.

**Every job this repository has exported carries `ankleFromPelvisInLegs`, and
`blender_movement_render.py` has discarded it.** Not the height alone — the
whole field, across and ahead as well as up. On every phase of every drill the
athlete's feet are drawn at the rig's REST position.

This was found while fixing something smaller. A drill named
`netball_double_foot_landing` has a phase named `flight`, the solve puts her
15.80 cm off the ground there, and no render could leave the ground. The height
was the symptom. The feet not being placed at all is the fault.

## What was measured

The old renderer, extracted verbatim with
`git show 320bd01:blender_movement_render.py`, against jobs with the new height
field stripped out, so that nothing of the fix was in the path:

```
netball_double_foot_landing, 4 phases
  approach  l=(+0.1730,-0.0134,+0.0736)  r=(-0.1730,-0.0134,+0.0736)
  flight    l=(+0.1730,-0.0134,+0.0736)  r=(-0.1730,-0.0134,+0.0736)
  land      l=(+0.1730,-0.0134,+0.0736)  r=(-0.1730,-0.0134,+0.0736)
  absorb    l=(+0.1730,-0.0134,+0.0736)  r=(-0.1730,-0.0134,+0.0736)

netball_bounce_pass, 5 phases        DISTINCT FOOT PLACEMENTS: 1
  the same coordinates again, on a different drill, while that job's own
  ankleFromPelvisInLegs z reads -0.9120, -0.8516, -0.8817, -0.8965, -0.9027
```

**Two drills, nine phases, one foot position, in all three axes, to four
decimals.** Those coordinates are the rig's rest position. The second drill is
the one that settles it: its job asks for five different stances and the
renderer drew one.

**THAT IS THE SCOPE OF THE MEASUREMENT AND IT SHOULD NOT BE WIDENED IN THE
RETELLING.** Two drills were measured. The code path is unconditional, so the
same must follow for every drill, but "two drills, nine phases" is what was
run.

## The mechanism, and it is one line

`pose_stance` aims the legs at the job's target and then throws the aim away:

```python
rotate_bone_toward(rig, thigh, calf, knee)
rotate_bone_toward(rig, calf, foot, ankle)
rig.pose.bones[foot].matrix = foot_baseline[foot]
```

`foot_baseline` is captured once, in `Studio.__init__`, at rest. **A world
matrix carries a TRANSLATION as well as a rotation.** So the last line does not
merely restore the foot's angle — it returns the ankle to where it sat before
anything was posed, undoing both rotations above it.

The line was written for a real defect and the comment above it says so: the
engine has no floor constraint and holds the ankle 48 to 62 degrees
plantarflexed, which drives the ball of the foot through the floor. Keeping the
foot FLAT is what it was for. Flatness is rotation. The re-pinning was
accidental and silent.

The repair keeps the rotation and takes the translation from where the leg was
aimed.

## `blender_mpfb_reference_catch.py` has the same line and is NOT the same fault

It was checked, because the reference figures come from it and a second
instance would double the size of this.

`blender_mpfb_reference_catch.py:208` reads
`armature.pose.bones[foot].matrix = baseline[foot]`, which is textually the
same. It is semantically the opposite, and the reason is the FIRST statement in that
function:

```python
def pose_power_stance(armature, baseline, athlete):
    ankle_targets = {
        side: world_head(armature, f"foot_{side}").copy()
        for side in ("l", "r")
    }
```

**Its targets ARE the rest positions**, captured before anything moves. It then
translates the pelvis and aims the legs back at those same points, so restoring
the baseline puts the foot exactly where the target already asked. Nothing is
discarded. It is a deliberate construction — the hips move and the feet stay —
and it is correct.

The movement renderer's target comes from the JOB and is a different place from
rest. That is the whole difference: the same line is a no-op in one file and a
silent discard in the other.

## What it costs to correct, and this is not a regression figure

Rendering the same drill through the old renderer and the new one, against jobs
that are bit-identical apart from the height field:

```
CONTROL   identical code, identical job, two runs      0 to 7 px, level 0 to 30
CHANGE    the three planted phases            45762 to 61821 px, level 190 to 231
CHANGE    the flight phase                  328651 to 391783 px, level 251
```

**The planted numbers are the size of the correction, not the size of a
regression.** Her feet arrive where the job always said they should be, and
about 50000 pixels per view change as a result. A reader who mistakes one for
the other will revert a correct change.

**The proof usually asked for cannot be run here at all.** Byte-identity is
unachievable: two runs of identical code produce PNGs differing by about 15
bytes of metadata while the pixels are identical. Compare pixels, and compare
them against the control band above.

**THAT IS A GENERAL FACT ABOUT THIS RENDERER AND IT HAS ITS OWN DOCUMENT**, with
the band, how to measure it yourself, and how to attribute a difference to your
own change: [`COMPARING_TWO_RENDERS.md`](COMPARING_TWO_RENDERS.md). It was
written here first and moved, because somebody reaching for `sha256` to compare
two figures is not reading a document about feet.

## What this document does NOT claim

- **It does not say the new placement is right.** It says the feet now follow
  the job, and that they did not before. Whether the job's stance is what a
  coach should see is a question about the lower body, which this repository
  does not present as a graded value, and it is not the rendering lane's to
  settle.
- **It does not price a re-render of the library.** Every figure already
  produced has her feet at the rig's rest position regardless of the drill, and
  whether those are redrawn is not a technical decision.
- **It says nothing about the engine.** The solve carries the stance correctly.
  `spikes/export_blender_job.py` exports it correctly. The loss is entirely in
  the Blender render path, and the clip path to Tactics never had it: `bob` in
  the `"bob"` key in `spikes/clip_geometry.py` carries the same drill's flight
  at 0.1580 m. **That line moved from 258 to 267 between `320bd01` and
  `0353b76` — about six hours, on the day this was written** — which is why the
  citation names the key and not the number.

## How to re-measure it

```
git show 320bd01:blender_movement_render.py > old_render_320bd01.py
```

Then pose any job's phases through `old_render_320bd01.pose_phase` and print
`world_head(rig, "foot_l")` per phase. Every phase returns the same point.
Delete the extracted file afterwards; it is not part of the tree.

`scripts/flight_probe.py` measures the other half — how high off the floor she
is IN THE PICTURE — by hiding the floor, turning the film transparent and
reading the alpha channel. It is calibrated against known lifts and will not
report a height it has not first been shown able to report.
