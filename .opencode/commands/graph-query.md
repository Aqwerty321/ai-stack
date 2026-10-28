---
description: Query the repo-local GraphKV graph for a broad structural question
---
Use `graphkv-local_query_graph` with:

- `question`: `$ARGUMENTS`
- `mode`: `bfs`
- `depth`: `3`
- `token_budget`: `1800`

Then summarize:

- the core nodes and edges that answer the question
- the highest-signal files or repo entities to inspect next
- whether `get_node`, `get_neighbors`, `get_community`, or `shortest_path` would sharpen the answer
- whether the graph looks stale enough that the repo should review `.graphkvignore` and refresh GraphKV before trusting the result fully
