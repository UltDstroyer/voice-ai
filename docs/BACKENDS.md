# Speech backend setup

## Whisper.cpp (speech to text)

Project: https://github.com/ggml-org/whisper.cpp

Build whisper.cpp according to its official docs, choosing CPU, Vulkan, or
ROCm support compatible with your NixOS drivers. Download a ggml model
(e.g. ggml-base.en.bin). Confirm your locally installed whisper-cli accepts:

    whisper-cli -m /path/to/ggml-base.en.bin -f sample.wav -otxt -of result -nt -np

Set the paths:

    ctx voice set whisper_binary /absolute/path/to/whisper-cli
    ctx voice set whisper_model /absolute/path/to/ggml-base.en.bin

All speech audio passed to whisper.cpp is 16-kHz mono PCM WAV. The CLI
writes transcript text into a temporary directory that is deleted after use.

## Silero VAD (turn detection)

Project: https://github.com/snakers4/silero-vad

Realtime detection uses load_silero_vad() and VADIterator() against
512-sample float32 chunks at 16 kHz, on CPU. Install the optional
Python package into your compatible local environment:

    pip install -e '.[audio,vad]'

## Ollama (language model)

Project: https://ollama.com/

Voice mode requests http://127.0.0.1:11434/api/chat only. It never
passes arbitrary shell or operating-system tools to the model.

    ollama pull qwen3:8b
    ctx voice set ollama_model qwen3:8b

Setting a custom non-loopback Ollama endpoint is intentionally rejected.

## Chatterbox Turbo (default TTS)

Project: https://github.com/resemble-ai/chatterbox

This optional backend uses ChatterboxTurboTTS.from_pretrained with
PyTorch device cuda when torch.cuda.is_available(), which is also
the PyTorch device interface used by ROCm. Generation calls model.generate
and torchaudio.save. Enrolling your own short, clean WAV is optional.

    ctx voice set tts_engine chatterbox
    ctx voice set voice_reference /absolute/path/to/my-voice.wav

Chatterbox and its PyTorch/torchaudio versions are substantial dependencies
and may not build as a normal pip wheel on NixOS AMD. Install them in a
compatible environment with working ROCm, then test on your GPU. This
repository intentionally does NOT download or install them automatically.
If torch.cuda.is_available() is false, it falls back to CPU and might be slow.

The Chatterbox reference clone is approximate, not guaranteed to match
your own voice perfectly. Only use your own voice or consented voice data.

## Piper (low resource alternate TTS)

Project: https://github.com/rhasspy/piper

Install piper and download a voice model ONNX plus its matching config:

    ctx voice set tts_engine piper
    ctx voice set piper_binary /path/to/piper
    ctx voice set piper_model /path/to/voice.onnx

Piper receives text on stdin and produces a WAV through output_file.
This is useful on the laptop or Pi, and can run when Chatterbox cannot.

## Resource modes

    ctx voice mode quiet
    ctx voice mode balanced
    ctx voice mode maximum

Quiet uses 6 Ollama GPU layers, 2 CPU threads and a modest context window.
Balanced increases offloading and CPU threads. Maximum removes voluntary
GPU-layer and thread constraints. These are **not VRAM or GPU usage caps**.
Voice TTS still uses whatever device its separate Torch/Piper backend selects.

Coordinated GPU scheduling with ctx-agent is a later integration. Do not
assume two independent local models will share VRAM fairly or avoid stutters.
