# /// script
# requires-python = ">=3.12, <3.13"
# dependencies = [
#     "mcp",
#     "requests",
#     "trafilatura",
# ]
# ///

import math
import os
import re
from concurrent.futures import ThreadPoolExecutor
from urllib.parse import urlparse
import requests
import trafilatura
from mcp.server.fastmcp import FastMCP
from typing import Optional

# Initialize the MCP Server
mcp = FastMCP("SearXNG Intelligence")
SESSION = requests.Session()
SESSION.headers.update({"User-Agent": "searxng-local-mcp/1.0"})
HTTP_ADAPTER = requests.adapters.HTTPAdapter(pool_connections=8, pool_maxsize=8)
SESSION.mount("http://", HTTP_ADAPTER)
SESSION.mount("https://", HTTP_ADAPTER)

SEARXNG_URL = "http://127.0.0.1:8888/search"
EMBED_URL = os.environ.get("EMBED_URL", "http://127.0.0.1:8001/v1/embeddings")
EMBED_MODEL = os.environ.get("EMBED_MODEL", "qwen3-embedding-4b-q4_k_m")
EMBED_CANDIDATES = int(os.environ.get("EMBED_CANDIDATES", "6"))
EMBED_MAX_CHARS = int(os.environ.get("EMBED_MAX_CHARS", "4000"))
EMBED_QUERY_TASK = os.environ.get(
    "EMBED_QUERY_TASK",
    "Given a web search query, retrieve relevant passages that answer the query",
)
RERANK_URL = os.environ.get("RERANK_URL", "http://127.0.0.1:8002/rerank")
RERANK_MODEL = os.environ.get("RERANK_MODEL", "qwen3-reranker-4b")
USE_RERANKER = os.environ.get("USE_RERANKER", "false").lower() == "true"
RERANK_CANDIDATES = int(os.environ.get("RERANK_CANDIDATES", "10"))
RERANK_DOC_CHARS = int(os.environ.get("RERANK_DOC_CHARS", "4000"))
DISPLAY_SNIPPET_CHARS = int(os.environ.get("DISPLAY_SNIPPET_CHARS", "400"))
ANSWER_SENTENCE_CHARS = int(os.environ.get("ANSWER_SENTENCE_CHARS", "280"))
SOCIAL_DOMAINS = {
    "facebook.com",
    "instagram.com",
    "linkedin.com",
    "pinterest.com",
    "reddit.com",
    "tiktok.com",
    "twitter.com",
    "x.com",
    "youtube.com",
}
GATED_DOMAINS = {
    "brainly.com",
    "chegg.com",
    "coursehero.com",
    "studocu.com",
    "study.com",
}
REFERENCE_DOMAINS = {
    "britannica.com",
    "wikipedia.org",
}
SCIENCE_DOMAINS = {
    "arxiv.org",
    "nih.gov",
    "nature.com",
    "ncbi.nlm.nih.gov",
    "pubmed.ncbi.nlm.nih.gov",
    "science.org",
}
LOW_SIGNAL_PATTERNS = (
    "create an account",
    "enable javascript",
    "javascript is required",
    "sign in",
    "subscribe to continue",
    "to unlock this lesson",
)
STOPWORDS = {
    "a",
    "an",
    "and",
    "are",
    "as",
    "at",
    "be",
    "by",
    "for",
    "from",
    "how",
    "in",
    "is",
    "it",
    "of",
    "on",
    "or",
    "that",
    "the",
    "this",
    "to",
    "what",
    "when",
    "where",
    "which",
    "who",
    "why",
}


def _hostname(url: str) -> str:
    return (urlparse(url).hostname or "").lower()


def _host_matches(hostname: str, domains: set[str]) -> bool:
    return any(
        hostname == domain or hostname.endswith(f".{domain}") for domain in domains
    )


