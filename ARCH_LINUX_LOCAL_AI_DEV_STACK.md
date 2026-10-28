# Arch Linux Local AI Dev Stack

## What This Is

This repo documents the local AI engineering environment I run on my Arch Linux machine.

The setup is designed to support:

- local-first coding with OpenCode
- repo-aware retrieval and structural code search
- persistent task and decision memory
- web research, scraping, and browser automation
- local LLM inference and retrieval services
- domain-specific retrieval for frontend and design work

This is a self-hosted developer platform, not just a single model server.

It combines:

- Arch Linux host tooling
- `systemd --user` services for long-running AI runtimes
- Docker Compose services for Firecrawl and related infrastructure
- OpenCode global and repo-local MCP configuration
- repo-local commands, agents, and skills
- shared OpenAI-compatible local model endpoints

## Arch Linux Host

This machine is an Arch Linux host, not a WSL guest.

That matters because the setup depends on:

- native `systemd --user` service management
- direct local GPU access
- local Docker networking and host/container routing
- repo-local binaries and wrapper scripts under `/home/Aaditya/bin`
- a persistent local filesystem layout across repos, models, venvs, and services

## Host Facts

| Item | Value |
| --- | --- |
| OS | Arch Linux (rolling) |
| Shell wrapper style | `zsh` scripts in `/home/Aaditya/bin` |
| Main repo | `/home/Aaditya/ai-stack` |
| GPU | `RTX 5090 Laptop GPU` |
| GPU capability | `SM 12.0` |
| Available VRAM | about `24 GB` |
| Service model | `systemd --user` plus Docker Compose |

## High-Level Architecture

```text
OpenCode
  -> global MCPs
     -> playwright-local
     -> searxng-local
     -> firecrawl-local
     -> neo4j-memory-local
     -> frontend-design-vault
  -> repo-local MCP
     -> graphkv-local
  -> repo-local commands, agents, skills, and plugin logic

Shared local AI infrastructure
  -> rag-embed.service      :8001
  -> rag-rerank.service     :8002
  -> local-reasoner.service :8000  (retrieval profile)
  -> gemma4-vllm.service    :8000  (gemma profile)
  -> nemotron-sglang.service:8000  (nemotron profile)
  -> qwen38-sglang.service  :8000  (qwen profile)

Supporting services
  -> Firecrawl MCP          :3000/mcp
  -> Firecrawl REST API     :3002
  -> Neo4j Memory MCP       :3010/mcp
  -> GraphKV artifacts     graphkv-out/*
  -> Design vault cache     ~/.mcp-skills-vault/.skills-cache/qdrant
```

## Core Components

| Component | Runtime | Entry Point / Endpoint | Purpose |
| --- | --- | --- | --- |
| OpenCode | local client | repo + global config | Main coding and orchestration environment |
| `graphkv-local` | repo-local MCP | `uv run --with-requirements /home/Aaditya/GraphKV-Engine/mcp-server/search_requirements.txt python /home/Aaditya/GraphKV-Engine/mcp-server/search_server.py` | Multi-workspace repo structure, topology, graph drilldown |
| `searxng-local` | global local MCP | `uv run /home/Aaditya/ai-stack/searxng_mcp.py` | Lightweight web search plus local semantic/rerank-assisted ranking |
| `firecrawl-local` | global remote MCP | `http://127.0.0.1:3000/mcp` | Search, scrape, map, extract, browser automation, agentic research |
| Firecrawl REST API | Docker Compose | `http://127.0.0.1:3002` | Direct scrape and extraction API behind the MCP |
| `neo4j-memory-local` | global remote MCP | `http://127.0.0.1:3010/mcp` | Persistent memory, preferences, facts, and reasoning traces |
| `playwright-local` | global local MCP | Playwright MCP binary in `~/.config/opencode/node_modules/.bin` | Browser automation and deterministic UI verification |
| `frontend-design-vault` | global local MCP | `~/.mcp-skills-vault/.venv/bin/python ... skill_vault_mcp.py --transport stdio` | Domain-specific frontend and design retrieval |
| `rag-embed.service` | `systemd --user` | `http://127.0.0.1:8001/v1/embeddings` | Shared local embedding service |
| `rag-rerank.service` | `systemd --user` | `http://127.0.0.1:8002/rerank` | Shared local reranking service |
| `local-reasoner.service` | `systemd --user` | `http://127.0.0.1:8000/v1/models` | Local OpenAI-compatible reasoning endpoint in retrieval mode |
| `gemma4-vllm.service` | `systemd --user` | `http://127.0.0.1:8000/v1/models` | Local Gemma 4 serving in gemma mode |
| `nemotron-sglang.service` | `systemd --user` | `http://127.0.0.1:8000/v1/models` | Local SGLang Nemotron serving in nemotron mode |
| `qwen38-sglang.service` | `systemd --user` | `http://127.0.0.1:8000/v1/models` | Local SGLang Qwen 3.8 serving in qwen mode |

