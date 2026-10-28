# Runtime Notes

This repo normally works best in retrieval mode:

```bash
/home/Aaditya/bin/ai-profile retrieval
```

That keeps these services hot:

- `rag-embed.service`
- `rag-rerank.service`
- `local-reasoner.service`
- `neo4j-memory-mcp.service`

- `rag-embed.service` now serves `qwen3-embedding-0_6b-q8_0` on `http://127.0.0.1:8001/v1/embeddings`.
- `rag-rerank.service` now serves `qwen3-reranker-0.6b` on `http://127.0.0.1:8002/rerank`.

`local-reasoner.service` is a vLLM-backed NVFP4 model and has a noticeable cold-start path. The first startup can spend several minutes downloading weights, compiling, and warming the model before `http://127.0.0.1:8000/v1/models` responds. Treat the service as healthy only after the OpenAI-compatible endpoint answers requests, not just after systemd shows it as running.

Firecrawl reads its LLM-assisted extraction settings from `/home/Aaditya/services/firecrawl/.env` when the `api` container is created. This affects schema extraction, prompt-driven extraction, and other agentic research paths that rely on the configured model. After changing `OPENAI_API_KEY`, `OPENAI_BASE_URL`, or `MODEL_NAME`, recreate the `api` container so the new env is applied:

```bash
/home/Aaditya/bin/firecrawl-compose up -d --force-recreate api
```

This is enough for Firecrawl model changes. The rest of the Firecrawl stack does not need to be restarted unless other services changed.

VoiceChat mode is:

```bash
/home/Aaditya/bin/ai-profile voicechat
```

That starts `nemotron-voicechat.service`, which currently serves the official `NeMo-Speech.cpp` realtime VoiceChat stack on `http://127.0.0.1:8080` and `ws://127.0.0.1:8080/v1/realtime`.

Current target:
- bundle: `/home/Aaditya/models/NVIDIA-NemotronLabs-VoiceChat-11B-NVFP4-GGUF`
- runtime: `/home/Aaditya/.local/opt/NeMo-Speech.cpp/build/cuda-s2s/bin/nemo-speech`
- wrapper: `/home/Aaditya/bin/nemotron-voicechat-start`

Why this path exists:
- the older Python/container VoiceChat docs under `NVIDIA-NeMo/Speech` still document an 80 GB-class workflow for the reference runtime
- the current official `NVIDIA/NeMo-Speech.cpp` runtime explicitly supports local NemotronLabs VoiceChat conversion and serving, including `nvfp4` for the LLM backbone, and is the practical path for this 24 GB laptop GPU

Current managed tuning for this laptop:
- `S2S_TTS_POSITIONS_PER_SEQUENCE=4096`
- `RNNT_MAX_AGENT_RESPONSE_SEC=12`
- `--s2s-max-streams 1`

Measured local behavior:
- clean-start health ready time is about `6s`
- stable idle VRAM after a short soak is about `12.8 GB used`
- turn-taking sample first audio arrived in about `357.5 ms`
- higher EarTTS KV-budget probes on the same NVFP4 bundle still loaded: about `17.3 GB` used at `3072`, about `17.8 GB` used at `4096`

Current caveats:
- longer file-driven sessions can still hit `S2SStream: step budget exhausted`
- after an internal inference failure, later sessions can sometimes report `S2SPipeline: maximum concurrent streams reached` until the service is restarted
- the local voice client now has compaction and Neo4j memory tool plumbing; compaction-triggered rollover was observed, but natural spoken memory-tool selection still needs stronger validation or a more tool-friendly prompting strategy
- this means the NVFP4 profile is functionally working and benchmarkable, but should still be treated as an early managed profile rather than a polished daily-driver voice appliance

Manual testing path:
- `/home/Aaditya/bin/voicechat-browser` starts a localhost browser bridge on `http://127.0.0.1:8090/`; this is the preferred path for real microphone and playback testing because the browser owns the audio devices directly, and the current UI includes a richer single-page frontend with transcripts, tool logs, memory status, and hold-to-talk controls
- `/home/Aaditya/bin/voicechat-live [session-name]` starts a microphone-driven session with transcript, function-call, conversation, and received-audio logging under `out/ai-stack/voicechat-live/<session-name>/`
- `/home/Aaditya/bin/voicechat-tui [session-name]` wraps the same live session in a `rich` terminal UI with live panes for user transcript, agent transcript, tool calls, recent conversation log, and memory/session status; controls include mute (`m`), push-to-talk (`p`), pane selection (`1`/`2`/`3`), and pane scroll (`j`/`k`)

