---
name: project-bootstrap
description: Bootstrap the current repo into the local MCP workflow with one command
argument-hint: "optional extra ignore patterns"
agent: agent
tools:
  - read
  - grep
  - terminal
---
Do a single run-and-orient pass.

Quickly inspect only enough repo-local context to determine:

- whether bootstrap artifacts already exist
- which obvious generated, vendored, dependency, fixture, cache, or build-output folders should be passed as `--graphkv-ignore PATTERN`

Also identify the most likely real build/test entrypoints so the post-bootstrap orientation reflects the actual repo rather than generic scaffold text.

Do not manually create scaffold files that `/home/Aaditya/bin/opencode-project-init` generates.

If bootstrap artifacts are mostly missing, run `/home/Aaditya/bin/opencode-project-init` with the smallest justified set of repeatable `--graphkv-ignore PATTERN` flags.

If bootstrap artifacts already exist, do not recreate them. Summarize the current bootstrap state, note missing pieces, and say whether rerunning bootstrap is actually necessary.

After the bootstrap decision, continue with the orientation pass in the same prompt:

- run `./.opencode/scripts/audit-opencode` when bootstrap artifacts are present
- read `AGENTS.md`, `.graphkvignore`, `GRAPHKV_NOTES.md`, `docs/opencode/mcp-workflows.md`, `docs/opencode/runtime-notes.md`, `opencode.json`, and `.vscode/mcp.json` when present
- summarize the generated slash commands, MCP wiring, ignore strategy, and the repo-specific follow-up customizations still needed

Then summarize:

- whether bootstrap was run or intentionally skipped
- which flags were used and why
- what the repo's likely real build/test entrypoints are
- which files or configs were created or detected
- whether `./.opencode/scripts/audit-opencode` passed
- whether `graphkv-local` and `graphkvLocal` wiring are present
- whether `.graphkvignore` looks sufficient or needs follow-up
- which scaffolded slash commands and guidance files are now available
- the next repo-specific customizations to make