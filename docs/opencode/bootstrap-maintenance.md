# Bootstrap Maintenance

These files affect future `/project-bootstrap` runs on this machine but are not tracked by the `ai-stack` git repo itself:

- `/home/Aaditya/bin/opencode-project-init`
- `/home/Aaditya/.config/opencode/commands/project-bootstrap.md`
- `/home/Aaditya/AGENTS_TEMPLATE.md`

When bootstrap behavior changes in `ai-stack`, keep these machine-global files in sync.

## When To Update Them

Update the machine-global bootstrap files when any of these change in `ai-stack`:

- `.opencode/agents/*`
- `.opencode/skills/*`
- `.opencode/commands/*`
- `.opencode/plugins/*`
- `.opencode/scripts/*`
- `docs/opencode/graphify-notes-template.md`
- `docs/opencode/mcp-workflows.md`
- `docs/opencode/runtime-notes.md`
- `GRAPHIFY_NOTES.md`
- the intended top-level `AGENTS.md` guidance for new repos

## Minimum Sync Checklist

- copy any newly required scaffolded file into `opencode-project-init`
- update `/project-bootstrap` summary bullets if bootstrap outputs changed
- update `AGENTS_TEMPLATE.md` if the intended default routing guidance changed
- re-run bootstrap on a fresh throwaway repo and inspect the generated files

## Verification Target

Use a fresh scratch repo and confirm it receives:

- `AGENTS.md`
- `GRAPHIFY_NOTES.md`
- `docs/opencode/mcp-workflows.md`
- `docs/opencode/runtime-notes.md`
- `.opencode/agents/*`
- `.opencode/skills/*`
- `.opencode/commands/*`
- `.opencode/scripts/*`
- `opencode.json` with `graphify-local`
- `.gitignore` entries for generated artifacts
