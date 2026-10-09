import unittest
from voice_ai.segment import SpeechSegmenter


class SegmentTests(unittest.TestCase):
    def setUp(self):
        self.segmenter = SpeechSegmenter(
            block_bytes=4, preroll_blocks=2, max_blocks=5,
        )

    def test_preroll_and_voice_end(self):
        s = self.segmenter
        self.assertIsNone(s.accept(b"aaaa", None))
        self.assertIsNone(s.accept(b"bbbb", None))
        self.assertIsNone(s.accept(b"cccc", {"start": 1}))
        self.assertIsNone(s.accept(b"dddd", None))
        pcm = s.accept(b"eeee", {"end": 5})
        self.assertEqual(pcm, b"bbbbccccddddeeee")

    def test_segment_is_bounded(self):
        s = self.segmenter
        s.accept(b"aaaa", {"start": 0})
        for n in range(3):
            self.assertIsNone(s.accept(b"bbbb", None))
        self.assertEqual(s.accept(b"cccc", None), b"aaaa" + b"bbbb" * 3 + b"cccc")
        self.assertFalse(s.active)

    def test_short_block_denied(self):
        with self.assertRaises(ValueError):
            self.segmenter.accept(b"x", None)

    def test_reset(self):
        self.segmenter.accept(b"aaaa", {"start": 0})
        self.segmenter.reset()
        self.assertFalse(self.segmenter.active)
        self.assertEqual(len(self.segmenter.frames), 0)


if __name__ == "__main__":
    unittest.main()
