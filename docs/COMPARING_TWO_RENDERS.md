# Comparing two renders here

Measured 2026-09-14 by the rendering lane, against `320bd01`, on this machine.
Lifted out of `THE_FEET_WERE_NEVER_PLACED.md`, where it was true and unfindable.

**Do not reach for byte-identity. It is unachievable in this renderer and
asking for it costs a day.** Read the three sections below before you compare
anything, in order. They take five minutes and they are the difference between
"this change broke the figures" and "this change corrected them".

## 1. Byte-identity is unachievable. Pixel-identity is nearly achievable

Two runs of identical code on an identical job produce **twelve PNGs that all
differ**, by about 15 bytes each. The difference is PNG metadata. The pixels are
the same.

```
same code, same job, two runs, twelve views
  sha256 differs                   12 of 12
  file size differs                e.g. 1605302 against 1605317 bytes
  pixels differing at all          0 on ten of the twelve
                                   1 px at level 1, and 12 px at level 1
```

A SECOND control run, of a different pair of identical renders, was quieter on
those two views and showed **7 px at level 30 on a third**. Both runs are
reported because one run does not give you the band: it gives you one sample of
it.

So `sha256` answers a question you did not ask. Compare pixels.

## 2. The renderer has a run-to-run band, and it is NOT zero

The numbers above are the band, across two control runs. **It reaches 12 pixels
at level 1, and on one view 7 pixels at level 30** — a handful of pixels can
differ by a LOT, not just a little, so a small count at a high level is not
automatically your change.

**And it moved between the two runs**, which is why one control is a sample and
not the band. If a view matters to your conclusion, run the control on that
view.

**Measure it yourself before you trust these numbers.** It is one extra render:

```
render the same job twice into two directories, then compare them
```

That is the control. Without it you cannot tell a regression from noise, and
this repository has a whole entry about tests with no power to separate two
answers.

## 3. A difference above the band is still not automatically yours

**An earlier render in the same directory showed 24 px at level 3 that predated
the change under test**, because it came from an older export of the job. Charge
that to your change and you revert a correct one.

To attribute a difference to your own edit, hold everything else still:

```
git show <base>:<file> > old_copy.py
```

Run the OLD code against a job that is **bit-identical to the new one apart from
the one field you added**, and compare that against the new code. Anything left
is yours. Delete the extracted copy afterwards — it is not part of the tree.

That is how the foot finding was attributed. The result was unambiguous because
nothing else could have moved:

```
control                              0 to      7 px, level   0 to  30
planted phases, old against new  45762 to  61821 px, level 190 to 231
flight phase,   old against new 328651 to 391783 px, level 251
```

## And a number that big can be a CORRECTION

Those planted numbers are not a regression. They are the size of a repair: her
feet arriving where the job had always said they should be. **A large pixel
difference tells you something moved and nothing about whether it should
have.** Say which you mean, every time, or a reader will assume the worse one.

## The tools

| tool | what it answers |
|---|---|
| `scripts/before_after_sheet.py` | Two or more builds of one figure, side by side, with the share of pixels that moved and the worst step. Labels each column by the BUILD in its own receipt. |
| `scripts/flight_probe.py` | How high off the floor she is IN THE PICTURE. Hides the floor, turns the film transparent, reads alpha. Calibrated against known lifts, so it cannot report a height it has not been shown able to report. |

**`before_after_sheet` counts a pixel as moved above 8 of 255.** That is above
the renderer's sampling noise and below anything a person would call a change,
and it is the right threshold for "did this figure change". It is the WRONG
threshold for establishing the band in section 2, where you want every pixel
that differs at all. Compare at `> 0` there.

## Related

- `docs/THE_FEET_WERE_NEVER_PLACED.md` — the finding this was measured during,
  and the worked example of section 3.
- `docs/RENDER_ARTEFACTS.md` — whether a render is usable at all, which is a
  different question from whether two of them agree.
