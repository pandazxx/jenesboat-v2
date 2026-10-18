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


def _stdout_sink(line: str) -> None:
    console = _browser_console()
    if console is not None:
        # Only the JS console: on a phone pygbag has no in-page terminal and routes stdout to
        # the console too, so printing as well would show every event twice.
        console.log(line)
    else:
        print(line, flush=True, file=sys.stdout)


_sink: Sink = _stdout_sink


def set_sink(sink: Sink | None) -> None:
    """Redirect events (used by tests and the headless CLI)."""
    global _sink
    _sink = sink or _stdout_sink


def format_event(event: str, **data: Any) -> str:
    payload = {"event": event, **data}
    return PREFIX + json.dumps(payload, separators=(",", ":"), sort_keys=True)


def emit(event: str, **data: Any) -> None:
    _sink(format_event(event, **data))


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