## GPU Runtime Profiles

This machine intentionally uses five managed GPU profiles.

Switch profiles with:

```bash
/home/Aaditya/bin/ai-profile retrieval
/home/Aaditya/bin/ai-profile gemma
/home/Aaditya/bin/ai-profile nemotron
/home/Aaditya/bin/ai-profile qwen
/home/Aaditya/bin/ai-profile muse
```

The switching logic lives in `/home/Aaditya/bin/ai-profile` and uses `systemctl --user` to stop one set of services and start the other.

### Retrieval Profile

Use this for normal repo work and MCP-heavy coding.

Services started:

- `rag-embed.service`
- `rag-rerank.service`
- `local-reasoner.service`
- `neo4j-memory-mcp.service`

Service stopped:

- `gemma4-vllm.service`

Current endpoints and models:

- embeddings: `qwen3-embedding-0_6b-q8_0` on `http://127.0.0.1:8001/v1/embeddings`
- reranker: `qwen3-reranker-0.6b` on `http://127.0.0.1:8002/rerank`
- reasoner: OpenAI-compatible endpoint on `http://127.0.0.1:8000/v1/models`

Operational note:

- `local-reasoner.service` has a real cold-start path and should be treated as healthy only when the OpenAI-compatible endpoint responds, not just when `systemd` says the unit is running.

### Gemma Profile

Use this when the goal is direct local Gemma inference rather than keeping the retrieval stack hot.

Service started:

- `gemma4-vllm.service`

Services stopped:

- `rag-embed.service`
- `rag-rerank.service`
- `local-reasoner.service`
- `neo4j-memory-mcp.service`

Current verified target:

- model path: `/home/Aaditya/models/RedHatAI-gemma-4-26B-A4B-it-NVFP4`
- served model name: `gemma4-26b-a4b-nvfp4`
- backend: `VLLM_NVFP4_GEMM_BACKEND=cutlass`

Important constraint:

- `LilaRest/gemma-4-31B-it-NVFP4-turbo` was evaluated and partially recognized by the local runtime, but it was not stable on this laptop GPU because the model did not have enough VRAM headroom during startup.

### Nemotron Profile

Use this when the goal is direct local SGLang inference experiments on the laptop 5090.

Service started:

- `nemotron-sglang.service`

Services stopped:

- `rag-embed.service`
- `rag-rerank.service`
- `local-reasoner.service`
- `neo4j-memory-mcp.service`
- `gemma4-vllm.service`

Current configured target:

- model path: `nvidia/NVIDIA-Nemotron-3.5-Lightning-30B-A3B-NVFP4`
- runtime: `/home/Aaditya/venvs/sglang-cu13/bin/sglang`
- memory envelope: `--context-length 8192 --max-total-tokens 8192 --max-running-requests 1 --chunked-prefill-size 1024 --mem-fraction-static 0.68`
- decode graph cap: `--cuda-graph-max-bs-decode 4`
- mamba path: `--mamba-ssm-dtype float16`

Operational note:

- the first start will download the Nemotron checkpoint because it is not stored under `/home/Aaditya/models/` yet
- the official single-GPU speculative Nemotron variants were tested on this laptop and failed with CUDA OOM during draft-worker initialization, so they are not the managed default here
- the reduced non-speculative Nemotron path still fails during hybrid state-cache initialization on this laptop, so this profile is kept as an experimental retest path rather than a stable daily profile

### Qwen Profile

Use this when the goal is an SGLang-first single-GPU local model on the laptop 5090.

Service started:

- `qwen38-sglang.service`

Services stopped:

- `rag-embed.service`
- `rag-rerank.service`
- `local-reasoner.service`
- `neo4j-memory-mcp.service`
- `gemma4-vllm.service`

Current configured target:

