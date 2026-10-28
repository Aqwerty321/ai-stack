# Bootstrap Regression Checklist

Run this checklist after changing bootstrap, GraphKV integration, repo overlay logic, or seeded MCP guidance.

## Fresh Repo Scaffold

- create a fresh throwaway git repo
- run `/home/Aaditya/bin/opencode-project-init`
- confirm bootstrap completes without manual edits

## Scaffolded Files

Confirm the new repo contains:

- `AGENTS.md`
- `GRAPHKV_NOTES.md`
- `.graphkvignore`
- confirm `GRAPHKV_NOTES.md` does not mention `ai-stack` or any other unrelated repo name
- `docs/opencode/mcp-workflows.md`
- `docs/opencode/runtime-notes.md`
- `docs/opencode/graphkvignore-template`
- `.github/prompts/project-bootstrap.prompt.md`
- `.opencode/agents/mcp-orchestrator.md`
- `.opencode/agents/mcp-researcher.md`
- `.opencode/agents/repo-surgeon.md`
- `.opencode/skills/mcp-research/SKILL.md`
- `.opencode/skills/repo-triage/SKILL.md`
- `.opencode/commands/refresh-graph.md`
- `.opencode/commands/mcp-audit.md`
- `.opencode/commands/repo-research.md`
- `.opencode/commands/graph-report.md`
- `.opencode/commands/graph-query.md`
- `.opencode/commands/graph-path.md`
- `.opencode/plugins/graphkv.js`
- `.opencode/scripts/build-graphkv`
- `.opencode/scripts/audit-opencode`

## GraphKV Wiring

- run `/home/Aaditya/bin/opencode-project-init --graphkv-ignore generated-client/ --graphkv-max-files 1000` on one fresh scratch repo
- confirm `.graphkvignore` includes `generated-client/` exactly once
- confirm `graphkv-out/graph.json` exists after bootstrap
- confirm `graphkv-out/GRAPH_REPORT.md` exists after bootstrap
- confirm `graphkv-out/graph.html` exists after bootstrap
- confirm `graphkv-out/wiki/index.md` exists after bootstrap
- confirm `opencode.json` registers `graphkv-local`
- confirm `.vscode/mcp.json` registers `graphkvLocal` when VS Code scaffolding is enabled
- confirm both configs point at `/home/Aaditya/GraphKV-Engine/mcp-server/run_search_server.sh`
- confirm `./.opencode/scripts/build-graphkv --ignore vendor/generated-sdk/` appends the pattern and rebuilds successfully
- confirm GraphKV still starts inside a repo that pins a different `uv` version than the system `uv`

## Empty Repo Behavior

- run the checklist on an empty repo
- confirm graph seeding still works when GraphKV reports no code files
- confirm `graph.html` still renders for the seeded graph

## Guidance Quality

Inspect the generated files and confirm they teach:

- `/project-bootstrap` to run `/home/Aaditya/bin/opencode-project-init` after a quick repo read instead of hand-creating scaffold files
- GraphKV orientation through `graph_stats` and `god_nodes`
- `query_graph` routing with `bfs` for broad questions and `dfs` for narrower tracing
- `get_node`, `get_neighbors`, `get_community`, and `shortest_path` as normal routing tools
- Firecrawl routing across `search`, `map`, `scrape`, `extract`, `agent`, and browser flows
- SearXNG as a lightweight answer and cross-check path
- Firecrawl LLM-assisted extraction dependency on the `api` container env
- `.graphkvignore` customization before expensive refreshes
- `build-graphkv --ignore PATTERN` and bootstrap `--graphkv-ignore PATTERN` usage for repo-specific excludes

## Audit Command

- run `./.opencode/scripts/audit-opencode`
- confirm it reports scaffold files present

## Generated Artifacts Hygiene

- confirm `.gitignore` contains `/graphkv-out/`
- confirm `.gitignore` contains `/.graphkv/`
- confirm `.gitignore` contains `/.opencode/package-lock.json`
- confirm generated graph artifacts are not staged by default
