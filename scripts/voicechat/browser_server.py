#!/usr/bin/env python3
import argparse
import json
import os
import threading
import time
import unicodedata
import uuid
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse

import requests


ROOT = Path("/home/Aaditya/ai-stack")
STATIC_ROOT = ROOT / "web" / "voicechat-browser"
SESSIONS_ROOT = ROOT / "out" / "ai-stack" / "voicechat-browser"
INSTRUCTIONS_FILE = ROOT / "config" / "voicechat" / "default_instructions.txt"
TOOLS_FILE = ROOT / "config" / "voicechat" / "default_tools.json"
VOICECHAT_WS_URL = "ws://127.0.0.1:8080/v1/realtime"
VOICECHAT_READY_URL = "http://127.0.0.1:8080/v1/realtime/health"
EMBED_READY_URL = "http://127.0.0.1:8001/v1/models"
MEMORY_MCP_URL = os.environ.get("VOICECHAT_MEMORY_MCP_URL", "http://127.0.0.1:3010/mcp")


def ascii_sanitize(text, limit=None):
    if text is None:
        return ""
    value = str(text)
    value = value.replace("\u2013", "-").replace("\u2014", "-").replace("\u2019", "'")
    value = value.replace("\u201c", '"').replace("\u201d", '"')
    value = (
        unicodedata.normalize("NFKD", value).encode("ascii", "ignore").decode("ascii")
    )
    value = " ".join(value.split())
    if limit and len(value) > limit:
        value = value[: max(0, limit - 3)].rstrip() + "..."
    return value


def clip_text(text, limit):
    return ascii_sanitize(text, limit=limit)


class MCPToolSession:
    def __init__(self, url, client_name):
        self.url = url
        self.client_name = client_name
        self.session_id = None
        self.initialized = False
        self.request_id = 0
        self.http = requests.Session()
        self.http.headers.update(
            {
                "Accept": "application/json, text/event-stream",
                "Content-Type": "application/json",
            }
        )

    def _next_id(self):
        self.request_id += 1
        return self.request_id

    def _extract_payload(self, text):
        for line in (text or "").splitlines():
            if line.startswith("data:"):
                payload = line[5:].strip()
                if payload:
                    return json.loads(payload)
        raise ValueError("MCP response did not contain a data payload")

    def _post(self, payload, timeout=60):
        headers = {}
        if self.session_id:
            headers["mcp-session-id"] = self.session_id
        resp = self.http.post(self.url, headers=headers, json=payload, timeout=timeout)
        resp.raise_for_status()
        if not self.session_id and resp.headers.get("mcp-session-id"):
            self.session_id = resp.headers["mcp-session-id"]
        if not resp.text.strip():
            return None
        data = self._extract_payload(resp.text)
        if "error" in data:
            raise RuntimeError(data["error"].get("message", "Unknown MCP error"))
        return data.get("result")

    def ensure_initialized(self):
        if self.initialized:
            return
        self._post(
            {
                "jsonrpc": "2.0",
                "id": self._next_id(),
                "method": "initialize",
                "params": {
                    "protocolVersion": "2025-03-26",
                    "capabilities": {},
                    "clientInfo": {"name": self.client_name, "version": "1.0"},
                },
            },
            timeout=30,
        )
        self._post(
            {"jsonrpc": "2.0", "method": "notifications/initialized", "params": {}},
            timeout=30,
        )
        self.initialized = True

    def call_tool(self, name, arguments, timeout=60):
        self.ensure_initialized()
        result = self._post(
            {
                "jsonrpc": "2.0",
                "id": self._next_id(),
                "method": "tools/call",
                "params": {"name": name, "arguments": arguments},
            },
            timeout=timeout,
        )
        if not isinstance(result, dict):
            return result
        structured = result.get("structuredContent") or {}
        if isinstance(structured, dict) and "result" in structured:
            value = structured["result"]
        else:
            content = result.get("content") or []
            value = (
                content[0].get("text", "")
                if content and isinstance(content[0], dict)
                else ""
            )
        if isinstance(value, str):
            try:
                return json.loads(value)
            except json.JSONDecodeError:
                return {"result": value}
        return value


