# Graphify Notes

## Runtime Pin

This repo currently targets the local Graphify runtime in:

- `/home/Aaditya/venvs/graphify`

Pinned operational version:

- `graphifyy 0.4.12`

## Why 0.4.12

`0.4.12` is the best practical line for this machine and repo setup right now.

Reasons:

- installs cleanly on the current Python 3.14 environment
- includes newer MCP robustness fixes compared with the older `0.4.1` install
- includes better stdio handling, matching, and semantic-preservation behavior than the old install
- avoids the `graspologic` dependency path that currently makes the `v1` line fragile on newer Python versions

## Why Not v1 Right Now

The `v1.0.0` / `v1` line is not the active target here because:

- packaging metadata regresses to `0.1.x`
- it depends on `graspologic`
- that dependency chain is not reliable on this Python 3.14 machine
- the `v1` code path also drops some useful behavior that exists in `0.4.12`

## Local Wrapper Expectations

Even on `0.4.12`, this repo keeps local wrapper logic for things upstream does not solve well enough for our workflow:

- empty repo bootstrap fallback graph
- repo-local OpenCode plugin and slash command wiring
- repo-specific graph overlay for `ai-stack`
- bootstrap defaults and audit checks

## View Graph Filtering

This repo now generates reports, wiki pages, and HTML from a filtered presentation graph.

The raw `graphify-out/graph.json` still keeps the full merged graph, but presentation outputs intentionally drop low-value nodes that were making reports noisy.

Current local filtering removes:

- long truncated prose/docstring snippet nodes that Graphify sometimes materializes as graph nodes

This is a repo-local cleanup layer in `.opencode/scripts/graphify_repo_overlay.py` so we can keep `0.4.12` stable while improving report quality without depending on more upstream changes.

## Large Repo HTML

The local runtime has been relaxed to allow large HTML graph export attempts instead of failing immediately at the upstream hard node cap.

This does not guarantee the HTML will always be pleasant on very large repos, but it avoids unnecessary hard failure for cases where a large generated HTML artifact is still acceptable.

## Related Docs

- `docs/opencode/bootstrap-maintenance.md` tracks the machine-global bootstrap files that also need manual sync.
- `docs/opencode/bootstrap-regression-checklist.md` captures the regression checks to run after bootstrap or Graphify changes.
