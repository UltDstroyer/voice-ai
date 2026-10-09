"""Conversation-only Ollama backend. AI tool/host execution is NOT exposed."""

from __future__ import annotations

import json
import urllib.request
from .config import Settings, ollama_options, require_loopback

SYSTEM = (
    "You are a warm, concise conversational assistant. Keep responses natural "
    "when spoken aloud, usually one to three sentences. Avoid Markdown or "
    "stage directions. Do not claim to operate the computer: no tools are "
    "available in this voice extension. The microphone is explicitly enabled "
    "only for this session."
)


class OllamaConversation:
    def __init__(self, settings: Settings):
        self.settings = settings.validate()
        self.messages = [{"role": "system", "content": SYSTEM}]

    def respond(self, utterance: str) -> str:
        if not utterance.strip():
            return ""
        history = self.messages + [{"role": "user", "content": utterance[:3000]}]
        payload = json.dumps({
            "model": self.settings.ollama_model,
            "messages": history,
            "options": ollama_options(self.settings.resource_mode),
            "stream": False,
            "keep_alive": "10s",
        }).encode("utf-8")
        request = urllib.request.Request(
            require_loopback(self.settings.ollama_url), data=payload,
            method="POST", headers={"Content-Type": "application/json"},
        )
        with urllib.request.urlopen(request, timeout=self.settings.model_timeout) as r:
            body = r.read(500_001)
        if len(body) > 500_000:
            raise ValueError("Ollama reply too large")
        reply = json.loads(body)["message"]["content"].strip()[:4000]
        if reply:
            self.messages = history + [{"role": "assistant", "content": reply}]
            self.messages = [self.messages[0]] + self.messages[-2 * self.settings.max_turns:]
        return reply
