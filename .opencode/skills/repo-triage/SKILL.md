---
name: repo-triage
description: Triage repo work by separating structure, memory, web, and edit paths
license: MIT
compatibility: opencode
metadata:
  audience: maintainers
  workflow: triage
---

## Purpose

Use this skill at the start of non-trivial repo tasks to choose the right retrieval and editing path.

## Triage Checklist

1. Decide whether the task is primarily:
   - structural code understanding
   - prior-context recovery
   - external documentation lookup
   - direct implementation in obvious files
2. Choose the smallest tool path that fits.
3. Spawn subagents only when breadth or parallelism will save tokens.
4. Keep edits surgical after context is gathered.
5. Use project-local subagents when breadth or parallelism will save tokens.

## Routing Rules

### Structural

- start with `graphkv-local_graph_stats` or `graphkv-local_god_nodes` if you need orientation
- use `graphkv-local_query_graph` with `bfs` for broad relationship questions
- use `graphkv-local_query_graph` with `dfs` for narrower dependency or propagation tracing
- use `graphkv-local_get_node` and `graphkv-local_get_neighbors` once the entity is known
- use `graphkv-local_shortest_path` for explicit connection questions
- use `graphkv-local_get_community` after graph report or wiki orientation
- before rebuilding stale graph artifacts, append unhelpful generated, vendored, dependency, fixture, cache, and build-output folders to `.graphkvignore`
- use local file reads once the relevant nodes/files are known

### Memory / Continuity

- start with `neo4j-memory-local`
- only write back high-signal conclusions

### External Docs

- start with `firecrawl-local_firecrawl_search` when you want the best results or expect to scrape follow-up pages
- use `searxng-local_search_web` or `searxng-local_answer_web` for quick answers or cross-checks
- use `firecrawl-local_firecrawl_map` when the correct docs page is unclear
- use `firecrawl-local_firecrawl_scrape` for a known URL and prefer JSON-style extraction for exact fields or lists
- use `firecrawl-local_firecrawl_extract` when multiple known URLs should be reduced to one structured answer
- use `firecrawl-local_firecrawl_agent` or `firecrawl-local_firecrawl_interact` only for dynamic, JS-heavy, or multi-step flows

### Direct Edits

- if file paths are obvious, read local files directly first
- do not over-search the repo before making a small obvious fix

### Broad Investigation

- use `explore` when many files may match
- use `general` when multiple retrieval paths should run in parallel

## Output To Parent Agent

Return:

- the chosen path
- the highest-signal files or facts
- any missing information that blocks implementation
