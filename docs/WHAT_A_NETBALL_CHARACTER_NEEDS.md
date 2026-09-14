# What a netball character needs

Stage 1, item 2 of the character and animation lane. Read on 2026-09-09 against
`0528935`. The rendered figures are this build's own, not the archive's.

The brief asks what the sport's own figures look like, and what the current
character gets wrong against them. Item 1 called the kit a judgment. This makes
it a description with evidence.

## 1. The method, and its limit

The manual is 728 images and one converted markdown file. Four opened images
cannot answer what is in it, so the population was counted first.

`scripts/manual_figure_census.py` measures the share of each image that is page
white, and reports the distribution rather than a verdict. The population is
bimodal: 623 images sit below 0.4 and 82 sit above 0.7, and the middle band from
0.4 to 0.7 holds 23 of the 728. The boundary at 0.55 therefore sits in the
trough and is not a tuned number.

    728 images
    DRAWN ON THE PAGE (>= 55% white):  92   median  263 kpx
    PHOTOGRAPHED      (<  55% white): 636   median   67 kpx

**I opened 10 of the 728.** The cover, the four largest photographs, the two
largest drawn figures, the two figures beside the chest-pass drill, and the
photograph that opens CATCHING. That is a sample and it is stated as one.

**The discriminator is guarded, and the guard was proved failing.** Eight tests
in `tests/test_manual_figure_census.py` build their own images rather than read
the manual, so none of them skips on a machine without it. Six mutations were
applied and each was killed by a named test.

**One mutation survived the first round, and the test set was wrong, not the
code.** Averaging the three channels instead of requiring all three passed every
test, because the yellow used to check saturation has an average far below the
threshold anyway. The two rules only disagree on a colour whose average is above
the threshold while one channel is below it. `(255, 255, 230)` is such a colour,
and the test that uses it exists for that reason.

**A second mutation was a broken experiment rather than a surviving one.** It
inserted a statement that changed no behaviour, so it tested nothing under its
own name. It was rewritten to actually count every pixel as white, and it is now
killed by six tests. A mutation string that stops doing what its label says runs
a different experiment under the old name.

## 2. What the manual's own figures are

**The manual has no figure that shows how a body performs a technique.** It has
two kinds of picture and neither is one.

- **92 drawn figures are court plans.** Players are top-down clip-art tokens: a
  brown head seen from above, blue shoulders, a small ball. They say where a
  player stands and where the ball goes. The two largest, on pages 133 and 169,
  are a full court and a small grid, both with the same tokens.
- **636 photographs are sessions and atmosphere.** Training on outdoor courts,
  gym work, coaches, and motivational images. They are section dividers, not
  instruction.

The technique itself is carried in the text. The CATCHING section lists the
skills by name and then describes drills in numbered steps.

**That is the gap this lane's figures fill.** The rendered library is not
competing with an illustration standard in the manual, because the manual has
none. It is supplying the thing the manual leaves to the coach's own
demonstration.

## 3. The sport's own figure, from the photograph that opens CATCHING

Page 69, the photograph directly under the heading `## Catching` and above the
skill list. It is the manual's own answer to what a catching netballer looks
like.

| | The photograph |
|---|---|
| kit | A fitted sleeveless dress over fitted shorts. Bare arms and shoulders. |
| bib | Worn over the dress, with the position letter **C** and sponsor panels. |
| hair | Tied up in a bun, clear of the neck and shoulders. |
| footwear | High-cut white court shoes, laced over the ankle, with LOW socks. |
| support | Strapping on the catching wrist. |
| build | Lean, long-limbed, with visible shoulder and upper-back definition. |
| ball | White, a Gilbert match ball. |
| ground | Indoor wooden court, crowd behind, dark surround. |
| pose | A one-handed catch at full stretch, trailing leg behind, about to land. |

The training photographs elsewhere in the manual show a different register:
singlets and crop tops, black shorts or skirts, high crew socks, white trainers,
ponytails, outdoor courts in daylight. **Match kit and training kit are two
answers, and the manual contains both.** Which one a coach figure should wear is
a decision, not a fact, and it belongs in item 3.

## 4. What the current character gets wrong

Rendered on this branch: `netball_chest_pass`, phase `ready`, side view,
receipt naming `9ea602b` with a clean tree. Refer to `out/kit-comparison.png`,
which is written to a gitignored directory and is NOT committed, because the
manual photograph beside it is third-party and carries a credit.

| | The character | The photograph | Where it is set |
|---|---|---|---|
| kit | Grey t-shirt WITH SLEEVES and loose shorts | Sleeveless fitted dress | `female_casualsuit02.mhclo` |
| bib | None | Position bib, letter C | no asset exists |
| hair | A long loose ponytail, well below the shoulder | A bun, off the neck | `ponytail01.mhclo` |
| footwear | Low trainers, dark heel | High-cut court shoes | `shoes05.mhclo` |
| socks | High crew socks | Low socks | part of `shoes05` |
| ball | Coral and teal | White | `create_panelled_netball`, presentation config |
| ground | Grey studio, black upper wall | Wooden court | presentation config |

**Every row is a configuration value or an asset path.** Not one of them needs a
new mesh, which is what item 1 section 2 established and what makes item 3 a
cheap decision rather than a modelling project.

**Two rows are not equal in cost.** The bib has no asset at all and is the only
row that needs something made or bought. Every other row is a swap.

**One thing a coach would call wrong that is NOT in the table.** The character's
phenotype carries `muscle` 0.88, which is high, and the render still reads soft
against the photograph's visible shoulder and back definition. Whether that is
the phenotype, the skin material, or the four-light studio rig is UNMEASURED,
and I am not guessing. It is a judgment until somebody varies one of the three
and renders it.

## 5. What this is not

- **It is not a ruling on kit.** Match kit and training kit are both in the
  manual. Item 3 puts the options to Marius.
- **It does not license anything.** The manual's photographs are third-party
  with a visible photographer's credit, and they are evidence for a reader
  inside this project, never a source for an asset. That constraint is an input
  to item 3, not a conclusion of item 2.
- **It says nothing about the pose.** The photograph is a one-handed catch at
  full stretch and the render is a chest-pass ready. The comparison is of kit,
  hair, footwear, ball and ground, and pairing two different actions would be
  the error this repository already names: a name is not a correspondence.

## 6. One question for the content lane, raised and not answered

The manual's CATCHING list names eleven skills. The engine's library renders
eight drills in total, of which some carry the same words. **I have not paired
them**, because pairing by label is exactly the mistake this repository has paid
for, and the pairing would have to be made on what the movement actually does.
Whether the library covers the manual's catching list, and what is missing, is a
question for whoever owns the library's content. It is recorded here so that it
is asked rather than assumed.

## 7. How to reproduce section 1

    python scripts/manual_figure_census.py
    python scripts/manual_figure_census.py --list diagram

The manual is junctioned into `references/` from the repository root
`.assets/manual`. It is not in git.
