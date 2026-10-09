# Development milestones

## Milestone 0: extension architecture
- [x] Initialize independent voice-ai repository
- [x] Publish ctx-ext-voice as Extension API v1 executable
- [x] Optional NixOS module that installs commands only
- [x] Local-only model interfaces and explicit microphone consent
- [x] Offline mocked CI tests for the core controls
- [ ] Hardware smoke test on desktop NixOS and RX 7700 XT

## Milestone 1: usable turn-by-turn conversation
- [x] 16 kHz microphone capture with Silero streaming VAD
- [x] Offline whisper.cpp STT adapter
- [x] Ollama conversation history bounded to session
- [x] Chatterbox Turbo and Piper backend adapters
- [x] Barge-in playback stop and latest pending-turn queue
- [ ] Verify actual whisper.cpp and Chatterbox/Piper startup on NixOS
- [ ] Measure perceptual response latency and real-time factor
- [ ] Handle invalid audio devices and missing model gracefully in GUI
- [ ] Fix and test playback self-echo on speaker setups

## Milestone 2: human-quality streaming
- [ ] Token/sentence-level TTS chunks; overlap transcription and synthesis
- [ ] True cancellation/stop of running inference requests
- [ ] Echo cancellation, endpoint tuning and natural conversational pauses
- [ ] Pipecat or equivalent streaming transport and headless audio protocol
- [ ] Empirical comparison of Chatterbox Turbo, Qwen3-TTS and Piper

## Milestone 3: ecosystem integration
- [ ] Cooperative VRAM/GPU scheduler with ctx-agent
- [ ] Consent-gated voice tool requests with audited approvals
- [ ] Optional visible microphone user service and voice activation mode
- [ ] Shared owner voice profiles for video narration extension
- [ ] Phone/laptop client transport with authenticated sessions