Gemma mode is:

```bash
/home/Aaditya/bin/ai-profile gemma
```

The Gemma service start script currently targets `/home/Aaditya/models/RedHatAI-gemma-4-26B-A4B-it-NVFP4`.

The current stable local Gemma path uses `VLLM_NVFP4_GEMM_BACKEND=cutlass` and does not force a `--moe-backend` override. On this machine, that path successfully serves `gemma4-26b-a4b-nvfp4` at `http://127.0.0.1:8000/v1/models`.

`LilaRest/gemma-4-31B-it-NVFP4-turbo` was evaluated on this machine with `vllm-nightly` on CUDA 13.0 and Blackwell-class FP4 support. `vllm` recognized the model and `modelopt` quantization correctly, but the service failed to initialize reliably because the local `RTX 5090 Laptop GPU` only exposes about 24 GB VRAM and did not have enough startup headroom for the 31B turbo checkpoint in the normal desktop environment. Treat the model card's RTX 5090 fit claim as guidance for desktop 32 GB 5090-class setups, not as a guaranteed fit for this laptop GPU.

Nemotron mode is:

```bash
/home/Aaditya/bin/ai-profile nemotron
```

That starts `nemotron-sglang.service`, which currently serves `nvidia/NVIDIA-Nemotron-3.5-Lightning-30B-A3B-NVFP4` through `/home/Aaditya/venvs/sglang-cu13/bin/sglang` on `http://127.0.0.1:8000/v1/models`.

The current wrapper uses the strongest stable non-speculative Nemotron recipe that fit this 24 GB laptop GPU: `--mamba-ssm-dtype float16 --context-length 8192 --max-prefill-tokens 8192 --max-running-requests 1 --max-total-tokens 8192 --chunked-prefill-size 1024 --mem-fraction-static 0.68 --cuda-graph-max-bs-decode 4`.

The first Nemotron start will download the main checkpoint into the local Hugging Face cache because there is no repo-local model directory for it yet.

The official single-GPU speculative Nemotron variants were tested here and both failed on this laptop after the base NVFP4 model loaded: `DSpark` OOMed during draft-worker rotary-cache initialization, and `MTP` OOMed during draft-worker MoE weight allocation.

The reduced non-speculative Nemotron path also failed here during hybrid state-cache initialization, so `nemotron-sglang.service` should be treated as an experimental retry path, not a verified stable profile.

Qwen mode is:

```bash
/home/Aaditya/bin/ai-profile qwen
```

That starts `qwen38-sglang.service`, which currently serves `RadixArk/Qwen3.8-27B-NVFP4` through `/home/Aaditya/venvs/sglang-cu13/bin/sglang` on `http://127.0.0.1:8000/v1/models`.

The current wrapper starts from the official single-GPU RTX 5090 Qwen 3.8 recipe and then tightens it for the 24 GB laptop GPU: `--attention-backend flashinfer --kv-cache-dtype fp8_e4m3 --mamba-ssm-dtype bfloat16 --max-mamba-cache-size 1 --disable-radix-cache --context-length 8192 --max-prefill-tokens 8192 --max-running-requests 1 --max-total-tokens 8192 --chunked-prefill-size 1024 --mem-fraction-static 0.93 --cuda-graph-max-bs-decode 1`.

The first Qwen start will download the checkpoint into the local Hugging Face cache because there is no repo-local model directory for it yet.

Muse mode is:

```bash
/home/Aaditya/bin/ai-profile muse
```

That starts `muse-glimmer.service`, which currently serves `/home/Aaditya/models/Muse-Glimmer-30B-KQuant-17GB/muse-glimmer-30B-kquant-17gb.gguf` through `/home/Aaditya/.local/opt/llama.cpp-b10513/bin/llama-server` on `http://127.0.0.1:8000/v1/models`.

The current wrapper uses the local quantized Muse stack with both companions already on disk: `mmproj-kquant.gguf` for multimodal input and `Muse-Glimmer-30B-DFlash2-Q4_K_M.gguf` for the newer local draft path.

