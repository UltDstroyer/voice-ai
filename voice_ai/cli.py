"""User-invoked local CLI, also exposed as ctx-ext-voice."""

from __future__ import annotations

import argparse
import importlib.util
import json
import os
import shutil
import sys
import wave
from pathlib import Path

from .config import MODES, Settings, config_path
from .transcribe import WhisperCLI
from .speech import make_speech
from .brain import OllamaConversation

SETTABLE = (
    "whisper_binary", "whisper_model", "ollama_model", "tts_engine",
    "voice_reference", "piper_binary", "piper_model", "resource_mode",
)


def doctor(settings: Settings) -> dict:
    return {
        "extension_api": "1",
        "context": os.environ.get("CTX_CONTEXT", ""),
        "resource_mode": settings.resource_mode,
        "microphone_is_off": True,
        "packages": {x: importlib.util.find_spec(x) is not None
                     for x in ("numpy", "sounddevice", "soundfile",
                               "torch", "silero_vad", "chatterbox")},
        "whisper_cli_available": shutil.which(settings.whisper_binary) is not None,
        "whisper_model_exists": bool(settings.whisper_model and
                                    Path(settings.whisper_model).is_file()),
        "piper_cli_available": shutil.which(settings.piper_binary) is not None,
        "piper_model_exists": bool(settings.piper_model and
                                  Path(settings.piper_model).is_file()),
        "voice_reference_exists": bool(settings.voice_reference and
                                       Path(settings.voice_reference).is_file()),
        "ollama_url": settings.ollama_url,
    }


def wav_to_pcm16(path: Path) -> bytes:
    with wave.open(str(path), "rb") as stream:
        if (stream.getframerate(), stream.getnchannels(),
                stream.getsampwidth(), stream.getcomptype()) != (
                16000, 1, 2, "NONE"):
            raise ValueError("Expected 16-kHz, mono, 16-bit PCM WAV")
        if stream.getnframes() > 16000 * 60:
            raise ValueError("Transcription clips must be <= 60 seconds")
        return stream.readframes(stream.getnframes())


def add_commands(parser: argparse.ArgumentParser):
    sub = parser.add_subparsers(dest="action", required=True)
    sub.add_parser("doctor", help="Inspect optional backend setup without microphone access")
    sub.add_parser("config", help="Print current local configuration")
    setting = sub.add_parser("set", help="Set one supported local configuration field")
    setting.add_argument("key", choices=SETTABLE)
    setting.add_argument("value")
    mode = sub.add_parser("mode", help="Change voluntary inference budget")
    mode.add_argument("value", choices=MODES)
    chat = sub.add_parser("chat", help="Explicitly enable live microphone conversation")
    chat.add_argument("--headphones", action="store_true",
                      help="Acknowledge headphones/echo isolation for barge-in")
    say = sub.add_parser("say", help="Produce spoken WAV from text")
    say.add_argument("text")
    say.add_argument("--output", type=Path, required=True)
    prompt = sub.add_parser("text", help="Talk to Ollama without enabling the microphone")
    prompt.add_argument("prompt")
    trans = sub.add_parser("transcribe", help="Transcribe an existing 16-kHz PCM WAV")
    trans.add_argument("wav", type=Path)
    sub.add_parser("version", help="Show extension version")


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(prog="ctx voice")
    add_commands(parser)
    try:
        args = parser.parse_args(argv)
        version = os.environ.get("CTX_EXTENSION_API_VERSION")
        if version not in (None, "1"):
            raise ValueError("Unsupported Context Switcher Extension API version")
        settings = Settings.load()
        if args.action == "doctor":
            print(json.dumps(doctor(settings), indent=2))
        elif args.action == "config":
            print(json.dumps(settings.__dict__, indent=2))
        elif args.action == "set":
            settings.with_values(**{args.key: args.value}).save()
            print("Saved voice configuration to", config_path())
        elif args.action == "mode":
            settings.with_values(resource_mode=args.value).save()
            print("Voice resource mode:", args.value)
        elif args.action == "text":
            print(OllamaConversation(settings).respond(args.prompt))
        elif args.action == "transcribe":
            print(WhisperCLI(settings.whisper_binary, settings.whisper_model,
                             settings.stt_timeout).transcribe(wav_to_pcm16(args.wav)))
        elif args.action == "say":
            target = args.output.expanduser()
            if target.exists() or target.suffix.lower() != ".wav":
                raise ValueError("Choose a new .wav output path")
            target.parent.mkdir(parents=True, exist_ok=True)
            make_speech(settings).render(args.text, target)
            print("Generated", target)
        elif args.action == "chat":
            if not args.headphones:
                raise ValueError(
                    "Use ctx voice chat --headphones to acknowledge that "
                    "headphones are needed to avoid self-transcription"
                )
            from .session import VoiceSession
            VoiceSession(settings).run()
        elif args.action == "version":
            from . import __version__
            print("ctx-voice", __version__, "Extension API v1")
        return 0
    except (OSError, RuntimeError, ValueError, KeyError, TimeoutError) as exc:
        print("ctx-voice:", exc, file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