def _query_mentions_domain(query: str, hostname: str) -> bool:
    query_lower = query.lower()
    domain_checks = {
        "facebook.com": ("facebook",),
        "instagram.com": ("instagram",),
        "linkedin.com": ("linkedin",),
        "reddit.com": ("reddit",),
        "tiktok.com": ("tiktok",),
        "twitter.com": ("twitter",),
        "x.com": (" x ", "twitter"),
        "youtube.com": ("youtube",),
    }

    for domain, terms in domain_checks.items():
        if _host_matches(hostname, {domain}):
            return any(term in f" {query_lower} " for term in terms)

    return False


def _clip(text: str, limit: int) -> str:
    text = " ".join((text or "").split())
    if len(text) <= limit:
        return text
    return text[: max(0, limit - 3)].rstrip() + "..."


def _looks_like_dump(text: str) -> bool:
    text = (text or "").strip()
    if not text:
        return False

    upper_tokens = re.findall(r"\b[A-Z0-9_]{6,}\b", text)
    if len(upper_tokens) >= 6:
        return True

    if text.count("=") >= 6 or text.count("{") + text.count("}") >= 8:
        return True

    return False


def _source_quality_score(result: dict, query: str, category: Optional[str]) -> float:
    hostname = _hostname(result.get("url") or "")
    url = (result.get("url") or "").lower()
    snippet = (result.get("content") or "").lower()
    page_text = (result.get("page_text") or "").lower()
    score = 0.0

    if hostname.endswith(".gov"):
        score += 0.12
    elif hostname.endswith(".edu"):
        score += 0.10

    if _host_matches(hostname, REFERENCE_DOMAINS):
        score += 0.10

    if category == "it":
        if _host_matches(hostname, {"react.dev", "developer.mozilla.org"}):
            score += 0.12
        if _host_matches(hostname, {"github.com"}):
            score += 0.12
            if any(part in url for part in ("/blob/", "/raw/", "/commit/", "/issues/")):
                score -= 0.10
            if url.endswith("/.config") or "/.config" in url:
                score -= 0.18
            if any(part in url for part in ("/readme", "/releases", "/wiki")):
                score += 0.06
        if (
            hostname.startswith("docs.")
            or hostname.startswith("developer.")
            or "readthedocs" in hostname
        ):
            score += 0.08
        if _host_matches(
            hostname,
            {
                "docs.python.org",
                "docs.vllm.ai",
                "react.dev",
                "requests.readthedocs.io",
            },
        ):
            score += 0.12
        if any(
            term in url
            for term in ("docs", "api", "reference", "requests.readthedocs.io")
        ):
            score += 0.06

    if category == "science" and _host_matches(hostname, SCIENCE_DOMAINS):
        score += 0.12

    if _host_matches(hostname, GATED_DOMAINS):
        score -= 0.18

    if _host_matches(hostname, SOCIAL_DOMAINS) and not _query_mentions_domain(
        query, hostname
    ):
        score -= 0.20

    if any(
        pattern in snippet or pattern in page_text for pattern in LOW_SIGNAL_PATTERNS
    ):
        score -= 0.10

    if _looks_like_dump(snippet or page_text) and not re.search(
        r"\b(config|yaml|json|ini|toml|openwrt|kernel|env)\b", query.lower()
    ):
        score -= 0.12

    return score


def _format_query_for_embedding(query: str) -> str:
    return f"Instruct: {EMBED_QUERY_TASK}\nQuery:{query}"


def _fetch_page_text(url: str) -> str:
    if not url:
        return ""

    try:
        response = SESSION.get(url, timeout=15)
        response.raise_for_status()

        content = trafilatura.extract(
            response.text,
            output_format="txt",
            include_links=False,
        )
        if not content:
            return ""

        return " ".join(content.split())[:EMBED_MAX_CHARS]
    except Exception:
        return ""


def _build_semantic_document(result: dict, page_text: str) -> str:
    title = (result.get("title") or "").strip()
    snippet = (result.get("content") or "").strip()
    parts = [part for part in [title, snippet, page_text] if part]
    document = "\n\n".join(parts)
    return (document or (result.get("url") or "")).strip()[:EMBED_MAX_CHARS]


