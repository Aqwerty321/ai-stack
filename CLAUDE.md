# ai-stack — Claude Code

The shared rules live in `AGENTS.md` and `docs/opencode/mcp-workflows.md` (also used by OpenCode, which loads the same files via `opencode.json` `instructions`). Edit those, not this file, for harness-neutral guidance.

@AGENTS.md
@AGENTS.local.md
@docs/opencode/mcp-workflows.md

## Claude Code Specifics

### Tool naming

Shared docs use shorthand OpenCode names `<server>_<tool>`. In Claude Code a tool is `mcp__<server>__<tool>`; server names are identical. Verified tool names (2026-10-17):

- `graphkv-local`: `graph_stats`, `god_nodes`, `query_graph`, `get_node`, `get_neighbors`, `get_community`, `shortest_path`, `search_symbols`, `list_workspaces`, `workspace_index_status`
- `searxng-local`: `search_web`, `answer_web`, `deep_read`
- `firecrawl-local`: tools carry a `firecrawl_` prefix, e.g. `mcp__firecrawl-local__firecrawl_search`, `firecrawl_map`, `firecrawl_scrape`, `firecrawl_extract`, `firecrawl_crawl`, `firecrawl_agent`, `firecrawl_interact`, `firecrawl_parse`
- `react-bits-local`: `search_components`, `get_component`, `copy_component_variant`

The Firecrawl MCP is pinned to `firecrawl-mcp@3.20.6` in `~/bin/firecrawl-mcp-http`: newer releases send hosted-only search fields that the self-hosted API rejects, and they drop `firecrawl_extract`. Self-hosted limits: no `query` scrape format and no `firecrawl_research_*` tools. There is no `browser_*` tool: use `firecrawl_interact`, or `playwright-local` for real browser automation.

### Where things are registered

- User scope (`~/.claude.json`, every repo): `playwright-local`, `searxng-local`, `firecrawl-local`, `neo4j-memory-local`, `react-bits-local`, `frontend-design-vault`, `time-local`
- Project scope (`.mcp.json`, this repo): `graphkv-local`, `trellis-3d-local`
- Agents (`~/.claude/agents/`): `mcp-orchestrator`, `mcp-researcher`, `repo-surgeon`
- Skills / slash commands (`~/.claude/skills/`): `/graph-report`, `/graph-query`, `/graph-path`, `/refresh-graph`, `/mcp-audit`, `/repo-research`, `/council`, `/react-bits-search`, `/react-bits-copy`, `/project-bootstrap`, plus model-invoked `repo-triage` and `mcp-research`
- Hooks in `~/.claude/hooks/`:
  - `ai-stack-session.sh` (SessionStart): replaces `.opencode/plugins/graphkv.js`, flags a stale graph and a non-retrieval `ai-profile`, and puts `~/bin` on PATH for Bash
  - `laya-guard.py` (PostToolUse on web/scrape tools): regex prefilter plus the Laya `guard` pack; adds an advisory warning when fetched content looks like a prompt injection, and logs hits to `out/ai-stack/laya/claude-guard.jsonl`
  - `notify.sh` (Notification): desktop toast when Claude Code is waiting on the user

### Laya findings (2026-10-17)

- `tool_risk` is not reliable on raw shell commands (21/31 on realistic cases; it blocks `cat`/`grep`/`npm test`, and the verdict flips on `Bash` vs `bash`). Threshold optimization does not help; it is a model ceiling. Do not use it as a PreToolUse gate.
- `guard` has high recall but ~50% false positives on benign docs, so it only runs on regex-prefiltered windows and stays advisory.
- When you observe a wrong Laya verdict, record it: `laya-gate <pack> --state-json '<state>' --feedback <correct>`, then `python3 scripts/laya_ingest_feedback.py`.

When MCP topology changes, update `opencode.json`, `.mcp.json`, `.vscode/mcp.json`, and this file together.

### Subagent mapping

OpenCode `explore` → `Explore`; OpenCode `general` → `general-purpose`.

### Memory

Two memory systems exist; keep them distinct:

- `neo4j-memory-local` is shared with OpenCode, VS Code, and the voicechat client. Durable repo facts, architectural decisions, and bug root causes go here so every harness sees them. Follow the Memory Rules in `AGENTS.md`.
- Claude Code's built-in auto memory is only for Claude-specific working preferences and feedback.

### Runtime notes (on demand)

`docs/opencode/runtime-notes.md` is not auto-loaded here to save context. Read it before touching services, ports, `ai-profile`, GPU model servers, Laya, TRELLIS, or Firecrawl's `.env`. The authoritative profile list is `/home/Aaditya/bin/ai-profile` (it has profiles beyond those listed in `AGENTS.md`).

### Side effects to confirm first

- `mcp__trellis-3d-local__generate_3d_model` runs `ai-god-route`, which stops the retrieval services, takes the GPU, and opens Blender. Confirm with the user before calling it.
- `ai-profile` switches stop and start GPU services that other tools depend on.
- For heavy GPU jobs, prefer `gpu-exclusive -- <command>` (see `AGENTS.md`): it is authorized for routine use and self-restores. Batch GPU work into one call where possible, since each cycle costs ~80 s and briefly disables embedding-backed MCP tools.