This is a GGUF K-quant path, not an NVFP4 path.

The current local Muse profile successfully loads the newer DFlash2 GGUF drafter on this laptop and serves the OpenAI-compatible endpoint without downloading additional weights.

The promoted managed Muse profile now decodes at about `92 tok/s` on the local merge-interval benchmark, which was materially faster than the earlier local DFlash baseline on this machine.

`blank` is the login default (2026-10-20): every GPU model service (`rag-embed`, `rag-rerank`, `local-reasoner`, and the exclusive servers including `nemotron-voicechat`) is disabled at boot, so the GPU starts empty. Only `neo4j-memory-mcp`, `neo4j-memory-docker`, `laya-decide`, Firecrawl and Steel start at login. Run `ai-profile retrieval` before work that needs embedding-backed tools (memory search, SearXNG reranking, react-bits, frontend-design-vault). Until 2026-10-20 `nemotron-voicechat` was also enabled, and its `Conflicts=` stopped rerank and the reasoner at boot, so logins silently came up in voicechat. `ai-profile status` shows the current and boot profile, service health, GPU memory and processes, any `gpu-exclusive` job, free disk and the last Drive backup in one view.

`graphkv-local` only knows what is in each workspace's `graphkv-out/graph.json`. Rebuild the graph artifacts if major repo structure changes make GraphKV answers look stale.

Before rebuilding, inspect `.graphkvignore` and append repo-specific generated, vendored, dependency, fixture, cache, build-output, or data-heavy folders that should not be indexed. The refresh script also accepts repeatable `--ignore PATTERN` flags and appends them before the build.

The local GraphKV search MCP is provided by `/home/Aaditya/GraphKV-Engine/mcp-server/search_server.py` and is launched through `/home/Aaditya/GraphKV-Engine/mcp-server/run_search_server.sh`. The wrapper changes into the GraphKV server directory before invoking `uv`, which avoids workspace-local `uv` version pins from breaking MCP startup when a repo requires a different `uv` version.

It is an additive search surface: it exposes graph and symbol lookup while leaving native file, shell, edit, web, memory, browser, and other MCP capabilities available to the agent.

## Laya Decision Service (`laya-decide.service`)

`laya-decide.service` is an always-on local System-1 typed-decision router (the open,
self-hosted analog to TypeSafe Jev), serving `laya` v0.3.6 (`convaiinnovations/laya`
checkpoints) through a FastAPI daemon on `http://127.0.0.1:8008`.

- Wrapper `/home/Aaditya/bin/laya-decide-start` runs venv `/home/Aaditya/venvs/laya`
  (Python 3.12, torch 2.13.0+cu130) against `/home/Aaditya/bin/laya-decide-server.py`.
- It runs on **CPU by default**. Measured reality: in retrieval mode `local-reasoner`
  (vLLM) holds ~19 GB and only ~4-5 GB VRAM is free and fragments, so a CUDA Laya OOMs and
  falls back to CPU anyway. Warm CPU latency is ~260 ms/call with `OMP_NUM_THREADS`,
  `MKL_NUM_THREADS`, and `LAYA_TORCH_THREADS` capped to 6; uncapped torch oversubscribed
  cores and produced ~4 s tail-latency spikes co-tenant with the retrieval services.
- Because it is CPU-only and profile-independent, it is managed by a new
  `always_on_services` group in `/home/Aaditya/bin/ai-profile`: started in every profile and
  never stopped, so gates/routing decisions survive retrieval/gemma/muse/ornith9 switches.
  Its unit intentionally has no `Conflicts=` with the exclusive model services.
- Startup warmup preloads checkpoints and probes each installed pack's question shape;
  `/healthz` reports `router_ready:false` until warm (~30-60 s), then true.
- HTTP surface: `/healthz`, `/packs`, `/decide` (generic state+questions), `/gate/{pack}`
  (named versioned decision pack -> thresholded verdict envelope), `/feedback` (labeled
  correction -> feedback corpus), `/metrics`.