def _embed_texts(texts: list[str]) -> list[list[float]]:
    response = SESSION.post(
        EMBED_URL,
        json={"model": EMBED_MODEL, "input": texts},
        timeout=30,
    )
    response.raise_for_status()

    data = response.json().get("data", [])
    vectors = [
        item["embedding"] for item in sorted(data, key=lambda item: item["index"])
    ]
    if len(vectors) != len(texts):
        raise ValueError("Embedding response size mismatch")

    return vectors


def _cosine_similarity(left: list[float], right: list[float]) -> float:
    dot = sum(left_value * right_value for left_value, right_value in zip(left, right))
    left_norm = math.sqrt(sum(value * value for value in left))
    right_norm = math.sqrt(sum(value * value for value in right))
    if not left_norm or not right_norm:
        return 0.0
    return dot / (left_norm * right_norm)


def _semantic_rank_results(
    query: str, category: Optional[str], results: list[dict], max_results: int
) -> list[dict]:
    if len(results) < 2:
        return results[:max_results]

    candidate_count = min(len(results), max(max_results, EMBED_CANDIDATES))
    candidates = [dict(result) for result in results[:candidate_count]]
    max_workers = min(4, candidate_count)

    if max_workers > 1:
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            page_texts = list(
                executor.map(
                    lambda result: _fetch_page_text(result.get("url") or ""), candidates
                )
            )
    else:
        page_texts = [_fetch_page_text(candidates[0].get("url") or "")]

    for candidate, page_text in zip(candidates, page_texts):
        candidate["page_text"] = page_text
        candidate["semantic_text"] = _build_semantic_document(candidate, page_text)
        candidate["source_quality_score"] = _source_quality_score(
            candidate, query, category
        )

    try:
        embeddings = _embed_texts(
            [_format_query_for_embedding(query)]
            + [candidate["semantic_text"] for candidate in candidates]
        )
    except Exception:
        candidates.sort(
            key=lambda result: result.get("source_quality_score", 0.0), reverse=True
        )
        return candidates

    query_embedding = embeddings[0]
    for candidate, embedding in zip(candidates, embeddings[1:]):
        candidate["semantic_score"] = _cosine_similarity(query_embedding, embedding)

    candidates.sort(
        key=lambda result: (
            result.get("semantic_score", float("-inf"))
            + result.get("source_quality_score", 0.0)
        ),
        reverse=True,
    )
    return candidates


def _fetch_searxng_results(query: str, category: Optional[str]) -> list[dict]:
    params = {"q": query, "format": "json", "categories": category}
    response = SESSION.get(SEARXNG_URL, params=params, timeout=10)
    response.raise_for_status()
    data = response.json()
    return data.get("results", [])


def _dedupe_results(results: list[dict]) -> list[dict]:
    deduped = []
    seen_urls = set()
    for result in results:
        url = (result.get("url") or "").strip()
        if not url or url in seen_urls:
            continue
        seen_urls.add(url)
        deduped.append(result)
    return deduped


def _it_results_need_fallback(results: list[dict]) -> bool:
    if len(results) < 3:
        return True

    low_signal = 0
    for result in results[:4]:
        hostname = _hostname(result.get("url") or "")
        snippet = result.get("content") or ""
        url = (result.get("url") or "").lower()
        if _host_matches(hostname, {"github.com"}) and (
            _looks_like_dump(snippet)
            or "/.config" in url
            or any(part in url for part in ("/blob/", "/raw/"))
        ):
            low_signal += 1

    return low_signal >= 2


def _build_rerank_document(result: dict) -> str:
    semantic_text = (result.get("semantic_text") or "").strip()
    if semantic_text:
        return semantic_text[:RERANK_DOC_CHARS]

    title = (result.get("title") or "").strip()
    snippet = (result.get("content") or "").strip()
    url = (result.get("url") or "").strip()

    if title and snippet:
        return f"{title}\n\n{snippet}"
    return title or snippet or url


