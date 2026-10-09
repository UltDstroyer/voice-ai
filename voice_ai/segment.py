"""Audio segmentation using Silero event boundaries; pure-Python logic is testable."""

from collections import deque


class SpeechSegmenter:
    """Accept 16-bit mono 16-kHz audio in frames, plus VAD start/end markers.

    Marker events are {"start": sample_index} or {"end": sample_index}.
    A bounded pre-roll prevents clipping the beginning of speech.
    """

    def __init__(self, block_bytes: int = 1024, preroll_blocks: int = 16,
                 max_blocks: int = 16 * 60):
        self.block_bytes = block_bytes
        self.pre = deque(maxlen=preroll_blocks)
        self.max_blocks = max_blocks
        self.active = False
        self.frames: list[bytes] = []

    def accept(self, frame: bytes, marker: dict | None) -> bytes | None:
        if len(frame) != self.block_bytes:
            raise ValueError("Unexpected microphone frame size")
        if not self.active:
            self.pre.append(frame)
            if marker and "start" in marker:
                self.active = True
                self.frames = list(self.pre)
                self.pre.clear()
                return None
            return None
        self.frames.append(frame)
        if marker and "end" in marker or len(self.frames) >= self.max_blocks:
            pcm = b"".join(self.frames)
            self.active = False
            self.frames.clear()
            self.pre.clear()
            return pcm
        return None

    def reset(self):
        self.active = False
        self.pre.clear()
        self.frames.clear()
