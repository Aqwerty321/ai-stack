---
name: mcp-research
description: Use paired MCP workflows for efficient repo and web research. Use when a task spans local files, GraphKV, memory, SearXNG, or Firecrawl.
---

## Purpose

Use this skill when the task involves gathering context efficiently across multiple MCP servers.

## Core Pairings

### Firecrawl + SearXNG

For external knowledge:

1. Use #tool:firecrawlLocal/firecrawl_search first when result quality matters or you expect to scrape follow-up pages.
2. Use #tool:searxngLocal/search_web or #tool:searxngLocal/answer_web when a quick answer or shortlist is enough.
3. Use #tool:firecrawlLocal/firecrawl_map when the correct page inside a docs site is unclear.
4. Use #tool:firecrawlLocal/firecrawl_scrape for a known URL; prefer JSON-style extraction for fields, parameters, endpoints, and lists.
5. Use #tool:firecrawlLocal/firecrawl_extract when multiple known URLs should become one structured result.
6. Use #tool:firecrawlLocal/firecrawl_agent or interactive browser flows only for dynamic, JS-heavy, or multi-step web work.

### Graph + Memory

For repo knowledge:

1. Use #tool:graphkvLocal/graph_stats and #tool:graphkvLocal/god_nodes for orientation.
2. Use #tool:graphkvLocal/query_graph with `bfs` for broad structural questions.
3. Use #tool:graphkvLocal/query_graph with `dfs` when tracing a narrower dependency or propagation path.
4. Use #tool:graphkvLocal/get_node and #tool:graphkvLocal/get_neighbors for focused drilldown.
5. Use #tool:graphkvLocal/shortest_path for explicit connection questions.
6. Use #tool:graphkvLocal/get_community when a graph report or wiki points to a promising cluster.
7. Use `neo4jMemoryLocal` for prior decisions, durable facts, and continuity.
8. Combine both when you need to connect a code entity to prior work or decisions.
9. Keep memory repo-scoped and avoid duplicating whole graph structure.

## Efficiency Rules

- Prefer local files when the path is obvious.
- Prefer `graphkvLocal` over grep when the question is structural.
- Prefer `graphkv-out/GRAPH_REPORT.md` or `graphkv-out/wiki/index.md` when they can answer the question faster than a fresh graph traversal.
- Before rebuilding stale artifacts, append generated, vendored, dependency, fixture, cache, and build-output folders to `.graphkvignore` or pass `./.opencode/scripts/build-graphkv --ignore PATTERN`.
- Prefer memory over re-deriving prior decisions.
- Return the minimum useful context.
