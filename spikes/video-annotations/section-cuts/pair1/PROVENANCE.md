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

## The posters

`<section>-<view>-poster.sha256` holds ONE digest: the DECODED PIXELS of the
poster frame. The eight files they were read from are the JPEGs already on
Erin's page, in `.remember/erin-page/erin-stage/video-clips-v2/`, rendered by
`build_v13.py` from the recordings at each section's poster index with
`-q:v 3`.

The FILE is not what is pinned. A JPEG re-encoded at a different quality
setting changes every byte while showing the same picture, and a JPEG of the
WRONG frame re-encoded at the same setting changes none of the things a file
hash would notice. The manifest carries both hashes for each poster, because
they answer different questions: the file hash finds a poster swapped in the
directory, the frame digest finds a poster showing the wrong instant.

| poster | index | file sha256 (first 16) | bytes |
|---|---|---|---|
| catch-rep01-front | 276 | 495b6fba570acfe1 | 74054 |
| catch-rep01-side | 271 | 7d05db7ddf6dda7e | 43345 |
| release-rep09-front | 619 | e4d9b69453c9c6bc | 72487 |
| release-rep09-side | 614 | 4c7efd3c6e5e9151 | 42908 |
| hold-rep09-front | 673 | 221cdf02ea557eb5 | 69238 |
| hold-rep09-side | 668 | af2a7cd34830d8bb | 42484 |
| ready-between-front | 560 | 0547b5184bb68d2f | 77813 |
| ready-between-side | 555 | 66e8950cadc9c7c9 | 44049 |

Rendering the same frames here at the same `-q:v 3` produces BYTE-IDENTICAL
files, measured on both views before the setting was written into the tool.
That is why `POSTER_QUALITY` is 3 and not a number chosen for looking round.

## The build these poster pins were taken on

`ffmpeg version 8.1.2-full_build-www.gyan.dev`

IT MATTERS FOR THE POSTERS AND NOT FOR THE CLIPS. H.264 decoding is exact, so
the clip digests above are a property of the recordings. JPEG is not: the
standard allows a tolerance in the inverse transform, and the mjpeg encoder's
own transform can differ between builds. A different ffmpeg could therefore
fail `test_every_poster_matches_the_digest_committed_for_it` on the RIGHT
frame, with a message saying the poster shows a different frame from the one
committed for it.

That has not happened. The version is written here so that if it ever does,
the first thing anybody checks is the build rather than the frame.

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
