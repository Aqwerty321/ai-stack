# GraphKV Notes

## Runtime

This repo uses the local GraphKV search MCP:

- OpenCode server id: `graphkv-local`
- VS Code server id: `graphkvLocal`
- server entry point: `/home/Aaditya/GraphKV-Engine/mcp-server/search_server.py`
- launch wrapper: `/home/Aaditya/GraphKV-Engine/mcp-server/run_search_server.sh`

The default GraphKV MCP is additive. It augments repository search with structural graph tools and does not disable native file, shell, edit, web, memory, browser, or other MCP capabilities.

VS Code and OpenCode launch GraphKV through the wrapper script so workspace-local `uv` version pins do not break MCP startup.

## Generated Artifacts

Run the refresh command when repo structure changes:

```bash
./.opencode/scripts/build-graphkv
```

Before expensive refreshes, review `.graphkvignore`. Agents may append repo-specific generated, vendored, dependency, fixture, cache, build-output, or data-heavy folders when they do not need graph indexing:

```bash
./.opencode/scripts/build-graphkv --ignore vendor/generated-sdk/
```

That regenerates:

- `graphkv-out/graph.json`
- `graphkv-out/GRAPH_REPORT.md`
- `graphkv-out/graph.html`
- `graphkv-out/wiki/index.md`

## Tool Surface

Use GraphKV for structure, topology, relationships, named repo entities, and symbol search:

- `graph_stats`
- `god_nodes`
- `query_graph`
- `get_node`
- `get_neighbors`
- `get_community`
- `shortest_path`
- `search_symbols`

## Ignore Rules

`.graphkvignore` is repo-local. Use repo-relative patterns, comments with `#`, directory patterns ending in `/`, globs such as `build-*/`, and `!pattern` to re-include after an earlier match. The default builder also skips common cache, dependency, and artifact directories.