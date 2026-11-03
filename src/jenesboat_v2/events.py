"""Structured events for agents.

Every event is one line on stdout: the ``JENESBOAT `` prefix followed by a compact JSON
object with at least an ``event`` key.  In the browser (pygbag) stdout goes to the JS
console, so the same lines can be collected with Playwright.
"""

from __future__ import annotations

import json
import platform
import sys
from collections.abc import Callable
from typing import Any

PREFIX = "JENESBOAT "

Sink = Callable[[str], None]


_js_console: Any = None
_js_console_resolved = False


def _browser_console() -> Any:
    """In pygbag, stdout goes to the in-page terminal; mirror events to the JS console so a
    Playwright driver (or a human with devtools) can collect them.  ``None`` elsewhere."""
    global _js_console, _js_console_resolved
    if not _js_console_resolved:
        _js_console_resolved = True
        if platform.system() == "Emscripten":
            try:
                _js_console = platform.window.console  # type: ignore[attr-defined]
            except AttributeError:
                _js_console = None
    return _js_console


_js_log: Any = None
_js_log_resolved = False


def _browser_log() -> Any:
    """The page's ``jb_log(line)`` hook, which keeps the whole run's events for the LOG
    button to download (``web/noctx.tmpl``); ``None`` elsewhere or on an old page."""
    global _js_log, _js_log_resolved
    if not _js_log_resolved:
        _js_log_resolved = True
        if platform.system() == "Emscripten":
            try:
                _js_log = platform.window.jb_log  # type: ignore[attr-defined]
            except AttributeError:
                _js_log = None
    return _js_log


def _stdout_sink(line: str) -> None:
    console = _browser_console()
    if console is not None:
        # Only the JS console: on a phone pygbag has no in-page terminal and routes stdout to
        # the console too, so printing as well would show every event twice.
        console.log(line)
        hook = _browser_log()
        if hook is not None:
            try:
                hook(line)
            except Exception:  # noqa: BLE001 - the page's problem, not the game's
                pass
    else:
        print(line, flush=True, file=sys.stdout)


_sink: Sink = _stdout_sink
_log_file: Any = None


def log_to_file(path: str | None) -> None:
    """Also append every event to ``path`` (the battle log of a native or headless run);
    ``None`` closes the file."""
    global _log_file
    if _log_file is not None:
        _log_file.close()
        _log_file = None
    if path:
        _log_file = open(path, "a", encoding="utf-8")  # noqa: SIM115 - kept open for the run


def _tee(line: str) -> None:
    if _log_file is not None:
        _log_file.write(line + "\n")
        _log_file.flush()


def set_sink(sink: Sink | None) -> None:
    """Redirect events (used by tests and the headless CLI)."""
    global _sink
    _sink = sink or _stdout_sink


def format_event(event: str, **data: Any) -> str:
    payload = {"event": event, **data}
    return PREFIX + json.dumps(payload, separators=(",", ":"), sort_keys=True)


def emit(event: str, **data: Any) -> None:
    line = format_event(event, **data)
    _sink(line)
    _tee(line)


def parse(line: str) -> dict[str, Any] | None:
    """Return the event dict if ``line`` is a jenesboat event, else ``None``."""
    line = line.strip()
    idx = line.find(PREFIX)
    if idx < 0:
        return None
    try:
        obj = json.loads(line[idx + len(PREFIX) :])
    except json.JSONDecodeError:
        return None
    if not isinstance(obj, dict) or "event" not in obj:
        return None
    return obj