- Decision packs live in `/home/Aaditya/bin/laya-packs/*.json` — 9 retrieval-stack reflexes:
  `route_mcp`, `web_scope`, `repo_structural`, `memory_worthy`, `done_verify`, `clarify`,
  `guard`, `rag_triage`, `tool_risk`. (The old `escalate`/`route_model` idea was dropped:
  `local-reasoner` :8000 is only Firecrawl's extraction backend, never a decision target.)
  Decisions are logged to
  `/home/Aaditya/ai-stack/out/ai-stack/laya/decisions.jsonl` for future calibration/fine-tune.
- CLI `laya-gate` (`/home/Aaditya/bin/laya-gate`) and importable `scripts/laya_client.py`
  wrap the service. `laya-gate` exit codes compose in shell gates: 0 proceed, 2 hold, 3 abstain,
  1 error. `laya-gate <pack> --feedback <correct-verdict>` records a labeled correction.
  Pack accuracy is scored by `scripts/laya_eval.py` against `eval/laya_packs_eval.json`
  (hardened to **89 cases**; **78/89 = 88%** after policy auto-optimization).
- Recursive self-improvement loop (policy layer, calibration-safe, GPU-free):
  `/feedback` -> `out/ai-stack/laya/feedback.jsonl` -> `scripts/laya_ingest_feedback.py`
  (folds into eval, dedup) -> `scripts/laya_optimize.py` (caches raw answers once, then
  coordinate-descends numeric noul/score thresholds, tracks `ece_score`, writes back packs
  with `.bak` + version bump) -> `scripts/laya_eval.py` re-verifies live. `route_mcp` residual
  misses are a 6-way `choice` model-margin ceiling that thresholds cannot fix.
  `scripts/laya_finetune.py` is an EXPERIMENTAL gated scaffold for the weight layer only
  (refuses without `--i-understand-this-is-experimental`, >=500 cases, held-out ECE gate).
- Full design: `docs/laya/LAYA_DECISION_SERVICE_DESIGN.md`. Ports on this box: 8000 reasoner,
  8001 embed, 8002 rerank, 8008 laya-decide.

## TRELLIS Text→3D + Laya God-Router (`trellis-3d.service`)

On-demand, CLI-only local text→3D generation, orchestrated by Laya and wired into
`ai-profile` + systemd. Full doc: `docs/trellis/TRELLIS_3D_WORKFLOW.md`.

- `trellis-3d.service` is an on-demand GPU daemon on `http://127.0.0.1:8010` (port joins
  8000 reasoner / 8001 embed / 8002 rerank / 8008 laya-decide). Its unit `Conflicts=` every
  other GPU model service, and it is left **disabled** — the orchestrator starts/stops it.
- Wrapper `/home/Aaditya/bin/trellis-3d-start` runs venv `/home/Aaditya/venvs/trellis`
  (py3.12, `torch==2.13.0+cu130`, the locally proven build whose arch list includes `sm_120`)
  with `ATTN_BACKEND=flash_attn`, `SPCONV_ALGO=native`, `TORCH_CUDA_ARCH_LIST=12.0`,
  `CUDA_HOME=/opt/cuda` (13.2). Model `microsoft/TRELLIS-text-xlarge` via
  `TrellisTextTo3DPipeline` (TRELLIS **v1** — TRELLIS.2 is image-only).
- God-router `/home/Aaditya/bin/ai-god-route` runs the full lifecycle: snapshot active
  profile → `ai-profile blank` (free GPU) → VRAM check → start daemon → health-poll/retry →
  generate → write `generated_3d_models/<task>/{model.glb,metadata.json}` → open the `.glb`
  in Flatpak Blender (`org.blender.Blender`, dynamically detected, sandbox dir granted via
  `flatpak override --user --filesystem=...`) → stop daemon → restore the previous profile
  (which reconnects the retrieval MCP services).
- MCP surface: `trellis-3d-local` in `opencode.json` (stdio `scripts/trellis/trellis_mcp.py`,
  tool `generate_3d_model`). MCP config is read at OpenCode startup only — one restart needed.
- Laya pack `route_generate.json` detects text→3D requests (verdict `trellis_3d`), leaving the
  6-way `route_mcp` ceiling untouched.
- Install: `scripts/trellis/install_trellis.sh` + `finish_install.sh`; per-phase logs in
  `out/ai-stack/trellis-install/`. kaolin must be **built from source** (`IGNORE_TORCH_VER=1`);
  prebuilt wheels are ABI-locked to torch 2.7.1/cu128 and fail against torch 2.13+cu130.
  `spconv-cu126` (cu120 has no cp312 wheel). CUDA extensions (`nvdiffrast`, `diffoctreerast`
  `--recurse-submodules`, `diff-gaussian-rasterization` from `mip-splatting`) compiled for sm_120.
- Attention backend: TRELLIS sparse attention only accepts `xformers`/`flash_attn`, and the
  `xformers==0.0.35` wheel has **no sm_120 kernels**. So `flash-attn 2.8.3` is built from source
  for sm_120 via `scripts/trellis/build_flash_attn.sh` (use `FLASH_ATTN_CUDA_ARCHS=120`, NOT
  `TORCH_CUDA_ARCH_LIST`; gcc-15 host via `-ccbin g++-15`; `FLASH_ATTENTION_FORCE_BUILD=TRUE`;
  ~13 min). FA2's varlen C++ kernels run on sm_120 (SM80-compatible `mma.sync`); FA4/CuTe does
  not. All compiler work uses gcc-15 because CUDA 13.2 `nvcc` rejects gcc>15 / clang>=22.
- `ai-profile`'s trailing `systemctl status` is now `|| true` so profile switches (esp.
  `blank`) return 0 even when units are inactive; otherwise `ai-god-route` aborted on a false
  failure. Verified end-to-end: `ai-god-route` freed the GPU, generated a `.glb` in ~49s on
  sm_120, opened it in Flatpak Blender, and restored the prior profile (exit 0).

