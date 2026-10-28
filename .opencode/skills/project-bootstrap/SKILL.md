---
name: project-bootstrap
description: Bootstrap a repo into the local MCP workflow with one command, or orient an already bootstrapped repo without recreating scaffolded files
license: MIT
compatibility: opencode
metadata:
  audience: maintainers
  workflow: bootstrap
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
- Use `graphkv-local` for structure and relationship questions when the graph already exists.
- Use `neo4j-memory-local` for durable prior decisions and preferences.
- Use `time-local` when the task depends on exact current time, date, timezone conversion, or readable timestamp formatting.
- Use `firecrawl-local` and `searxng-local` only for external docs or current web information.
- Review `.graphkvignore` before expensive GraphKV rebuilds or before the first bootstrap run in repos with obvious generated or dependency trees.
- Keep repo-specific instructions in `AGENTS.md`; do not leave the generic template unchanged.

For frontend-oriented repos, encode this routing rule in the repo-local guidance:

- `frontend-design-vault` decides frontend direction: pattern family, visual language, motion level, and composition
- `react-bits-local` supplies concrete component implementations, full component docs, and code copy
- use them sequentially, not redundantly: direction first, implementation second
- do not import React Bits into an established design system unless it fills a real missing primitive

## Recommended Follow-Up

- run `/graph-report` for fast graph orientation
- review `.graphkvignore` before expensive graph refreshes
- run `/mcp-audit` to confirm scaffold health
- use `repo-triage` for the first non-trivial task in the repo
- use `mcp-research` when a task spans graph, memory, and web retrieval
- if `time-local` is available, document its productive uses such as log correlation, incident timing, schedule planning, and timezone-aware deadlines
- for frontend repos, document whether agents should prefer `frontend-design-vault`, `react-bits-local`, or both for UI build-out tasks

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
