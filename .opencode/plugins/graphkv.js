import { existsSync } from "node:fs"
import { join } from "node:path"

const reminder = [
  "GraphKV knowledge graph is available in graphkv-out/.",
  "Use graphkv-local_graph_stats, graphkv-local_god_nodes, and graphkv-local_query_graph for fast structural search when relationships matter.",
  "Use graphkv-local_get_node, graphkv-local_get_neighbors, or graphkv-local_shortest_path for drilldown; native file, shell, and MCP tools remain available.",
  "Use graphkv-out/GRAPH_REPORT.md or graphkv-out/wiki/index.md when a generated artifact is faster than a tool call.",
  "Before refreshing stale artifacts, update .graphkvignore for generated, vendored, dependency, cache, fixture, or build-output folders.",
].join(" ")

const remindedSessions = new Set()

export const GraphKVPlugin = async ({ directory }) => {
  const graphPath = join(directory, "graphkv-out", "graph.json")

  return {
    "experimental.chat.system.transform": async (_input, output) => {
      if (!existsSync(graphPath)) return
      output.system.push(reminder)
    },
    "tool.execute.before": async (input, output) => {
      if (!existsSync(graphPath)) return
      if (input.tool !== "bash") return
      if (remindedSessions.has(input.sessionID)) return
      if (!output.args || typeof output.args.command !== "string") return

      output.args.command = [
        "printf '%s\\n' '[graphkv] Knowledge graph available. graphkv-local augments search; native tools remain available.' >&2",
        output.args.command,
      ].join(" && ")
      remindedSessions.add(input.sessionID)
    },
  }
}