"""Guards for the overlay's four rules, and for the import that broke CI.

The overlay is the instrument a person grades by eye, so its faults are the
kind an eye cannot catch: a skeleton drawn from the wrong frame, a view placed
on the wrong clock, or a topology invented rather than read. Each one produces
a confident picture.
"""

import json
import subprocess
import tempfile
import sys
import unittest
from pathlib import Path

MODULE_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(MODULE_DIR / "scripts"))

from keypoint_overlay import (  # noqa: E402
    check_sync_direction,
    edges_for,
    frame_nearest,
    reference_to_local,
    sync_offset,
)

EDGES = [["left_shoulder", "left_elbow"], ["left_elbow", "left_wrist"]]


def side_file(offset=1.0, worked=None):
    return {
        "source": {"view": "side", "videoFile": "side 0.1.mp4"},
        "model": {"tool": "mediapipe", "landmarkEdges": EDGES},
        "sync": {
            "referenceView": "front",
            "offsetSecondsToReference": offset,
            **({"worked": worked} if worked else {}),
        },
        "frames": [],
    }


class SyncDirectionTest(unittest.TestCase):
    def test_the_sign_error_from_the_schema_is_refused(self):
        """The exact defect found in the schema this morning, made mechanical.

        The two lanes define their offsets in opposite directions, each one
        unambiguous alone. Written down together without a worked example, the
        schema's first draft carried -1.1 with a note saying to ADD it, which
        moves a side timestamp 2.1 s the WRONG way and lands inside real
        footage, so nothing throws.

        Prose about direction is what failed. This reads the file's own
        numbers.
        """
        wrong = side_file(offset=-1.0, worked={
            "thisViewSeconds": 8.25, "referenceViewSeconds": 9.25,
        })

        with self.assertRaises(SystemExit) as refusal:
            check_sync_direction(wrong, Path("side.json"))

        message = str(refusal.exception)
        self.assertIn("8.25", message)
        self.assertIn("9.25", message)
        self.assertIn("a viewer must not pick", message)

    def test_the_working_sign_passes(self):
        right = side_file(offset=1.0, worked={
            "thisViewSeconds": 8.25, "referenceViewSeconds": 9.25,
        })

        check_sync_direction(right, Path("side.json"))  # must not raise

    def test_a_file_with_no_worked_example_is_not_invented_for(self):
        """Absence of the check is not a failure of it.

        The field is new. A file without it must load, and must not be given a
        pass that reads like a measurement either: nothing is asserted here
        because nothing was stated.
        """
        check_sync_direction(side_file(offset=1.0), Path("side.json"))


class UnmeasuredSyncTest(unittest.TestCase):
    """Set 0.2 has no measured offset, and must not be paired as though it had.

    Only set 0.1 carries two matched events. The movement lane records that
    honestly with `measured: false` and a null offset.
    """

    def test_a_default_of_zero_is_a_claim_and_is_never_invented(self):
        """`sync.get(field, 0.0)` says the cameras started together.

        A first version of this did exactly that AND ignored `measured`, so it
        would have paired two unsynchronised views into a picture that looks
        matched. It happened not to, only because the movement lane wrote
        `null` and the arithmetic threw a TypeError. Their defensiveness
        covered for this code; nothing here did.
        """
        self.assertIsNone(sync_offset({"sync": {"measured": False,
                                                "offsetSecondsToReference": 0.0}}))
        self.assertIsNone(sync_offset({"sync": {"offsetSecondsToReference": None}}))
        self.assertIsNone(sync_offset({"sync": {}}))
        self.assertEqual(1.0, sync_offset({"sync": {"offsetSecondsToReference": 1.0}}))

    def test_an_unmeasured_view_refuses_the_reference_clock(self):
        """It must say why, and what to do, not raise a TypeError on None."""
        unmeasured = {
            "source": {"view": "side"},
            "sync": {"referenceView": "front", "measured": False,
                     "offsetSecondsToReference": None},
        }

        with self.assertRaises(SystemExit) as refusal:
            reference_to_local(unmeasured, 9.0)

        message = str(refusal.exception)
        self.assertIn("no measured offset", message)
        self.assertIn("--local", message)
        self.assertIn("never been lined up", message)

    def test_the_reference_view_needs_no_offset_to_be_drawn(self):
        """Its own clock IS the reference, measured or not.

        Set 0.2's front file says `measured: false` and is still the reference
        view, so a single-view overlay of it must work.
        """
        front = {
            "source": {"view": "front"},
            "sync": {"referenceView": "front", "measured": False,
                     "offsetSecondsToReference": 0.0},
        }

        self.assertAlmostEqual(12.0, reference_to_local(front, 12.0), places=9)

    def test_a_file_with_no_measured_offset_still_loads(self):
        """The direction check must not fire on an offset that is not stated.

        A file that records honestly that nobody has measured it must LOAD, or
        a single view of set 0.2 could never be drawn at all.
        """
        check_sync_direction(
            {"source": {"view": "side"},
             "sync": {"referenceView": "front", "measured": False,
                      "offsetSecondsToReference": None,
                      "worked": {"thisViewSeconds": 1.0,
                                 "referenceViewSeconds": 2.0}}},
            Path("side-0.2.json"),
        )


