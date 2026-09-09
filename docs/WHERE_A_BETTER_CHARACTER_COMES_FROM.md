# Where a better character comes from, and at what licence

Stage 1, item 3 of the character and animation lane. Written on 2026-09-09
against `f555cf8`. **This is a decision for Marius. Nothing here is a
recommendation, and no option is presented as a finding.**

Three kinds of statement appear below and each is labelled: MEASURED on this
machine, READ in this repository, or SEARCHED on the web. A searched price is a
vendor's published range, not a quote.

## 1. A decision already exists, and it narrows the question

**READ.** The product path deliberately left SMPL-X, and the reason is the
licence. `spikes/export_manual_page.py` says so in its own docstring:

> It drew an SMPL-X body through a numpy rasteriser before. SMPL-X is under a
> research licence and may not be sold without a licence from the Max Planck
> Institute, so it does not belong on the path that makes the product.

`LICENCE-RISK.md` records the 18 August 2026 decision to bring SMPL-X in under
its research licence for the figure, and records what must happen before
anything is sold.

**MEASURED.** The SMPL-X code is still here and it is dormant.
`spikes/smplx_body.py` and `spikes/smplx_retarget.py` are imported by
`spikes/render_figure.py` and `spikes/export_figure_check.py`, both of which are
the numpy debug rasteriser and neither of which makes a coach figure.
`spikes/smplx-assets/` contains a README and no model file, so that path cannot
run on this machine at all.

**So the question is not which body model.** It is which MPFB assets and which
configuration values. That is a much cheaper question, and item 1 section 2
established why: the character is nine numbers and seven asset paths, not a
mesh.

## 2. The axis, named exactly

Everything below changes one of these and nothing else.

| what | where | today |
|---|---|---|
| body | `athlete.phenotype`, nine values | `muscle` 0.88, `height` 0.72, `gender` 0.0, `race` caucasian 1.0 |
| kit mesh | `create_athlete`, one asset path | `clothes/female_casualsuit02` |
| shoes | one asset path | `clothes/shoes05` |
| hair | one asset path | `hair/ponytail01` |
| kit colour | `presentation.kit.baseColor` | `[0.018, 0.024, 0.036]`, near black |
| ball colour | `presentation.ball`, four colours | coral, teal, cream, near-black seam |
| ground | `presentation.studio` | a grey cyclorama |

## 3. Option A: reconfigure what is already installed. Cost zero.

**MEASURED on this machine.** The installed MPFB library holds 78 assets and
**every one of the 78 declares CC0 in its own file header**, in these words:

> This asset was explicitly released as CC0 in september 2020.

| category | assets | declare CC0 |
|---|---|---|
| clothes | 20 | 20 |
| skins | 23 | 23 |
| eyebrows | 12 | 12 |
| hair | 10 | 10 |
| teeth | 6 | 6 |
| eyelashes | 4 | 4 |
| eyes | 2 | 2 |
| tongue | 1 | 1 |

**This is stronger evidence than `docs/LICENSING.md` carries.** That document
says the receipt labels the MPFB-derived OUTPUT as CC0 and asks for every newly
selected asset to be reconfirmed. The assets reconfirm themselves, in writing,
in their own headers.

What is available and unused:

- **`female_sportsuit01`** is installed and is not the casual suit that ships.
- **Six shoe sets**, `shoes01` to `shoes06`. `shoes05` ships.
- **Ten hair assets** including `braid01`, `bob01`, `bob02` and four short
  styles. **None of them is a bun**, which is what the manual's own catching
  photograph shows.
- **Twenty-three skins**, of which one ships.

**`female_sportsuit01` WAS RENDERED, and it is not netball kit.** The
experiment swapped one asset path in the generator and its determination in
`asset_licences.py`, rendered `netball_chest_pass ready`, then restored both
files from git. The asset's own header was read FIRST and it declares CC0,
which is the process the module demands rather than a way around it.

