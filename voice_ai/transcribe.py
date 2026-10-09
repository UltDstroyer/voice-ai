"""whisper.cpp offline transcription via its documented whisper-cli interface."""

from __future__ import annotations

import subprocess
import tempfile
import wave
from pathlib import Path


def write_pcm16(path: Path, frames: bytes, sample_rate: int = 16000) -> None:
    if len(frames) % 2:
        raise ValueError("PCM16 requires an even byte count")
    with wave.open(str(path), "wb") as handle:
        handle.setnchannels(1)
        handle.setsampwidth(2)
        handle.setframerate(sample_rate)
        handle.writeframes(frames)


class WhisperCLI:
    def __init__(self, binary: str, model: str, timeout: int = 90):
        if not model or not Path(model).is_file():
            raise FileNotFoundError("Download and configure a whisper.cpp ggml model first")
        self.binary, self.model, self.timeout = binary, model, timeout

    def transcribe(self, frames: bytes) -> str:
        if not frames:
            return ""
        with tempfile.TemporaryDirectory(prefix="ctx-voice-stt-") as d:
            root = Path(d)
            audio, out = root / "utterance.wav", root / "speech"
            write_pcm16(audio, frames)
            args = [
                self.binary, "-m", self.model, "-f", str(audio),
                "-otxt", "-of", str(out), "-nt", "-np",
            ]
            result = subprocess.run(
                args, stdin=subprocess.DEVNULL, capture_output=True,
                text=True, timeout=self.timeout, check=False,
            )
            if result.returncode:
                raise RuntimeError("whisper.cpp failed: " + result.stderr[-1000:])
            transcript = out.with_suffix(".txt")
            if not transcript.is_file():
                raise RuntimeError("whisper.cpp produced no transcript")
            return transcript.read_text(encoding="utf-8").strip()[:3000]