- model path: `RadixArk/Qwen3.8-27B-NVFP4`
- runtime: `/home/Aaditya/venvs/sglang-cu13/bin/sglang`
- memory envelope: `--kv-cache-dtype fp8_e4m3 --mamba-ssm-dtype bfloat16 --max-mamba-cache-size 1 --disable-radix-cache --max-running-requests 1 --max-total-tokens 8192 --chunked-prefill-size 1024 --mem-fraction-static 0.93`
- decode graph cap: `--cuda-graph-max-bs-decode 1`
- attention backend: `--attention-backend flashinfer`

Operational note:

- this profile is derived from the official single-GPU RTX 5090 Qwen 3.8 recipe and then tightened for the 24 GB laptop by minimizing the GDN state pool pressure

### Muse Profile

Use this when the goal is a consumer-GPU local Muse agent stack rather than an NVFP4 server path.

Service started:

- `muse-glimmer.service`

Services stopped:

- `rag-embed.service`
- `rag-rerank.service`
- `local-reasoner.service`
- `neo4j-memory-mcp.service`
- `gemma4-vllm.service`
- `nemotron-sglang.service`
- `qwen38-sglang.service`

Current configured target:

- model path: `/home/Aaditya/models/Muse-Glimmer-30B-KQuant-17GB/muse-glimmer-30B-kquant-17gb.gguf`
- runtime: `/home/Aaditya/.local/opt/llama.cpp-b10513/bin/llama-server`
- vision projector: `/home/Aaditya/models/Muse-Glimmer-30B-KQuant-17GB/mmproj-kquant.gguf`
- drafter: `/home/Aaditya/models/Muse-Glimmer-30B-KQuant-17GB/Muse-Glimmer-30B-DFlash2-Q4_K_M.gguf`
- speculative path: `--spec-type draft-dflash --spec-draft-n-max 15 --gpu-layers-draft 99`

Operational note:

- this is a GGUF K-quant path, not an NVFP4 path
- the managed Muse profile now uses the newer local DFlash2 GGUF drafter and the newer local llama.cpp build that successfully served it in isolated testing

## OpenCode Configuration Layers

There are two distinct OpenCode configuration layers.

### Global OpenCode Config

Path:

```text
/home/Aaditya/.config/opencode/opencode.json
```

This global config registers:

- `playwright-local`
- `searxng-local`
- `firecrawl-local`
- `neo4j-memory-local`
- `frontend-design-vault`

The important part is that these tools are available across projects, not just inside `ai-stack`.

### Repo-Local OpenCode Config

Path:

```text
/home/Aaditya/ai-stack/opencode.json
```

This repo-local config adds:

- project-specific instructions from `docs/opencode/mcp-workflows.md`
- project-specific instructions from `docs/opencode/runtime-notes.md`
- the repo-local `graphkv-local` MCP
- the repo-local GraphKV plugin at `.opencode/plugins/graphkv.js`

This lets the environment behave differently inside `ai-stack` than it would in a random repo.

## MCP Servers In The Working Setup

### `graphkv-local`

Role:

- structural code graph for this repo
- topology, communities, file/symbol relationships, shortest-path style drilldown

Inputs and artifacts:

- source graph: `graphkv-out/graph.json`
- orientation artifact: `graphkv-out/GRAPH_REPORT.md`
- optional wiki artifact: `graphkv-out/wiki/index.md`
- optional HTML graph: `graphkv-out/graph.html`

Operational note:

- GraphKV only knows what is currently in `graphkv-out/graph.json`; if the repo changes substantially, the graph artifacts need to be rebuilt.

Pinned runtime note:

- the local GraphKV search MCP is provided by `/home/Aaditya/GraphKV-Engine/mcp-server/search_server.py`

### `searxng-local`

Role:

- lightweight web search and cited answer synthesis
- semantic ranking and reranking on top of raw web results

Configuration details from global OpenCode config:

- uses the local shared embedder on `:8001`
- uses the local shared reranker on `:8002`
- runs from `uv run /home/Aaditya/ai-stack/searxng_mcp.py`

This is the low-latency web lookup layer.

### `firecrawl-local`

Role:

- heavy-duty web search, structured scraping, extraction, site mapping, browser automation, and agentic research

Important port distinction:

- MCP endpoint for OpenCode: `http://127.0.0.1:3000/mcp`
- direct REST API: `http://127.0.0.1:3002`

Deployment model:

- Docker Compose project rooted at `/home/Aaditya/services/firecrawl`
- wrapper script: `/home/Aaditya/bin/firecrawl-compose`

Host integrations from `.env`:

