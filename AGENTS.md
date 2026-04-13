# AI Stack Project Rules

This repo is a local AI tooling stack with four MCP servers already available in OpenCode:

- `graphify-local` for repo structure, topology, communities, and graph drilldown
- `searxng-local` for lightweight web lookup and cited answer synthesis
- `firecrawl-local` for high-quality web search, scraping, site mapping, structured extraction, agent research, and browser automation
- `neo4j-memory-local` for persistent memory, preferences, facts, and session continuity

## MCP Usage Rules

Choose tools by information type instead of by habit.

- Use `graphify-local` first for code-structure questions inside this repo:
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

Do not write durable facts to memory automatically for every task. Store only high-signal items:

- architectural decisions
- bug root causes
- user preferences
- stable external constraints
- important task continuity notes

## Expected Retrieval Order

For repo-internal implementation work:

1. Check local files directly when the path is obvious.
2. Use `graphify-local` when structure or relationships matter.
3. Use `neo4j-memory-local` when past context may matter.
4. Use `searxng-local` and `firecrawl-local` only for external docs or current web information.

For external API or library work:

1. Use `firecrawl-local_search` when you want the best current result set or expect to scrape follow-up pages. Use `searxng-local` when a quick lightweight answer or shortlist is enough.
2. Use `firecrawl-local_map` when the correct page inside a docs site is unclear.
3. Use `firecrawl-local_scrape` for a known URL. Use JSON-style extraction for exact fields or parameters, and markdown only when the full page content is what you need.
4. Use `firecrawl-local_extract` when you already have multiple URLs and want one structured result.
5. Use `firecrawl-local_agent` or `firecrawl-local_browser_*` only for multi-step, heavily dynamic, or JS-rendered research that simpler flows do not handle well.
6. Persist only the durable takeaway to `neo4j-memory-local` if it is likely to matter again.

## MCP Pairings

Use the MCPs in deliberate pairs when the task benefits from it.

### Firecrawl + SearXNG

Treat these as a web-discovery-and-extraction stack.

- use `firecrawl-local_search` for primary discovery when you need strong result quality or expect to scrape follow-up pages
- use `searxng-local_answer_web` or `searxng-local_search_web` when a lightweight cited answer or quick cross-check is enough
- use `firecrawl-local_map` to find the right page inside a docs site before scraping broadly
- use `firecrawl-local_scrape` on a known URL; prefer structured JSON extraction for exact fields, parameters, endpoints, prices, or lists
- use `firecrawl-local_extract` when you already know multiple URLs and want one structured extraction pass
- use `firecrawl-local_agent` only when search/map/scrape is still insufficient or the task inherently spans many sources
- use `firecrawl-local_browser_*` for deterministic browser interaction, debugging dynamic pages, or stateful navigation

### Graphify + Neo4j Memory

Treat these as a structure-plus-continuity pair.

- use `graphify-local` to understand code entities and relationships
- use `neo4j-memory-local` to recover prior decisions, durable findings, and user preferences
- combine them when prior conclusions need to be anchored to real code entities
- do not duplicate the full code graph into memory; store only the durable takeaway and references

### Graphify Tool Routing

- start with `graphify-local_graph_stats` and `graphify-local_god_nodes` when you need fast repo orientation
- use `graphify-local_query_graph` with `bfs` for open-ended structural questions like "how do these parts fit together"
- use `graphify-local_query_graph` with `dfs` when tracing a narrower dependency or propagation path through a subsystem
- use `graphify-local_get_node` and `graphify-local_get_neighbors` when the user names a symbol, file, agent, command, skill, or MCP explicitly
- use `graphify-local_shortest_path` for "what connects X and Y" questions
- use `graphify-local_get_community` after `GRAPH_REPORT.md`, `graph.html`, or `graphify-out/wiki/index.md` points at a relevant cluster
- prefer Graphify over raw grep when the question is about relationships rather than exact text matches

## Subagent Strategy

Use subagents to save tokens and keep edits surgical.

- use read-only exploration subagents for broad discovery across the repo
- use general-purpose subagents for parallel research or multi-step investigation
- keep the parent agent focused on synthesis, decisions, and minimal edits once the right context is identified
- prefer subagents when the alternative would require loading many files into the main thread

## Local Runtime Reality

This machine intentionally runs one of two GPU profiles:

- retrieval profile:
  - `rag-embed.service`
  - `local-reasoner.service`
  - `neo4j-memory-mcp.service`
- gemma profile:
  - `gemma4-vllm.service`

Switch profiles with:

```bash
/home/Aaditya/bin/ai-profile retrieval
/home/Aaditya/bin/ai-profile gemma
```

Assume retrieval mode is preferred for repo work unless the user explicitly wants local Gemma.

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

## Graphify Rules

`graphify-local` only knows what is in the built repo graph.

- trust it for repo-internal structure
- do not expect it to know unrelated files outside the indexed project
- if the graph appears stale after major code movement, rebuild the graph artifacts before trusting topology answers
- `graphify-local_graph_stats`, `graphify-local_god_nodes`, `graphify-local_get_node`, `graphify-local_get_neighbors`, `graphify-local_get_community`, and `graphify-local_shortest_path` are all part of the normal routing surface, not specialist-only tools
- `graphify-out/GRAPH_REPORT.md` is the cheapest orientation artifact; read it before broad repo searching when it answers the question
- `graphify-out/wiki/index.md` is the best crawlable entry point when the graph has already been rebuilt
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