def _display_snippet(result: dict) -> str:
    snippet = (result.get("content") or "").strip()
    if snippet:
        return _clip(snippet, DISPLAY_SNIPPET_CHARS)

    page_text = (result.get("page_text") or "").strip()
    if page_text:
        return _clip(page_text, DISPLAY_SNIPPET_CHARS)

    return _clip(
        _build_rerank_document(result) or "No snippet available.",
        DISPLAY_SNIPPET_CHARS,
    )


def _query_terms(query: str) -> set[str]:
    return {
        token
        for token in re.findall(r"[a-z0-9]+", query.lower())
        if len(token) > 1 and token not in STOPWORDS
    }


def _extract_sentences(text: str) -> list[str]:
    return [
        sentence.strip()
        for sentence in re.split(r"(?<=[.!?])\s+", " ".join(text.split()))
        if sentence.strip()
    ]


def _sentence_score(
    query: str, query_terms: set[str], sentence: str, result: dict
) -> float:
    sentence_lower = sentence.lower()
    if len(sentence) > ANSWER_SENTENCE_CHARS or _looks_like_dump(sentence):
        return float("-inf")

    sentence_terms = set(re.findall(r"[a-z0-9]+", sentence_lower))
    overlap = len(sentence_terms & query_terms)
    if query_terms and overlap == 0:
        return float("-inf")

    score = float(overlap) + result.get(
        "final_score", result.get("semantic_score", 0.0)
    )
    if 40 <= len(sentence) <= 260:
        score += 0.5
    if any(pattern in sentence_lower for pattern in LOW_SIGNAL_PATTERNS):
        score -= 2.0
    if re.search(
        r"\b(how much|how many|grams|kg|percent|calories|population|age|year)\b",
        query.lower(),
    ) and any(char.isdigit() for char in sentence):
        score += 0.5
    return score


def _normalize_text(text: str) -> str:
    return re.sub(r"\s+", " ", re.sub(r"[^a-z0-9]+", " ", text.lower())).strip()


def _synthesize_answer(query: str, results: list[dict]) -> str:
    if not results:
        return "I couldn't find enough evidence to answer that."

    query_terms = _query_terms(query)
    candidates = []
    for result in results[:4]:
        combined_text = "\n".join(
            part
            for part in [
                _display_snippet(result),
                (result.get("page_text") or "")[:800],
            ]
            if part
        )
        for sentence in _extract_sentences(combined_text):
            score = _sentence_score(query, query_terms, sentence, result)
            if score != float("-inf"):
                candidates.append((score, result.get("citation_index", 0), sentence))

    candidates.sort(reverse=True)
    chosen = []
    seen = set()
    for _, citation_index, sentence in candidates:
        normalized = _normalize_text(sentence)
        if not normalized or normalized in seen:
            continue
        seen.add(normalized)
        chosen.append((citation_index, sentence))
        if len(chosen) == 2:
            break

    if not chosen:
        fallback = _display_snippet(results[0]).strip()
        if not fallback:
            return "I couldn't synthesize a reliable short answer from the current sources."
        return f"{fallback[:300].rstrip()} [1]"

    answer_parts = []
    for citation_index, sentence in chosen:
        sentence = _clip(sentence.rstrip(), ANSWER_SENTENCE_CHARS)
        if sentence and sentence[-1] not in ".!?":
            sentence += "."
        answer_parts.append(f"{sentence} [{citation_index}]")

    return " ".join(answer_parts)


