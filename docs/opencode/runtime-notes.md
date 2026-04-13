# Runtime Notes

This repo normally works best in retrieval mode:

```bash
/home/Aaditya/bin/ai-profile retrieval
```

That keeps these services hot:

- `rag-embed.service`
- `local-reasoner.service`
- `neo4j-memory-mcp.service`

The reranker is optional and is not part of the default retrieval profile. Start `rag-rerank.service` manually only if you specifically want the extra reranking layer.

`local-reasoner.service` is a vLLM-backed NVFP4 model and has a noticeable cold-start path. The first startup can spend several minutes downloading weights, compiling, and warming the model before `http://127.0.0.1:8000/v1/models` responds. Treat the service as healthy only after the OpenAI-compatible endpoint answers requests, not just after systemd shows it as running.

Firecrawl reads its LLM-assisted extraction settings from `/home/Aaditya/services/firecrawl/.env` when the `api` container is created. This affects schema extraction, prompt-driven extraction, and other agentic research paths that rely on the configured model. After changing `OPENAI_API_KEY`, `OPENAI_BASE_URL`, or `MODEL_NAME`, recreate the `api` container so the new env is applied:

```bash
/home/Aaditya/bin/firecrawl-compose up -d --force-recreate api
```

This is enough for Firecrawl model changes. The rest of the Firecrawl stack does not need to be restarted unless other services changed.

Gemma mode is:

```bash
/home/Aaditya/bin/ai-profile gemma
```

`graphify-local` only knows what is in `graphify-out/graph.json`. Rebuild the graph artifacts if major repo structure changes make Graphify answers look stale.

The local Graphify runtime is pinned operationally to `graphifyy 0.4.12`. That line has the practical balance of MCP stability and Python compatibility on this machine, and the local wrapper layer carries the remaining repo-specific cleanup and bootstrap behavior.
