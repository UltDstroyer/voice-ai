"""Explicit microphone capture; no background daemon and no audio retention."""

from __future__ import annotations

from .config import Settings


class Microphone:
    def __init__(self, settings: Settings):
        self.settings = settings
        self._stream = None

    def __enter__(self):
        try:
            import sounddevice as sd
        except ImportError as exc:
            raise RuntimeError("Install sounddevice to use the microphone") from exc
        self._stream = sd.RawInputStream(
            samplerate=self.settings.sample_rate, channels=1,
            dtype="int16", blocksize=512,
        )
        self._stream.start()
        return self

    def read(self) -> bytes:
        if self._stream is None:
            raise RuntimeError("Microphone not active")
        frames, overflowed = self._stream.read(512)
        if overflowed:
            return b"\x00" * 1024
        return bytes(frames)

    def __exit__(self, *_):
        if self._stream is not None:
            self._stream.stop()
            self._stream.close()
            self._stream = None


class SileroStream:
    def __init__(self, settings: Settings):
        try:
            import numpy as np
            import torch
            from silero_vad import VADIterator, load_silero_vad
        except ImportError as exc:
            raise RuntimeError(
                "Install optional VAD dependencies: pip install -e '.[vad]'"
            ) from exc
        torch.set_num_threads(1)
        self.np, self.torch = np, torch
        self.iterator = VADIterator(
            load_silero_vad(), sampling_rate=16000,
            threshold=settings.vad_threshold,
            min_silence_duration_ms=450,
            speech_pad_ms=160,
        )

    def feed(self, frame: bytes) -> dict | None:
        floats = self.np.frombuffer(frame, dtype=self.np.int16).astype(self.np.float32) / 32768.0
        return self.iterator(self.torch.from_numpy(floats), return_seconds=False)

    def reset(self):
        self.iterator.reset_states()
