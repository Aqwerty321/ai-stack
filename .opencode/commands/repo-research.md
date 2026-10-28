---
description: Use the repo-local MCP research workflow on a specific query
agent: mcp-researcher
subtask: true
---
Research this repo-specific question efficiently using local files, GraphKV, Neo4j memory, SearXNG, and Firecrawl as appropriate.

When the repo already has `graphkv-out/GRAPH_REPORT.md` or `graphkv-out/wiki/index.md`, prefer those artifacts before broad searching if they can answer the question faster.

If the graph looks stale or missing, say so explicitly and recommend reviewing `.graphkvignore` before running `./.opencode/scripts/build-graphkv`.

Question: $ARGUMENTS

Return:
- the chosen retrieval path
- the highest-signal findings
- the smallest next context the parent agent should load
