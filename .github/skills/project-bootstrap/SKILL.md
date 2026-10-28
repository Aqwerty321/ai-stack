---
name: project-bootstrap
description: Bootstrap a repo into the local MCP workflow with one command, or orient an already bootstrapped repo without recreating scaffolded files. Use when opening a fresh repo or a newly bootstrapped repo.
---

## Purpose

Use this skill to do the minimum repo read needed to decide whether bootstrap should run, which GraphKV ignore flags are needed, and what repo-specific follow-up remains after bootstrap.

Do not manually recreate files that `/home/Aaditya/bin/opencode-project-init` already generates.

If the repo is already bootstrapped, use this skill to orient the repo and identify the remaining repo-specific edits instead of rerunning bootstrap blindly.

## What Bootstrap Provides

Expect these files and directories to exist after bootstrap:

- `AGENTS.md`
- `GRAPHKV_NOTES.md`
- `.graphkvignore`
- `docs/opencode/mcp-workflows.md`
- `docs/opencode/runtime-notes.md`
- `docs/opencode/graphkvignore-template`
- `.opencode/agents/*`
- `.opencode/skills/*`
- `.opencode/commands/*`
- `.opencode/scripts/*`
- `opencode.json`

## Bootstrap Workflow

1. Read only enough repo-local context to identify the real build/test entrypoints and obvious generated, vendored, dependency, fixture, cache, or build-output folders.
2. Check whether bootstrap artifacts already exist: `AGENTS.md`, `GRAPHKV_NOTES.md`, `.graphkvignore`, `opencode.json`, `.vscode/mcp.json`, and `.opencode/scripts/build-graphkv`.
3. If those artifacts are mostly missing, run `/home/Aaditya/bin/opencode-project-init` with any needed repeatable `--graphkv-ignore PATTERN` flags.
4. If those artifacts already exist, do not recreate them manually. Summarize the current state, note missing pieces, and recommend whether rerunning bootstrap is necessary.
5. After bootstrap runs, immediately continue with a post-bootstrap orientation pass: run `./.opencode/scripts/audit-opencode` when present, read the generated guidance files, confirm GraphKV wiring, and identify the repo-specific follow-up edits that still need a human or agent pass.

## Working Rules

- Prefer local files first when the target path is obvious.
- Use `graphkvLocal` for structure and relationship questions when the graph already exists.
- Review `.graphkvignore` before expensive GraphKV rebuilds or before the first bootstrap run in repos with obvious generated or dependency trees.
- Use `neo4jMemoryLocal` for durable prior decisions and preferences.
- Use `timeLocal` when the task depends on exact current time, date, timezone conversion, or readable timestamp formatting.
- Use `firecrawlLocal` and `searxngLocal` only for external docs or current web information.

## Output

Return:

- whether bootstrap was run or intentionally skipped
- which `--graphkv-ignore` flags were used and why
- what the repo's likely real build/test entrypoints are
- which generated files or configs were created or detected
- whether `./.opencode/scripts/audit-opencode` passed
- whether `graphkvLocal` and `graphkv-local` wiring are present
- which scaffolded slash commands and guidance files are now available
- the next repo-specific customizations to make
