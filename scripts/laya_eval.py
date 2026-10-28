#!/usr/bin/env python3
"""laya_eval — score laya-decide pack verdicts against a labeled set.

Usage:
  laya_eval.py [--url http://127.0.0.1:8008] [--pack NAME] [eval.json]

Reads eval/laya_packs_eval.json, POSTs each case to /gate/{pack} (log disabled),
and reports per-pack and overall verdict accuracy plus each miss with confidence.
"""

from __future__ import annotations

import argparse
import json
import sys
import urllib.request
from collections import defaultdict

DEFAULT_EVAL = "/home/Aaditya/ai-stack/eval/laya_packs_eval.json"


def gate(url: str, pack: str, state: dict) -> dict:
    body = json.dumps({"state": state, "log": False}).encode()
    req = urllib.request.Request(
        f"{url}/gate/{pack}", data=body, headers={"content-type": "application/json"}
    )
    with urllib.request.urlopen(req, timeout=60) as r:
        return json.loads(r.read())


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("eval_file", nargs="?", default=DEFAULT_EVAL)
    ap.add_argument("--url", default="http://127.0.0.1:8008")
    ap.add_argument("--pack", default=None, help="only run cases for this pack")
    ap.add_argument("--json", action="store_true", help="emit machine-readable summary")
    args = ap.parse_args()

    cases = json.load(open(args.eval_file))["cases"]
    if args.pack:
        cases = [c for c in cases if c["pack"] == args.pack]

    per = defaultdict(lambda: {"n": 0, "ok": 0})
    misses = []
    for c in cases:
        try:
            res = gate(args.url, c["pack"], c["state"])
        except Exception as e:  # noqa: BLE001
            print(f"ERROR {c['pack']}: {e}", file=sys.stderr)
            continue
        got = res.get("verdict")
        ok = got == c["expect"]
        per[c["pack"]]["n"] += 1
        per[c["pack"]]["ok"] += int(ok)
        if not ok:
            misses.append(
                {
                    "pack": c["pack"],
                    "expect": c["expect"],
                    "got": got,
                    "confidence": res.get("confidence"),
                    "abstained": res.get("abstained"),
                    "state": c["state"],
                }
            )

    total_n = sum(v["n"] for v in per.values())
    total_ok = sum(v["ok"] for v in per.values())

    if args.json:
        print(
            json.dumps(
                {"per_pack": per, "total": [total_ok, total_n], "misses": misses},
                indent=2,
                default=dict,
            )
        )
        return 0

    print("\n=== per-pack verdict accuracy ===")
    for pack in sorted(per):
        v = per[pack]
        print(f"  {pack:16s} {v['ok']}/{v['n']}")
    print(
        f"\n  OVERALL          {total_ok}/{total_n}  ({100 * total_ok / max(total_n, 1):.0f}%)"
    )

    if misses:
        print("\n=== misses ===")
        for m in misses:
            st = json.dumps(m["state"])[:80]
            print(
                f"  [{m['pack']}] expected={m['expect']} got={m['got']} "
                f"conf={m['confidence']:.2f} abstain={m['abstained']}"
            )
            print(f"      state: {st}")
    return 0 if total_ok == total_n else 1


if __name__ == "__main__":
    raise SystemExit(main())
