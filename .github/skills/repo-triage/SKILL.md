---
name: repo-triage
description: Triage repo work by separating structure, memory, web, time, and edit paths. Use at the start of non-trivial repo tasks.
---

## Purpose

Use this skill at the start of non-trivial repo tasks to choose the right retrieval and editing path.

## Triage Checklist

1. Decide whether the task is primarily structural code understanding, prior-context recovery, external documentation lookup, time-sensitive reasoning, or direct implementation in obvious files.
2. Choose the smallest tool path that fits.
3. Keep edits surgical after context is gathered.

## Routing Rules

### Structural

- start with #tool:graphkvLocal/graph_stats or #tool:graphkvLocal/god_nodes if you need orientation
- use #tool:graphkvLocal/query_graph with `bfs` for broad relationship questions
- use #tool:graphkvLocal/query_graph with `dfs` for narrower dependency or propagation tracing
- use #tool:graphkvLocal/get_node and #tool:graphkvLocal/get_neighbors once the entity is known
- before rebuilding stale graph artifacts, append unhelpful generated, vendored, dependency, fixture, cache, and build-output folders to `.graphkvignore`
- use local file reads once the relevant nodes/files are known

### Memory / Continuity

- start with `neo4jMemoryLocal`
- only write back high-signal conclusions

### External Docs

- start with #tool:firecrawlLocal/firecrawl_search when you want the best results or expect to scrape follow-up pages
- use #tool:searxngLocal/search_web or #tool:searxngLocal/answer_web for quick answers or cross-checks
- use #tool:firecrawlLocal/firecrawl_map when the correct docs page is unclear
- use #tool:firecrawlLocal/firecrawl_scrape for a known URL and prefer JSON-style extraction for exact fields or lists

### Time Anchoring

- use #tool:timeLocal/get_current_time, #tool:timeLocal/get_current_date, or #tool:timeLocal/get_datetime_info when exact current time matters
- use #tool:timeLocal/format_timestamp for logs, incidents, deadlines, and schedule translation across timezones

### Direct Edits

- if file paths are obvious, read local files directly first
- do not over-search the repo before making a small obvious fix
