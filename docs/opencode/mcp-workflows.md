# MCP Workflows

Use the MCPs in pairs when it reduces token usage and avoids redundant retrieval.

## Search + Scrape

- use `firecrawl-local_search` for primary discovery when you want strong result quality or expect to scrape follow-up pages
- use `searxng-local_search_web` or `searxng-local_answer_web` when a lightweight cited answer or quick cross-check is enough
- use `firecrawl-local_map` when the correct page inside a docs site is unclear
- use `firecrawl-local_scrape` on a known URL; for structured details such as fields, parameters, endpoints, or lists, prefer JSON-style extraction over broad page reads
- use `firecrawl-local_extract` when you already have multiple URLs and want one structured result
- use `firecrawl-local_agent` or `firecrawl-local_browser_*` only for multi-step, JS-heavy, or dynamic-page work that simpler search/map/scrape flows do not handle well

## Graph + Memory

- use `graphify-local_graph_stats` and `graphify-local_god_nodes` for orientation
- use `graphify-local_query_graph` with `bfs` for open-ended structure, topology, and relationship questions
- use `graphify-local_query_graph` with `dfs` when tracing a narrower path or dependency chain
- use `graphify-local_get_node` and `graphify-local_get_neighbors` for focused drilldown on a symbol, command, agent, skill, or MCP
- use `graphify-local_shortest_path` for explicit connection questions
- use `graphify-local_get_community` when a graph report or wiki points to a promising cluster
- use `neo4j-memory-local` for prior decisions, preferences, and continuity
- combine them when a durable conclusion needs to be anchored to a real code entity
- do not duplicate whole code structure into memory

When the graph exists, prefer `graphify-out/GRAPH_REPORT.md` or `graphify-out/wiki/index.md` before broad repo searching if they can answer the question faster.

## Subagent Usage

- use `explore` for broad read-only repo discovery
- use `general` for multi-step or parallel research
- keep the parent agent focused on synthesis and surgical edits
