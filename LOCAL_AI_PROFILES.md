# Local AI Profiles

Use `/home/Aaditya/bin/ai-profile` to switch the GPU between the managed local AI modes.

Retrieval mode is the startup default. The retrieval services stay enabled at login, while the mutually exclusive single-GPU model servers stay disabled until explicitly selected.

## Multiview 3D batch profiles

`ai-profile multiview`, `ai-profile hunyuan3d`, `ai-profile hunyuan-paint`, `ai-profile triposg`, and `ai-profile 3d-lab` release GPU model services for isolated batch jobs. They prepare the GPU without launching an idle server. Use `3d-lab views` for MV-Adapter and `3d-lab shape` for Hunyuan3D reconstruction; these helpers log jobs, guard VRAM, serialize lab runs, and restore retrieval afterward. Paths, installation recipes, and evaluation guidance are in [docs/3d-lab/README.md](docs/3d-lab/README.md).

## VoiceChat Mode

```bash
/home/Aaditya/bin/ai-profile voicechat
```

This keeps the local Nemotron VoiceChat realtime server hot:
- `nemotron-voicechat.service`
- `neo4j-memory-mcp.service`
- `rag-embed.service`

Current target:
- model bundle: `/home/Aaditya/models/NVIDIA-NemotronLabs-VoiceChat-11B-NVFP4-GGUF`
- runtime: `/home/Aaditya/.local/opt/NeMo-Speech.cpp/build/cuda-s2s/bin/nemo-speech`
- wrapper: `/home/Aaditya/bin/nemotron-voicechat-start`
- service: `/home/Aaditya/.config/systemd/user/nemotron-voicechat.service`
- listener: `http://127.0.0.1:8080`
- realtime health: `http://127.0.0.1:8080/v1/realtime/health`
- realtime websocket: `ws://127.0.0.1:8080/v1/realtime`

Why NVFP4 was selected first:
- the current official `NeMo-Speech.cpp` VoiceChat conversion path supports `nvfp4` for the large conversational LLM backbone on supported NVIDIA GPUs
- on this Blackwell laptop GPU, the official NVFP4 conversion and runtime build both succeeded
- the managed profile keeps the VoiceChat bundle in the official mixed profile shape: perception `Q8_0`, LLM backbone `NVFP4`, EarTTS backbone `Q4_K_M`, aux head `BF16`, codec `F32`

Local tuning applied:
- EarTTS per-stream KV budget is trimmed with `S2S_TTS_POSITIONS_PER_SEQUENCE=4096` in the wrapper so the NVFP4 bundle fits while moving closer to a 20 GB operating point on this 24 GB laptop GPU
- `RNNT_MAX_AGENT_RESPONSE_SEC=12` is set to limit runaway assistant turns during local realtime use
- `--s2s-max-streams 1` is used intentionally for this first managed profile to preserve VRAM and responsiveness
- `rag-embed.service` is kept running so the voice client can call the local Neo4j memory MCP with embeddings enabled

Measured startup / footprint:
- health endpoint reached ready state in about `6.0s` after a clean start
- idle VRAM after a stable 30s soak: about `12.8 GB used`, `11.2 GB free`
- a transient earlier probe measured as low as about `2.3 GB used` before the full model residency settled; use the 30s soak number as the real idle budget
- higher-budget probes on the same NVFP4 bundle also loaded successfully:
  - `3072` positions: about `17.3 GB used`
  - `4096` positions: about `17.8 GB used`

Measured sample benchmark results:
- turn-taking sample (`41.08s` source + `6s` trailing silence):
  - time to first response: about `357.5 ms`
  - mean inter-chunk latency: about `83.4 ms`
  - server stats: `589` input frames, `589` output chunks, `295` inferences, `0` dropped chunks, `47.12s` audio received
- long-context probe (`82.16s` duplicated sample + `6s` trailing silence):
  - time to first response: about `371.9 ms`
  - mean inter-chunk latency: about `80.6 ms`
  - server stats before failure: `991` input frames, `986` output chunks, `494` inferences, `0` dropped chunks, `79.28s` audio received

