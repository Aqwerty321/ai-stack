# Nemotron VoiceChat Profile

This repo manages NVIDIA NemotronLabs VoiceChat as a first-class `ai-profile` named `voicechat`.

## What It Is

- local realtime speech-to-speech service
- localhost-only listener
- managed by systemd user service + `ai-profile`
- built on the official `NeMo-Speech.cpp` runtime

This is a voice capability server, not the main text router.

## Why This Runtime

The older `NVIDIA-NeMo/Speech` VoiceChat branch still documents an 80 GB-class reference workflow for the Hugging Face / Triton path.

For this 24 GB RTX 5090 Laptop GPU, the practical official path is `NVIDIA/NeMo-Speech.cpp`, which now supports:

- NemotronLabs VoiceChat conversion
- local realtime serving
- NVFP4 LLM-backbone conversion on supported NVIDIA GPUs

## Managed Profile

- profile command: `/home/Aaditya/bin/ai-profile voicechat`
- wrapper: `/home/Aaditya/bin/nemotron-voicechat-start`
- service: `/home/Aaditya/.config/systemd/user/nemotron-voicechat.service`
- runtime root: `/home/Aaditya/.local/opt/NeMo-Speech.cpp`
- runtime binary: `/home/Aaditya/.local/opt/NeMo-Speech.cpp/build/cuda-s2s/bin/nemo-speech`

## Model And Quantization

Current selected bundle:

- `/home/Aaditya/models/NVIDIA-NemotronLabs-VoiceChat-11B-NVFP4-GGUF`

Why NVFP4 was selected first:

- the current official `NeMo-Speech.cpp` VoiceChat conversion path supports `nvfp4`
- the bundle converted successfully on this machine
- the runtime loads successfully after local EarTTS KV-budget tuning

Actual mixed component formats in this bundle:

- perception: `Q8_0`
- LLM backbone: `NVFP4`
- LLM aux: `BF16`
- EarTTS backbone: `Q4_K_M`
- EarTTS side: `Q8_0`
- codec: `F32`

This matches the official `NeMo-Speech.cpp` VoiceChat design: NVFP4 only applies to the large conversational LLM backbone.

## Listener

- HTTP health: `http://127.0.0.1:8080/v1/realtime/health`
- model list: `http://127.0.0.1:8080/v1/models`
- realtime websocket: `ws://127.0.0.1:8080/v1/realtime`

The service is intentionally localhost-only.

## Start / Stop / Status

Profile-level:

```bash
/home/Aaditya/bin/ai-profile voicechat
/home/Aaditya/bin/ai-profile blank
/home/Aaditya/bin/ai-profile retrieval
```

Direct service control:

```bash
systemctl --user start nemotron-voicechat.service
systemctl --user stop nemotron-voicechat.service
systemctl --user restart nemotron-voicechat.service
systemctl --user status nemotron-voicechat.service
```

## Live Testing Interface

Recommended for audio reliability: use the browser interface, because the browser owns microphone capture and playback directly and bypasses the current PyAudio/PipeWire ALSA playback quirks.

Start the browser bridge:

```bash
/home/Aaditya/bin/voicechat-browser
```

Then open:

```text
http://127.0.0.1:8090/
```

The browser UI provides:

- browser-native microphone capture
- browser-native playback
- a richer Vapi-inspired single-page frontend adapted for the local VoiceChat stack
- live user transcript
- live agent transcript
- tool call log
- conversation log
- session status / memory status
- hold-to-talk controls in the browser UI
- save/load session-name workflow against local logs
- local session logging under `out/ai-stack/voicechat-browser/<session-name>/`

For natural long-running microphone conversations with automatic transcripts and tool logs, use:

```bash
/home/Aaditya/bin/voicechat-live
```

For the terminal UI version with live panes for user transcript, agent transcript, tool calls, and conversation log, use:

```bash
/home/Aaditya/bin/voicechat-tui
```

Optional stable session name:

```bash
/home/Aaditya/bin/voicechat-live paris-memory-test
```

TUI with stable session name:

```bash
/home/Aaditya/bin/voicechat-tui paris-memory-test
```

This launcher:

- connects to `ws://127.0.0.1:8080`
- enables persistent-memory plumbing
- uses the default voice tool policy from `config/voicechat/default_instructions.txt`
- uses the default tool schema from `config/voicechat/default_tools.json`
- removes the old 5-minute microphone cap by passing `--max-duration 0`
- when EasyEffects is active, prefers `PULSE_SINK=easyeffects_sink` and `PULSE_SOURCE=easyeffects_source` so the session follows the same virtual audio path as the rest of your desktop audio
- writes outputs to `/home/Aaditya/ai-stack/out/ai-stack/voicechat-live/<session-name>/`

Per-session outputs:

- `user_text.txt`
- `agent_text.txt`
- `function_calls.jsonl`
- `conversation.jsonl`
- `received_audio.wav`

This is the intended manual interface for testing the voice agent yourself.

The terminal launchers remain useful for transcript/debug work, but the browser interface is now the preferred path when the issue is simply hearing the agent reliably.

TUI controls:

- `q` to quit
- `Ctrl+C` to quit
- `m` to toggle microphone mute
- `p` to toggle push-to-talk gate
- `1` select user transcript pane
- `2` select agent transcript pane
- `3` select conversation pane
- `j` / `k` scroll the selected pane

