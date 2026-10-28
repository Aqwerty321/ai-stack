# Laya Decision Service — Design (`laya-decide.service`)

Status: **INSTALLED + ENABLED** (2026-09-23) — running, thread-capped, ~260 ms/call warm; 9 retrieval-stack packs live, hardened eval **78/89 (88%)** after policy auto-optimization, recursive self-improvement loop (`/feedback` → ingest → `laya_optimize.py`) shipped, `laya-gate` CLI + `laya_client.py` shipped
Target: always-on local System‑1 typed-decision router for the retrieval-mode AI stack
Grounded against: `laya` **v0.3.6** (PyPI), `convaiinnovations/laya` checkpoints

> **Deployment reality (measured):** venv `/home/Aaditya/venvs/laya` (Python 3.12,
> torch 2.13.0+cu130), service on `127.0.0.1:8008`, **CPU device** (GPU is saturated by
> `local-reasoner` in retrieval mode). Warm latency **~260 ms/call** with `OMP/MKL/torch`
> threads capped to 6 (uncapped caused ~4 s tail spikes under co-tenancy). Startup warmup
> preloads checkpoints + probes each pack's question shape; `/healthz` `router_ready` flips
> true in ~30–60 s. Enabled at login and kept alive in every `ai-profile` via the new
> `always_on_services` group.

---

## 1. What this is (and is not)

Laya is a **non-autoregressive System‑1 decision engine**: it answers a fixed set of *typed
questions* about a *state* in a single ~33 ms encoder forward pass, returning calibrated
probabilities (trained with RLCD / strictly proper scoring rules). It is the closest open,
self-hostable analog to TypeSafe's hosted **Jev**.

It is **not** a generator. It never writes prose, code, or tool arguments. It emits three
primitives only:

| Primitive | Output | Meaning |
|---|---|---|
| `choice` | top label + per-option probabilities + `confidence` | pick 1 of N |
| `score`  | expected level on an ordinal rubric + `confidence` | graded severity/urgency |
| `noul`   | `P(true)` in `[0,1]` | calibrated yes/no |

Design intent: **Laya is the System‑1 reflex layer that gates and routes the System‑2 layer**
(local Gemma/Muse, and premium cloud agents like Claude/GPT). It decides *fast and cheap*
so the expensive models are invoked *deliberately*.

### Explicitly rejected alternatives (recorded so we don't relitigate)
- **DiffusionGemma 26B A4B** — generative diffusion; structured-output is unsolved; benches
  worse than plain Gemma 4. Wrong tool for a reflex router.
- **Distilling from real Jev outputs** — prohibited by TypeSafe terms. We fine-tune Laya on
  *our own* logged states/labels instead.

---

## 2. Why it fits this machine

- Two small encoders: `laya` = ModernBERT-large ~421M, `laya-multilingual`/`typed-decisions`
  = mmBERT-base ~322M. In fp16 the hot set is ~1–2 GB VRAM — negligible next to the retrieval
  services, and it can also run on **CPU** (193–464 ms/call) when the GPU is claimed by an
  exclusive model profile.
- This gives the key property the user asked for: **truly always-on**.
- **Measured reality (2026-09-23):** even in retrieval mode `local-reasoner` (vLLM) holds
  ~19 GB and only ~4–5 GB VRAM is free and fragments under load, so a CUDA Laya OOMs and
  falls back to CPU anyway. Warm CPU latency is **~135 ms/call** (first 1–2 calls ~4 s while
  threads warm), which is fine for a reflex gate. **Therefore the service runs CPU-by-default**
  (`LAYA_DEVICE=cpu`), which also means it never contends with any GPU model profile — truly
  always-on across retrieval/gemma/muse/ornith9. Force `LAYA_DEVICE=cuda` only when the GPU is
  known idle.

---

## 3. Verified API surface (v0.3.6)

```python
import laya
from laya import Router

router = Router(preload=True, device="cuda")   # preload = no per-switch reload

state = {"subject": "...", "body": "..."}       # any dict, any language
questions = {
  "department": {"type": "choice", "instructions": "...",
                 "criteria": {"billing": "...", "technical": "..."}},
  "urgency":    {"type": "score",  "instructions": "...",
                 "criteria": ["not urgent", "soon", "critical"]},
  "refund":     {"type": "noul",   "instructions": "..."},
}

res = router.predict(state, questions)          # ONE forward pass, all questions
res["answers"]["department"]["choice"]          # -> "billing"
res["answers"]["department"]["confidence"]      # -> 0.94   (RLCD-calibrated)
res["answers"]["urgency"]["score"]              # -> 1.84 / 2.0
res["answers"]["refund"]["noul"]                # -> 0.892  (P(true))
res["routing"]["model"], res["routing"]["reason"]

router.route(state, questions).reason           # routing decision, NO forward pass
```

