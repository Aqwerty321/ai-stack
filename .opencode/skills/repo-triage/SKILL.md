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

- start with `graphify-local_graph_stats` or `graphify-local_god_nodes` if you need orientation
- use `graphify-local_query_graph` for broad relationship questions
- use `graphify-local_get_node` and `graphify-local_get_neighbors` once the entity is known
- use `graphify-local_shortest_path` for explicit connection questions
- use `graphify-local_get_community` after graph report or wiki orientation
- use local file reads once the relevant nodes/files are known

### Memory / Continuity

- start with `neo4j-memory-local`
- only write back high-signal conclusions

### External Docs

- start with `searxng-local`
- then use `firecrawl-local` for exact extraction

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
