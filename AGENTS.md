# AI Stack Project Rules

This repo is a local AI tooling stack with five MCP servers already available in OpenCode:

- `graphkv-local` for repo structure, topology, communities, and graph drilldown
- `searxng-local` for lightweight web lookup and cited answer synthesis
- `firecrawl-local` for high-quality web search, scraping, site mapping, structured extraction, agent research, and browser automation
- `neo4j-memory-local` for persistent memory, preferences, facts, and session continuity
- `time-local` for exact local time/date reads, timezone-aware conversions, and timestamp formatting

Additional domain-specific MCPs may also be available locally:

- `react-bits-local` for implementation-ready React component retrieval, full component fetch, and code copy
- `frontend-design-vault` for frontend pattern guidance, visual direction, and design-system-adjacent retrieval

## MCP Usage Rules

Choose tools by information type instead of by habit.

- Use `graphkv-local` first for code-structure questions inside this repo:
  - broad structural questions via `query_graph`
  - symbol drilldown via `get_node` and `get_neighbors`
  - community inspection via `get_community`
  - shortest paths via `shortest_path`
  - repo orientation via `graph_stats` and `god_nodes`
- Use `neo4j-memory-local` for:
  - prior decisions
  - recurring fixes
  - user preferences
  - session continuity
  - durable implementation notes worth remembering
- Use `time-local` for:
  - exact current local time or date
  - timezone conversion
  - log and incident timestamp formatting
  - deadline, release, or maintenance-window anchoring
  - time-aware planning or date-sensitive creative output
- Use `firecrawl-local` for:
  - primary external web discovery when result quality matters or you expect to scrape follow-up pages
  - scraping a known URL
  - structured extraction from one or more known docs/pages
  - site mapping when docs are spread across many pages
  - autonomous research or browser automation only when simpler search/map/scrape flows are not enough
- Use `searxng-local` for:
  - lightweight web lookup
  - quick cited answers
  - cross-checking or narrowing a query without heavier scraping

Do not use web tools for questions that can be answered from the code graph or repo files.

For frontend work, keep `react-bits-local` and `frontend-design-vault` separate in purpose:

- use `frontend-design-vault` for design direction, layout systems, interaction patterns, and visual-language decisions
- use `react-bits-local` for concrete component implementations you may actually adapt or copy
- when both are needed, use them sequentially: direction first, implementation second
- do not ask both tools the same vague prompt at the same abstraction level

Do not write durable facts to memory automatically for every task. Store only high-signal items:

- architectural decisions
- bug root causes
- user preferences
- stable external constraints
- important task continuity notes

## Expected Retrieval Order

For repo-internal implementation work:

1. Check local files directly when the path is obvious.
2. Use `graphkv-local` when structure or relationships matter.
3. Use `neo4j-memory-local` when past context may matter.
4. Use `time-local` when the task depends on exact current time, local timezone, or readable timestamp conversion.
5. Use `searxng-local` and `firecrawl-local` only for external docs or current web information.

For external API or library work:

1. Use `firecrawl-local_firecrawl_search` when you want the best current result set or expect to scrape follow-up pages. Use `searxng-local` when a quick lightweight answer or shortlist is enough.
2. Use `firecrawl-local_firecrawl_map` when the correct page inside a docs site is unclear.
3. Use `firecrawl-local_firecrawl_scrape` for a known URL. Use JSON-style extraction for exact fields or parameters, and markdown only when the full page content is what you need.
4. Use `firecrawl-local_firecrawl_extract` when you already have multiple URLs and want one structured result.
5. Use `firecrawl-local_firecrawl_agent` or `firecrawl-local_firecrawl_interact` only for multi-step, heavily dynamic, or JS-rendered research that simpler flows do not handle well.
6. Persist only the durable takeaway to `neo4j-memory-local` if it is likely to matter again.

For frontend build-outs:

1. Use `frontend-design-vault` first when the problem is page direction, layout composition, interaction style, or visual system choice.
2. Use `react-bits-local` first when the problem is a specific UI primitive or reusable section that should be implemented quickly.
3. When both are needed, extract a small pattern brief from `frontend-design-vault`, then turn that into 1-3 targeted `react-bits-local` queries.
4. Fetch full React Bits docs only for shortlisted candidates and copy only after the target component and variant are chosen.
5. Preserve the existing repo design system; React Bits supplies primitives, not permission to replace the project’s visual language.

