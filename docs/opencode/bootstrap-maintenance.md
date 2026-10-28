# Bootstrap Maintenance

These files affect future `/project-bootstrap` runs on this machine but are not tracked by the `ai-stack` git repo itself:

- `/home/Aaditya/bin/opencode-project-init`
- `/home/Aaditya/.config/opencode/commands/project-bootstrap.md`
- `/home/Aaditya/AGENTS_TEMPLATE.md`
- `/home/Aaditya/.copilot/prompts/*`
- `/home/Aaditya/.copilot/agents/*`
- `/home/Aaditya/.copilot/skills/*/SKILL.md`
- `/home/Aaditya/.copilot/instructions/*`

When bootstrap behavior changes in `ai-stack`, keep these machine-global files in sync.

## When To Update Them

Update the machine-global bootstrap files when any of these change in `ai-stack`:

- `.opencode/agents/*`
- `.opencode/skills/*`
- `.opencode/commands/*`
- `.opencode/plugins/*`
- `.opencode/scripts/*`
- `.graphkvignore` defaults or `docs/opencode/graphkvignore-template`
- `docs/opencode/graphkv-notes-template.md`
- `docs/opencode/mcp-workflows.md`
- `docs/opencode/runtime-notes.md`
- `GRAPHKV_NOTES.md`
- the intended top-level `AGENTS.md` guidance for new repos

## Minimum Sync Checklist

- copy any newly required scaffolded file into `opencode-project-init`
- update `/project-bootstrap` summary bullets if bootstrap outputs changed
- update `AGENTS_TEMPLATE.md` if the intended default routing guidance changed
- keep `.copilot` prompt, agent, skill, and instruction sources in sync with `.github` copies
- update `.graphkvignore` guidance whenever GraphKV skip semantics or bootstrap flags change
- re-run bootstrap on a fresh throwaway repo and inspect the generated files

## Verification Target

Use a fresh scratch repo and confirm it receives:

- `AGENTS.md`
- `GRAPHKV_NOTES.md`
- `.graphkvignore`
- `docs/opencode/graphkvignore-template`
- `docs/opencode/mcp-workflows.md`
- `docs/opencode/runtime-notes.md`
- `.opencode/agents/*`
- `.opencode/skills/*`
- `.opencode/skills/project-bootstrap/SKILL.md`
- `.opencode/skills/llm-council/SKILL.md`
- `.github/prompts/project-bootstrap.prompt.md`
- `.opencode/commands/*`
- `.opencode/scripts/*`
- `opencode.json` with `graphkv-local`
- `.vscode/mcp.json` with `graphkvLocal`
- `.gitignore` entries for generated artifacts
- generated guidance that tells agents to append repo-specific GraphKV ignores before expensive graph builds
- generated VS Code slash-command guidance that tells agents to run the bootstrap command instead of hand-creating scaffold files
