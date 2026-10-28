#!/usr/bin/env python3
import argparse
import json
import sys
import time
import urllib.request


def post_json(url: str, payload: dict, timeout: int) -> tuple[dict, float]:
    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        url, data=data, headers={"Content-Type": "application/json"}
    )
    start = time.time()
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        body = resp.read().decode("utf-8")
    end = time.time()
    return json.loads(body), end - start


def extract_message_text(message: dict) -> str:
    content = message.get("content") or ""
    if content:
        return content
    return message.get("reasoning_content") or ""


def stream_json(
    url: str, payload: dict, timeout: int
) -> tuple[str, float | None, float]:
    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        url, data=data, headers={"Content-Type": "application/json"}
    )
    start = time.time()
    first = None
    pieces: list[str] = []
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        for raw in resp:
            line = raw.decode("utf-8").strip()
            if not line.startswith("data: "):
                continue
            chunk = line[6:]
            if chunk == "[DONE]":
                break
            obj = json.loads(chunk)
            delta = obj["choices"][0].get("delta", {})
            piece = (delta.get("content") or "") or (
                delta.get("reasoning_content") or ""
            )
            if piece and first is None:
                first = time.time()
            if piece:
                pieces.append(piece)
    end = time.time()
    return "".join(pieces), (first - start) if first else None, end - start


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Benchmark a local OpenAI-compatible model endpoint."
    )
    parser.add_argument(
        "--base-url", default="http://127.0.0.1:8000", help="OpenAI-compatible base URL"
    )
    parser.add_argument("--model", required=True, help="Model ID to query")
    parser.add_argument("--prompt", required=True, help="Prompt text")
    parser.add_argument(
        "--max-tokens", type=int, default=256, help="Max completion tokens"
    )
    parser.add_argument(
        "--temperature", type=float, default=0.0, help="Sampling temperature"
    )
    parser.add_argument(
        "--timeout", type=int, default=300, help="Request timeout seconds"
    )
    parser.add_argument(
        "--preview-chars", type=int, default=800, help="Returned preview length"
    )
    args = parser.parse_args()

    url = args.base_url.rstrip("/") + "/v1/chat/completions"
    messages = [{"role": "user", "content": args.prompt}]

    payload = {
        "model": args.model,
        "messages": messages,
        "max_tokens": args.max_tokens,
        "temperature": args.temperature,
    }

    non_stream, elapsed = post_json(url, payload, args.timeout)
    usage = non_stream.get("usage", {})
    content = extract_message_text(non_stream["choices"][0]["message"])
    completion_tokens = usage.get("completion_tokens") or 0

    stream_payload = dict(payload)
    stream_payload["stream"] = True
    streamed_text, ttft, stream_elapsed = stream_json(url, stream_payload, args.timeout)

    result = {
        "model": args.model,
        "base_url": args.base_url,
        "prompt_tokens": usage.get("prompt_tokens"),
        "completion_tokens": completion_tokens,
        "total_tokens": usage.get("total_tokens"),
        "non_stream_elapsed_ms": round(elapsed * 1000, 1),
        "approx_output_tok_per_s": round(completion_tokens / elapsed, 2)
        if completion_tokens
        else None,
        "stream_ttft_ms": round(ttft * 1000, 1) if ttft is not None else None,
        "stream_elapsed_ms": round(stream_elapsed * 1000, 1),
        "non_stream_preview": content[: args.preview_chars],
        "stream_preview": streamed_text[: args.preview_chars],
    }
    json.dump(result, sys.stdout, indent=2)
    sys.stdout.write("\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