- uses the host SearXNG instance at `http://host.docker.internal:8888`
- uses the local OpenAI-compatible reasoner endpoint at `http://host.docker.internal:8000/v1`

Operational note:

- after changing `OPENAI_API_KEY`, `OPENAI_BASE_URL`, or `MODEL_NAME`, recreate only the Firecrawl `api` container with:

```bash
/home/Aaditya/bin/firecrawl-compose up -d --force-recreate api
```

### `neo4j-memory-local`

Role:

- persistent memory layer for session continuity, preferences, decisions, facts, and reasoning traces

Endpoint:

```text
http://127.0.0.1:3010/mcp
```

Important architectural note:

- the memory MCP reuses the shared embedding service instead of hosting its own dedicated embedder

### `playwright-local`

Role:

- deterministic browser automation and UI verification

Why it exists separately from Firecrawl:

- Firecrawl is the better fit for search, scrape, mapping, extraction, and research
- Playwright MCP is the better fit when direct browser interaction itself is the task

### `frontend-design-vault`

Role:

- specialized frontend and design retrieval layer on top of the broader local AI stack

Runtime details:

- root: `/home/Aaditya/.mcp-skills-vault`
- transport: local `stdio` MCP server
- embeddings: shared endpoint on `:8001`
- reranking: shared endpoint on `:8002`
- vector storage: local Qdrant cache in `~/.mcp-skills-vault/.skills-cache/qdrant`

This is a domain-specific extension, not the central runtime plane.

## Repo-Local Workflow Layer

This repo does more than register MCPs. It also defines workflow logic for how the assistant should think and route work.

### Instructions

Important instruction files:

- `AGENTS.md`
- `docs/opencode/mcp-workflows.md`
- `docs/opencode/runtime-notes.md`

These encode:

- which MCP to use for which kind of question
- when to prefer graph search over grep
- how to pair web search with structured scraping
- how to keep memory, graph, web, and retrieval responsibilities separate

### Repo Commands

Repo-local command files include:

- `/graph-report`
- `/graph-query`
- `/graph-path`
- `/refresh-graph`
- `/repo-research`
- `/mcp-audit`

These are convenience entry points for graph refresh, topology queries, repo research, and MCP auditing.

### Repo Agents

Project-local agents include:

- `mcp-orchestrator`
- `mcp-researcher`
- `repo-surgeon`

These help keep the main assistant focused on synthesis while delegating broad retrieval or narrow edits.

### Repo Skills

Project-local skills include:

- `llm-council`
- `mcp-research`
- `project-bootstrap`
- `repo-triage`

These package repeatable workflows for multi-agent reasoning, MCP research, bootstrapping, and routing.

## Retrieval and Routing Strategy

The stack is opinionated about routing.

For repo-internal work, the preferred order is:

1. read obvious local files directly
2. use GraphKV when structure or relationships matter
3. use Neo4j memory if prior decisions or continuity matter
4. use SearXNG or Firecrawl only for external information

For external docs and live web work, the preferred order is:

1. use Firecrawl search when discovery quality matters
2. use SearXNG when a lightweight answer or quick shortlist is enough
3. use Firecrawl map when the right docs page is not obvious
4. use Firecrawl scrape or extract when the target page is known
5. use Playwright or Firecrawl agent only when simpler retrieval is not enough

This separation is intentional:

- GraphKV owns structural truth about the repo
- Neo4j memory owns durable memory and continuity
- shared embeddings and reranking own semantic relevance filtering
- SearXNG and Firecrawl own live web retrieval

## Developer Workflow On This Machine

A normal coding session usually looks like this:

1. switch the GPU to retrieval mode with `/home/Aaditya/bin/ai-profile retrieval`
2. open the target repo in OpenCode
3. use GraphKV orientation artifacts or graph queries to get structural context fast
4. use memory only if there is likely prior context worth recovering
5. use Firecrawl or SearXNG for external docs and current web information
6. use Playwright when a browser flow needs deterministic interaction or verification
7. use the frontend design vault when the task is specifically UI/design-system heavy

If the goal changes from retrieval-heavy coding to direct local inference experiments, the GPU can be flipped into Gemma mode.

## Operational Runbook

### Switch To Retrieval Mode

```bash
/home/Aaditya/bin/ai-profile retrieval
```

### Switch To Gemma Mode

```bash
/home/Aaditya/bin/ai-profile gemma
```

### Switch To Nemotron Mode