It renders as a cropped short-sleeved top and **full-length leggings**, with a
bare midriff. Two things follow:

1. **It is a gym outfit, not netball kit.** Netball is a dress, or a top with a
   skirt or shorts. The manual's training photographs do show crop tops, so it
   is not absurd as a TRAINING figure, and it is not a match figure at all.
2. **THE LEGGINGS COVER THE KNEE**, and the knee is what the landing drills
   grade. `docs/KNOWN_ISSUES.md` records sixteen graded checkpoints below the
   hips, of which `double_foot_landing` alone carries six. A kit that hides the
   joint a figure exists to show is a worse figure, whatever it costs.

**That objection did not exist until the picture did**, which is the argument
for rendering an option rather than describing it.

**The receipt marked itself correctly.** The run printed `tree not verified
clean (f555cf8), so these pictures cannot be reproduced from that commit
alone`, because the experiment had modified the working tree. The build stamp
caught the thing it exists to catch, and the pictures are labelled accordingly.

**What option A cannot do.** There is no bib in the installed library, and no
netball dress. It cannot reach the manual's match-kit figure.

## 4. Option B: the MakeHuman community asset packs. Cost zero money.

**SEARCHED.** The packs are listed by licence on the MakeHuman Community site,
and the split is explicit rather than assumed.

CC0 packs that bear on this lane: **Dress 01** (female gowns and dresses),
**Skirts 01**, **Shirts 01** (t-shirts, sweaters and tops), **Shoes 01**,
**Underwear 04** (socks), **Hair 01**, **Hats 01**, and **Poses 02** (sports
poses, which this lane does not need because it poses from the solve).

CC-BY packs, which require attribution: **Shirts 02** and **03**, **Shoes 02**
(low shoes and sneakers), **Skirts 02**, **Hair 02** and **03**, **Dress 02**
and **03**. The FAQ states it plainly: CC-BY "means that you can do whatever you
want with the asset as long as you give credit to the author".

**A CC-BY asset is not free of obligation.** Nothing in this repository carries
an attribution mechanism today, and the receipt would have to name the author
as well as the licence. That is work, not a blocker, and it is Marius's to
choose.

**The rule for adopting any of them is already enforced.** `asset_licences.py`
refuses an asset with no recorded determination, so a downloaded pack cannot
reach a receipt until somebody reads its header and records what it says.

**What option B cannot do.** Still no bib. The packs are general wardrobe, not
sports teamwear.

## 5. Option C: a third-party marketplace model

**SEARCHED, and the result is thin.** A search for netball kit as a 3D garment
returns stock photographs, dress mockups and teamwear design tools far more
often than a riggable garment. Marketplaces carry netball models, but they are
mostly balls, posts and courts.

**Licences vary per marketplace and per item, and are rarely CC0.** A model
bought from a marketplace usually arrives under that marketplace's own royalty
free licence, which is not the same as public domain and usually forbids
redistributing the asset itself.

**This option cannot be costed until a specific item is named**, its own licence
is read, and its topology is checked against MPFB's fitting requirements. An
`.mhclo` is fitted to the MakeHuman base mesh, so an arbitrary garment mesh is
not a drop-in.

## 6. Option D: commission the kit

**SEARCHED, and these are published ranges from vendor pages, not quotes.**
Treat them as an order of magnitude and get a real quote before believing any
of them.

| what | published range |
|---|---|
| simple stylised character | about EUR 2,000 to 5,000 |
| custom character with production body and face rigging | about EUR 5,000 to 15,000 |
| complex, multiple outfits, advanced rigging | EUR 15,000 to 40,000 and up |
| freelance 3D artist hourly | USD 25 to 150 |

**A netball kit is far smaller than a character.** These ranges are for whole
characters. A single garment fitted to an existing base mesh is a fraction of
that, and none of the sources found priced that job specifically. **I am not
going to invent a number for it.**

## 7. Option E: the bib as a material, not a mesh