class SessionState:
    def __init__(self, session_id: str):
        self.session_id = ascii_sanitize(session_id, limit=120)
        self.session_dir = SESSIONS_ROOT / self.session_id
        self.session_dir.mkdir(parents=True, exist_ok=True)
        self.conversation = []
        self.tool_calls = []
        self.user_transcripts = []
        self.agent_transcripts = []
        self.compaction_summary = None
        self.rollovers = 0
        self.memory_context_text = None
        self.updated_at = time.time()
        self.memory = MCPToolSession(
            MEMORY_MCP_URL, f"voicechat-browser-{self.session_id}"
        )

    def output_path(self, name: str) -> Path:
        return self.session_dir / name

    def save_files(self):
        self.output_path("user_text.txt").write_text(
            "\n".join(self.user_transcripts), encoding="utf-8"
        )
        self.output_path("agent_text.txt").write_text(
            "\n".join(self.agent_transcripts), encoding="utf-8"
        )
        with self.output_path("conversation.jsonl").open("w", encoding="utf-8") as f:
            for entry in self.conversation:
                f.write(json.dumps(entry, ensure_ascii=False) + "\n")
        with self.output_path("function_calls.jsonl").open("w", encoding="utf-8") as f:
            for entry in self.tool_calls:
                f.write(json.dumps(entry, ensure_ascii=False) + "\n")
        state = {
            "session_id": self.session_id,
            "rollovers": self.rollovers,
            "memory_context_loaded": bool(self.memory_context_text),
            "updated_at": self.updated_at,
        }
        self.output_path("session_state.json").write_text(
            json.dumps(state, ensure_ascii=True), encoding="utf-8"
        )

    def build_compaction_summary(self, focus=None):
        pairs = []
        current_user = None
        for entry in self.conversation:
            role = entry.get("role")
            if role == "user":
                current_user = ascii_sanitize(entry.get("content", ""), limit=600)
            elif role == "agent":
                agent = ascii_sanitize(entry.get("content", ""), limit=600)
                if current_user or agent:
                    pairs.append((current_user or "", agent or ""))
                current_user = None
        if not pairs:
            return ascii_sanitize(
                focus or "No prior conversation to summarize.", limit=300
            )

        bullets = []
        for user, agent in pairs[-8:]:
            if user:
                bullets.append(f"User: {user}")
            if agent:
                bullets.append(f"Assistant: {agent}")

        latest_user = self.user_transcripts[-1] if self.user_transcripts else ""
        latest_agent = self.agent_transcripts[-1] if self.agent_transcripts else ""
        summary = []
        if focus:
            summary.append(f"Focus: {ascii_sanitize(focus, limit=240)}")
        if latest_user:
            summary.append(
                f"Latest user request: {ascii_sanitize(latest_user, limit=500)}"
            )
        if latest_agent:
            summary.append(
                f"Latest assistant reply: {ascii_sanitize(latest_agent, limit=500)}"
            )
        summary.append("Recent conversation highlights:")
        summary.extend(f"- {line}" for line in bullets[-10:])
        return clip_text("\n".join(summary), 2800)


