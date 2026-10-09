"""Optional offline TTS backends, loaded only on explicit user requests."""

from __future__ import annotations

import subprocess
import threading
from pathlib import Path

from .config import Settings


class PiperSpeech:
    def __init__(self, settings: Settings):
        if not settings.piper_model or not Path(settings.piper_model).is_file():
            raise FileNotFoundError("Configure a local Piper .onnx voice model")
        self.settings = settings

    def render(self, text: str, output: Path) -> Path:
        if not text.strip() or len(text) > 4000:
            raise ValueError("Speech text must be 1..4000 characters")
        args = [
            self.settings.piper_binary, "--model", self.settings.piper_model,
            "--output_file", str(output),
        ]
        result = subprocess.run(
            args, input=text, text=True, capture_output=True,
            timeout=self.settings.tts_timeout, check=False,
        )
        if result.returncode or not output.is_file():
            raise RuntimeError("Piper synthesis failed: " + result.stderr[-1000:])
        return output


class ChatterboxSpeech:
    """Chatterbox Turbo on CUDA/ROCm via the torch.cuda device interface."""

    def __init__(self, settings: Settings):
        self.settings = settings
        self._model = None
        self._lock = threading.Lock()

    def load(self):
        if self._model is not None:
            return self._model
        try:
            import torch
            from chatterbox.tts_turbo import ChatterboxTurboTTS
        except ImportError as exc:
            raise RuntimeError(
                "Install a compatible Chatterbox Turbo + Torch environment; "
                "see docs/BACKENDS.md"
            ) from exc
        device = "cuda" if torch.cuda.is_available() else "cpu"
        self._model = ChatterboxTurboTTS.from_pretrained(device=device)
        return self._model

    def render(self, text: str, output: Path) -> Path:
        if not text.strip() or len(text) > 4000:
            raise ValueError("Speech text must be 1..4000 characters")
        with self._lock:
            model = self.load()
            kwargs = {}
            if self.settings.voice_reference:
                ref = Path(self.settings.voice_reference).expanduser()
                if not ref.is_file() or ref.is_symlink():
                    raise ValueError("Voice reference missing or symlinked")
                kwargs["audio_prompt_path"] = str(ref)
            audio = model.generate(text, **kwargs)
            import torchaudio
            torchaudio.save(str(output), audio.detach().cpu(), model.sr)
            return output


def make_speech(settings: Settings):
    if settings.tts_engine == "chatterbox":
        return ChatterboxSpeech(settings)
    if settings.tts_engine == "piper":
        return PiperSpeech(settings)
    raise ValueError("Unrecognized TTS backend")


class AudioPlayer:
    """Local playback with immediate stop for barge-in."""

    def __init__(self):
        self.lock = threading.RLock()
        self.active = False

    def play(self, path: Path, interrupted: threading.Event):
        try:
            import sounddevice as sd
            import soundfile as sf
        except ImportError as exc:
            raise RuntimeError("Install audio extras for playback") from exc
        data, rate = sf.read(path, dtype="float32")
        with self.lock:
            if interrupted.is_set():
                return
            self.active = True
            sd.play(data, samplerate=rate, blocking=False)
        try:
            while True:
                stream = sd.get_stream()
                if stream is None or not stream.active:
                    break
                if interrupted.wait(0.04):
                    break
        finally:
            self.stop()

    def stop(self):
        with self.lock:
            try:
                import sounddevice as sd
                sd.stop()
            except ImportError:
                pass
            self.active = False