Built-in pre-tuned schemas (reuse before writing our own):
`laya.router_questions()` · `laya.guard_questions()` (jailbreak/injection/leak) ·
`laya.moderation_questions()` · `laya.triage_questions()`.

**Known limits (baked into the design):**
- Context: multilingual/typed default **1024 tokens** (`head_max_len=256`, encoder up to 8192).
  → We feed a *compact RouterState*, never a raw transcript.
- High-cardinality `choice` (>20 options) degrades (fixed per-label token budget). → Keep
  option sets ≤ ~12; use `predict_shortlist` or split questions when larger.
- English checkpoint is confidently wrong on non-Latin scripts → always go through `Router`.

---

## 4. Service architecture

```
                         ┌──────────────────────────────────────────┐
  cloud/local agent ──►  │  laya-decide.service  (127.0.0.1:8008)    │
  (Claude, GPT,          │  FastAPI + uvicorn, 1 worker              │
   Gemma, opencode)      │  ├─ Router(preload=True, device=auto)     │
                         │  ├─ named decision packs (versioned)      │
                         │  ├─ JSONL decision log (for calibration)  │
                         │  └─ Prometheus-style /metrics             │
                         └──────────────────────────────────────────┘
   ports already taken: 8000 reasoner · 8001 embed · 8002 rerank  →  Laya = 8008
```

Single always-on user service, same pattern as the other retrieval services
(`Type=simple`, `Restart=on-failure`, `WantedBy=default.target`).

### 4.1 HTTP API

- `GET  /healthz` → `{status, device, loaded_checkpoints, uptime_s}`
- `GET  /packs` → list installed decision packs + versions
- `POST /decide` → **generic**: `{state, questions, model?}` → raw Laya result
- `POST /gate/{pack}` → **named pack**: `{state, context?}` → typed, thresholded verdict
- `GET  /metrics` → counts, latency histogram, per-pack confidence distribution

`/gate/{pack}` is the primary surface: callers don't hand-write question schemas, they invoke
a *reviewed, versioned* decision pack and get back a small verdict object with an explicit
`action` already resolved against confidence thresholds.

### 4.2 Verdict envelope (uniform across packs)

```json
{
  "pack": "escalate", "pack_version": 3,
  "verdict": "escalate_cloud",
  "action": "route:cloud-frontier",
  "confidence": 0.91,
  "raw": { "answers": {...}, "routing": {...} },
  "abstained": false,
  "latency_ms": 34,
  "decided_at": "2026-09-23T...Z"
}
```

`abstained=true` when max confidence < the pack's floor → caller applies its own safe default
(usually: fall through to the more expensive/ conservative path).

---

## 5. RouterState — the compact input contract

Never send transcripts. Callers assemble a bounded, high-signal dict (target ≤ ~700 state
tokens so it fits the 1024 window with head budget):

```json
{
  "goal": "one-line task objective",
  "last_user": "latest user message, trimmed",
  "last_action": "tool or step just taken",
  "last_result": "short outcome / error summary",
  "open_tools": ["bash", "edit", "webfetch"],
  "proposed_tool": "bash",
  "proposed_args_summary": "rm -rf build/",
  "steps_taken": 7,
  "errors_seen": 2,
  "budget_left": "medium"
}
```

Packs read only the fields they need. This keeps every decision inside one forward pass and
makes logged states reusable as future fine-tuning data.

---

## 6. Decision packs (shipped set)

Each pack = a versioned question schema + threshold policy + verdict mapping, stored as
JSON under `/home/Aaditya/bin/laya-packs/` and hot-loaded. The daemon warms each pack's
question shape at startup. The escalate/route_model idea was **dropped**: `local-reasoner`
(:8000) is only Firecrawl's extraction backend, not a decision target, so Laya never routes
work to it. The 9 shipped packs are all **retrieval-stack reflexes**:

