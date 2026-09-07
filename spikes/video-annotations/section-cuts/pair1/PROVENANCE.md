# Where these digests came from

Each `<section>-<view>.sha256` holds one sha256 per DECODED FRAME, in order,
for one clip of pair 1. `video_section_cuts.frame_digests()` writes them and
`reference_digests()` reads them, so the numbers and the instrument that made
them are in the same commit.

## The clips they were read from

They are **not** this tool's output. They are the clips an earlier instrument
cut on 2026-09-07, outside this repository, under
`.remember/extraction/pair1/` on the orchestrator's machine. That directory is
not in git and is on one machine only, which is why the digests are here: the
test that compares against it used to read that absolute path and skip
everywhere else, and it was the only test that could see three of the
mutations run against this pack.

| clip | file sha256 (first 16) | bytes | frames |
|---|---|---|---|
| catch-rep01-front.mp4 | 1a843e532486fcc9 | 367992 | 55 |
| catch-rep01-side.mp4 | ffbba898c6723516 | 262945 | 55 |
| release-rep09-front.mp4 | 3e219328bf698782 | 391905 | 56 |
| release-rep09-side.mp4 | db759eb3305ee966 | 263740 | 56 |
| hold-rep09-front.mp4 | 2a6e9f8487da27ef | 428531 | 62 |
| hold-rep09-side.mp4 | 3966da63a0c9a7f8 | 274343 | 62 |
| ready-between-front.mp4 | f3f9aab0f2eb95db | 255941 | 47 |
| ready-between-side.mp4 | a02c842341840626 | 179313 | 47 |

440 frames in total.

## How to read them again

```bash
python -c "import video_section_cuts as c; print('\n'.join(c.frame_digests(__import__('pathlib').Path('F:/Repositories/braven-movement/.remember/extraction/pair1/catch-rep01-front.mp4'))))"
```

## What the comparison proves, and what it does not

It proves REPRODUCTION: this tool and the earlier instrument produce the same
pictures. Both were given the same windows and the same frame offset, so if
both mapped an index wrongly, all 440 rows would still agree.

Correctness is answered elsewhere, against the RECORDINGS: every clip frame
must be closer to the source frame it claims than to either neighbour, with
the source frames selected by `select='between(n,a,b)'` rather than by the
`trim` the cut uses. Refer to the comment above `RELATIVE_MARGIN_DB` in
`video_section_cuts.py`.

Frames, not bytes. Two encodes of the same pictures differ in bytes for
reasons that have nothing to do with what they show.
