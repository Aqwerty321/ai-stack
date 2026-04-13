# Graph + Memory Stack Plan

## Bottom Line

Yes, augmenting the current stack with a structural graph plus persistent memory is feasible.

The version that best fits this machine is not:

- Graphify + full MDEMG + Qdrant + current retrieval stack all introduced at once

The version that best fits this machine is:

- Web plane: existing `SearXNG` + `Firecrawl`
- Structural plane: `Graphify`
- Memory plane: `Neo4j`-backed memory
- Retrieval plane: existing local embedder + reranker
- Reasoning plane: current OpenCode model and/or local Gemma profile

Qdrant is not needed at the start.

## Current Stack Reality

Already running or available now:

- `gemma4-vllm.service` for local Gemma inference
- `rag-embed.service` using `llama.cpp` when the retrieval profile is active
- `rag-rerank.service` using `Qwen3-Reranker-4B` via `vLLM` when the retrieval profile is active
- `searxng_mcp.py` already using the local embedder and reranker for search ranking
- self-hosted `Firecrawl` backend via Docker
- `firecrawl-mcp.service` exposed to OpenCode at `http://127.0.0.1:3000/mcp`

Not currently present:

- `MDEMG`
- `Qdrant`

Important operational constraint:

- Gemma and the GPU-heavy retrieval profile intentionally do not co-run
- the active retrieval profile now keeps the shared embedder, reranker, and memory MCP hot together
- the memory MCP no longer hosts its own embedding model; it reuses the shared `llama.cpp` embedder on `:8001`

## What Changes From The Earlier AI Plan

The original chat was directionally useful, but it assumed a stack that does not exist yet and it blurred too many roles.

The corrected version is:

- `Graphify` is a structural compiler for the codebase, not a long-term memory brain
- persistent memory should be a separate layer, not a duplicate copy of all structural facts
- the current embedder and reranker should remain the relevance gate
- web retrieval should stay separate from code graph and memory retrieval
- `Qdrant` is optional only if `Neo4j` vector retrieval later becomes a real bottleneck

## Recommended Architecture

### 1. Structural Truth: Graphify

Use `Graphify` for:

- AST-derived structure
- file, symbol, and relationship discovery
- repo communities and god-node style topology summaries
- exported artifacts like `GRAPH_REPORT.md`, `graph.json`, and optional wiki output

Use it as:

- an on-demand or scheduled codebase map
- the authoritative structural view of the repo

Do not use it as:

- session memory
- preference memory
- long-term agent state

Best fit with this stack:

- run it explicitly first, not as an always-on hook on day one
- keep its outputs local in the repo
- only later decide whether to expose its MCP server or export into `Neo4j`

### 2. Persistent Memory: Neo4j-Backed Memory

Treat the memory layer as a different truth type from the code graph.

Store in this layer:

- session goals
- architectural decisions discovered while working
- repeated failure modes and fixes
- user preferences
- reasoning traces and task continuity
- links from memory items to relevant code entities

Use `Neo4j` as the memory store first.

Why:

- `Neo4j` already supports vector indexes
- current Cypher `SEARCH` supports vector search plus filtering
- this avoids introducing both `Neo4j` and `Qdrant` before there is evidence that both are needed

Implementation recommendation:

- first choice: `neo4j-agent-memory` as the initial memory layer
- optional later evaluation: actual `MDEMG` if you still want its coding-agent-specific hidden-layer and Hebbian features

Reason for preferring `neo4j-agent-memory` first:

- public docs and MCP support are straightforward
- it supports both local-model embeddings and API-backed embeddings
- it is a smaller operational jump than the full `MDEMG` stack

### 3. Retrieval Gate: Keep The Existing Local Models

Do not replace the current retrieval plane.

Keep using:

- broad semantic recall: local embedder on `:8001`
- hard precision filter: local reranker on `:8002`

Role of this plane in the augmented stack:

- rerank candidates coming from `Graphify`
- rerank candidates coming from memory search
- merge structural, semantic, and memory candidates into a small final context

This means the current retrieval services become shared infrastructure, not a dead-end web-search-only add-on.

### 4. Web Plane: Keep SearXNG + Firecrawl Separate

Do not merge live web retrieval into the code graph or memory graph by default.

Use the existing web plane for:

- current information
- docs lookup
- scraping and extraction

Only persist into memory when the result is curated and worth remembering, for example:

- a stable design decision
- an external API constraint that affected implementation
- a resolved bug root cause

Do not persist raw scrape dumps or whole search result pages into memory automatically.

## Data Ownership

Keep the boundaries sharp.

- `Graphify` owns structural truth about the codebase
- `Neo4j` memory owns persistent task, user, and reasoning memory
- the current embedder and reranker own semantic recall and pruning
- `SearXNG` + `Firecrawl` own live web retrieval

Do not let two systems be authoritative for the same raw fact.

## Retrieval Flow

### Code Question