Current TUI features:

- color-coded panes for user, agent, tool calls, and conversation log
- memory/session status pane showing phase, memory-context load status, last tool, rollover count, chunk counts, mute state, and push-to-talk state
- scrollable transcript and conversation panes
- push-to-talk / mute controls driven through small file-based control flags consumed by the live client

Non-interactive launcher check:

```bash
/home/Aaditya/bin/voicechat-tui --check smoke-test
```

## Local Tuning

The wrapper currently sets:

- `S2S_TTS_POSITIONS_PER_SEQUENCE=4096`
- `RNNT_MAX_AGENT_RESPONSE_SEC=12`
- `--s2s-max-streams 1`

Why these are set:

- upstream EarTTS KV reservation is too large for the 24 GB laptop when combined with the full NVFP4 VoiceChat bundle
- trimming the EarTTS per-stream KV budget below the upstream default makes the NVFP4 bundle fit while still keeping materially more headroom than the first 1536-position laptop-safe setting
- the response-length cap reduces runaway assistant turns during local realtime use
- `1` stream is the right first managed operating point for latency and VRAM headroom
- `rag-embed.service` is intentionally started alongside `voicechat` so the local memory MCP can perform embedding-backed recall during voice sessions

## VRAM / Load Time

Measured on this machine:

- clean-start health ready time: about `6.0s`
- stable idle VRAM after a 30s soak: about `12.8 GB used`
- free VRAM at that point: about `11.2 GB`
- probe results for higher EarTTS budgets on the same NVFP4 bundle:
  - `3072` positions: loaded, about `17.3 GB used`
  - `4096` positions: loaded, about `17.8 GB used`

The managed profile is currently set to `4096` to move closer to a 20 GB operating point while preserving successful startup.

## Benchmarks

Representative successful run:

- sample: official `turn_taking.wav`
- source duration: `41.08s`
- trailing silence added: `6s`
- effective received audio: `47.12s`
- time to first response: `357.5 ms`
- mean inter-chunk latency: `83.4 ms`
- server stats: `589` chunks in, `589` chunks out, `295` inferences, `0` dropped

Longer-context probe:

- sample: duplicated `turn_taking.wav`
- effective received audio before failure: `79.28s`
- time to first response: `371.9 ms`
- mean inter-chunk latency: `80.6 ms`
- eventually failed with `S2SStream: step budget exhausted`

Artifacts are in:

- `/home/Aaditya/ai-stack/out/ai-stack/voicechat-bench/`

## Integration In The Stack

Conceptually:

- text: existing LLM profiles
- retrieval: existing embedding/rerank/reasoner stack
- voice: `nemotron-voicechat.service`

Operationally:

- `voicechat` is a mutually exclusive GPU profile, like the other heavy model services
- `neo4j-memory-mcp.service` stays up in `voicechat` mode
- `rag-embed.service` also stays up in `voicechat` mode so persistent memory retrieval can work
- `laya-decide.service` stays up in every profile

## Compaction And Memory Tools

The local reference client has been extended with built-in voice-agent tools:

- `compact_conversation_context`
- `recall_relevant_memory`
- `remember_note`

The intent is:

- compaction can preserve the active goal, latest user request, latest assistant reply, and recent dialogue highlights before a fresh working session continues
- memory recall can query the local Neo4j memory MCP for relevant persistent facts/preferences
- remember-note can store concise notes back into persistent memory

Current state of this integration:

- the client now contains real local MCP plumbing for Neo4j memory over `http://127.0.0.1:3010/mcp`
- memory retrieval depends on `rag-embed.service` being live, which is why `voicechat` mode now keeps it started
- tool registration and dispatch plumbing are in place
- explicit long-context validation did trigger `compact_conversation_context` and reopened a fresh session successfully
- explicit direct memory-MCP validation succeeded once `rag-embed.service` was running
- however, a tool-biased replay of the official `tool_call.wav` sample still did not naturally choose the memory tools, so the end-to-end spoken memory path should still be treated as partially wired rather than production-verified

Observed behavior in current validation:

- long-context replay triggered compaction automatically and reopened a fresh session
- once `rag-embed.service` was live, direct memory store/search/context retrieval worked again
- stronger instructions alone were not enough to make the official `tool_call.wav` sample naturally choose memory tools

## Known Limitations

- longer sessions can still hit `S2SStream: step budget exhausted`
- after an internal inference failure, later sessions can sometimes require a service restart before new sessions behave normally
- repetition, derailment, and self-talk are still visible in the current official sample runs
- this should be treated as a working and benchmarkable early managed profile, not a polished daily-driver voice appliance yet

## Recommended Next Order

1. validate long-context behavior on the final `4096` managed profile and confirm whether auto-rollover from `step budget exhausted` behaves acceptably
2. validate the spoken end-to-end compaction and Neo4j memory tools with prompts or synthetic audio that explicitly trigger them
3. investigate the upstream session-lifecycle behavior after inference failures so new sessions do not require restart hygiene
4. benchmark a fallback `Q4_K_M` VoiceChat bundle only if NVFP4 quality/stability remains worse than desired over longer sessions
5. add a small local scripted benchmark harness that records readiness time, TTFR, idle VRAM, and failure mode into a single JSON report
