"""Opt-in local voice conversation; user controls microphone lifetime.

Barge-in stops audible playback immediately. An inference call that is
already running may finish before the next queued turn is processed.
"""

from __future__ import annotations

import queue
import tempfile
import threading
from pathlib import Path

from .brain import OllamaConversation
from .config import Settings
from .listen import Microphone, SileroStream
from .segment import SpeechSegmenter
from .speech import AudioPlayer, make_speech
from .transcribe import WhisperCLI


class VoiceSession:
    def __init__(self, settings: Settings, on_event=print):
        self.settings = settings.validate()
        self.on_event = on_event
        self.pending = queue.Queue(maxsize=1)
        self.shutdown = threading.Event()
        self.interrupted = threading.Event()
        self.thread: threading.Thread | None = None
        self.player = AudioPlayer()

    def interrupt(self):
        self.interrupted.set()
        self.player.stop()

    def submit(self, pcm: bytes):
        # A new spoken utterance replaces an obsolete queued utterance.
        try:
            self.pending.put_nowait(pcm)
        except queue.Full:
            try:
                self.pending.get_nowait()
                self.pending.task_done()
            except queue.Empty:
                pass
            self.pending.put_nowait(pcm)

    def worker(self):
        try:
            stt = WhisperCLI(
                self.settings.whisper_binary, self.settings.whisper_model,
                self.settings.stt_timeout,
            )
            brain = OllamaConversation(self.settings)
            speech = make_speech(self.settings)
        except Exception as exc:
            self.on_event("Voice backend initialization failed: " + str(exc))
            self.shutdown.set()
            return

        while not self.shutdown.is_set():
            try:
                pcm = self.pending.get(timeout=0.15)
            except queue.Empty:
                continue
            try:
                self.interrupted.clear()
                phrase = stt.transcribe(pcm)
                if not phrase or self.interrupted.is_set():
                    continue
                self.on_event("You: " + phrase)
                response = brain.respond(phrase)
                if not response or self.interrupted.is_set():
                    continue
                self.on_event("Assistant: " + response)
                with tempfile.TemporaryDirectory(prefix="ctx-voice-tts-") as temp:
                    wav = Path(temp) / "reply.wav"
                    speech.render(response, wav)
                    if not self.interrupted.is_set():
                        self.player.play(wav, self.interrupted)
            except Exception as exc:
                self.on_event("Voice turn failed: " + str(exc))
            finally:
                self.pending.task_done()

    def run(self):
        detector = SileroStream(self.settings)
        segmenter = SpeechSegmenter(
            block_bytes=1024, preroll_blocks=16,
            max_blocks=(self.settings.max_utterance_seconds * 16000 // 512),
        )
        self.thread = threading.Thread(
            target=self.worker, name="ctx-voice-worker", daemon=True
        )
        self.thread.start()
        self.on_event("Microphone ON. Use headphones to reduce echo. Ctrl-C to stop.")
        try:
            with Microphone(self.settings) as mic:
                while not self.shutdown.is_set():
                    frame = mic.read()
                    event = detector.feed(frame)
                    if event and "start" in event:
                        self.interrupt()
                    pcm = segmenter.accept(frame, event)
                    if pcm is not None:
                        self.submit(pcm)
        except KeyboardInterrupt:
            self.on_event("Stopping conversation.")
        finally:
            self.shutdown.set()
            self.interrupt()
            if self.thread is not None:
                self.thread.join(timeout=1)
            self.on_event("Microphone OFF.")
