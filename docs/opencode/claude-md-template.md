# Claude Code

Shared agent rules live in `AGENTS.md` and `docs/opencode/mcp-workflows.md` (also loaded by OpenCode). Edit those for harness-neutral guidance; keep only Claude Code specifics here.

@AGENTS.md
@docs/opencode/mcp-workflows.md

## Claude Code Specifics

- Tools are named `mcp__<server>__<tool>`; shared docs use the OpenCode shorthand `<server>_<tool>`. Server names are identical.
- Firecrawl tools carry a `firecrawl_` prefix (`mcp__firecrawl-local__firecrawl_search`, `firecrawl_map`, `firecrawl_scrape`, `firecrawl_extract`, `firecrawl_agent`, `firecrawl_interact`); there is no `browser_*` tool.
- `graphkv-local` is registered in this repo's `.mcp.json`; the rest of the MCP stack is user-scope in `~/.claude.json`.
- OpenCode `explore` → `Explore`; `general` → `general-purpose`. Agents `mcp-orchestrator`, `mcp-researcher`, `repo-surgeon` and the graph slash commands are global in `~/.claude/`.
- `neo4j-memory-local` is the shared cross-harness memory for durable repo facts; Claude's auto memory is only for Claude-specific preferences.
- Read `docs/opencode/runtime-notes.md` on demand before touching services, ports, or `ai-profile`.