class SessionStore:
    def __init__(self):
        self.lock = threading.Lock()
        self.sessions = {}
        self.default_instructions = INSTRUCTIONS_FILE.read_text(
            encoding="utf-8"
        ).strip()
        self.default_tools = json.loads(TOOLS_FILE.read_text(encoding="utf-8"))

    def get(self, session_id: str) -> SessionState:
        with self.lock:
            state = self.sessions.get(session_id)
            if state is None:
                state = SessionState(session_id)
                self._load_existing(state)
                self.sessions[session_id] = state
            return state

    def _load_existing(self, state: SessionState):
        conv = state.output_path("conversation.jsonl")
        if conv.exists():
            for line in conv.read_text(encoding="utf-8").splitlines():
                if not line.strip():
                    continue
                try:
                    entry = json.loads(line)
                except json.JSONDecodeError:
                    continue
                state.conversation.append(entry)
                role = entry.get("role")
                content = entry.get("content")
                if role == "user" and isinstance(content, str):
                    state.user_transcripts.append(content)
                elif role == "agent" and isinstance(content, str):
                    state.agent_transcripts.append(content)
                elif role == "tool_call":
                    state.tool_calls.append(content)
        state_file = state.output_path("session_state.json")
        if state_file.exists():
            try:
                data = json.loads(state_file.read_text(encoding="utf-8"))
                state.rollovers = int(data.get("rollovers") or 0)
            except Exception:
                pass

    def load_memory_context(self, state: SessionState):
        try:
            result = state.memory.call_tool(
                "memory_get_context",
                {
                    "session_id": state.session_id,
                    "query": "voice conversation preferences ongoing tasks remembered facts",
                    "max_items": 6,
                    "include_short_term": True,
                    "include_long_term": True,
                    "include_reasoning": False,
                },
                timeout=60,
            )
        except Exception as exc:
            state.memory_context_text = None
            return {"error": str(exc)}
        context = result.get("context") if isinstance(result, dict) else result
        state.memory_context_text = clip_text(context or "", 2400) or None
        state.updated_at = time.time()
        state.save_files()
        return {"ok": True, "memory_context_loaded": bool(state.memory_context_text)}

    def effective_instructions(self, state: SessionState) -> str:
        parts = [self.default_instructions]
        if state.compaction_summary:
            parts.append(
                "Carry-over summary: " + clip_text(state.compaction_summary, 2400)
            )
        if state.memory_context_text:
            parts.append(
                "Relevant persistent memory: "
                + clip_text(state.memory_context_text, 2400)
            )
        return "\n\n".join([p for p in parts if p])

    def bootstrap(self, session_id: str):
        state = self.get(session_id)
        self.load_memory_context(state)
        return {
            "session_id": state.session_id,
            "ws_url": VOICECHAT_WS_URL,
            "instructions": self.effective_instructions(state),
            "tools": self.default_tools,
            "memory_context_loaded": bool(state.memory_context_text),
            "rollovers": state.rollovers,
            "output_dir": str(state.session_dir),
            "conversation": state.conversation,
            "tool_calls": state.tool_calls,
            "user_transcripts": state.user_transcripts,
            "agent_transcripts": state.agent_transcripts,
        }

    def append_event(self, session_id: str, role: str, content, extra=None):
        state = self.get(session_id)
        entry = {
            "role": role,
            "content": content,
            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
        }
        if extra:
            entry.update(extra)
        state.conversation.append(entry)
        if role == "user":
            state.user_transcripts.append(str(content))
            try:
                state.memory.call_tool(
                    "memory_store_message",
                    {
                        "session_id": state.session_id,
                        "role": "user",
                        "content": ascii_sanitize(content, limit=4000),
                        "metadata": {
                            "source": "voicechat-browser",
                            "kind": "user_transcript",
                        },
                    },
                    timeout=60,
                )
            except Exception:
                pass
        elif role == "agent":
            state.agent_transcripts.append(str(content))
            try:
                state.memory.call_tool(
                    "memory_store_message",
                    {
                        "session_id": state.session_id,
                        "role": "assistant",
                        "content": ascii_sanitize(content, limit=4000),
                        "metadata": {
                            "source": "voicechat-browser",
                            "kind": "agent_transcript",
                        },
                    },
                    timeout=60,
                )
            except Exception:
                pass
        elif role == "tool_call":
            state.tool_calls.append(content)
        state.updated_at = time.time()
        state.save_files()
        return {"ok": True}

    def handle_tool_call(self, session_id: str, name: str, arguments):
        state = self.get(session_id)
        args = arguments if isinstance(arguments, dict) else {}
        if name == "compact_conversation_context":
            summary = state.build_compaction_summary(args.get("focus"))
            state.compaction_summary = summary
            state.rollovers += 1
            try:
                state.memory.call_tool(
                    "memory_store_message",
                    {
                        "session_id": state.session_id,
                        "role": "assistant",
                        "content": ascii_sanitize(
                            f"Compaction summary for rollover {state.rollovers}: {summary}",
                            limit=4000,
                        ),
                        "metadata": {
                            "source": "voicechat-browser",
                            "kind": "compaction_summary",
                        },
                    },
                    timeout=60,
                )
            except Exception:
                pass
            state.updated_at = time.time()
            state.save_files()
            return {
                "result": clip_text(
                    "Context compacted. I kept the current goal, the recent exchange, and the details most likely to matter for the next turn. I will reopen a fresh working context and continue from that summary.",
                    600,
                ),
                "summary": summary,
                "session_id": state.session_id,
                "rollover_count": state.rollovers,
                "client_action": "rollover_after_response",
            }
        if name == "recall_relevant_memory":
            try:
                result = state.memory.call_tool(
                    "memory_search",
                    {
                        "query": ascii_sanitize(args.get("query", ""), limit=500),
                        "limit": 5,
                        **(
                            {"session_id": state.session_id}
                            if args.get("scope") == "session"
                            else {}
                        ),
                    },
                    timeout=60,
                )
                return {
                    "result": clip_text(json.dumps(result, ensure_ascii=True), 2400)
                }
            except Exception as exc:
                return {"error": f"Memory recall failed: {exc}"}
        if name == "remember_note":
            try:
                state.memory.call_tool(
                    "memory_store_message",
                    {
                        "session_id": state.session_id,
                        "role": "user",
                        "content": ascii_sanitize(args.get("note", ""), limit=4000),
                        "metadata": {
                            "source": "voicechat-browser",
                            "category": args.get("category") or "memory_note",
                        },
                    },
                    timeout=60,
                )
                return {"result": "I saved that for later."}
            except Exception as exc:
                return {"error": f"Remember note failed: {exc}"}
        return {"result": f"Tool {name} is not available"}


