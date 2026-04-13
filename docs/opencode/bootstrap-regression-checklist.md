# Bootstrap Regression Checklist

Run this checklist after changing bootstrap, Graphify integration, repo overlay logic, or seeded MCP guidance.

## Fresh Repo Scaffold

- create a fresh throwaway git repo
- run `/home/Aaditya/bin/opencode-project-init`
- confirm bootstrap completes without manual edits

## Scaffolded Files

Confirm the new repo contains:

- `AGENTS.md`
- `GRAPHIFY_NOTES.md`
- confirm `GRAPHIFY_NOTES.md` does not mention `ai-stack` or any other unrelated repo name
- `docs/opencode/mcp-workflows.md`
- `docs/opencode/runtime-notes.md`
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
- `.opencode/plugins/graphify.js`
- `.opencode/scripts/build-graphify`
- `.opencode/scripts/audit-opencode`
- `.opencode/scripts/graphify_repo_overlay.py`

## Graphify Wiring

- confirm `graphify-out/graph.json` exists after bootstrap
- confirm `graphify-out/GRAPH_REPORT.md` exists after bootstrap
- confirm `graphify-out/graph.html` exists after bootstrap
- confirm `graphify-out/wiki/index.md` exists after bootstrap
- confirm `opencode.json` registers `graphify-local`
- confirm bootstrap output reports Graphify runtime `0.4.12`

## Empty Repo Behavior

- run the checklist on an empty repo
- confirm graph seeding still works when Graphify reports no code files
- confirm `graph.html` still renders for the seeded graph

## Guidance Quality

Inspect the generated files and confirm they teach:

- Graphify orientation through `graph_stats` and `god_nodes`
- `query_graph` routing with `bfs` for broad questions and `dfs` for narrower tracing
- `get_node`, `get_neighbors`, `get_community`, and `shortest_path` as normal routing tools
- Firecrawl routing across `search`, `map`, `scrape`, `extract`, `agent`, and browser flows
- SearXNG as a lightweight answer and cross-check path
- Firecrawl LLM-assisted extraction dependency on the `api` container env

## Audit Command

- run `./.opencode/scripts/audit-opencode`
- confirm it reports scaffold files present

## Generated Artifacts Hygiene

- confirm `.gitignore` contains `/graphify-out/`
- confirm `.gitignore` contains `/.opencode/package-lock.json`
- confirm generated graph artifacts are not staged by default
