#!/usr/bin/env python3
import argparse
import json
import pathlib
import time
import urllib.request


def request_json(url: str, payload: dict, timeout: int) -> tuple[dict, float]:
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


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Run a fixed local model evaluation suite."
    )
    parser.add_argument(
        "--base-url", default="http://127.0.0.1:8000", help="OpenAI-compatible base URL"
    )
    parser.add_argument("--model", required=True, help="Model ID")
    parser.add_argument(
        "--suite", default="eval/local_model_suite_10.json", help="Path to suite JSON"
    )
    parser.add_argument("--out", required=True, help="Output JSON path")
    parser.add_argument(
        "--timeout", type=int, default=300, help="Per-request timeout seconds"
    )
    args = parser.parse_args()

    suite_path = pathlib.Path(args.suite)
    out_path = pathlib.Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)

    suite = json.loads(suite_path.read_text())
    url = args.base_url.rstrip("/") + "/v1/chat/completions"

    results = []
    started_at = time.strftime("%Y-%m-%dT%H:%M:%S%z")
    for item in suite:
        payload = {
            "model": args.model,
            "messages": [{"role": "user", "content": item["prompt"]}],
            "max_tokens": item.get("max_tokens", 256),
            "temperature": item.get("temperature", 0.0),
        }
        response, elapsed = request_json(url, payload, args.timeout)
        usage = response.get("usage", {})
        content = extract_message_text(response["choices"][0]["message"])
        results.append(
            {
                "id": item["id"],
                "category": item.get("category"),
                "prompt": item["prompt"],
                "elapsed_ms": round(elapsed * 1000, 1),
                "usage": usage,
                "response": content,
            }
        )

    output = {
        "model": args.model,
        "base_url": args.base_url,
        "suite": str(suite_path),
        "started_at": started_at,
        "finished_at": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
        "results": results,
    }
    out_path.write_text(json.dumps(output, indent=2))
    print(
        json.dumps(
            {
                "model": args.model,
                "count": len(results),
                "out": str(out_path),
            },
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
