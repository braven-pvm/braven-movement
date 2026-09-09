# What the honest kit workflow costs

Measured 2026-09-09 by the character and animation lane, on main `b011d39`.

**This measures and it determines nothing.** No licence was recorded, nothing
that selects a new asset was committed, both touched files were restored, and
`git status` was READ afterwards rather than the restore being trusted.

It exists because the item 3 options table prices four options partly on a
number nobody had measured: **what reconfirming an asset's licence actually
costs.** It was measured BEFORE Marius rules, deliberately. A number taken after
a ruling is read as support for the option that was chosen; taken before, it is
just a number.

## 1. The workflow, which is the only path the code permits

For an asset this repository has not licensed, the code allows exactly one
sequence:

1. Select the asset in `create_athlete`. The render then **refuses**.
2. Read the asset's own file header.
3. Record what it says.
4. Render.

**That is not a policy anybody chose.** `Studio.__init__` calls
`source_asset_records`, which raises on an asset with no determination, so no
figure can be drawn past step 1. The rendering lane's variant C established the
refusal fires on a real edit to the real generator; this measures what walking
past it costs.

## 2. The numbers

`netball_chest_pass`, phase `ready`, three views, on this machine.

| stage | measured | repeats per asset? |
|---|---|---|
| meet the refusal, one asset | **6.1 s**, Blender exits 9, no receipt | **yes** |
| meet the refusal, two assets | **5.5 s**, and it names **one of the two** | **yes** |
| read the asset's own header | **1.0 ms** | **yes** |
| record the determination | one edit | **yes** |
| render to completion | **68.9 s**, exit 0, receipt written | **no, once for all** |

## 3. THE FINDING: N UNLICENSED ASSETS COST N REFUSAL CYCLES

**Two unlicensed assets were selected and one run named ONE of them.** Measured,
not inferred. `source_asset_records` is a list comprehension over
`source_asset_record`, so it raises on the first and never reaches the second.

**So five assets is five build-and-refuse cycles, not one.** At 6 seconds each
that is cheap in machine time and it is five round trips of a person's
attention, which is the part that is not cheap.

**AND THE FUNCTION THAT WOULD FIX IT ALREADY EXISTS AND IS WIRED TO NOTHING.**
`asset_licences.undetermined()` takes a list of paths and returns **every** one
with no determination. Its own docstring says why it was written:

> Nothing in the render path uses this yet; it exists so that a person adding
> four assets is told about four.

A search of the repository finds no caller. **This is a requirement and not a
change**: whoever wires it decides whether the refusal should name all of them,
and that touches the rendering lane's `Studio`. It is recorded here because the
measurement above is what shows the cost of leaving it unwired.

## 4. What the fifth asset costs after the first four

The question the options table is really pricing.

    per asset      ~6 s refusal  +  ~1 ms read  +  one edit
    once, at the end   ~69 s render

**The marginal cost of one more asset is about six seconds of machine time and
one reading of one file.** The render is paid once however many assets there
are. **If `undetermined()` were wired, the per-asset six seconds would collapse
into a single cycle for the whole set** and the marginal cost would be the
reading alone.

## 5. The asset's own statement, recorded as an OBSERVATION and NOT as a determination

`clothes/female_sportsuit01/female_sportsuit01.mhclo`, first lines of its header,
quoted:

    # This asset was explicitly released as CC0 in september 2020. The license
    # text for CC0 can be found in the root of this repository.

**This is evidence of what the asset says about itself. It is NOT a
determination and it has not been recorded as one.** `docs/LICENSING.md` makes
determinations, and adding this asset to `asset_licences.SELECTED_MPFB_ASSETS`
would be one. **The temporary table entry used to complete stage 4 was
restored.** Refer to `docs/TWO_RECEIPTS_AND_A_SECOND_ASSET_LIST.md`: a
declaration, a transcription and an asset's own header are three strengths of
the same word, and walking this path must not quietly collapse two of them.

## 6. What the receipt then carried

With the determination temporarily in place, the completed render's receipt held
**16 source assets** against the usual 15, and the new one carried:

    path      female_sportsuit01.mhclo
    sha256    6df057d3116db93a...
    licence   CC0

**So the receipt pins which bytes were licensed**, which is the property PR #105
added and the one that makes "CC0 at that path" into a claim about a file.

## 7. A limit of THIS document's own instrument

**The header reader takes one LINE, and the header WRAPS.** The captured text
ends `...released as CC0 in september 2020. The license`, because the sentence
about where the licence text lives continues on the next line.

**The determination itself survived intact here by luck of where the wrap fell.**
On an asset whose CC0 sentence wraps mid-claim, a one-line reader would capture
half a determination and it would still look like a quotation.

**That is mode 4 of the search procedure in
`docs/WHAT_BETTER_ANIMATION_MEANS.md` section 8 — line wrapping — hit by an
instrument written after that procedure was published.** Anything that reads
these headers for real must read the comment BLOCK, not a line.

## 8. What was not done

- **No determination was recorded.** The table is unchanged on this branch.
- **Nothing that selects a new asset was committed.** The generator is unchanged.
- **The tree was restored and then READ**: `git status` was clean afterwards,
  because a restore that is trusted rather than checked is not evidence.
- **The asset was added to `source_assets` only, not loaded as a garment.** The
  figure was not changed. This measures the licence path and nothing about how
  the kit looks; the earlier render of `female_sportsuit01` in
  `docs/WHERE_A_BETTER_CHARACTER_COMES_FROM.md` section 3 is that measurement.
- **One machine, one run per stage.** The 6.1 and 5.5 second refusals differ by
  more than I would read anything into.
