# Local AI Profiles

Use `/home/Aaditya/bin/ai-profile` to switch the GPU between the two intended modes.

## Retrieval Mode

```bash
/home/Aaditya/bin/ai-profile retrieval
```

This keeps the retrieval stack hot:
- `rag-embed.service`
- `local-reasoner.service`
- `neo4j-memory-mcp.service`

It also stops:
- `gemma4-vllm.service`
- `rag-rerank.service`

Notes:
- `local-reasoner.service` can take a few minutes on a cold start before `http://127.0.0.1:8000/v1/models` is reachable.
- Firecrawl structured extraction depends on that endpoint when `/home/Aaditya/services/firecrawl/.env` points `OPENAI_BASE_URL` at the local reasoner.
- If Firecrawl model env changes, recreate only the API container with `/home/Aaditya/bin/firecrawl-compose up -d --force-recreate api`.

## Gemma Mode

```bash
/home/Aaditya/bin/ai-profile gemma
```

This keeps the local Gemma server hot:
- `gemma4-vllm.service`

It also stops:
- `rag-embed.service`
- `rag-rerank.service`
- `local-reasoner.service`
- `neo4j-memory-mcp.service`