STORE = SessionStore()


class Handler(BaseHTTPRequestHandler):
    def _json(self, status, payload):
        data = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(data)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(data)

    def _read_json(self):
        length = int(self.headers.get("Content-Length", "0"))
        data = self.rfile.read(length) if length else b"{}"
        return json.loads(data.decode("utf-8"))

    def _serve_static(self, relpath: str, content_type: str):
        path = STATIC_ROOT / relpath
        if not path.exists():
            self.send_error(HTTPStatus.NOT_FOUND)
            return
        data = path.read_bytes()
        self.send_response(HTTPStatus.OK)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def do_GET(self):
        parsed = urlparse(self.path)
        if parsed.path == "/":
            self._serve_static("index.html", "text/html; charset=utf-8")
            return
        if parsed.path == "/app.js":
            self._serve_static("app.js", "application/javascript; charset=utf-8")
            return
        if parsed.path == "/style.css":
            self._serve_static("style.css", "text/css; charset=utf-8")
            return
        if parsed.path == "/api/health":
            payload = {
                "ok": True,
                "voicechat_ready": requests.get(VOICECHAT_READY_URL, timeout=5).ok,
                "embed_ready": requests.get(EMBED_READY_URL, timeout=5).ok,
            }
            self._json(HTTPStatus.OK, payload)
            return
        self.send_error(HTTPStatus.NOT_FOUND)

    def do_POST(self):
        parsed = urlparse(self.path)
        body = self._read_json()
        if parsed.path == "/api/session/bootstrap":
            session_id = ascii_sanitize(
                body.get("session_id") or f"browser-{uuid.uuid4().hex[:8]}", limit=120
            )
            self._json(HTTPStatus.OK, STORE.bootstrap(session_id))
            return
        if parsed.path == "/api/session/event":
            self._json(
                HTTPStatus.OK,
                STORE.append_event(
                    ascii_sanitize(body.get("session_id", ""), limit=120),
                    body.get("role", ""),
                    body.get("content", ""),
                    body.get("extra") or None,
                ),
            )
            return
        if parsed.path == "/api/tool-call":
            payload = STORE.handle_tool_call(
                ascii_sanitize(body.get("session_id", ""), limit=120),
                body.get("name", ""),
                body.get("arguments") or {},
            )
            STORE.append_event(
                ascii_sanitize(body.get("session_id", ""), limit=120),
                "tool_call",
                {
                    "name": body.get("name", ""),
                    "arguments": body.get("arguments") or {},
                    "result": payload,
                },
            )
            self._json(HTTPStatus.OK, payload)
            return
        self.send_error(HTTPStatus.NOT_FOUND)

    def log_message(self, fmt, *args):
        return


def main():
    parser = argparse.ArgumentParser(description="VoiceChat browser bridge")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8090)
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()

    if args.check:
        print(f"voicechat-browser check ok\nurl=http://{args.host}:{args.port}/")
        return 0

    SESSIONS_ROOT.mkdir(parents=True, exist_ok=True)
    httpd = ThreadingHTTPServer((args.host, args.port), Handler)
    print(f"VoiceChat browser bridge listening at http://{args.host}:{args.port}/")
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        httpd.server_close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
