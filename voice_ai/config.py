"""Configuration uses explicit opt-ins; no stored microphone or dialogue history."""

from __future__ import annotations

import json
import os
from dataclasses import dataclass, fields, replace
from pathlib import Path
from urllib.parse import urlsplit

MODES = ("quiet", "balanced", "maximum")
ENGINES = ("chatterbox", "piper")


def config_path() -> Path:
    root = Path(os.environ.get("XDG_CONFIG_HOME", Path.home() / ".config"))
    return root / "ctx-voice" / "config.json"


def private_config_path(path: Path) -> Path:
    path = path.expanduser()
    if path.is_symlink():
        raise ValueError("Refusing symlinked voice configuration")
    return path


def require_loopback(url: str) -> str:
    parsed = urlsplit(url)
    if (parsed.scheme != "http" or parsed.hostname not in ("127.0.0.1", "localhost")
            or parsed.port != 11434 or parsed.username or parsed.password
            or parsed.path != "/api/chat" or parsed.query or parsed.fragment):
        raise ValueError("Ollama URL must be local http://127.0.0.1:11434/api/chat")
    return url


@dataclass(frozen=True)
class Settings:
    whisper_binary: str = "whisper-cli"
    whisper_model: str = ""
    ollama_url: str = "http://127.0.0.1:11434/api/chat"
    ollama_model: str = "qwen3:8b"
    tts_engine: str = "chatterbox"
    voice_reference: str = ""
    piper_binary: str = "piper"
    piper_model: str = ""
    resource_mode: str = "quiet"
    sample_rate: int = 16000
    max_utterance_seconds: int = 18
    stt_timeout: int = 90
    model_timeout: int = 90
    tts_timeout: int = 120
    max_turns: int = 8
    vad_threshold: float = 0.5

    def validate(self) -> "Settings":
        require_loopback(self.ollama_url)
        if self.resource_mode not in MODES or self.tts_engine not in ENGINES:
            raise ValueError("Unknown engine or resource mode")
        if self.sample_rate != 16000:
            raise ValueError("Silero realtime VAD requires 16 kHz input")
        if not 2 <= self.max_utterance_seconds <= 60:
            raise ValueError("max_utterance_seconds outside 2..60")
        for x in ("stt_timeout", "model_timeout", "tts_timeout"):
            if not 5 <= getattr(self, x) <= 300:
                raise ValueError(x + " timeout outside 5..300")
        if not 1 <= self.max_turns <= 32 or not 0.2 <= self.vad_threshold <= 0.9:
            raise ValueError("Invalid max_turns or vad_threshold")
        for name in ("whisper_binary", "ollama_model", "piper_binary"):
            s = getattr(self, name)
            if not isinstance(s, str) or not s or len(s) > 160:
                raise ValueError("Invalid " + name)
        for name in ("whisper_model", "voice_reference", "piper_model"):
            s = getattr(self, name)
            if not isinstance(s, str) or len(s) > 4096:
                raise ValueError("Invalid " + name)
        return self

    @classmethod
    def load(cls, path: Path | None = None) -> "Settings":
        source = private_config_path(path or config_path())
        if not source.exists():
            return cls().validate()
        payload = json.loads(source.read_text(encoding="utf-8"))
        if not isinstance(payload, dict) or set(payload) - {f.name for f in fields(cls)}:
            raise ValueError("Invalid or unknown voice setting")
        return cls(**payload).validate()

    def save(self, path: Path | None = None) -> Path:
        dest = private_config_path(path or config_path())
        dest.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
        os.chmod(dest.parent, 0o700)
        # Atomic replacement, no symlink-following destination write.
        import tempfile
        tmp = None
        try:
            with tempfile.NamedTemporaryFile(
                mode="w", encoding="utf-8", dir=dest.parent,
                prefix=".settings-", delete=False
            ) as f:
                tmp = Path(f.name)
                os.fchmod(f.fileno(), 0o600)
                json.dump({name.name: getattr(self, name.name)
                           for name in fields(self)}, f, indent=2)
                f.write("\n")
            os.replace(tmp, dest)
            return dest
        finally:
            if tmp is not None:
                tmp.unlink(missing_ok=True)

    def with_values(self, **kwargs) -> "Settings":
        valid = {f.name for f in fields(self)}
        if set(kwargs) - valid:
            raise ValueError("Unknown settings keys")
        return replace(self, **kwargs).validate()


def ollama_options(mode: str) -> dict:
    if mode not in MODES:
        raise ValueError("Unknown resource mode")
    return {
        "quiet": {"num_gpu": 6, "num_thread": 2, "num_ctx": 3072, "num_predict": 256},
        "balanced": {"num_gpu": 18, "num_thread": 4, "num_ctx": 4096, "num_predict": 384},
        "maximum": {"num_ctx": 8192, "num_predict": 512},
    }[mode].copy()
