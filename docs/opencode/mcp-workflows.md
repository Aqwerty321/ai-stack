# MCP Workflows

Use the MCPs in pairs when it reduces token usage and avoids redundant retrieval.

## Search + Scrape

- use `searxng-local` to discover the right external page
- use `firecrawl-local` to extract exact details from the chosen page
- for structured details such as fields, parameters, or lists, prefer structured extraction over broad page reads
- do not scrape widely until search has narrowed the target

## Graph + Memory

- use `graphify-local_graph_stats` and `graphify-local_god_nodes` for orientation
- use `graphify-local_query_graph` for open-ended structure, topology, and relationship questions
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