## MCP Pairings

Use the MCPs in deliberate pairs when the task benefits from it.

### Firecrawl + SearXNG

Treat these as a web-discovery-and-extraction stack.

- use `firecrawl-local_firecrawl_search` for primary discovery when you need strong result quality or expect to scrape follow-up pages
- use `searxng-local_answer_web` or `searxng-local_search_web` when a lightweight cited answer or quick cross-check is enough
- use `firecrawl-local_firecrawl_map` to find the right page inside a docs site before scraping broadly
- use `firecrawl-local_firecrawl_scrape` on a known URL; prefer structured JSON extraction for exact fields, parameters, endpoints, prices, or lists
- use `firecrawl-local_firecrawl_extract` when you already know multiple URLs and want one structured extraction pass
- use `firecrawl-local_firecrawl_agent` only when search/map/scrape is still insufficient or the task inherently spans many sources
- use `firecrawl-local_firecrawl_interact` for deterministic browser interaction, debugging dynamic pages, or stateful navigation

### GraphKV + Neo4j Memory

Treat these as a structure-plus-continuity pair.

- use `graphkv-local` to understand code entities and relationships
- use `neo4j-memory-local` to recover prior decisions, durable findings, and user preferences
- combine them when prior conclusions need to be anchored to real code entities
- do not duplicate the full code graph into memory; store only the durable takeaway and references

### Time Anchoring

- use `time-local` when the task depends on exact current time, date, local timezone, or timestamp conversion
- use `time-local_get_current_time`, `time-local_get_current_date`, or `time-local_get_datetime_info` to anchor “today”, “now”, release timing, maintenance windows, or deadlines
- use `time-local_format_timestamp` for logs, incidents, cron outputs, and schedule translation across timezones
- use it productively for planning, incident reconstruction, status reporting, and date-sensitive creative work when current time meaningfully shapes the output

### React Bits + Frontend Design Vault

Treat these as a design-direction-plus-implementation pair.

- use `frontend-design-vault` for layout ideas, visual language, motion constraints, composition guidance, and frontend best-practice references
- use `react-bits-local` for implementation-ready component candidates, full normalized component docs, and code copy
- for broad frontend requests, start with `frontend-design-vault`, reduce the result to a pattern brief, then query `react-bits-local`
- for concrete component requests, start with `react-bits-local` and consult `frontend-design-vault` only if page-level composition or styling guidance is still unclear
- do not use `frontend-design-vault` to hunt for copy-paste component code
- do not use `react-bits-local` for broad design brainstorming
- stop retrieval once the pattern is chosen and the component shortlist is strong enough to build

### GraphKV Tool Routing

- start with `graphkv-local_graph_stats` and `graphkv-local_god_nodes` when you need fast repo orientation
- use `graphkv-local_query_graph` with `bfs` for open-ended structural questions like "how do these parts fit together"
- use `graphkv-local_query_graph` with `dfs` when tracing a narrower dependency or propagation path through a subsystem
- use `graphkv-local_get_node` and `graphkv-local_get_neighbors` when the user names a symbol, file, agent, command, skill, or MCP explicitly
- use `graphkv-local_shortest_path` for "what connects X and Y" questions
- use `graphkv-local_get_community` after `GRAPH_REPORT.md`, `graph.html`, or `graphkv-out/wiki/index.md` points at a relevant cluster
- prefer GraphKV over raw grep when the question is about relationships rather than exact text matches

## Subagent Strategy

Use subagents to save tokens and keep edits surgical.

- use read-only exploration subagents for broad discovery across the repo
- use general-purpose subagents for parallel research or multi-step investigation
- keep the parent agent focused on synthesis, decisions, and minimal edits once the right context is identified
- prefer subagents when the alternative would require loading many files into the main thread

## Local Runtime Reality

This machine runs one managed GPU profile at a time. `/home/Aaditya/bin/ai-profile` is the source of truth; keep this list in sync with it.