## Claude Code Wiring

Claude Code runs side by side with OpenCode over the same MCP stack. See `CLAUDE.md` for the full map.

- User-scope MCPs (`~/.claude.json`, registered with `claude mcp add-json -s user`): `playwright-local`, `searxng-local`, `firecrawl-local`, `neo4j-memory-local`, `react-bits-local`, `frontend-design-vault`, `time-local`. Project MCPs: `.mcp.json` (`graphkv-local`, `trellis-3d-local`). `build-graphkv` and `opencode-project-init` write the `graphkv-local` entry into `.mcp.json`.
- Health check: `claude mcp list`. MCP config is read at session start; restart Claude Code after changing it.
- Python MCP servers using `from mcp.server.fastmcp import FastMCP` must pin `mcp<2` (2.x renamed FastMCP to MCPServer). Pinned in GraphKV, `trellis_mcp.py`, and `react_bits_mcp.py`; an unpinned `uv run --script` server breaks as soon as uv resolves a fresh env.
- Hooks live in `~/.claude/hooks/` (session context + PATH, Laya guard on web output, desktop notifications); configured in `~/.claude/settings.json`.
- `firecrawl-mcp` is pinned to `3.20.6` in `/home/Aaditya/bin/firecrawl-mcp-http` (backup `.bak-20261017`). Releases `>=3.21` send hosted-only search fields (`highlights`, `toolDetail`, `domainTools`, `alexandria` sources) that the self-hosted API on :3002 rejects (`Invalid request body`) or answers with empty data, and they drop `firecrawl_extract`. Verify search, scrape, and extract against the local API before bumping.

## Exclusive GPU jobs (`gpu-exclusive`)

`/home/Aaditya/bin/gpu-exclusive` wraps `scripts/surface_lifting/gpu_runtime.py` as a general CLI (added 2026-10-17). It runs one command in a transient systemd user unit under the shared GPU lock (`~/.cache/3d-lab/gpu.lock`), stops the active retrieval GPU services (`rag-embed`, `rag-rerank`, `local-reasoner`), and restores exactly that set from `ExecStopPost`, waiting for each `/health` endpoint. Restoration does not depend on the caller surviving. Measured: a smoke cycle took 80 s end to end, with the worker seeing 22.2 GB free VRAM versus ~4 GB in retrieval mode. The worker is killed if free VRAM drops below the 3 GB reserve or the timeout expires; host RAM is capped by `-m`. Per-run state and logs are in `~/.cache/3d-lab/gpu-runs/<timestamp>-<name>/`.

## Disk space and Drive backup (2026-10-19)

