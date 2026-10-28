#!/usr/bin/env python3
"""laya_optimize.py -- offline policy-threshold auto-optimizer for Laya decision packs.

Recursive self-improvement at the POLICY layer, without touching model weights:

  1. Replay each eval case once through /gate (logging disabled) and cache the raw
     model answers (noul / score / choice / probabilities / confidence) to disk.
     Raw answers are the expensive part; caching makes the threshold search GPU-free
     and instant on reruns.
  2. Coordinate-descent search the numeric thresholds (the ``value`` on each noul/score
     policy rule) per pack to maximize verdict accuracy against the ground-truth labels
     in eval/laya_packs_eval.json.
  3. Report accuracy delta AND expected calibration error (ECE) so a tuning pass never
     silently trades calibration for one point of accuracy.
  4. With --write, persist the improved thresholds back into the pack JSONs (a .bak of
     each changed pack is written first). Restart the service to load them.

This is deliberately conservative: it only moves numeric thresholds that already exist
in a pack's policy. It never invents rules, reorders them, or edits verdict labels.
"""

from __future__ import annotations

import argparse
import copy
import json
import os
import sys
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PACKS_DIR = Path(os.environ.get("LAYA_PACKS_DIR", "/home/Aaditya/bin/laya-packs"))
EVAL_PATH = ROOT / "eval" / "laya_packs_eval.json"
CACHE_PATH = ROOT / "out" / "ai-stack" / "laya" / "opt_cache.json"
DEFAULT_URL = "http://127.0.0.1:8008"

NUMERIC_OPS = {">=", "<=", ">", "<"}


# --------------------------------------------------------------------------- #
# Verdict resolution -- a faithful local replica of the server's resolve_verdict
# so we can score candidate policies against cached answers with no GPU calls.
# --------------------------------------------------------------------------- #
def resolve(pack: dict, answers: dict) -> dict:
    floor = float(pack.get("floor", 0.0))
    top_conf = 0.0
    for a in answers.values():
        c = a.get("confidence")
        if isinstance(c, (int, float)):
            top_conf = max(top_conf, float(c))

    for rule in pack.get("policy", []):
        w = rule["when"]
        a = answers.get(w["key"], {})
        prim = w["primitive"]
        val = a.get(prim)
        if val is None:
            continue
        val = float(val) if isinstance(val, (int, float)) else val
        op, ref = w["op"], w["value"]
        hit = (
            (op == ">=" and val >= ref)
            or (op == "<=" and val <= ref)
            or (op == ">" and val > ref)
            or (op == "<" and val < ref)
            or (op == "==" and val == ref)
        )
        if hit:
            return {
                "verdict": rule.get("verdict"),
                "confidence": top_conf,
                "abstained": top_conf < floor,
            }
    d = pack.get("default", {})
    return {
        "verdict": d.get("verdict"),
        "confidence": top_conf,
        "abstained": top_conf < floor,
    }


# --------------------------------------------------------------------------- #
# Cache of raw model answers per (pack, state)
# --------------------------------------------------------------------------- #
def _cache_key(pack: str, state: dict) -> str:
    return pack + "\u0000" + json.dumps(state, sort_keys=True, ensure_ascii=False)


def gate_raw(url: str, pack: str, state: dict, cache: dict) -> dict:
    key = _cache_key(pack, state)
    if key in cache:
        return cache[key]
    body = json.dumps({"state": state, "log": False}).encode()
    req = urllib.request.Request(
        f"{url}/gate/{pack}", data=body, headers={"content-type": "application/json"}
    )
    with urllib.request.urlopen(req, timeout=120) as r:
        res = json.loads(r.read().decode())
    answers = res.get("raw", {}).get("answers", {})
    cache[key] = answers
    return answers


# --------------------------------------------------------------------------- #
# Tunable parameters + candidate thresholds (decision-stump style)
# --------------------------------------------------------------------------- #
def tunable_rules(pack: dict) -> list[int]:
    idxs = []
    for i, rule in enumerate(pack.get("policy", [])):
        w = rule["when"]
        if w["primitive"] in ("noul", "score") and w["op"] in NUMERIC_OPS:
            idxs.append(i)
    return idxs


def candidates_for(
    pack: dict, rule_idx: int, cases: list, cache_answers: list
) -> list[float]:
    """Candidate thresholds = midpoints between sorted observed values at that key,
    plus the endpoints and the current value -- the set of splits that can change any
    single decision."""
    w = pack["policy"][rule_idx]["when"]
    key, prim = w["key"], w["primitive"]
    vals = sorted(
        {
            float(ans[key][prim])
            for ans in cache_answers
            if key in ans and isinstance(ans[key].get(prim), (int, float))
        }
    )
    cands = set()
    cands.add(float(w["value"]))
    if vals:
        cands.add(vals[0] - 0.01)
        cands.add(vals[-1] + 0.01)
        for a, b in zip(vals, vals[1:]):
            cands.add(round((a + b) / 2, 4))
    return sorted(cands)


