# voice-ai

**ctx-voice** is a local-first conversational speech extension for
[Context Switcher](https://github.com/UltDstroyer/context_switcher).
Features stay in this repository; the ctx core only discovers an executable
named ctx-ext-voice on PATH.

**Status: Milestone 0/1 developer preview.** Core speech pipeline and offline
tests exist. Hardware inference has NOT been benchmarked on NixOS/AMD ROCm.
This is not yet seamless human-level voice conversation.

## What exists

- Opt-in microphone session: ctx voice chat --headphones
- CPU-side Silero VAD utterance boundaries, 16-kHz microphone capture
- whisper.cpp local speech-to-text (CLI subprocess; no API upload)
- Local Ollama conversation backend, short spoken-language responses
- Chatterbox Turbo TTS with optional owner-supplied reference WAV
- Piper TTS alternative for low-resource machines
- Voice interruptions: speech onset stops audible playback and queues the
  latest utterance; noninterruptible model inference may finish first
- Quiet/balanced/maximum *soft* Ollama resource settings, with GPU on in quiet
- ctx voice say, transcribe, text, doctor, set, config, and mode
- An optional NixOS module that installs the extension CLI but never opens
  the microphone or starts an always-listening service

No audio, transcript, or session history is permanently saved by default.
Speech chunks and generated WAV files use temporary directories, and
conversation messages live only in process memory.

## Install the extension, separately from the Context Switcher core

For the private GitHub repository, clone the development branch using your
configured GitHub SSH key:

    git clone git@github.com:UltDstroyer/voice-ai.git ~/src/voice-ai

Option A: develop locally with Python 3.11+ in an environment that supports
audio and the required Torch/ROCm stack:

    cd ~/src/voice-ai
    python -m venv .venv
    source .venv/bin/activate
    pip install -e '.[audio,vad]'
    python -m unittest discover -s tests -v
    ctx-ext-voice doctor

To enable Chatterbox, separately install its compatible Torch/ROCm
environment as described in docs/BACKENDS.md; packages are large and hardware
dependent. Use Piper instead if you want a lightweight CPU TTS backend.

Option B: install the base extension using your existing NixOS flake:

    inputs.voice-ai.url = "path:/home/lena/src/voice-ai";

and add the voice module to the host module list:

    inputs.voice-ai.nixosModules.default

then:

    programs.ctxVoice.enable = true;

Review your NixOS changes and rebuild with your normal flake command.
The base Nix package installs Python/audio essentials, NOT whisper model
weights, Silero, or the GPU-heavy Chatterbox stack. Use a separate compatible
speech environment for the latter. Avoid installing multiple independent
instances of this command in PATH.

After installation:

    ctx extensions
    ctx voice version
    ctx voice doctor

If the Context Switcher core is not installed, run ctx-ext-voice instead.

## Configure models

Download whisper.cpp and a local ggml model, install a local Ollama model,
and install Chatterbox Turbo (or Piper). See docs/BACKENDS.md.

    ctx voice set whisper_binary /path/to/whisper-cli
    ctx voice set whisper_model /path/to/ggml-base.en.bin
    ctx voice set ollama_model qwen3:8b
    ctx voice set tts_engine chatterbox
    ctx voice mode quiet
    ctx voice doctor

To clone your OWN voice for live TTS, provide an owner-recorded WAV:

    ctx voice set voice_reference /home/YOU/Voice/my-reference.wav

The file is never imported automatically. Do not enroll a voice you
lack permission to use. The extension config lives in
~/.config/ctx-voice/config.json by default and is saved with mode 0600.

## Try it without a microphone

    ctx voice text "Tell me something interesting in two sentences"
    ctx voice say "Hello, welcome to Context Switcher" --output ~/Videos/hello.wav
    ctx voice transcribe /path/to/16000-mono-pcm.wav

For live conversation, use a headset to avoid the agent transcribing its
own playback:

    ctx voice chat --headphones

The terminal explicitly shows microphone activation. Ctrl-C exits and
closes the device. This is an interactive process, not an unattended daemon.

## Important limitations

- Current version uses turn-by-turn transcription and completed-file TTS,
  not token-level streaming speech synthesis. Latency can be noticeable.
- Barge-in stops playback immediately; an ongoing Ollama/TTS call may not
  be cancellable until it completes.
- No echo cancellation yet. Use headphones.
- Chatterbox GPU memory consumption is not hard-capped; quiet mode only
  limits Ollama request offload hints and CPU threads.
- Does not invoke ctx-agent's tools or interact with your computer.
  Voice commands that *change files* require a future authenticated,
  confirmation-driven agent broker.
- This does not run a background microphone monitor, capture your desktop,
  or share voice profiles with a different extension.
- Initial NixOS module builds must be tested on your hardware before
  treating AMD GPU acceleration as verified.

## Development

    python -m unittest discover -s tests -v
    python -m compileall -q voice_ai tests

See docs/ARCHITECTURE.md, docs/BACKENDS.md and docs/ROADMAP.md.