1. Classify the question as code-structure-heavy.
2. Query `Graphify` output first for communities, exact paths, or neighborhood context.
3. Pull matching memory items from `Neo4j` only if prior decisions or past work are relevant.
4. Convert the candidate set into small text snippets.
5. Use the existing reranker to cut that set down aggressively.
6. Send only the top context to the model.

### Memory Question

1. Query the memory layer first.
2. Expand linked code entities if the answer needs structural proof.
3. Rerank the merged memory + code candidates.
4. Return the smallest useful context.

### Web Question

1. Use `SearXNG` and `Firecrawl`.
2. Rerank with the existing local retrieval pipeline if helpful.
3. Only store the result in memory if it becomes durable operational knowledge.

## Update Flow

### Structural Update

- code changes happen
- `Graphify` updates its local graph artifacts
- a bridge later imports only selected high-signal structure into `Neo4j` if needed

### Memory Update

- the agent finishes work, learns a preference, records a correction, or resolves a bug
- that observation is written directly to the memory graph
- the memory layer stores links back to code entities where available

### Embedding Update

- embeddings are generated asynchronously
- only high-signal nodes are embedded
- no synchronous full-repo re-embedding loop

## What To Embed

Embed only high-signal material.

Good candidates:

- file summaries
- function or class summaries
- community summaries from `Graphify`
- architectural decisions
- recurring fixes
- task observations
- curated docs notes

Skip:

- imports
- trivial variables
- boilerplate directories
- every AST edge
- raw search result dumps
- transient low-value tool chatter

## Qdrant Decision

Do not add `Qdrant` in the first version.

Why:

- `MDEMG` itself is built around `Neo4j` with native vector indexes
- `Neo4j` now supports vector search via Cypher `SEARCH`
- filtered vector search exists in current Neo4j docs
- adding `Qdrant` now would create another place to duplicate semantic state

Re-evaluate `Qdrant` only if one of these becomes true:

- vector scale grows beyond what is comfortable in `Neo4j`
- retrieval latency becomes the primary bottleneck
- you need independent scaling or isolation of vector workloads
- you prove that `Neo4j` graph + vector in one store is operationally getting in the way

For this laptop stack, adding `Qdrant` now would be premature.

## Recommended Phases

### Phase 0: Keep The Current Stack Stable

Do nothing disruptive to:

- Gemma service
- current retrieval services
- `searxng_mcp.py`
- Firecrawl + SearXNG

### Phase 1: Add Graphify Only

Goal:

- get structural value quickly with minimal ops cost

Actions:

- install `Graphify` in a separate env
- run it manually on the repo first
- inspect `GRAPH_REPORT.md`, `graph.json`, and optional wiki output
- do not install its always-on OpenCode plugin yet

Success criteria:

- it answers real repo navigation questions better than grep-only search

### Phase 2: Add Neo4j Memory

Goal:

- persistent memory without replacing the current retrieval layer

Actions:

- run `Neo4j` as a separate service
- stand up `neo4j-agent-memory` first
- store only session and reasoning memory at first
- do not ingest the whole codebase into the memory layer yet

Success criteria:

- cross-session recall works
- preferences, decisions, and recent findings survive context resets

### Phase 3: Bridge Structural Graph To Memory Graph

Goal:

- connect structural truth to persistent memory without duplication

Actions:

- import selected `Graphify` entities or summaries into `Neo4j`
- create links from memory nodes to code entities
- embed only high-signal nodes

Success criteria:

- memory retrieval can anchor to real code entities
- reranked context is smaller and more accurate than either layer alone

### Phase 4: Reuse The Existing Retrieval Plane As The Shared Arbiter

Goal:

- make the local embedder and reranker the final candidate gate across structure + memory + web

Actions:

- build a small orchestrator that merges candidates from `Graphify`, memory, and optional web sources
- rerank the merged set with the existing `Qwen3-Reranker-4B`

Success criteria:

- fewer retrieved tokens
- better answer grounding
- no GPU usage added beyond the retrieval profile you already accept

### Phase 5: Optional Evaluation Of Actual MDEMG

Only do this if you still want the specific `MDEMG` system after the simpler version is working.

Why defer it:

- it overlaps with current web and retrieval responsibilities
- its public README assumes its own embedding choices (`OpenAI` or `Ollama`)
- it also wants to own codebase ingestion, which can blur the boundary with `Graphify`

If evaluated later, treat it as:

- an optional replacement for the memory implementation
- not an additional third owner of code structure

## Practical Recommendation

Best fit for the current machine and stack:

1. Add `Graphify` first.
2. If it proves useful, add `Neo4j` memory next.
3. Use `neo4j-agent-memory` as the first persistent memory implementation.
4. Keep the existing local embedder + reranker as the shared retrieval gate.
5. Skip `Qdrant` for now.
6. Defer the full `MDEMG` product until you can prove you need more than `Graphify + Neo4j + current retrieval`.

## Sources Checked

- `Graphify` README v4 and current project docs
- `MDEMG` public README
- `Neo4j Agent Memory` docs and README
- current Neo4j Cypher `SEARCH` documentation for vector search and filtering
