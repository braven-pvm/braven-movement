# Where the anchor-sheet tile digests came from

Each `pair<N>/<kind>-<index>.sha256` holds fourteen digests, one per tile of
one sheet: the front row left to right, then the side row. `sheet_tiles()` in
`video_anchor_sheets.py` writes them and reads them, by cropping a FINISHED
SHEET into seven columns and two rows and hashing each tile's RGB pixels.

Cropping the delivered sheet, rather than hashing an intermediate file, is
what makes the comparison below possible at all: the same measurement can be
taken on a sheet this tool did not draw.

## pair2 — pinned against sheets a person read

These are **not** this tool's output. They are the three sheets the
orchestrator drew and read on 2026-09-07 to confirm pair 2's frame offset of
−78, in `.remember/extraction/pair2/`, which is not in git and is on one
machine.

| committed as | read from | centre | kind |
|---|---|---|---|
| `pair2/anchor-324.sha256` | `catch-1-anchor-proof.png` | front 324 / side 246 | anchor |
| `pair2/check-484.sha256` | `catch-2-anchor-proof.png` | front 484 / side 406 | check |
| `pair2/anchor-635.sha256` | `catch-3-anchor-proof.png` | front 635 / side 557 | anchor |

42 tiles in total, and 84 across both pairs. Re-derive them with
`.remember/review-instruments/video-anchor-sheets/A2-tile-provenance.py`.

**The names changed and the pictures did not.** The instrument that drew them
called all three `catch-N` and its docstring called all three anchors. `PAIRS`
records 324 and 635 as the anchors the offset was FITTED to, and 484 as a
CHECK the fitted offset had to explain afterwards. Same sheets, honest names.

## pair1 — pinned after a person read them, and the difference matters

Pair 1's three sheets are in `.remember/extraction/pair1-anchors/`, and unlike
pair 2's they were **drawn by this tool**. They were held unpinned until the
orchestrator read all three by eye on 2026-09-08 and confirmed the offset of
−5 on the pictures:

| sheet | what was seen |
|---|---|
| `anchor-274` | the ball reaching her hands in column four of BOTH rows (front 274, side 269), and the gap still there in column three of both |
| `anchor-605` | the same in column four (front 605 with the ball above at 603; side 600 with the ball above at 598) |
| `check-534` | the hands meeting in column four of both rows (front 534, side 529), apart in column three |

Three moments about 11 seconds apart, all agreeing.

**WHAT THE PIN PROVES HERE IS NARROWER THAN FOR PAIR 2, AND THE WORDING IS NOT
DECORATION.** Pair 2's sheets came from an instrument outside this repository,
so matching them is agreement between two tools. Pair 1's came from this tool,
so matching them is this tool agreeing with itself: a change-detector. It
catches an accidental change to the pipeline, the font, the scaler or the
frames, and it catches nothing about whether −5 is right.

What makes −5 right is the reading in the table above. The digests exist so
that nobody has to read the same sheet twice, and so that a sheet which has
quietly stopped showing what was read fails loudly.

## What the tiles depend on besides the frames

**The label is rendered into the picture.** `drawtext` burns
`FRONT idx 318  t=10.600s` into the top-left of each tile, so a committed
digest depends on the text, the size, the box and the font file as much as on
the frame.

- ffmpeg: `8.1.2-full_build-www.gyan.dev`
- font: `C:/Windows/Fonts/arialbd.ttf`, 989780 bytes,
  sha256 `e8f4e3baf6cc35fed6fcce3a540e8b39e8f6cda1d22a28f2ec8f526fef7a43f5`
- rendered at `scale=-2:360`, `fontsize=20`, `box=1:boxcolor=black@0.6:boxborderw=6`

`check_font()` refuses by name when that file is absent, rather than letting
ffmpeg fall back to another face: a fallback would fail all 84 pinned tiles
with a message about the pictures, which is the wrong place to go looking.

### The label runs past the edge of the tile

A tile is 202 px wide and `FRONT idx 268  t=8.933s` at fontsize 20 does not
fit, so the seconds read truncated on the picture as `t=8.9`. This is true of
every sheet under both pairs, including the three that were confirmed before
this tool existed, because it is the same chain.

**What is cut off is not the measurement.** The frame INDEX is fully visible
on every tile, and a pairing is made of indices. The seconds are derived from
each file's own pts, drift about 11 microseconds a frame between the two
cameras, and the manifest carries them in full.

It is left alone because every fix costs more than it buys. A smaller font or
a caption band changes the pixels, so all 84 tile digests would need re-pinning
against sheets nobody has read, which cuts the tie to the artefacts that were
actually confirmed. A second, legible sheet would be an artefact with no pin
at all. Any change to the label format fails the pins loudly, which is right.

The same caution as the posters applies to the decoder. H.264 decoding is
exact, so which FRAME a tile shows is a property of the recording. The PNG the
tile is written to is lossless, so the pixels are exact too — but the scaler
and the text renderer are ffmpeg's, and a different build could move them.

## What a sheet proves, and what it does not

A sheet is read by a person. If the offset is right, the gap-then-contact
transition falls in the SAME COLUMN in both rows. That is the one check on a
frame offset that shares nothing with the arithmetic that produced it.

Matching the pinned digests proves this tool draws the pictures somebody
confirmed. It does not re-confirm the pairing: only a person looking does
that, and these digests exist so nobody has to look twice at the same sheet.