**READ in this repository, and this option came out of the code rather than a
search.** `make_fabric_material` in `blender_mpfb_reference_catch.py:928` is
procedural. It builds a Principled BSDF, sets a base colour and a roughness from
the configuration, and already wires a texture-coordinate node into a noise
weave for the fabric bump. `make_netball_material` does the same with a wave
texture, which is where the ball's coral and teal bands come from.

**So a bib panel and a position letter could be a texture on the top that
already ships.** No new mesh, no new asset, no new licence question, and it
changes files this lane already touches.

**What option E cannot do.** A texture has no silhouette. A real bib hangs away
from the body, moves, and shows its edge against the arm. A painted one will not
do any of that, and a coach looking at a side view would see a printed shirt.

## 8. A caution that applies to every option: the studio moves the colour

**MEASURED, on one 80 by 80 patch of the torso in
`out/netball_chest_pass.ready.side.png`, rendered on `9ea602b`.**

The configured kit base colour is `[0.018, 0.024, 0.036]`, whose channel ratios
are 0.500 : 0.667 : 1.000. The rendered patch, converted from sRGB to linear,
has ratios 0.614 : 0.772 : 1.000. The hue survives in direction, blue highest
and red lowest, and it is pulled towards neutral.

**That is consistent with the light rig adding a near-neutral component**, and
it is what makes a near-black configured kit read as mid grey on the page. This
assumes the illumination is itself neutral, which was not separately checked.

**The consequence for a decision.** A colour chosen in the configuration will
not render as chosen. If team colours matter, the light rig has to be part of
the same change, and that is a second piece of work.

## 9. What Marius has to decide

Four questions. None of them has a technical answer waiting.

1. **Match kit or training kit?** The manual contains both. The match figure is
   a sleeveless dress with a lettered bib. The training figure is a top and
   shorts, which is close to what ships. Item 2 section 3 shows both.
2. **Does the bib matter enough to pay for?** It is the only element with no
   asset anywhere. Option E gets its colour and its letter for engineering time
   only, and gets its silhouette not at all.
3. **Is CC-BY acceptable?** It doubles the reachable wardrobe and it puts an
   attribution obligation into the product. Nothing carries attribution today.
4. **Does the athlete stay one body?** The phenotype is nine numbers and the
   installed library has 23 skins. This is the cheapest change of all and it is
   the one nobody has asked for. Netball in South Africa is not one body type,
   and the shipped figure is `race` caucasian 1.0 and a single build.

## 10. What I did not do

- **I downloaded nothing.** No asset pack was fetched, and no marketplace item
  was bought or evaluated in the hand.
- **I did not price the bib.** No source found priced a single fitted garment,
  and inventing that number would be worse than leaving it open.
- **I did not re-open the SMPL-X decision.** The record says it is off the
  product path for a licence reason. If Marius wants it re-opened, that is his
  to say, and `LICENCE-RISK.md` already lists what a commercial licence needs.
- **I rendered `female_sportsuit01` and I changed nothing.** The experiment is
  in section 3. Both files were restored from git and `git status` is clean; the
  only untracked things left are this document and a gitignored output.
- **I did not render the other five shoe sets, the nine unused hair assets, or
  the twenty-two unused skins.** One render answered one question. The rest wait
  on a ruling, because rendering thirty options before anyone has said what the
  figure is for is the wrong order.

## Sources

- [Asset Packs :: MakeHuman Community](https://static.makehumancommunity.org/assets/assetpacks.html)
- [Asset Packs FAQ :: MakeHuman Community](https://static.makehumancommunity.org/assets/assetpacks/faq.html)
- [3D Character Modeling Cost: 2026 Pricing Guide](https://www.mimiccartoon.com/post/3d-character-modeling-cost)
- [How Much Does a 3D Character Model Cost - RetroStyle Games](https://retrostylegames.com/blog/how-much-does-a-3d-character-model-cost/)
- [3D Netball Models - TurboSquid](https://www.turbosquid.com/Search/3D-Models/netball)