Known limitations observed locally:
- the NVFP4 profile now loads and serves, but the local runtime can still hit `S2SStream: step budget exhausted` on longer file-driven sessions; this is a runtime budget issue, not a model-load failure
- after an internal inference error, later sessions can sometimes see `S2SPipeline: maximum concurrent streams reached` until the service is restarted; treat that as a current runtime/session-lifecycle bug in this local stack
- sample quality is conversationally usable, but repetition / derailment / self-talk are still visible in the official sample runs, which matches the upstream model-card caveats
- client-side compaction and Neo4j memory tool plumbing now exist; compaction was triggered successfully in long-context validation, but spoken memory-tool selection still remains weak in the official sample replay even with stronger instructions

Useful commands:
- start profile: `/home/Aaditya/bin/ai-profile voicechat`
- stop / free GPU: `/home/Aaditya/bin/ai-profile blank`
- browser audio interface: `/home/Aaditya/bin/voicechat-browser` then open `http://127.0.0.1:8090/`
- live manual testing interface: `/home/Aaditya/bin/voicechat-live [session-name]`
- live terminal UI: `/home/Aaditya/bin/voicechat-tui [session-name]`
- direct service control:
  - `systemctl --user start nemotron-voicechat.service`
  - `systemctl --user stop nemotron-voicechat.service`
  - `systemctl --user restart nemotron-voicechat.service`
  - `systemctl --user status nemotron-voicechat.service`

It also stops:
- `rag-rerank.service`
- `local-reasoner.service`
- `gemma4-vllm.service`
- `muse-glimmer.service`
- `ornith9-vllm.service`
- `trellis-3d.service`

## Retrieval Mode

```bash
/home/Aaditya/bin/ai-profile retrieval
```

This keeps the retrieval stack hot:
- `rag-embed.service`
- `rag-rerank.service`
- `local-reasoner.service`
- `neo4j-memory-mcp.service`

It also stops:
- `gemma4-vllm.service`
- `nemotron-sglang.service`
- `muse-glimmer.service`

Notes:
- `rag-embed.service` now serves `qwen3-embedding-0_6b-q8_0` on `http://127.0.0.1:8001/v1/embeddings`.
- `rag-rerank.service` now serves `qwen3-reranker-0.6b` on `http://127.0.0.1:8002/rerank`.
- `local-reasoner.service` can take a few minutes on a cold start before `http://127.0.0.1:8000/v1/models` is reachable.
- Firecrawl structured extraction depends on that endpoint when `/home/Aaditya/services/firecrawl/.env` points `OPENAI_BASE_URL` at the local reasoner.
- If Firecrawl model env changes, recreate only the API container with `/home/Aaditya/bin/firecrawl-compose up -d --force-recreate api`.

## Gemma Mode

```bash
/home/Aaditya/bin/ai-profile gemma
```

This keeps the local Gemma server hot:
- `gemma4-vllm.service`

Current target:
- `/home/Aaditya/models/RedHatAI-gemma-4-26B-A4B-it-NVFP4`
- served model name: `gemma4-26b-a4b-nvfp4`
- NVFP4 GEMM backend: `cutlass`
- MoE backend selection: auto

Verified local compatibility notes:
- machine GPU: `RTX 5090 Laptop GPU` (`SM 12.0`, ~24 GB VRAM)
- local runtime: `vllm 0.19.1rc1.dev...` on `CUDA 13.0`
- local `transformers`: `5.5.3`
- the current Red Hat Gemma 4 NVFP4 path is already known to boot on this machine
- the currently verified stable path uses `VLLM_NVFP4_GEMM_BACKEND=cutlass` rather than forcing `marlin`

Evaluated but not kept as the default target:
- `LilaRest/gemma-4-31B-it-NVFP4-turbo`
- `vllm` recognized `Gemma4ForCausalLM` and `modelopt` quantization correctly
- the model still failed to initialize reliably on this laptop GPU due VRAM headroom / CUDA OOM during startup
- the model card's "fits on a single RTX 5090" claim should be treated as desktop 32 GB 5090 guidance, not a guarantee for this 24 GB laptop GPU

It also stops:
- `rag-embed.service`
- `rag-rerank.service`
- `local-reasoner.service`
- `neo4j-memory-mcp.service`

## Nemotron Mode

```bash
/home/Aaditya/bin/ai-profile nemotron
```