```bash
/home/Aaditya/bin/ai-profile nemotron
```

### Switch To Qwen Mode

```bash
/home/Aaditya/bin/ai-profile qwen
```

### Switch To Muse Mode

```bash
/home/Aaditya/bin/ai-profile muse
```

### Show Current Service State

`ai-profile` already prints the status of:

- `gemma4-vllm.service`
- `nemotron-sglang.service`
- `qwen38-sglang.service`
- `muse-glimmer.service`
- `rag-embed.service`
- `rag-rerank.service`
- `local-reasoner.service`
- `neo4j-memory-mcp.service`

### Recreate The Firecrawl API Container After Model Env Changes

```bash
/home/Aaditya/bin/firecrawl-compose up -d --force-recreate api
```

### Rebuild GraphKV Artifacts When The Repo Structure Changes

Use the repo-local graph refresh command or the associated scripts in `.opencode/scripts/`.

## Constraints And Design Choices

- retrieval mode is the default because it keeps the shared embedder, reranker, reasoner, and memory MCP hot together
- gemma mode is intentionally separate because the laptop GPU does not have enough comfortable headroom to co-run everything at once
- nemotron mode is intentionally separate for the same reason and uses a tighter single-GPU Blackwell memory envelope than the Gemma path
- qwen mode is the current best SGLang-first local-model candidate because it has an official single-GPU Blackwell recipe, unlike the current Nemotron fit on this laptop
- muse mode is the best non-NVFP4 local agentic alternative because the target model, multimodal projector, and DFlash drafter are already present on disk in 24 GB-friendly GGUF form
- non-default single-GPU model services such as `gemma4-vllm.service`, `nemotron-sglang.service`, and `muse-glimmer.service` stay disabled at login so retrieval remains the actual startup profile
- GraphKV is treated as structural truth, not a memory system
- memory is treated as a separate truth type from code structure
- live web retrieval is kept separate from both graph and memory
- shared embeddings and reranking are reused across multiple tools instead of duplicated per subsystem

## Why This Is Resume-Worthy

This setup demonstrates more than personal tinkering.

It shows end-to-end ownership across:

- local AI infrastructure
- GPU-aware runtime orchestration
- retrieval system design
- service integration
- developer workflow design
- operational documentation
- evaluation and regression protection

## Resume Framing

### Honest One-Line Description

Built and operated a self-hosted AI developer platform on Arch Linux that combined local LLM inference, retrieval services, MCP-based tooling, repo-aware automation, and domain-specific knowledge retrieval.

### Project Summary

Designed and maintained a local-first AI engineering environment on Arch Linux for coding, retrieval, research, and automation. The stack combined OpenCode, multiple MCP servers, shared embedding and reranking infrastructure, local model serving, Dockerized scraping services, persistent memory, and repo-specific workflow automation into a unified developer setup optimized for a single laptop GPU.

### Resume Bullets

- Architected a self-hosted AI engineering environment on Arch Linux using OpenCode, MCP integrations, local model serving, and GPU-aware runtime profiles.
- Built a dual-profile local inference strategy that switched a single `RTX 5090 Laptop GPU` between a retrieval-optimized service stack and a local Gemma 4 serving stack.
- Integrated repo graph search, persistent memory, browser automation, web scraping, and search systems into one developer workflow with clear routing boundaries between structural, memory, and web retrieval.
- Reused shared OpenAI-compatible embedding and reranking endpoints across multiple tools instead of duplicating retrieval infrastructure per service.
- Operated a mixed `systemd --user` and Docker Compose environment for local AI services, including health-aware model serving and targeted container recreation for configuration changes.
- Added a domain-specific frontend/design retrieval vault backed by local vector storage, reranking, corpus cleanup, and regression testing.

### Keywords

Arch Linux, systemd, Docker Compose, Python, zsh, CUDA, vLLM, Gemma, embeddings, reranking, MCP, Qdrant, Neo4j, GraphKV, Firecrawl, SearXNG, browser automation, RAG, AI developer tooling

## How To Describe It Honestly In Interviews

The accurate framing is:

- I built and integrated the platform around existing open-source components and my own wrappers, routing rules, docs, custom retrieval layers, and workflow automation.

The inaccurate framing would be:

- claiming authorship of upstream projects like Firecrawl, GraphKV, Neo4j, or Playwright themselves.

The strongest honest claim is that I designed, integrated, operated, tuned, and documented the whole working system as a coherent local developer platform.