- `research-backup.timer` (nightly at 03:30, idle I/O priority) copies the folders listed in `~/.config/research-backup/paths` to `gdrive:ai-stack-backup/` with `rclone copy`. It is one-way: deleting a local file never deletes its Drive copy. Log: `~/.cache/research-backup/backup.log`.
- `disk-guard.timer` runs every 15 minutes and sends a desktop warning below 120 GiB free on `/home`. `l3_isolated.py` and `generate_inputs.py` stop taking new work below 100 GiB (`DISK_GUARD_FLOOR_GIB`).
- To free space: `research-offload [-n] <dir>` uploads, verifies hashes (`rclone check`), then removes the local copy and leaves `<dir>.OFFLOADED.txt`. Restore with `research-fetch <dir>`; list offloaded folders with `research-fetch --list`.

## Web search engines (SearXNG :8888)

Fixed 2026-10-18. Root causes of "search returns nothing":

- Upstream SearXNG ships `google`, `bing`, `openalex` and `crossref` with `disabled: true`. Listing an engine in `use_default_settings.engines.keep_only` does not enable it; it also needs an `engines:` entry with `disabled: false`. Google had been listed but never enabled, so general search depended on DuckDuckGo and Brave alone.
- From this machine DuckDuckGo always times out (10 s), Brave gets rate-limited under agent load, Startpage and Google Scholar return CAPTCHAs, Qwant and Mojeek return access denied.
- Any request with `categories=general` waits for DuckDuckGo's 10 s timeout, and SearXNG adds a category's engines to explicitly named ones. Clients therefore name engines and send no category.

Current wiring:

- `/etc/searxng/settings.yml` (root-owned, backup `settings.yml.bak-20261018`) is edited by `scripts/searxng_enable_engines.py` (idempotent). `search.suspended_times.SearxEngineTooManyRequests: 600` shortens rate-limit suspension from 1 h to 10 min.
- Firecrawl `.env` (backup `.env.bak-20261018`): `SEARXNG_ENGINES=google,bing,brave,wikipedia`, `SEARXNG_CATEGORIES=` (empty). Recreate the `api` container after changes.
- `searxng_mcp.py` general searches send `SEARXNG_GENERAL_ENGINES` (default `google,bing,brave,wikipedia`) without a category; other categories are unchanged.
- Measured: general ~0.5–1.5 s (was 10 s or empty); science ~1.7 s with 49 results from arXiv, Semantic Scholar, OpenAlex and Crossref. General-web result quality is limited while Brave is suspended and Google is blocked; prefer the `science` category for papers.
- Firecrawl search (2026-10-22): Firecrawl sends its default `lang` "en" to SearXNG as `language=en`. On 2026-10-18 Bing returned 0/10 relevant results for `language=en` but 10/10 for `auto`, so a local patch maps `en`/`en-US` to `auto` (`~/services/firecrawl/patches/`, bind-mounted read-only into the `api` container by `docker-compose.override.yml`; rollback and image-update steps in `patches/README.md`). Re-measured 2026-10-22: Bing's junk results are query- and time-dependent and occur with every `language` value (e.g. "vllm sampling parameters documentation" gave 0/10 for en, auto, all and none, while other queries gave 8–10/10), so the patch is harmless but does not fix junk results. The real limit is engine diversity: Google blocked, Brave rate-limited, DuckDuckGo timing out.

## Switching networks (college ethernet / phone hotspot)

Observed 2026-10-18 when switching from college ethernet to a Jio hotspot:

- The Firecrawl containers keep the DNS server that was current when they started, so all scrapes fail (`EAI_AGAIN` inside `firecrawl-api-1`). Fix: `/home/Aaditya/bin/firecrawl-compose up -d --force-recreate`. Do not use `firecrawl-compose restart`: it starts every container at once, the API races RabbitMQ (`ECONNREFUSED :5672`) and exits. If that happens, run `firecrawl-compose up -d api`.
- The Jio hotspot's DNS returns NAT64 IPv6 addresses (`64:ff9b::…`), but IPv6 does not work, so tools that try IPv6 first can fail. Use `curl -4` for one-off checks.
- Search-engine reputation is per public IP. College ethernet (Sify) and Jio mobile (carrier-grade NAT) are both shared and flagged by Google and DuckDuckGo. Bing and the science engines work on both. Scraping official pages directly works on either network.
