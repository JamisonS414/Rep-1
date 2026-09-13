"""Tests for the parts that don't need ffmpeg/yt-dlp installed."""

import unittest

from clipper import audio, cli
from clipper.util import Candidate, slug, timecode


class TestUtil(unittest.TestCase):
    def test_timecode(self):
        self.assertEqual(timecode(0), "0:00:00")
        self.assertEqual(timecode(61), "0:01:01")
        self.assertEqual(timecode(3725), "1:02:05")
        self.assertEqual(timecode(-5), "0:00:00")

    def test_slug(self):
        self.assertEqual(slug("CRAZY 1v4 clutch!!"), "crazy-1v4-clutch")
        self.assertEqual(slug("!!!"), "clip")
        self.assertLessEqual(len(slug("x" * 200)), 60)

    def test_padding_respects_ceiling(self):
        c = Candidate(100.0, 100.0, 1.0, "peak").padded(30.0, 20.0, ceiling=110.0)
        self.assertEqual((c.start, c.end), (70.0, 110.0))

    def test_padding_clamps_at_zero(self):
        c = Candidate(5.0, 5.0, 1.0, "peak").padded(30.0, 20.0)
        self.assertEqual(c.start, 0.0)


class TestLoudnessParsing(unittest.TestCase):
    def test_parses_normal_line(self):
        m = audio._LINE.search("[Parsed_ebur128_0 @ 0x5] t: 12.3 TARGET:-23 LUFS M: -18.4 S: -21.0")
        self.assertEqual(m.group("t"), "12.3")
        self.assertEqual(m.group("m"), "-18.4")

    def test_ignores_unrelated_lines(self):
        self.assertIsNone(audio._LINE.search("Stream #0:0: Video: h264, yuv420p"))

    def test_percentile_bounds(self):
        vals = list(range(101))
        self.assertEqual(audio._percentile(vals, 0), 0)
        self.assertEqual(audio._percentile(vals, 100), 100)
        self.assertEqual(audio._percentile([], 50), 0.0)

    def test_smooth_flattens_transients(self):
        spike = [-60.0] * 10 + [0.0] + [-60.0] * 10
        smoothed = audio._smooth(spike, 5)
        # a single-sample bang must not survive at full height
        self.assertLess(max(smoothed), -10.0)

    def test_smooth_window_one_is_identity(self):
        vals = [1.0, 2.0, 3.0]
        self.assertEqual(audio._smooth(vals, 1), vals)


class TestCLI(unittest.TestCase):
    def test_scan_defaults(self):
        args = cli.build_parser().parse_args(["scan", "video.mp4"])
        self.assertEqual(args.length, 45.0)
        self.assertEqual(args.mode, "blur")
        self.assertFalse(args.dry_run)

    def test_clips_defaults(self):
        args = cli.build_parser().parse_args(["clips", "itzrealmemc"])
        self.assertEqual(args.days, 30)
        self.assertEqual(args.render, 0)

    def test_bad_mode_rejected(self):
        with self.assertRaises(SystemExit):
            cli.build_parser().parse_args(["scan", "v.mp4", "--mode", "sideways"])

    def test_missing_local_file_exits_two(self):
        self.assertEqual(cli.main(["scan", "/nonexistent/file.mp4"]), 2)


if __name__ == "__main__":
    unittest.main()
