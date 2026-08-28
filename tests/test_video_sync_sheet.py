"""Guards for the two places the sync sheet can lie about time.

The sheet exists to be believed about WHEN each picture was taken. Both faults
below produce a sheet that looks correct, carries confident labels, and is
wrong by about one frame, which is the size of the thing it is measuring.
"""

import sys
import unittest
from pathlib import Path

MODULE_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(MODULE_DIR / "scripts"))

from video_sync_sheet import (  # noqa: E402
    choose_nearest,
    degraded,
    pair_stamps_to_images,
    sample_times,
)


class SyncSheetTimeTest(unittest.TestCase):
    def test_the_extra_showinfo_timestamp_is_dropped_from_the_end(self):
        """ffmpeg reports more frames than it writes, and the extra is last.

        showinfo prints every frame the DECODER reads. `-frames:v N` stops the
        writer at N. Measured on the sample material: 5 timestamps, 4 files.
        Trimming from the wrong end shifts every label by one frame, so every
        picture on the sheet carries the time of its neighbour. The sheet would
        report about 33 ms of error that is not in the video.
        """
        stamps = [8.962978, 8.9964, 9.029722, 9.063044, 9.096367]

        kept = pair_stamps_to_images(stamps, 4)

        self.assertEqual([8.962978, 8.9964, 9.029722, 9.063044], kept)
        self.assertEqual(stamps[0], kept[0], "the FIRST file keeps the FIRST stamp")

    def test_the_frame_nearest_the_target_wins_even_when_it_is_earlier(self):
        """`-ss` serves the first frame at or after T, which is always late.

        On the side clip that ran 25 to 30 ms behind every request, against a
        33.3 ms frame. Always late is a BIAS, not noise: it moves one camera
        later than the other on every pair of the sheet, and a reader would see
        that as the sync being wrong.
        """
        stamps = [8.962978, 8.9964, 9.029722, 9.063044]

        # 8.9964 is 3.6 ms before the target; 9.029722 is 29.7 ms after it.
        self.assertEqual(1, choose_nearest(stamps, 9.000))
        # And the rule holds when the nearest frame is genuinely the later one.
        self.assertEqual(2, choose_nearest(stamps, 9.020))

    def test_a_negative_offset_never_asks_for_a_time_before_the_side_clip(self):
        """A negative offset means the side camera started LATER.

        The first front seconds then have no side frame at all. Asking anyway
        returns the side clip's first frame, which the sheet would label with
        the time requested rather than the time shown, and the mismatch would
        read as a fault in the shoot instead of a fault here.
        """
        times = sample_times(
            front_duration=28.867, side_duration=28.755, offset=-1.0, samples=12
        )

        self.assertTrue(times, "the clips do overlap at this offset")
        for front_time in times:
            self.assertGreaterEqual(
                round(front_time + -1.0, 6), 0.0,
                f"front {front_time:.3f}s maps to a side time before zero",
            )

    def test_no_sample_runs_past_the_end_of_either_clip(self):
        """The tail of a clip is where one camera was already being picked up.

        A sample past the end returns the last frame, or nothing, and either
        way the pair is not two views of one instant.
        """
        front_duration, side_duration, offset = 31.533, 32.987, 0.0

        times = sample_times(front_duration, side_duration, offset, samples=12)

        self.assertTrue(times)
        self.assertLessEqual(max(times), front_duration)
        self.assertLessEqual(max(times) + offset, side_duration)

    def test_a_smeared_or_dark_frame_is_named_as_not_footage(self):
        """A picture taken while the camera was lifted is not evidence.

        This lane read an overhead pose off a front frame at 21 percent of its
        clip's sharpness and reported it as a sync mismatch. The pose was real
        but earlier; the frame was camera handling. The sheet had shown the
        picture and said nothing, so it looked like footage.

        The real numbers from the sample material: good frames sat at 94 to 108
        percent of the clip median, the handling frame at 21 percent, and the
        final dark frame at 0 percent with a luminance of 35 against a normal
        120. Nothing real lies between 50 and 94 percent.
        """
        median = 850.0

        self.assertFalse(degraded(sharpness=0.94 * median, reference=median, luma=121))
        self.assertFalse(degraded(sharpness=1.08 * median, reference=median, luma=116))
        self.assertTrue(degraded(sharpness=0.21 * median, reference=median, luma=123),
                        "the camera-handling frame must be named")
        self.assertTrue(degraded(sharpness=0.0, reference=median, luma=35),
                        "the dark tail must be named")

    def test_a_dark_frame_is_named_even_when_it_is_sharp(self):
        """Darkness and blur are different faults and either one disqualifies.

        A lens covered by a hand can be perfectly sharp and carry no athlete.
        Judging on sharpness alone would pass it.
        """
        self.assertTrue(degraded(sharpness=900.0, reference=850.0, luma=12))

    def test_clips_that_do_not_overlap_produce_no_samples(self):
        """An offset larger than the clip is a caller error, not an empty sheet."""
        self.assertEqual(
            [], sample_times(front_duration=28.0, side_duration=28.0,
                             offset=-40.0, samples=8)
        )


if __name__ == "__main__":
    unittest.main()