This keeps the local SGLang Nemotron server hot:
- `nemotron-sglang.service`

Current target:
- `nvidia/NVIDIA-Nemotron-3.5-Lightning-30B-A3B-NVFP4`
- runtime: `/home/Aaditya/venvs/sglang-cu13/bin/sglang`
- profile recipe: stable non-speculative NVFP4, `--context-length 8192`, `--max-total-tokens 8192`, `--max-running-requests 1`, `--chunked-prefill-size 1024`, `--mem-fraction-static 0.68`, `--cuda-graph-max-bs-decode 4`

Notes:
- the first start will download the Nemotron checkpoint into the local Hugging Face cache because there is no local model directory yet
- the official single-GPU speculative Nemotron recipes (`MTP` and `DSpark`) both OOMed on this 24 GB laptop GPU after the base model loaded, so the managed profile keeps the strongest stable non-speculative path instead
- even the reduced non-speculative path currently fails on this laptop during hybrid state-cache initialization, so treat `ai-profile nemotron` as an experimental retry profile rather than a known-good daily driver

It also stops:
- `rag-embed.service`
- `rag-rerank.service`
- `local-reasoner.service`
- `neo4j-memory-mcp.service`
- `gemma4-vllm.service`
- `qwen38-sglang.service`
- `nemotron-sglang.service`

## Qwen Mode

```bash
/home/Aaditya/bin/ai-profile qwen
```

This keeps the local SGLang Qwen 3.8 server hot:
- `qwen38-sglang.service`

Current target:
- `RadixArk/Qwen3.8-27B-NVFP4`
- runtime: `/home/Aaditya/venvs/sglang-cu13/bin/sglang`
- profile recipe: laptop-tuned single-stream NVFP4, `--attention-backend flashinfer`, `--kv-cache-dtype fp8_e4m3`, `--mamba-ssm-dtype bfloat16`, `--max-mamba-cache-size 1`, `--disable-radix-cache`, `--max-running-requests 1`, `--max-total-tokens 8192`, `--chunked-prefill-size 1024`, `--mem-fraction-static 0.93`, `--cuda-graph-max-bs-decode 1`

Notes:
- this starts from the official RTX 5090 single-stream Qwen 3.8 recipe and then cuts state pressure for the 24 GB laptop by forcing `S=1` radix behavior and a smaller token pool
- the first start will download the Qwen checkpoint into the local Hugging Face cache because there is no local model directory yet
- this is the current best candidate for an SGLang-first local power profile on this machine because official Qwen 3.8 Blackwell single-GPU support exists, while the official Nemotron speculative profiles did not fit the laptop GPU

It also stops:
- `rag-embed.service`
- `rag-rerank.service`
- `local-reasoner.service`
- `neo4j-memory-mcp.service`
- `gemma4-vllm.service`

## Muse Mode

```bash
/home/Aaditya/bin/ai-profile muse
```

This keeps the local Muse Glimmer server hot:
- `muse-glimmer.service`

Current target:
- `/home/Aaditya/models/Muse-Glimmer-30B-KQuant-17GB/muse-glimmer-30B-kquant-17gb.gguf`
- runtime: `/home/Aaditya/.local/opt/llama.cpp-b10513/bin/llama-server`
- profile recipe: GGUF K-quant Muse with `mmproj-kquant.gguf` and local `Muse-Glimmer-30B-DFlash2-Q4_K_M.gguf`
- speculative path: `--spec-type draft-dflash --spec-draft-n-max 15 --model-draft .../Muse-Glimmer-30B-DFlash2-Q4_K_M.gguf`

Notes:
- this is not an NVFP4 path; it is the local 24 GB-targeted GGUF K-quant Muse build
- the current llama.cpp build is `10513`, which is new enough for Muse and the newer local DFlash2 draft path used here
- the promoted managed Muse path measured about `92 tok/s` decode on the local merge-interval benchmark after the DFlash2 upgrade
- Muse emits reasoning separately via `reasoning_content` under llama.cpp server mode, which avoids the Qwen SGLang blank-content parsing issue we hit earlier

It also stops:
- `rag-embed.service`
- `rag-rerank.service`
- `local-reasoner.service`
- `neo4j-memory-mcp.service`
- `gemma4-vllm.service`