- `retrieval` (default): `rag-embed.service`, `rag-rerank.service`, `local-reasoner.service`, `neo4j-memory-mcp.service`
- `gemma`: `gemma4-vllm.service`
- `muse`: `muse-glimmer.service`
- `ornith9`: `ornith9-vllm.service`
- `voicechat`: `nemotron-voicechat.service` plus `rag-embed.service` and `neo4j-memory-mcp.service`
- `trellis2`: `trellis2-3d.service`
- `blank`, `3d-lab`, `multiview`, `hunyuan3d`, `hunyuan-paint`, `triposg`: free the GPU (all model servers stopped); `neo4j-memory-mcp.service` stays up but embedding-backed calls fail until `retrieval` is restored

Machine-specific extra profiles, if any, are listed in `AGENTS.local.md` (gitignored; read it when it exists).

`laya-decide.service` (CPU, :8008) is always on in every profile.

`blank` is the boot default: no GPU model service is enabled at login. `ai-profile status` prints the current and boot profile, per-service boot/state/HTTP health, GPU memory and processes, any running `gpu-exclusive` job, free disk and the last Drive backup.

Switch profiles with `/home/Aaditya/bin/ai-profile <profile>`, e.g.:

```bash
/home/Aaditya/bin/ai-profile retrieval
/home/Aaditya/bin/ai-profile gemma
```

Assume retrieval mode is preferred for repo work unless the user explicitly wants one of the isolated local model profiles.

For a bounded GPU job that needs more VRAM than retrieval mode leaves free (~4 GB), use `/home/Aaditya/bin/gpu-exclusive [-n NAME] [-t TIMEOUT_S] [-m HOST_RAM_GIB] -- command ...` instead of switching profiles by hand. It stops the retrieval GPU services, runs the command with ~22 GB free, and restores exactly the services that were active, waiting for HTTP health. Restoration runs from a systemd `ExecStopPost`, so it happens even if the calling agent session dies. A full cycle adds about 80 s. Logs: `~/.cache/3d-lab/gpu-runs/`. Embedding-backed tools (memory search, SearXNG reranking, react-bits, frontend-design-vault) fail while the job runs.

## Memory Rules

The memory MCP currently reuses the shared `llama.cpp` embedder at `http://127.0.0.1:8001/v1`.

Keep memory repo-scoped whenever possible.

- prefer facts and entities that include repo context such as `ai-stack`
- prefer repo-specific session ids when running investigation or verification flows
- avoid storing conclusions that would be ambiguous across multiple unrelated repos

When storing memory, prefer compact factual entries over long narrative dumps.

Good memory writes:

- one-sentence architectural decision
- one bug root cause and fix
- one user preference
- one stable repo fact

Bad memory writes:

- raw logs
- large scrape dumps
- whole code listings
- transient brainstorming that will not matter later

## GraphKV Rules

`graphkv-local` only knows what is in the built repo graph.

- trust it for repo-internal structure
- do not expect it to know unrelated files outside the indexed project
- if the graph appears stale after major code movement, rebuild the graph artifacts before trusting topology answers
- `graphkv-local_graph_stats`, `graphkv-local_god_nodes`, `graphkv-local_get_node`, `graphkv-local_get_neighbors`, `graphkv-local_get_community`, and `graphkv-local_shortest_path` are all part of the normal routing surface, not specialist-only tools
- `graphkv-out/GRAPH_REPORT.md` is the cheapest orientation artifact; read it before broad repo searching when it answers the question
- `graphkv-out/wiki/index.md` is the best crawlable entry point when the graph has already been rebuilt
- use repo-local graph commands like `/graph-report`, `/graph-query`, and `/graph-path` when they fit the task more directly than manual tool selection

## Working Style

- prefer small, direct changes
- verify the changed path, not the whole world
- keep docs in sync with runtime changes
- if you change ports, services, wrappers, or MCP topology, update project docs immediately

## Project-Local Agents

This repo can define project-local agents in `.opencode/agents/`.

- use project-local subagents for MCP orchestration and surgical edit workflows
- keep project-specific agent behavior here instead of global OpenCode config
