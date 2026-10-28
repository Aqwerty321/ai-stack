# ai-stack

My self-hosted AI engineering platform on one laptop (Arch Linux, RTX 5090 Laptop GPU with 24 GB). It runs local
LLMs, embeddings and reranking as managed services, gives three coding-agent clients (OpenCode, Claude Code and VS Code
Copilot) one shared set of MCP tools, and lets long GPU batch jobs take the whole GPU and hand it back safely.

This repo is the configuration, wrappers, service units, agent instructions and docs for that setup. It is a personal
system, not an installable product: paths assume my machine.

## What it does

**GPU model services as switchable profiles.** Each model server (vLLM or llama.cpp) is a systemd user service.
[`bin/ai-profile`](bin/ai-profile) switches between profiles, since only one large model fits in 24 GB at a time:

| Profile | Services | Use |
|---|---|---|
| `retrieval` | embeddings `:8001`, reranker `:8002`, small reasoning LLM `:8000`, graph-memory MCP | everyday agent work: search, memory, RAG |
| `gemma`, `muse`, `ornith9` | one larger LLM on `:8000` (OpenAI-compatible) | local coding and chat models |
| `voicechat` | realtime speech-to-speech on `NeMo-Speech.cpp` | voice agent |
| `trellis2` | image-to-3D generation | 3D assets |
| `blank` | none (boot default) | GPU free for compute jobs |

`ai-profile status` prints the current and boot profile, per-service state and HTTP health, GPU memory and the
processes using it, any running GPU job, free disk against a floor, and the last backup.

**GPU job guard.** [`bin/gpu-exclusive`](bin/gpu-exclusive) runs one batch job with the whole GPU:

```bash
gpu-exclusive -n eval -t 7200 -m 32 -- python run_eval.py
```

It records which model services are running, stops them under a shared lock, and runs the job in a transient systemd
unit with a time limit and a host-memory limit. When the job ends, the unit's `ExecStopPost` restarts exactly the
services that were running before, one at a time, and waits for each to pass its HTTP health check. Because recovery is
owned by systemd, it still happens if the agent or terminal that started the job crashes. Implementation:
[`scripts/surface_lifting/gpu_runtime.py`](scripts/surface_lifting/gpu_runtime.py).

**One MCP layer for every agent client.** OpenCode ([`opencode.json`](opencode.json)), Claude Code
([`.mcp.json`](.mcp.json), [`CLAUDE.md`](CLAUDE.md)) and VS Code ([`.vscode/mcp.json`](.vscode/mcp.json),
[`.github/`](.github)) share the same servers:

- `graphkv-local`: code-structure graph of the repo ([GraphKV-Engine](https://github.com/Aqwerty321/GraphKV-Engine))
- `neo4j-memory-local`: persistent graph memory shared across all clients, backed by the local embedder
- `searxng-local` ([`searxng_mcp.py`](searxng_mcp.py)) and a self-hosted Firecrawl: web search, scraping, extraction
- `time-local`, Playwright, and design and component retrieval servers

[`AGENTS.md`](AGENTS.md) and [`docs/opencode/mcp-workflows.md`](docs/opencode/mcp-workflows.md) tell every agent which
tool fits which kind of question, so they use the cheap local sources before the web.

**Guardrails.** [`claude/hooks/laya-guard.py`](claude/hooks/laya-guard.py) screens every web and scrape result for
prompt injection: a regex prefilter finds text aimed at an AI agent, a local classifier service
([Laya](docs/laya/LAYA_DECISION_SERVICE_DESIGN.md), CPU-only, always on) judges those windows, and a warning is added to
the agent's context. It is advisory by design: the classifier has high recall but too many false positives on benign
docs to block on its own, and its wrong verdicts are logged for relabeling. A session hook
([`claude/hooks/ai-stack-session.sh`](claude/hooks/ai-stack-session.sh)) warns when the code graph is stale or the
retrieval services are down.

**Operations.** [`bin/disk-guard`](bin/disk-guard) and its timer warn below 120 GiB free and stop research jobs below
100 GiB. Local model benchmarks and eval suites live in [`scripts/`](scripts) and [`eval/`](eval).

## Layout

| Path | Contents |
|---|---|
| `bin/` | `ai-profile`, `gpu-exclusive`, `disk-guard`, and the start wrappers each service runs (copies of `~/bin`) |
| `systemd/` | systemd user units for the model servers, MCP bridges and timers (copies of `~/.config/systemd/user`) |
| `claude/hooks/` | Claude Code hooks (copies of `~/.claude/hooks`) |
| `.opencode/`, `.github/`, `.vscode/`, `.mcp.json` | per-client agents, commands, skills and MCP registration |
| `docs/` | runtime notes, MCP workflows, Laya design, VoiceChat profile |
| `scripts/`, `eval/` | Laya training and evaluation, local model benchmarks, VoiceChat clients |

## Docs

- Full system write-up: [`ARCH_LINUX_LOCAL_AI_DEV_STACK.md`](ARCH_LINUX_LOCAL_AI_DEV_STACK.md)
- Profiles and per-model serving recipes: [`LOCAL_AI_PROFILES.md`](LOCAL_AI_PROFILES.md)
- Runtime notes and operational lessons: [`docs/opencode/runtime-notes.md`](docs/opencode/runtime-notes.md)
- Laya decision service: [`docs/laya/LAYA_DECISION_SERVICE_DESIGN.md`](docs/laya/LAYA_DECISION_SERVICE_DESIGN.md)
- VoiceChat profile: [`docs/voicechat/README.md`](docs/voicechat/README.md)
