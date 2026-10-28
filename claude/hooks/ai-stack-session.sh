#!/usr/bin/env bash
# SessionStart hook: Claude Code port of .opencode/plugins/graphkv.js, plus
# graph staleness and ai-profile health checks. stdout becomes session context.
set -uo pipefail

root="${CLAUDE_PROJECT_DIR:-$PWD}"
lines=()

# Put ~/bin (ai-profile, laya-gate, firecrawl-compose, ...) on PATH for Bash tool calls.
if [[ -n "${CLAUDE_ENV_FILE:-}" ]] && ! grep -qs 'HOME/bin' "$CLAUDE_ENV_FILE"; then
  echo 'export PATH="$HOME/bin:$PATH"' >> "$CLAUDE_ENV_FILE"
fi

# --- GraphKV reminder (only in repos that have built graph artifacts) ---
graph="$root/graphkv-out/graph.json"
if [[ -f "$graph" ]]; then
  lines+=("[graphkv] Knowledge graph available in graphkv-out/. It augments search; native tools stay available.")
  if [[ -f "$root/.mcp.json" ]] && grep -q '"graphkv-local"' "$root/.mcp.json"; then
    lines+=("[graphkv] Structural questions: mcp__graphkv-local__graph_stats / god_nodes / query_graph (bfs broad, dfs narrow); drilldown: get_node / get_neighbors / shortest_path / get_community.")
  else
    lines+=("[graphkv] graphkv-local is not registered in this repo's .mcp.json; use graphkv-out/GRAPH_REPORT.md and graphkv-out/wiki/index.md directly.")
  fi
  lines+=("[graphkv] graphkv-out/GRAPH_REPORT.md is the cheapest orientation artifact. Before refreshing, update .graphkvignore for generated/vendored/dependency/cache/build-output folders.")

  if git -C "$root" rev-parse --git-dir >/dev/null 2>&1; then
    graph_mtime="$(stat -c %Y "$graph")"
    newer="$(git -C "$root" rev-list --count --since="@$graph_mtime" HEAD 2>/dev/null || echo 0)"
    if (( newer > 0 )); then
      built="$(date -d "@$graph_mtime" '+%Y-%m-%d %H:%M')"
      lines+=("[graphkv] Graph may be stale: built $built, $newer commit(s) since. Treat topology answers with care; /refresh-graph rebuilds it.")
    fi
  fi
fi

# --- ai-profile health: the shared embed/rerank/memory services back several MCPs ---
if command -v systemctl >/dev/null 2>&1; then
  down=()
  for svc in rag-embed rag-rerank neo4j-memory-mcp; do
    systemctl --user is-active --quiet "$svc.service" 2>/dev/null || down+=("$svc")
  done
  if (( ${#down[@]} > 0 )); then
    lines+=("[ai-stack] Not in retrieval profile (down: ${down[*]}). searxng reranking, react-bits-local, frontend-design-vault and neo4j-memory-local may fail. Restore with: /home/Aaditya/bin/ai-profile retrieval")
  fi
fi

(( ${#lines[@]} > 0 )) && printf '%s\n' "${lines[@]}"
exit 0
