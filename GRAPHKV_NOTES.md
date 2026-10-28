6233333333333# GraphKV Notes

## Runtime

This repo uses the local GraphKV search MCP in:

- `/home/Aaditya/GraphKV-Engine/mcp-server/search_server.py`
- `/home/Aaditya/GraphKV-Engine/mcp-server/run_search_server.sh`

OpenCode registers it as:

- `graphkv-local`

VS Code registers it as:

- `graphkvLocal`

The default server is additive and read-oriented. It augments repository search with structural graph tools while leaving native file, shell, edit, browser, web, memory, and other MCP capabilities available to the agent.

VS Code and OpenCode launch GraphKV through the wrapper script so workspace-local `uv` version pins do not break MCP startup.

## Workspace Scope

The MCP supports multiple workspaces through `GRAPHKV_WORKSPACE_ROOTS`, using `:`-separated paths on Linux. This coordinator repo currently points the server at:

- `/home/Aaditya/ai-stack`
- `/home/Aaditya/GraphKV-Engine`

Each workspace owns its own generated `graphkv-out/` directory.

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

The default GraphKV MCP exposes structural graph tools:

- `graph_stats`
- `god_nodes`
- `query_graph`
- `get_node`
- `get_neighbors`
- `get_community`
- `shortest_path`
- `search_symbols`
- `list_workspaces`
- `workspace_index_status`

The Binary Star proof/edit/sandbox profile in `/home/Aaditya/GraphKV-Engine/mcp-server/server.py` remains separate and is not the default route for this coordinator workspace.

## Ignore Rules

`.graphkvignore` is repo-local. Use repo-relative patterns, comments with `#`, directory patterns ending in `/`, globs such as `build-*/`, and `!pattern` to re-include after an earlier match. The default builder also skips common cache, dependency, and artifact directories.