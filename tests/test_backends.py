import json
import tempfile
import unittest
from pathlib import Path
import os
from unittest.mock import MagicMock, patch

from voice_ai.config import Settings
from voice_ai.brain import OllamaConversation
from voice_ai.transcribe import WhisperCLI, write_pcm16
from voice_ai.speech import PiperSpeech, make_speech
from voice_ai.session import VoiceSession


class BackendTests(unittest.TestCase):
    def test_pcm_wave_format(self):
        with tempfile.TemporaryDirectory() as td:
            out = Path(td) / "test.wav"
            write_pcm16(out, b"\x00\x00" * 512)
            from voice_ai.cli import wav_to_pcm16
            self.assertEqual(wav_to_pcm16(out), b"\x00\x00" * 512)

    def test_odd_pcm_rejected(self):
        with tempfile.TemporaryDirectory() as td:
            with self.assertRaises(ValueError):
                write_pcm16(Path(td) / "audio.wav", b"x")

    def test_transcription_uses_safe_argument_list(self):
        with tempfile.TemporaryDirectory() as td:
            model = Path(td) / "ggml.bin"
            model.write_bytes(b"x")
            stt = WhisperCLI("/usr/bin/whisper-cli", str(model))
            def fake_run(argv, **kwargs):
                out = Path(argv[argv.index("-of") + 1]).with_suffix(".txt")
                out.write_text(" test transcript \n")
                return MagicMock(returncode=0, stderr="")
            with patch("voice_ai.transcribe.subprocess.run", side_effect=fake_run) as run:
                self.assertEqual(stt.transcribe(b"\x00\x00" * 512), "test transcript")
                self.assertIsInstance(run.call_args.args[0], list)

    def test_workspace_name_provided_without_file_access(self):
        with patch.dict(os.environ, {"CTX_CONTEXT": "research"}):
            bot = OllamaConversation(Settings())
            self.assertIn("research", bot.messages[0]["content"])
        with patch.dict(os.environ, {"CTX_CONTEXT": "bad\ninjection"}):
            bot = OllamaConversation(Settings())
            self.assertNotIn("injection", bot.messages[0]["content"])

    def test_ollama_request_is_local_and_conversation_bounded(self):
        class Response:
            def __enter__(self): return self
            def __exit__(self, *_): return False
            def read(self, limit): return json.dumps({
                "message": {"content": "Hello, how are you?"}
            }).encode()
        settings = Settings(max_turns=1)
        with patch("voice_ai.brain.urllib.request.urlopen", return_value=Response()) as api:
            brain = OllamaConversation(settings)
            self.assertTrue(brain.respond("Hi"))
            self.assertTrue(brain.respond("Again"))
            self.assertEqual(len(brain.messages), 3)
            req = api.call_args.args[0]
            self.assertEqual(req.full_url, "http://127.0.0.1:11434/api/chat")
            self.assertNotIn("tools", json.loads(req.data))

    def test_piper_does_not_shell_out(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            model = root / "voice.onnx"
            model.write_bytes(b"x")
            backend = PiperSpeech(Settings(tts_engine="piper", piper_model=str(model)))
            out = root / "result.wav"
            def fake_run(argv, **kwargs):
                out.write_bytes(b"RIFF")
                return MagicMock(returncode=0, stderr="")
            with patch("voice_ai.speech.subprocess.run", side_effect=fake_run) as runner:
                backend.render("hello", out)
                self.assertIsInstance(runner.call_args.args[0], list)
                self.assertEqual(runner.call_args.kwargs["input"], "hello")

    def test_session_interrupt_is_nonprivileged(self):
        session = VoiceSession(Settings(), lambda _: None)
        with patch.object(session.player, "stop") as stop:
            session.interrupt()
            self.assertTrue(session.interrupted.is_set())
            stop.assert_called_once()

    def test_latest_pending_audio_wins(self):
        session = VoiceSession(Settings(), lambda _: None)
        session.submit(b"old")
        session.submit(b"new")
        self.assertEqual(session.pending.get_nowait(), b"new")


if __name__ == "__main__":
    unittest.main()
