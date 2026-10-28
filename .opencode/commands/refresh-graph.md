---
description: Build or refresh the repo-local GraphKV graph, report, HTML, wiki, and wiring
---
Review `.graphkvignore` first. If the repo contains generated, vendored, dependency, fixture, cache, or build-output folders that should not be indexed, append them or run `!./.opencode/scripts/build-graphkv --ignore PATTERN`.

Run the shell command `!./.opencode/scripts/build-graphkv` and then summarize whether these GraphKV artifacts were refreshed successfully:

- `graphkv-out/graph.json`
- `graphkv-out/GRAPH_REPORT.md`
- `graphkv-out/graph.html`
- `graphkv-out/wiki/index.md`

Also mention whether `graphkv-local` is still wired correctly in `opencode.json`, whether `graphkvLocal` is still wired correctly in `.vscode/mcp.json`, and whether `.graphkvignore` looks appropriate for the repo.