class ClockConversionTest(unittest.TestCase):
    def test_a_reference_time_converts_into_the_other_view_s_clock(self):
        """9.25 on the front's clock is 8.25 on the side's, for this material.

        Getting this backwards puts the two panels 2 s apart while both labels
        look reasonable, which reads as a shoot fault rather than a viewer one.
        """
        self.assertAlmostEqual(
            8.25, reference_to_local(side_file(offset=1.0), 9.25), places=9
        )

    def test_the_reference_view_is_already_on_its_own_clock(self):
        front = {
            "source": {"view": "front"},
            "sync": {"referenceView": "front", "offsetSecondsToReference": 0.0},
        }

        self.assertAlmostEqual(9.25, reference_to_local(front, 9.25), places=9)

    def test_a_reference_view_carrying_a_stray_offset_is_not_shifted(self):
        """Its own clock IS the reference, whatever the field happens to say.

        A file that names itself the reference and also carries an offset is
        inconsistent. Applying the offset would move the one view that defines
        the timeline, so every other view would then be judged against a
        moved reference and the error would be invisible.
        """
        front = {
            "source": {"view": "front"},
            "sync": {"referenceView": "front", "offsetSecondsToReference": 5.0},
        }

        self.assertAlmostEqual(9.25, reference_to_local(front, 9.25), places=9)


class FrameChoiceTest(unittest.TestCase):
    def test_an_undetected_frame_is_never_chosen(self):
        """An undetected frame carries no landmarks at all, by the schema.

        Choosing it draws nothing over a real picture, which looks like an
        athlete the model could not see rather than a frame it was never asked
        about.
        """
        document = {"frames": [
            {"ptsSeconds": 9.20, "detected": False},
            {"ptsSeconds": 9.40, "detected": True},
        ]}

        self.assertEqual(9.40, frame_nearest(document, 9.21)["ptsSeconds"])

    def test_the_nearest_detected_frame_wins_even_when_it_is_earlier(self):
        document = {"frames": [
            {"ptsSeconds": 9.20, "detected": True},
            {"ptsSeconds": 9.40, "detected": True},
        ]}

        self.assertEqual(9.20, frame_nearest(document, 9.24)["ptsSeconds"])

    def test_no_detected_frame_at_all_returns_nothing(self):
        self.assertIsNone(
            frame_nearest({"frames": [{"ptsSeconds": 1.0, "detected": False}]}, 1.0)
        )


class TopologyTest(unittest.TestCase):
    def test_a_file_without_edges_stops_rather_than_inventing_a_skeleton(self):
        """A guessed topology draws a limb through a chest, confidently.

        The landmark NAMES do not say which joints connect. Hardcoding one
        model's connections means the day the model changes, the picture is
        wrong and nothing fails.
        """
        document = {
            "source": {"videoFile": "front 0.1.mp4"},
            "model": {"landmarkNames": ["left_elbow"]},
        }

        with self.assertRaises(SystemExit) as refusal:
            edges_for(document, None)

        self.assertIn("landmarkEdges", str(refusal.exception))

    def test_the_file_s_own_edges_are_used_and_not_marked_as_guessed(self):
        edges, guessed = edges_for(side_file(), None)

        self.assertEqual([("left_shoulder", "left_elbow"),
                          ("left_elbow", "left_wrist")], edges)
        self.assertFalse(guessed)

    def test_an_assumed_topology_is_allowed_but_always_reported_as_assumed(self):
        """A person may override, and the picture then says so.

        The flag exists so a first look is possible before the schema carries
        edges. It must never be silent: the caller gets `guessed` back and the
        overlay stamps it on the image.
        """
        document = {
            "source": {"videoFile": "front 0.1.mp4"},
            "model": {"landmarkNames": ["left_elbow"]},
        }
        assumed = [("left_shoulder", "left_elbow")]

        edges, guessed = edges_for(document, assumed)

        self.assertEqual(assumed, edges)
        self.assertTrue(guessed, "an assumed topology must be reported as assumed")

    def test_the_file_s_edges_beat_an_assumption_that_was_also_offered(self):
        """Data wins. The flag is a fallback and never an override."""
        edges, guessed = edges_for(side_file(), [("nose", "left_eye")])

        self.assertEqual([("left_shoulder", "left_elbow"),
                          ("left_elbow", "left_wrist")], edges)
        self.assertFalse(guessed)


