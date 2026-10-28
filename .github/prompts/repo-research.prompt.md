---
name: repo-research
description: Use the repo-local MCP research workflow on a specific query
argument-hint: "repo question"
agent: agent
tools:
  - read
  - grep
  - graphkvLocal/*
  - neo4jMemoryLocal/*
  - searxngLocal/*
  - firecrawlLocal/*
---
Research the user's repo-specific question efficiently using local files, GraphKV, Neo4j memory, SearXNG, and Firecrawl as appropriate.

When the repo already has `graphkv-out/GRAPH_REPORT.md` or `graphkv-out/wiki/index.md`, prefer those artifacts before broad searching if they can answer the question faster.

If the graph looks stale or missing, say so explicitly and recommend reviewing `.graphkvignore` before running `./.opencode/scripts/build-graphkv`.

Return:

- the chosen retrieval path
- the highest-signal findings
- the smallest next context to load