### Tier A — agent control loop
1. **`route_mcp`** — which retrieval surface answers this request
   (`local_files` / `graphkv` / `memory` / `web` / `design` / `inline`). Automates the
   `AGENTS.md` routing rules. `choice{surface}` + `noul{needs_lookup}`.
2. **`tool_risk`** — is the proposed tool call safe to auto-run?
   `noul{remote_or_history}` + `noul{destructive}` + `noul{irreversible}` +
   `choice{risk}` reading `proposed_tool` + `proposed_args_summary`.
3. **`done_verify`** — is the task actually complete or is the agent stopping early?
   `noul{goal_met}` + `noul{verified}` + `score{completion}`.
4. **`clarify`** — is the request underspecified enough to ask first? `score{ambiguity}`
   (score-driven; the `noul{ambiguous}` signal proved inverted and is unused).
5. **`memory_worthy`** — should this be persisted, and in what category? Automates the
   store-only-high-signal rule.

### Tier B — safety reflex
6. **`guard`** — prompt-injection / jailbreak / secret-exfiltration screen on untrusted
   content. `noul{exfiltration}` → block, `noul{injection}` → quarantine, else allow.

### Tier C — retrieval quality
7. **`repo_structural`** — graphkv (relationships) vs grep (needle). `score{relationship_depth}`
   drives it; the `noul{structural}` signal proved unreliable and is unused.
8. **`web_scope`** — searxng vs firecrawl search/scrape/map for a web need. `choice{tool}`.
9. **`rag_triage`** — per-passage keep/drop before the reranker. `score{relevance}` < 0.5 → drop.

**Tuning insight (2026-09-23):** across `route_mcp`, `repo_structural`, `clarify`, and
`rag_triage`, the calibrated ordinal `score` primitive was far more reliable than the binary
`noul` on the same question (noul was often noisy or inverted), and many-option `choice`
degrades. Policies were moved onto `score` gates where a `noul` was fighting the label.
A `route_mcp` rewrite into a 5-way `noul` cascade *regressed* (everything fell to `inline`),
so it stays a single `choice`.

**Eval:** `eval/laya_packs_eval.json` (**89 labeled cases**, ~10/pack with hard negatives)
scored by `scripts/laya_eval.py`. On the hardened set the untuned baseline was **72/89 (81%)**;
after policy-layer auto-optimization (`scripts/laya_optimize.py`) it is **78/89 (88%)**, live-verified.
Perfect packs: `guard`, `rag_triage`, `repo_structural`, `web_scope`. The residual misses are
dominated by the `route_mcp` 6-way `choice` at its **model margin ceiling** (thresholds cannot
move a `choice` argmax), which is why the earlier small-set 94% did not survive harder negatives.

> **Overfitting caveat:** with ~10 cases/pack the tuned thresholds are decision-stump-optimal on
> the eval set itself, so 88% is an optimistic point estimate. The `/feedback` → ingest loop
> (§8) exists to grow the corpus so thresholds generalize; the optimizer tracks `ece_score` and
> only accepts equal-accuracy moves when calibration improves.

Packs are additive; new ones ship without touching the daemon.

---

## 6a. CLI + client

- **`laya-gate`** (`/home/Aaditya/bin/laya-gate`, stdlib-only): `--list`, `--health`, and
  `laya-gate <pack> -s k=v ... [--json|--state-json|--stdin]`. Exit codes compose in shell
  gates: `0` proceed, `2` hold (block/warn/quarantine/clarify/not_done/unverified), `3` abstain,
  `1` error — e.g. `laya-gate tool_risk -s proposed_args_summary="rm -rf /" && run || confirm`.
- **`scripts/laya_client.py`** (`LayaClient` / `Decision`): importable helper for stack code;
  `Decision.blocking`, truthiness = safe-to-proceed, `.raw` for full envelope.

---

## 7. Integration points

- **opencode / agents**: a lightweight pre-tool hook posts a RouterState to `/gate/tool_risk`;
  high-risk steps get confirmation. `/gate/route_mcp` picks the retrieval surface,
  `/gate/done_verify` guards premature "task complete", `/gate/guard` screens scraped content.
- **retrieval pipeline**: rag pipeline calls `/gate/rag_triage` between embed recall and
  rerank to drop obvious non-matches cheaply.
- **cloud-agent empowerment**: the whole point — cloud agents delegate the *reflex* decisions
  (route, risk, done, guard, triage) to a free local ~260 ms service, spending premium tokens
  only on genuine System‑2 work.