class VideoResolutionTest(unittest.TestCase):
    def test_a_bare_filename_from_the_schema_is_resolved(self):
        """The schema records `"videoFile": "side 0.1.mp4"`, and it is right to.

        A keypoint file describes a RECORDING, not a directory on the disk of
        whoever wrote it. So a reader has to resolve the name, and a first
        version of this treated it as a path and refused every real file.

        Found by reading their schema again while waiting for their data,
        rather than by watching the first real file be refused.
        """
        import keypoint_overlay

        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            (root / "side 0.1.mp4").write_bytes(b"not a real clip")

            found = keypoint_overlay.find_video("side 0.1.mp4", root)

            self.assertEqual(root / "side 0.1.mp4", found)

    def test_a_recording_that_is_nowhere_says_where_it_looked(self):
        """A path error must name the paths, or the reader guesses."""
        import keypoint_overlay

        with tempfile.TemporaryDirectory() as folder:
            with self.assertRaises(SystemExit) as refusal:
                keypoint_overlay.find_video("no such clip.mp4", Path(folder))

        message = str(refusal.exception)
        self.assertIn("no such clip.mp4", message)
        self.assertIn(folder, message)
        self.assertIn("--video-root", message)


class VideoProvenanceTest(unittest.TestCase):
    """The overlay printed where its landmarks came from and never checked it.

    A skeleton drawn over a different recording of the same drill is a body, a
    skeleton, and no relation between them. It looks entirely plausible.
    """

    def test_the_right_recording_verifies(self):
        import keypoint_overlay

        with tempfile.TemporaryDirectory() as folder:
            video = Path(folder) / "side 0.1.mp4"
            video.write_bytes(b"pretend this is a recording")
            digest = keypoint_overlay.sha256_of(video)

            result = keypoint_overlay.verify_video(video, digest)

            self.assertTrue(result["verified"])
            self.assertEqual(digest, result["actual"])

    def test_the_wrong_recording_refuses_rather_than_warns(self):
        """There is no honest picture for a label to make acceptable.

        A stamp works for a guessed topology, because the drawing is still of
        the thing named. Here the drawing is of a different recording, so
        nothing on the page could make it worth looking at.
        """
        import keypoint_overlay

        with tempfile.TemporaryDirectory() as folder:
            video = Path(folder) / "front 0.1.mp4"
            video.write_bytes(b"a different recording")

            with self.assertRaises(SystemExit) as refusal:
                keypoint_overlay.verify_video(video, "0" * 64)

            message = str(refusal.exception)
            self.assertIn("NOT the recording", message)
            self.assertIn("front 0.1.mp4", message)

    def test_a_file_with_no_hash_is_unverified_and_never_verified(self):
        """Absence of a check must not read as a passing check.

        The receipt and the picture both say unverified, which is the honest
        state for a producer that carries no hash.
        """
        import keypoint_overlay

        with tempfile.TemporaryDirectory() as folder:
            video = Path(folder) / "side 0.1.mp4"
            video.write_bytes(b"anything")

            result = keypoint_overlay.verify_video(video, None)

            self.assertIsNone(result["verified"])
            self.assertIsNot(result["verified"], True)


class ImportWithoutPillowTest(unittest.TestCase):
    def test_the_overlay_s_rules_import_with_no_image_library(self):
        """The same failure that turned main red this morning, one file over.

        `keypoint_overlay` draws, so it takes Pillow from `video_sync_sheet`.
        If it took it in a way that requires it at import, every rule above
        becomes unreachable on a runner without Pillow, and the suite reports
        one import error instead of eleven checks.
        """
        script = "\n".join([
            "import sys, importlib.abc",
            "class NoPillow(importlib.abc.MetaPathFinder):",
            "    def find_spec(self, name, path=None, target=None):",
            "        if name == 'PIL' or name.startswith('PIL.'):",
            "            raise ImportError('No module named PIL')",
            "        return None",
            "sys.meta_path.insert(0, NoPillow())",
            f"sys.path.insert(0, {str(MODULE_DIR / 'scripts')!r})",
            "import keypoint_overlay as k",
            "assert k.Image is None, 'Pillow was not actually blocked'",
            "doc = " + json.dumps(side_file(offset=1.0)),
            "assert abs(k.reference_to_local(doc, 9.25) - 8.25) < 1e-9",
            "assert k.edges_for(doc, None)[1] is False",
            "print('ok')",
        ])

        finished = subprocess.run(
            [sys.executable, "-c", script], capture_output=True, text=True
        )

        self.assertEqual(0, finished.returncode,
                         f"the rules must import without Pillow\n{finished.stderr}")
        self.assertIn("ok", finished.stdout)


if __name__ == "__main__":
    unittest.main()
