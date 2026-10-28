#!/usr/bin/env python3
"""laya_ingest_feedback.py -- fold real-usage corrections into the eval corpus.

Closes the recursive-improvement loop:

    /feedback  ->  feedback.jsonl  ->  [this script]  ->  eval/laya_packs_eval.json
                                                              |
                                                              v
                                                     scripts/laya_optimize.py re-tunes

Each feedback row ({pack, state, correct, ...}) becomes an eval case
({pack, expect, state}). Duplicate (pack,state) pairs are de-duplicated; a later
correction overrides an earlier expectation for the same state. Use --dry-run to
preview without writing.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
FEEDBACK = ROOT / "out" / "ai-stack" / "laya" / "feedback.jsonl"
EVAL = ROOT / "eval" / "laya_packs_eval.json"


def _key(pack: str, state: dict) -> str:
    return pack + "\u0000" + json.dumps(state, sort_keys=True, ensure_ascii=False)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--feedback", default=str(FEEDBACK))
    ap.add_argument("--eval", default=str(EVAL))
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    fb_path, eval_path = Path(args.feedback), Path(args.eval)
    if not fb_path.exists():
        print(f"no feedback file at {fb_path}; nothing to ingest")
        return 0

    eval_data = (
        json.loads(eval_path.read_text()) if eval_path.exists() else {"cases": []}
    )
    cases = eval_data.setdefault("cases", [])
    index = {_key(c["pack"], c["state"]): c for c in cases}

    added = updated = 0
    for line in fb_path.read_text().splitlines():
        line = line.strip()
        if not line:
            continue
        row = json.loads(line)
        pack, state, correct = row.get("pack"), row.get("state"), row.get("correct")
        if not (pack and isinstance(state, dict) and correct):
            continue
        k = _key(pack, state)
        if k in index:
            if index[k].get("expect") != correct:
                index[k]["expect"] = correct
                updated += 1
        else:
            case = {"pack": pack, "expect": correct, "state": state}
            cases.append(case)
            index[k] = case
            added += 1

    print(
        f"feedback rows -> +{added} new cases, {updated} updated (total {len(cases)})"
    )
    if args.dry_run:
        print("dry-run: eval file not modified")
        return 0
    if added or updated:
        eval_path.write_text(json.dumps(eval_data, indent=2, ensure_ascii=False) + "\n")
        print(f"wrote {eval_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
