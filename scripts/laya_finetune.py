#!/usr/bin/env python3
"""laya_finetune.py -- EXPERIMENTAL weight fine-tune scaffold for Laya decision packs.

STATUS: SCAFFOLD ONLY. This does NOT train by default and is not part of the managed
retrieval profile. It exists to document the *weight-layer* path once the policy-layer
optimizer (scripts/laya_optimize.py) is exhausted and enough real labeled data exists.

Why gated / not-now (see docs/laya/LAYA_DECISION_SERVICE_DESIGN.md):
  * laya 0.3.6 ships inference-only (Agent runs under @torch.no_grad / .eval); there is no
    turnkey trainer. This would drive laya.common.DecisionModel directly.
  * In retrieval mode local-reasoner (vLLM) already holds ~19 GB VRAM; a CUDA fine-tune
    OOMs and there is no headroom, so training would be CPU-only and slow.
  * The base mmBERT head is RLCD-calibrated. Fine-tuning on a few dozen cases would wreck
    calibration (rising ece_score) for a point or two of accuracy -- a bad trade. The
    threshold optimizer captures nearly all near-term gains with ZERO calibration risk.

Guardrails before this may run:
  1. --i-understand-this-is-experimental must be passed explicitly.
  2. At least MIN_CASES labeled examples must exist (default 500) across the corpus.
  3. A held-out split is scored with ece_score; if calibration degrades past --max-ece
     versus the frozen base model, the run is REJECTED and no checkpoint is written.

Data source: eval/laya_packs_eval.json (grown by scripts/laya_ingest_feedback.py from
real /feedback corrections) + out/ai-stack/laya/decisions.jsonl.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
EVAL = ROOT / "eval" / "laya_packs_eval.json"
MIN_CASES = 500


def load_corpus() -> list[dict]:
    data = json.loads(EVAL.read_text()) if EVAL.exists() else {"cases": []}
    return data.get("cases", [])


def main() -> int:
    ap = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    ap.add_argument(
        "--i-understand-this-is-experimental", action="store_true", dest="ack"
    )
    ap.add_argument("--min-cases", type=int, default=MIN_CASES)
    ap.add_argument(
        "--max-ece",
        type=float,
        default=0.10,
        help="reject the run if held-out ECE exceeds this",
    )
    ap.add_argument("--epochs", type=int, default=3)
    args = ap.parse_args()

    cases = load_corpus()
    print(f"corpus: {len(cases)} labeled cases (need >= {args.min_cases})")

    if not args.ack:
        print(
            "\nREFUSING TO TRAIN. This is an experimental weight-layer path.\n"
            "The policy-layer optimizer (scripts/laya_optimize.py) is the supported,\n"
            "calibration-safe way to improve packs today. If you truly intend to fine-tune\n"
            "model weights, re-run with --i-understand-this-is-experimental.\n"
            "Prerequisites: >= %d labeled cases, spare VRAM (not retrieval mode), and a\n"
            "held-out ECE gate below --max-ece." % args.min_cases,
            file=sys.stderr,
        )
        return 2

    if len(cases) < args.min_cases:
        print(
            f"REFUSING: only {len(cases)} cases (< {args.min_cases}). Grow the corpus first\n"
            "via /feedback + scripts/laya_ingest_feedback.py, and keep using\n"
            "scripts/laya_optimize.py in the meantime.",
            file=sys.stderr,
        )
        return 2

    # --- Training path intentionally left unimplemented -----------------------
    # When the guardrails above are satisfied, implement here with:
    #   from laya.common import DecisionModel, build_model, proper_reward, \
    #       td_lambda_targets, ece_score
    #   1. Split cases into train/held-out.
    #   2. Score the FROZEN base model's held-out ece_score as the calibration baseline.
    #   3. Fine-tune DecisionModel on train reward targets (proper_reward /
    #      td_lambda_targets) for --epochs on the available device.
    #   4. Re-score held-out ece_score; if it rose above --max-ece, REJECT (no write).
    #   5. Only on pass, save a checkpoint under a NEW name; never overwrite the
    #      managed checkpoints. Update the pack/router to point at it explicitly.
    print(
        "guardrails passed, but the training body is deliberately unimplemented in this\n"
        "scaffold. Implement steps 1-5 (see source comment) before enabling.",
        file=sys.stderr,
    )
    return 3


if __name__ == "__main__":
    raise SystemExit(main())
