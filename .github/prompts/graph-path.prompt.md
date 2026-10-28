---
name: graph-path
description: Find the shortest graph path between two repo concepts using `left | right` arguments
argument-hint: "source | target"
agent: agent
tools:
  - graphkvLocal/*
---
Interpret the user's argument text as `source | target`.

If the separator is missing, ask for arguments in that format.

If both sides are present, call #tool:graphkvLocal/shortest_path with:

- `source`: the trimmed text on the left side
- `target`: the trimmed text on the right side
- `max_hops`: `8`

Then explain:

- the path in plain language
- which files or nodes make the connection important
- whether `get_neighbors` on an intermediate node would be useful next
- whether the graph looks stale enough that the repo should review `.graphkvignore` and refresh GraphKV before trusting the path fully