---

## 8. Learning loop (why we log) — **SHIPPED (policy layer)**

Every `/decide` and `/gate` call appends one JSONL row: `{pack, pack_version, state, answers,
confidence, verdict, ts}` (PII-scrubbed, opt-out flag per request). The recursive
self-improvement loop is now implemented at the **policy/threshold layer** (calibration-safe,
GPU-free):

```
/gate  ──▶ decisions.jsonl (raw model outputs)
/feedback (or `laya-gate <pack> --feedback <correct>`) ──▶ feedback.jsonl (labeled corrections)
        │
        ▼  scripts/laya_ingest_feedback.py  (dedup by pack+state, later label wins)
eval/laya_packs_eval.json  ──▶  scripts/laya_optimize.py
        │  replay each case once via /gate, cache raw answers (no more GPU),
        │  coordinate-descent the numeric noul/score thresholds to maximize accuracy,
        │  track ece_score, write back improved packs (+.bak, version bump)
        ▼
scripts/laya_eval.py  ──▶  live re-verify
```

Scripts:
- `scripts/laya_optimize.py [--pack P] [--write] [--refresh-cache]` — offline threshold
  auto-optimizer. Faithful local replica of `resolve_verdict`; only moves numeric thresholds
  that already exist (never invents/reorders rules or edits verdict labels).
- `scripts/laya_ingest_feedback.py [--dry-run]` — folds `feedback.jsonl` into the eval corpus.
- `scripts/laya_finetune.py` — **EXPERIMENTAL, gated scaffold** for the weight layer. Refuses
  to run without `--i-understand-this-is-experimental`, `>= 500` labeled cases, and a held-out
  `ece_score` gate. Not-now because laya 0.3.6 is inference-only, retrieval-mode VRAM is
  saturated, and fine-tuning a calibrated head on tiny data would wreck calibration.

No Jev outputs involved; labels come from our own agent/human corrections and eventual outcomes.

Roadmap: keep growing `feedback.jsonl` → periodic `laya_optimize.py --write` → once the corpus
crosses ~hundreds of real cases, weekly calibration report → only then consider the gated
weight-layer fine-tune behind `/gate?pack_version=` A/B before promotion.

---

## 9. Runtime & profile behavior

- Added to the **retrieval** service set in `ai-profile`; enabled at login with the other
  retrieval services.
- Device selection is automatic in the wrapper: `cuda` if the current profile is retrieval
  and a GPU is free, else `cpu`. This keeps Laya alive during gemma/muse/ornith9 profiles
  without contending for the exclusive model's VRAM.
- `Conflicts=` is intentionally **not** set against the exclusive model services (unlike the
  other retrieval units) precisely because Laya must survive profile switches on CPU. This is
  the one deliberate asymmetry vs. rag-embed/rag-rerank.

---

## 10. Risks & mitigations

| Risk | Mitigation |
|---|---|
| First run downloads ~1–2 GB checkpoints | one-time, cached; document it; pre-warm on install |
| CPU latency (up to ~464 ms) during exclusive profiles | acceptable for a gate; batch where possible; keep only needed checkpoints hot via `preload([...])` |
| >20-option choices degrade | cap option sets, use `predict_shortlist`, or split questions |
| Miscalibration on our domain | temperature recalibration from the JSONL log before trusting thresholds |
| Over-gating slows agents | thresholds tuned to abstain→safe-default; `/metrics` watches abstain rate |

---

## 11. Deliverable artifacts (scaffolded alongside this doc)

- `/home/Aaditya/bin/laya-decide-server.py` — FastAPI daemon
- `/home/Aaditya/bin/laya-decide-start` — zsh wrapper (venv + auto device)
- `/home/Aaditya/.config/systemd/user/laya-decide.service` — user unit
- `ai-profile` — add `laya-decide.service` to retrieval set (pending edit)
- venv: `/home/Aaditya/venvs/laya` (pending install — heavy step, gated on approval)

Install is intentionally **not** executed yet (creates venv + downloads weights). See §12.

## 12. Go/no-go before install
1. Create `/home/Aaditya/venvs/laya`, `pip install laya fastapi uvicorn`.
2. First-run `Router(preload=True)` to pull checkpoints (~1–2 GB).
3. `systemctl --user enable --now laya-decide.service`; add to `ai-profile` retrieval set.
4. Smoke test `/healthz` + one `/gate/escalate` call.
