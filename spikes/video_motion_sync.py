"""Align two camera views by what MOVES, not by what is heard.

The audio route failed on session 1.0 and `video_sync.py` records why: there is
no clap in the material, and four correlation methods returned four different
answers with no peak worth the name.

This is the second instrument, and it fails differently on purpose. It reads
pixels rather than sound, so gym reverb, two microphone responses and two
sample rates cannot touch it. What it CAN get wrong is different: a camera that
wobbles, a bystander walking through one view, or a light flickering will all
put motion in one view that is not in the other.

The signal is total frame-to-frame change. During the talking at the top of a
take it is low and flat. When the drill starts it jumps. That shape is the same
seen from the front and from the side even though the pictures share no pixels,
which is what makes it correlate when a raw image never would.

TIMESTAMPS, NOT FRAME INDICES. The side cameras are variable rate: measured at
30.012 fps against the front's exact 30.000, which is 11 to 13 ms of drift by
the end of a half-minute clip. Every sample here carries its own presentation
timestamp read from the container, and the correlation runs on a common time
grid built from those.

    pixi run python video_motion_sync.py
"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import numpy as np

SPIKE_DIR = Path(__file__).resolve().parent
SAMPLES = Path("F:/Repositories/braven-movement/.assets/video-samples/session-1.0")
OUTPUT = SPIKE_DIR / "poc-output" / "video"

# Small enough that the correlation is cheap and large enough that an arm still
# covers several pixels. Motion energy does not need detail.
WIDTH = 64
# The common grid both views are resampled onto. 200 Hz is five times the frame
# rate, so the peak can land between frames rather than being quantised to one.
GRID_RATE = 200.0
# A tenth of a second of guard either side of the peak, when measuring how far
# the peak stands above everything else.
GUARD_SECONDS = 0.5


def timestamps(path: Path) -> np.ndarray:
    """Presentation timestamps of every video frame, in seconds."""
    done = subprocess.run(
        [
            "ffprobe", "-v", "error", "-select_streams", "v:0",
            "-show_entries", "frame=pts_time", "-of", "csv=p=0", str(path),
        ],
        capture_output=True,
        text=True,
        check=True,
    )
    return np.array(
        [float(line.strip().rstrip(",")) for line in done.stdout.splitlines() if line.strip()]
    )


def scaled_height(path: Path, width: int) -> int:
    """The height ffmpeg actually produces at this width, after rotation.

    Read off a real decoded frame rather than reasoned about. The rotation
    metadata on the front cameras means the container's width and height are
    not the decoded ones, and a tool that assumes otherwise gets sideways
    frames — the second of the traps on this material.
    """
    done = subprocess.run(
        [
            "ffmpeg", "-v", "error", "-i", str(path), "-frames:v", "1",
            "-vf", f"scale={width}:-1,format=gray", "-f", "image2pipe",
            "-vcodec", "png", "-",
        ],
        capture_output=True,
        check=True,
    )
    # PNG: the IHDR width and height are big-endian at bytes 16 and 20.
    import struct

    found_width, found_height = struct.unpack(">II", done.stdout[16:24])
    if found_width != width:
        raise RuntimeError(f"{path.name}: asked for width {width}, got {found_width}")
    return int(found_height)


def motion(path: Path, width: int = WIDTH) -> np.ndarray:
    """Mean absolute change between consecutive frames, one value per frame.

    Grey, tiny, and through ffmpeg so the rotation metadata is applied. The
    height is whatever the aspect makes it, which differs between the cameras
    and does not matter: the value is a mean, so it is comparable.
    """
    done = subprocess.run(
        [
            "ffmpeg", "-v", "error", "-i", str(path),
            "-vf", f"scale={width}:-1,format=gray",
            "-f", "rawvideo", "-pix_fmt", "gray", "-",
        ],
        capture_output=True,
        check=True,
    )
    raw = np.frombuffer(done.stdout, dtype=np.uint8)
    height = scaled_height(path, width)
    frames = len(raw) // (width * height)
    stack = raw[: frames * width * height].reshape(frames, height, width).astype(np.int16)
    return np.abs(np.diff(stack, axis=0)).mean(axis=(1, 2))


def on_grid(times: np.ndarray, values: np.ndarray, rate: float = GRID_RATE):
    """Resample an irregular series onto an even time grid by interpolation."""
    start, end = times[0], times[-1]
    grid = np.arange(start, end, 1.0 / rate)
    return grid, np.interp(grid, times, values)


def align(first, second, rate: float = GRID_RATE) -> dict:
    a = first - first.mean()
    b = second - second.mean()
    a = a / (np.linalg.norm(a) or 1.0)
    b = b / (np.linalg.norm(b) or 1.0)
    size = 1 << int(np.ceil(np.log2(len(a) + len(b))))
    joined = np.fft.irfft(np.fft.rfft(a, size) * np.conj(np.fft.rfft(b, size)), size)
    joined = np.concatenate((joined[-(len(b) - 1):], joined[: len(a)]))
    lags = np.arange(-(len(b) - 1), len(a))
    best = int(np.argmax(joined))
    guard = max(1, int(GUARD_SECONDS * rate))
    masked = joined.copy()
    masked[max(0, best - guard) : best + guard] = -np.inf
    sidelobe = float(np.max(masked))
    return {
        "offsetMs": float(lags[best]) * 1000.0 / rate,
        "peak": float(joined[best]),
        "peakToSidelobe": float(joined[best] / sidelobe) if sidelobe > 1e-12 else float("inf"),
    }


def halves(times, values):
    """The same measurement on the first and second half of the clip.

    Two events far apart measure DRIFT, which one event cannot. If the two
    halves disagree, the two cameras are running at different rates and a
    single offset is not enough to align them.
    """
    middle = len(values) // 2
    return (times[:middle], values[:middle]), (times[middle:], values[middle:])


def main(argv: list[str]) -> int:
    found = []
    for name in ("0.1", "0.2"):
        front, side = SAMPLES / f"front {name}.mp4", SAMPLES / f"side {name}.mp4"
        if not (front.exists() and side.exists()):
            continue
        entry = {"set": name}
        pairs = {}
        for label, path in (("front", front), ("side", side)):
            stamps = timestamps(path)
            energy = motion(path)
            count = min(len(stamps) - 1, len(energy))
            # A difference belongs to the LATER of the two frames it came from.
            pairs[label] = (stamps[1 : count + 1], energy[:count])
            entry[f"{label}Frames"] = int(count)

        grid_front, on_front = on_grid(*pairs["front"])
        grid_side, on_side = on_grid(*pairs["side"])
        whole = align(on_front, on_side)
        # The grids start at each file's own first timestamp, so the lag has to
        # be corrected by the difference between those starts.
        base = grid_front[0] - grid_side[0]
        whole["offsetMs"] += base * 1000.0
        entry["whole"] = whole

        parts = []
        for piece_front, piece_side in zip(halves(*pairs["front"]), halves(*pairs["side"])):
            gf, vf = on_grid(*piece_front)
            gs, vs = on_grid(*piece_side)
            piece = align(vf, vs)
            piece["offsetMs"] += (gf[0] - gs[0]) * 1000.0
            parts.append(piece)
        entry["firstHalf"], entry["secondHalf"] = parts
        entry["driftMs"] = round(parts[1]["offsetMs"] - parts[0]["offsetMs"], 2)
        found.append(entry)

    for entry in found:
        print(f"\nset {entry['set']}   {entry['frontFrames']} front frames against "
              f"{entry['sideFrames']} side frames")
        for label in ("whole", "firstHalf", "secondHalf"):
            one = entry[label]
            print(f"  {label:12s} offset {one['offsetMs']:+9.1f} ms   "
                  f"peak {one['peak']:.4f}   peak/sidelobe {one['peakToSidelobe']:6.2f}")
        print(f"  half to half the offset moves {entry['driftMs']:+.1f} ms")

    print(
        "\nPositive means the event happens LATER in the side file, so a side\n"
        "timestamp minus this offset lands on the front camera's clock.\n"
        "A peak/sidelobe near 1 means there is no peak and the number is not a\n"
        "measurement, whatever it says."
    )

    OUTPUT.mkdir(parents=True, exist_ok=True)
    where = OUTPUT / "motion-offsets.json"
    where.write_text(json.dumps(found, indent=2) + "\n", encoding="utf-8")
    print(f"\nwritten -> {where}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
