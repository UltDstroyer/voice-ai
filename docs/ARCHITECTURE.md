# Voice architecture and permissions

## Ownership

Context Switcher is the stable main platform, owner of context switching
and Extension API v1. voice-ai is an **independent extension** and installs
ctx-ext-voice; it does not edit src/ctx or depend on the ctx Python source.

A versioned ctx invocation provides CTX_EXTENSION_API_VERSION=1,
CTX_CONTEXT (possibly empty), and CTX_CONFIG_ROOT. The extension checks
protocol compatibility but does not interpret context identity as an
authorization token. In v0/1 CTX_CONTEXT supplies only a validated workspace label to the
conversation system prompt. It does NOT read context snapshots, infer
filesystem permissions, or authorize actions.

## Pipeline

1. Explicit CLI chat command opens RawInputStream in the user's interactive
   session (mono 16-bit PCM, 16 kHz; 512-sample blocks).
2. Silero VADIterator identifies speech start/end; bounded segmenter adds
   ~512 ms preroll and cuts off overly long utterances.
3. A single asynchronous processing thread invokes whisper.cpp CLI against
   a secure temporary WAV and receives UTF-8 text.
4. Ollama POST /api/chat at localhost runs text-only conversational inference.
   Tool calls are not exposed; this cannot control the computer.
5. Chatterbox Turbo or Piper synthesizes a WAV; local sounddevice plays it.
6. Microphone remains active while synthesis and playback proceed. Fresh
   speech stops audible playback and supersedes an older queued utterance.
   Heavy GPU calls are cooperative and cannot be preempted mid-kernel.

This v1 is not an end-to-end full-duplex streaming stack. Replacing the
worker with Pipecat or a dedicated streaming scheduler is a later milestone.

## Privacy and security

- NO microphone reads during doctor, version, set, mode, text or say.
- NO always-on background systemd service.
- NO passive voice recording by ctxd or a browser extension.
- NO remote endpoints: the Ollama endpoint is restricted to loopback.
- NO arbitrary host command execution from Ollama response. Backend calls
  use fixed argument arrays without shell=True.
- NO automatic voice enrollment. voice_reference is explicitly configured
  by the person operating the machine and isn't committed to Git.
- NO automatic logging to persistent conversation memory. User utterances
  print in the local terminal, so shell scrollback and terminal recorders
  are outside this module's privacy guarantees.
- Background resource controls must be coordinated with ctx-agent in a
  future revision; there is no hard GPU quota on Radeon/ROCm inference.
- VAD and STT models are local, but downloading backend weights or installing
  packages requires whatever network connections you independently choose.

Do not connect this extension to a remote AI control channel until
separate authentication, approval scope, and consent controls are built.

## Planned extension integration

- ctx voice status / voice devices / push-to-talk controls
- Independent optional NixOS/user session audio service with visible state
- Explicit per-session ctx-agent tool permissions and approval UI
- Resource scheduling between Ollama, speech engine and coding jobs
- Shared owner voice profile managed by a dedicated secure voice vault
- Improved streaming TTS chunks, text normalization, echo cancellation
- Benchmark suite for end-to-end first audio latency on RX 7700 XT
