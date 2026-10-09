import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from voice_ai.config import Settings, ollama_options, require_loopback
from voice_ai.cli import main, doctor


class SettingsTests(unittest.TestCase):
    def test_gpu_stays_enabled_in_quiet_mode(self):
        q, b, m = [ollama_options(mode) for mode in ("quiet", "balanced", "maximum")]
        self.assertGreater(q["num_gpu"], 0)
        self.assertLess(q["num_gpu"], b["num_gpu"])
        self.assertLess(q["num_thread"], b["num_thread"])
        self.assertNotIn("num_gpu", m)

    def test_reject_ollama_remote_host(self):
        for url in ("http://example.com/api/chat",
                    "https://127.0.0.1:11434/api/chat",
                    "http://127.0.0.1:9911/api/chat",
                    "http://127.0.0.1/api/chat"):
            with self.subTest(url=url), self.assertRaises(ValueError):
                require_loopback(url)

    def test_config_save_and_load_without_audio_access(self):
        with tempfile.TemporaryDirectory() as td:
            path = Path(td) / "voice" / "config.json"
            chosen = Settings().with_values(tts_engine="piper", resource_mode="balanced")
            chosen.save(path)
            self.assertEqual(Settings.load(path), chosen)
            self.assertEqual(path.stat().st_mode & 0o777, 0o600)
            self.assertEqual(path.parent.stat().st_mode & 0o777, 0o700)

    def test_unknown_config_attribute_rejected(self):
        with tempfile.TemporaryDirectory() as td:
            path = Path(td) / "settings.json"
            path.write_text(json.dumps({"enable_hidden_microphone": True}))
            with self.assertRaises(ValueError):
                Settings.load(path)

    def test_symlink_config_rejected(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            (root / "real.json").write_text("{}")
            (root / "link.json").symlink_to(root / "real.json")
            with self.assertRaises(ValueError):
                Settings.load(root / "link.json")

    def test_doctor_does_not_open_microphone(self):
        result = doctor(Settings())
        self.assertTrue(result["microphone_is_off"])
        self.assertIn("packages", result)

    def test_version_runs_without_audio_models(self):
        with tempfile.TemporaryDirectory() as td:
            with patch.dict(os.environ, {"XDG_CONFIG_HOME": td}):
                self.assertEqual(main(["version"]), 0)

    def test_reject_incompatible_extension_api(self):
        with tempfile.TemporaryDirectory() as td:
            with patch.dict(os.environ, {
                "XDG_CONFIG_HOME": td,
                "CTX_EXTENSION_API_VERSION": "99",
            }):
                self.assertEqual(main(["version"]), 1)


if __name__ == "__main__":
    unittest.main()
