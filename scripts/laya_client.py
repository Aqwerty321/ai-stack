"""laya_client - thin importable client for the local Laya decision service.

Wraps laya-decide.service (default http://127.0.0.1:8008) so other stack code can
make System-1 typed decisions without re-implementing HTTP plumbing. Stdlib only.

    from laya_client import LayaClient
    laya = LayaClient()                      # or LayaClient("http://host:8008")
    d = laya.gate("tool_risk", {"proposed_tool": "bash",
                                "proposed_args_summary": "git push --force origin main"})
    if d.blocking:                           # verdict in the pack's blocking set
        confirm_with_user()

The client is intentionally policy-agnostic: verdict semantics live in the pack
JSON, not here. `Decision.is_(...)` / `.verdict` expose the raw result.
"""

from __future__ import annotations

import json
import urllib.request
import urllib.error
from dataclasses import dataclass
from typing import Any, Optional

DEFAULT_URL = "http://127.0.0.1:8008"

# Verdicts that mean "do not auto-proceed" across the shipped packs. Advisory
# only; callers can inspect .verdict directly for finer control.
_BLOCKING = {"block", "warn", "quarantine", "clarify", "not_done", "unverified"}


@dataclass
class Decision:
    pack: str
    verdict: Optional[str]
    action: Optional[str]
    confidence: float
    abstained: bool
    raw: dict

    def is_(self, *verdicts: str) -> bool:
        return self.verdict in verdicts

    @property
    def blocking(self) -> bool:
        """True if the verdict indicates the agent should pause/confirm."""
        return self.verdict in _BLOCKING

    def __bool__(self) -> bool:
        """Truthy when it is safe to proceed (not blocking, not abstained)."""
        return not self.blocking and not self.abstained


class LayaError(RuntimeError):
    pass


class LayaClient:
    def __init__(self, url: str = DEFAULT_URL, timeout: float = 30.0):
        self.url = url.rstrip("/")
        self.timeout = timeout

    def _req(self, path: str, payload: Any = None) -> dict:
        data = json.dumps(payload).encode() if payload is not None else None
        req = urllib.request.Request(
            f"{self.url}{path}",
            data=data,
            headers={"Content-Type": "application/json"},
            method="POST" if data is not None else "GET",
        )
        try:
            with urllib.request.urlopen(req, timeout=self.timeout) as r:
                return json.load(r)
        except urllib.error.HTTPError as e:
            raise LayaError(
                f"HTTP {e.code}: {e.read().decode(errors='replace')}"
            ) from e
        except urllib.error.URLError as e:
            raise LayaError(f"cannot reach {self.url}: {e.reason}") from e

    # -- introspection ------------------------------------------------------
    def health(self) -> dict:
        return self._req("/healthz")

    def ready(self) -> bool:
        try:
            return bool(self.health().get("router_ready"))
        except LayaError:
            return False

    def packs(self) -> Any:
        return self._req("/packs")

    # -- decisions ----------------------------------------------------------
    def gate(self, pack: str, state: dict) -> Decision:
        """Evaluate a named decision pack against a state dict."""
        r = self._req(f"/gate/{pack}", {"state": state})
        return Decision(
            pack=r.get("pack", pack),
            verdict=r.get("verdict"),
            action=r.get("action"),
            confidence=float(r.get("confidence", 0.0) or 0.0),
            abstained=bool(r.get("abstained")),
            raw=r,
        )

    def decide(self, state: dict, questions: dict) -> dict:
        """Ad-hoc typed decision without a saved pack (raw answers)."""
        return self._req("/decide", {"state": state, "questions": questions})


if __name__ == "__main__":  # tiny smoke test
    c = LayaClient()
    print("ready:", c.ready())
    d = c.gate(
        "tool_risk",
        {
            "proposed_tool": "bash",
            "proposed_args_summary": "git push --force origin main",
        },
    )
    print(
        d.pack,
        "->",
        d.verdict,
        f"{d.confidence:.2f}",
        "blocking" if d.blocking else "ok",
    )