def score_pack(pack: dict, cases: list, cache_answers: list) -> tuple[int, float]:
    """Return (num_correct, ece) for a candidate pack over its cases."""
    correct = 0
    confs, hits = [], []
    for case, ans in zip(cases, cache_answers):
        out = resolve(pack, ans)
        ok = out["verdict"] == case["expect"]
        correct += int(ok)
        confs.append(out["confidence"])
        hits.append(1 if ok else 0)
    return correct, ece(confs, hits)


def ece(confs: list, hits: list, bins: int = 10) -> float:
    if not confs:
        return 0.0
    n = len(confs)
    total = 0.0
    for b in range(bins):
        lo, hi = b / bins, (b + 1) / bins
        idx = [
            i
            for i, c in enumerate(confs)
            if (c > lo or (b == 0 and c == 0)) and c <= hi
        ]
        if not idx:
            continue
        avg_conf = sum(confs[i] for i in idx) / len(idx)
        acc = sum(hits[i] for i in idx) / len(idx)
        total += (len(idx) / n) * abs(acc - avg_conf)
    return round(total, 4)


def optimize_pack(pack: dict, cases: list, cache_answers: list, passes: int = 6):
    best = copy.deepcopy(pack)
    base_correct, base_ece = score_pack(best, cases, cache_answers)
    cur_correct, cur_ece = base_correct, base_ece
    idxs = tunable_rules(best)
    for _ in range(passes):
        improved = False
        for ri in idxs:
            cands = candidates_for(best, ri, cases, cache_answers)
            local_best = best["policy"][ri]["when"]["value"]
            local_correct, local_ece = cur_correct, cur_ece
            for c in cands:
                trial = copy.deepcopy(best)
                trial["policy"][ri]["when"]["value"] = c
                nc, ne = score_pack(trial, cases, cache_answers)
                # accept if more correct, or equal correct with better calibration
                if nc > local_correct or (
                    nc == local_correct and ne < local_ece - 1e-9
                ):
                    local_best, local_correct, local_ece = c, nc, ne
            if local_best != best["policy"][ri]["when"]["value"]:
                best["policy"][ri]["when"]["value"] = local_best
                cur_correct, cur_ece = local_correct, local_ece
                improved = True
        if not improved:
            break
    return best, (base_correct, base_ece), (cur_correct, cur_ece)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--url", default=DEFAULT_URL)
    ap.add_argument("--pack", help="optimize only this pack")
    ap.add_argument("--write", action="store_true", help="persist improved thresholds")
    ap.add_argument(
        "--refresh-cache", action="store_true", help="ignore cached answers"
    )
    args = ap.parse_args()

    eval_data = json.loads(EVAL_PATH.read_text())
    cases_all = eval_data["cases"]

    CACHE_PATH.parent.mkdir(parents=True, exist_ok=True)
    cache = {}
    if CACHE_PATH.exists() and not args.refresh_cache:
        cache = json.loads(CACHE_PATH.read_text())

    packs = sorted({c["pack"] for c in cases_all})
    if args.pack:
        packs = [args.pack]

    grand_base = grand_new = grand_total = 0
    changed_packs = []
    print(f"Fetching raw answers (cache: {len(cache)} entries)...", file=sys.stderr)

    for pname in packs:
        pfile = PACKS_DIR / f"{pname}.json"
        if not pfile.exists():
            print(f"  skip {pname}: no pack file", file=sys.stderr)
            continue
        pack = json.loads(pfile.read_text())
        cases = [c for c in cases_all if c["pack"] == pname]
        cache_answers = [gate_raw(args.url, pname, c["state"], cache) for c in cases]
        CACHE_PATH.write_text(json.dumps(cache))

        best, (bc, be), (nc, ne) = optimize_pack(pack, cases, cache_answers)
        n = len(cases)
        grand_base += bc
        grand_new += nc
        grand_total += n
        flag = ""
        if nc > bc:
            flag = "  <== improved"
            changed_packs.append((pname, pack, best))
        print(f"  {pname:16s} {bc}/{n} (ece {be})  ->  {nc}/{n} (ece {ne}){flag}")
        if nc > bc:
            for ri in tunable_rules(pack):
                old = pack["policy"][ri]["when"]["value"]
                new = best["policy"][ri]["when"]["value"]
                if old != new:
                    w = best["policy"][ri]["when"]
                    print(
                        f"        {w['key']}.{w['primitive']} {w['op']} {old} -> {new}"
                    )

    print(
        f"\n  TOTAL {grand_base}/{grand_total} -> {grand_new}/{grand_total} "
        f"({100 * grand_new // max(grand_total, 1)}%)"
    )

    if args.write and changed_packs:
        for pname, old_pack, best in changed_packs:
            pfile = PACKS_DIR / f"{pname}.json"
            (PACKS_DIR / f"{pname}.json.bak").write_text(json.dumps(old_pack, indent=2))
            best["version"] = int(best.get("version", 1)) + 1
            pfile.write_text(json.dumps(best, indent=2) + "\n")
            print(f"  wrote {pfile} (v{best['version']}, .bak saved)")
        print("  restart service to load: systemctl --user restart laya-decide.service")
    elif args.write:
        print("  no packs improved; nothing written")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
