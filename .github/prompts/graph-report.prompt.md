---
name: graph-report
description: Read the repo-local GraphKV report before broad repo exploration
agent: agent
tools:
  - graphkvLocal/*
---
If `graphkv-out/GRAPH_REPORT.md` is missing or clearly stale relative to the repo state, say that first and recommend reviewing `.graphkvignore` before refreshing the graph.

Otherwise read `graphkv-out/GRAPH_REPORT.md` and summarize:

- the highest-signal god nodes
- the most relevant communities
- the most useful suggested questions for the current repo state
- which GraphKV MCP tool to call next if deeper drilldown is needed
- whether `.graphkvignore` likely needs repo-specific exclusions before the next rebuild