def _rerank_results(query: str, results: list[dict], max_results: int) -> list[dict]:
    if not USE_RERANKER:
        return results[:max_results]

    if len(results) < 2:
        return results[:max_results]

    candidate_count = min(len(results), max(max_results, RERANK_CANDIDATES))
    candidates = results[:candidate_count]
    payload = {
        "model": RERANK_MODEL,
        "query": query,
        "documents": [_build_rerank_document(result) for result in candidates],
        "top_n": candidate_count,
    }

    try:
        response = SESSION.post(RERANK_URL, json=payload, timeout=20)
        response.raise_for_status()
        data = response.json()
    except Exception:
        return candidates[:max_results]

    ranked = []
    for item in data.get("results", []):
        index = item.get("index")
        if isinstance(index, int) and 0 <= index < len(candidates):
            ranked_result = dict(candidates[index])
            ranked_result["rerank_score"] = item.get("relevance_score", 0.0)
            ranked_result["final_score"] = ranked_result[
                "rerank_score"
            ] + ranked_result.get("source_quality_score", 0.0)
            ranked.append(ranked_result)

    if not ranked:
        return candidates[:max_results]

    ranked.sort(
        key=lambda result: result.get("final_score", float("-inf")), reverse=True
    )
    return ranked[:max_results]


def _search_results(
    query: str, category: Optional[str], max_results: int
) -> list[dict]:
    results = _fetch_searxng_results(query, category)
    if category == "it" and _it_results_need_fallback(results):
        docs_query = f"{query} site:readthedocs.io OR site:docs.python.org OR site:developer.mozilla.org OR site:github.com"
        fallback_results = _fetch_searxng_results(query, "general")
        docs_results = _fetch_searxng_results(docs_query, "general")
        results = _dedupe_results(fallback_results + docs_results + results)

    if not results:
        return []

    semantic_results = _semantic_rank_results(
        query, category, results, max(1, max_results)
    )
    ranked_results = _rerank_results(query, semantic_results, max(1, max_results))

    return [
        dict(result, citation_index=index)
        for index, result in enumerate(ranked_results, start=1)
    ]


def _format_results(results: list[dict]) -> str:
    output = []
    for result in results:
        output.append(
            f"[{result.get('citation_index')}] {result.get('title')}\nSource: {result.get('url')}\nSnippet: {_display_snippet(result)}\n"
        )
    return "\n".join(output)


@mcp.tool()
def search_web(
    query: str, category: Optional[str] = "general", max_results: int = 5
) -> str:
    """
    Search the web via local SearXNG.
    Categories: 'general', 'it' (GitHub/StackOverflow), 'science' (ArXiv).
    """
    try:
        ranked_results = _search_results(query, category, max_results)
        if not ranked_results:
            return f"No results found for '{query}'."
        return _format_results(ranked_results)

    except Exception as e:
        return f"SearXNG connection error: {str(e)}"


@mcp.tool()
def answer_web(
    query: str, category: Optional[str] = "general", max_results: int = 5
) -> str:
    """
    Search the web and return a short cited answer plus ranked sources.
    Categories: 'general', 'it' (GitHub/StackOverflow), 'science' (ArXiv).
    """
    try:
        ranked_results = _search_results(query, category, max(3, max_results))
        if not ranked_results:
            return f"No results found for '{query}'."

        answer = _synthesize_answer(query, ranked_results)
        return f"Answer:\n{answer}\n\nSources:\n{_format_results(ranked_results[:max_results])}"

    except Exception as e:
        return f"SearXNG connection error: {str(e)}"


@mcp.tool()
def deep_read(url: str) -> str:
    """
    Extracts full Markdown text from a URL.
    Use this to read documentation or full articles found via search.
    """
    try:
        response = SESSION.get(url, timeout=20)
        response.raise_for_status()

        # Gemma-4-26B has a 6k context; returning ~10k chars (roughly 2.5k tokens)
        # is a safe 'deep read' without flooding the VRAM.
        content = trafilatura.extract(
            response.text, output_format="markdown", include_links=True
        )
        return content[:10000] if content else "Error: No readable text found."

    except Exception as e:
        return f"Extraction failed: {str(e)}"


if __name__ == "__main__":
    mcp.run()
