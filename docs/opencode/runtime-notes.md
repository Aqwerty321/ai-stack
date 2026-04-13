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

Firecrawl reads its extraction model settings from `/home/Aaditya/services/firecrawl/.env` when the `api` container is created. After changing `OPENAI_API_KEY`, `OPENAI_BASE_URL`, or `MODEL_NAME`, recreate the `api` container so the new env is applied:

```bash
/home/Aaditya/bin/firecrawl-compose up -d --force-recreate api
```

This is enough for extraction model changes. The rest of the Firecrawl stack does not need to be restarted unless other services changed.

Gemma mode is:

```bash
/home/Aaditya/bin/ai-profile gemma
```

`graphify-local` only knows what is in `graphify-out/graph.json`. Rebuild the graph artifacts if major repo structure changes make Graphify answers look stale.
