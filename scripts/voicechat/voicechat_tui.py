#!/usr/bin/env python3
import argparse
import json
import os
import signal
import subprocess
import sys
import termios
import threading
import time
import tty
from pathlib import Path

from rich.console import Console, Group
from rich.layout import Layout
from rich.live import Live
from rich.panel import Panel
from rich.table import Table
from rich.text import Text


SESSIONS_ROOT = Path("/home/Aaditya/ai-stack/out/ai-stack/voicechat-live")


def slugify(value: str) -> str:
    import re

    text = value.strip().lower()
    text = re.sub(r"[^a-z0-9._-]+", "-", text)
    return text.strip("-") or "session"


def read_text(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8").strip()
    except FileNotFoundError:
        return ""
    except Exception as exc:
        return f"<read error: {exc}>"


def tail_lines(path: Path, limit: int = 24) -> list[str]:
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
        return lines[-limit:]
    except FileNotFoundError:
        return []
    except Exception as exc:
        return [f"<read error: {exc}>"]


def read_state(path: Path) -> dict:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        return {}
    except Exception as exc:
        return {"phase": f"state read error: {exc}"}


def session_status(process: subprocess.Popen | None) -> str:
    if process is None:
        return "not started"
    if process.poll() is None:
        return "running"
    return f"exited ({process.returncode})"


def scroll_text(value: str, offset: int, window_chars: int = 7000) -> str:
    if not value:
        return ""
    lines = value.splitlines()
    if not lines:
        return value
    start = max(0, min(offset, max(0, len(lines) - 1)))
    visible = "\n".join(lines[start:])
    if len(visible) > window_chars:
        visible = visible[-window_chars:]
    return visible


def colorize_conversation(lines: list[str], offset: int) -> Text:
    text = Text()
    visible = lines[max(0, offset) :]
    if len(visible) > 24:
        visible = visible[-24:]
    for line in visible:
        style = "white"
        if '"role": "user"' in line:
            style = "green"
        elif '"role": "agent"' in line:
            style = "magenta"
        elif '"role": "tool_call"' in line:
            style = "yellow"
        text.append(line + "\n", style=style)
    if not visible:
        text.append("No conversation log yet.", style="dim")
    return text


class TUIState:
    def __init__(self, session_dir: Path):
        self.session_dir = session_dir
        self.user_offset = 0
        self.agent_offset = 0
        self.conv_offset = 0
        self.selected = "conversation"
        self.stop_event = threading.Event()

    @property
    def mute_file(self) -> Path:
        return self.session_dir / "mute.flag"

    @property
    def ptt_file(self) -> Path:
        return self.session_dir / "ptt.flag"

    @property
    def state_file(self) -> Path:
        return self.session_dir / "live_state.json"

    def toggle_mute(self):
        if self.mute_file.exists():
            self.mute_file.unlink()
        else:
            self.mute_file.write_text("muted\n", encoding="utf-8")

    def press_ptt(self):
        self.ptt_file.write_text("active\n", encoding="utf-8")

    def release_ptt(self):
        try:
            self.ptt_file.unlink()
        except FileNotFoundError:
            pass


def build_layout(
    session_name: str, session_dir: Path, process: subprocess.Popen | None, ui: TUIState
) -> Layout:
    layout = Layout()
    layout.split_column(
        Layout(name="header", size=7),
        Layout(name="body", ratio=1),
        Layout(name="footer", size=5),
    )
    layout["body"].split_row(
        Layout(name="left", ratio=2),
        Layout(name="right", ratio=1),
    )
    layout["left"].split_column(
        Layout(name="user"),
        Layout(name="agent"),
    )
    layout["right"].split_column(
        Layout(name="status", size=13),
        Layout(name="tools"),
        Layout(name="conversation"),
    )

    state = read_state(ui.state_file)
    header_table = Table.grid(expand=True)
    header_table.add_column(ratio=1)
    header_table.add_column(ratio=1)
    header_table.add_row(
        f"[bold cyan]VoiceChat TUI[/bold cyan]\nSession: [bold]{session_name}[/bold]",
        f"Status: [bold]{session_status(process)}[/bold]\nOutput: {session_dir}",
    )
    layout["header"].update(Panel(header_table, title="Session", border_style="cyan"))

    user_text = (
        read_text(session_dir / "user_text.txt") or "Waiting for user transcript..."
    )
    agent_text = (
        read_text(session_dir / "agent_text.txt") or "Waiting for agent transcript..."
    )
    tool_lines = tail_lines(session_dir / "function_calls.jsonl", limit=20)
    conv_lines = tail_lines(session_dir / "conversation.jsonl", limit=60)

    user_panel = Panel(
        Text(scroll_text(user_text, ui.user_offset), style="green"),
        title="User Transcript",
        subtitle=f"offset={ui.user_offset}",
        border_style="green",
    )
    agent_panel = Panel(
        Text(scroll_text(agent_text, ui.agent_offset), style="magenta"),
        title="Agent Transcript",
        subtitle=f"offset={ui.agent_offset}",
        border_style="magenta",
    )
    layout["user"].update(user_panel)
    layout["agent"].update(agent_panel)

    status_text = Text()
    status_text.append(f"phase: {state.get('phase', 'unknown')}\n", style="cyan")
    status_text.append(
        f"memory loaded: {state.get('memory_context_loaded', False)}\n", style="yellow"
    )
    status_text.append(
        f"last tool: {state.get('last_tool', '') or 'none'}\n", style="yellow"
    )
    status_text.append(f"rollovers: {state.get('rollover_count', 0)}\n", style="yellow")
    status_text.append(
        f"chunks sent/recv: {state.get('chunks_sent', 0)} / {state.get('chunks_received', 0)}\n",
        style="white",
    )
    status_text.append(
        f"mute: {state.get('mute', False)}\n",
        style="red" if state.get("mute") else "green",
    )
    status_text.append(
        f"ptt active: {state.get('push_to_talk_active', False)}\n",
        style="green" if state.get("push_to_talk_active") else "red",
    )
    if state.get("session_error_message"):
        status_text.append(
            f"last error: {state.get('session_error_message')}\n",
            style="bold red",
        )
    layout["status"].update(
        Panel(status_text, title="Memory / Session Status", border_style="cyan")
    )

    tool_text = Text()
    if tool_lines:
        for line in tool_lines[-12:]:
            tool_text.append(line + "\n", style="yellow")
    else:
        tool_text.append("No tool calls yet.", style="dim")
    layout["tools"].update(Panel(tool_text, title="Tool Calls", border_style="yellow"))

    layout["conversation"].update(
        Panel(
            colorize_conversation(conv_lines, ui.conv_offset),
            title="Conversation Log",
            subtitle=f"offset={ui.conv_offset}",
            border_style="blue",
        )
    )

    footer = Group(
        Text(
            "Controls: q quit | m mute toggle | p push-to-talk toggle | 1/2/3 select pane | j/k scroll",
            style="bold",
        ),
        Text(
            "Selected pane: user=1, agent=2, conversation=3. TUI tails files written by voicechat-live.",
            style="dim",
        ),
    )
    layout["footer"].update(Panel(footer, border_style="white"))
    return layout


def keyboard_thread(ui: TUIState):
    if not sys.stdin.isatty():
        return
    fd = sys.stdin.fileno()
    old = termios.tcgetattr(fd)
    try:
        tty.setcbreak(fd)
        while not ui.stop_event.is_set():
            ch = os.read(fd, 1)
            if not ch:
                continue
            if ch in (b"q", b"Q"):
                ui.stop_event.set()
                return
            if ch == b"m":
                ui.toggle_mute()
            elif ch == b"p":
                if ui.ptt_file.exists():
                    ui.release_ptt()
                else:
                    ui.press_ptt()
            elif ch == b"1":
                ui.selected = "user"
            elif ch == b"2":
                ui.selected = "agent"
            elif ch == b"3":
                ui.selected = "conversation"
            elif ch == b"j":
                if ui.selected == "user":
                    ui.user_offset += 1
                elif ui.selected == "agent":
                    ui.agent_offset += 1
                else:
                    ui.conv_offset += 1
            elif ch == b"k":
                if ui.selected == "user":
                    ui.user_offset = max(0, ui.user_offset - 1)
                elif ui.selected == "agent":
                    ui.agent_offset = max(0, ui.agent_offset - 1)
                else:
                    ui.conv_offset = max(0, ui.conv_offset - 1)
    finally:
        termios.tcsetattr(fd, termios.TCSADRAIN, old)


def main() -> int:
    parser = argparse.ArgumentParser(description="VoiceChat live TUI")
    parser.add_argument(
        "--check",
        action="store_true",
        help="Validate startup prerequisites and exit without launching the interactive UI.",
    )
    parser.add_argument(
        "--audio-mode",
        choices=["auto", "easyeffects", "direct"],
        default="auto",
        help="Audio routing mode for the wrapped live session.",
    )
    parser.add_argument(
        "session_name", nargs="?", default=f"session-{time.strftime('%Y%m%d-%H%M%S')}"
    )
    args = parser.parse_args()

    session_name = slugify(args.session_name)
    session_dir = SESSIONS_ROOT / session_name
    session_dir.mkdir(parents=True, exist_ok=True)

    if args.check:
        print(f"voicechat-tui check ok\nsession={session_name}\noutput={session_dir}")
        return 0

    launcher = [
        "/home/Aaditya/bin/voicechat-live",
        "--audio-mode",
        args.audio_mode,
        session_name,
    ]
    process = subprocess.Popen(
        launcher,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.STDOUT,
        stdin=subprocess.DEVNULL,
    )

    ui = TUIState(session_dir)

    def handle_signal(signum, frame):
        ui.stop_event.set()

    signal.signal(signal.SIGINT, handle_signal)
    signal.signal(signal.SIGTERM, handle_signal)

    key_thread = threading.Thread(target=keyboard_thread, args=(ui,), daemon=True)
    key_thread.start()

    console = Console()
    with Live(
        build_layout(session_name, session_dir, process, ui),
        console=console,
        refresh_per_second=4,
        screen=True,
    ) as live:
        while not ui.stop_event.is_set():
            live.update(build_layout(session_name, session_dir, process, ui))
            if process.poll() is not None:
                ui.stop_event.set()
                break
            time.sleep(0.25)

    ui.release_ptt()

    if process.poll() is None:
        process.terminate()
        try:
            process.wait(timeout=10)
        except subprocess.TimeoutExpired:
            process.kill()
            process.wait(timeout=5)

    console.print(f"Session outputs kept at [bold]{session_dir}[/bold]")
    return process.returncode or 0


if __name__ == "__main__":
    raise SystemExit(main())
