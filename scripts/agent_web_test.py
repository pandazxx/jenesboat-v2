#!/usr/bin/env python3
"""Drive a web build in headless Chromium the way an LLM agent would.

    uv run python scripts/agent_web_test.py https://pandazxx.github.io/jenesboat-v2/builds/abc1234/
    uv run python scripts/agent_web_test.py http://localhost:8000/ --keys W:3,D:2 --screenshot s.png

Loads the page, waits for the game's ``JENESBOAT {"event":"ready"}`` console line, presses
keys, collects ``state`` events, takes a screenshot and prints a JSON summary.  Exit code is
0 when the game became ready, produced state events and (if keys were pressed) the
submarine moved; 1 otherwise.  Requires ``uv run playwright install chromium``.
"""

from __future__ import annotations

import argparse
import json
import math
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from jenesboat_v2.events import parse  # noqa: E402

KEY_CODES = {"SPACE": "Space", "ENTER": "Enter", "ESC": "Escape"}


def key_code(name: str) -> str:
    name = name.strip()
    if name.upper() in KEY_CODES:
        return KEY_CODES[name.upper()]
    if len(name) == 1 and name.isalpha():
        return f"Key{name.upper()}"
    return name


def parse_keys(spec: str) -> list[tuple[str, float]]:
    out = []
    for item in filter(None, (s.strip() for s in spec.split(","))):
        key, _, secs = item.partition(":")
        out.append((key_code(key), float(secs or 1.0)))
    return out


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("url")
    p.add_argument("--keys", default="W:3,D:2", help="key:seconds sequence, '' for none")
    p.add_argument("--settle", type=float, default=2.0, help="seconds to observe after keys")
    p.add_argument("--ready-timeout", type=float, default=240.0)
    p.add_argument("--screenshot", default="dist/agent/web.png")
    p.add_argument("--out", default="dist/agent/web.json", help="where to write the summary")
    p.add_argument("--headed", action="store_true")
    args = p.parse_args()

    from playwright.sync_api import sync_playwright

    events: list[dict] = []
    console: list[str] = []
    errors: list[str] = []

    def on_console(msg):
        text = msg.text
        console.append(text)
        ev = parse(text)
        if ev:
            events.append(ev)
        elif msg.type == "error":
            errors.append(text)

    def has(event: str) -> bool:
        return any(e["event"] == event for e in events)

    summary: dict = {"url": args.url, "ok": False}
    with sync_playwright() as pw:
        browser = pw.chromium.launch(headless=not args.headed, args=["--use-gl=swiftshader"])
        page = browser.new_page(viewport={"width": 1024, "height": 640})
        page.on("console", on_console)
        page.on("pageerror", lambda err: errors.append(str(err)))
        t0 = time.time()
        page.goto(args.url, wait_until="load", timeout=120_000)
        while not has("ready") and time.time() - t0 < args.ready_timeout:
            page.wait_for_timeout(250)
        summary["ready_seconds"] = round(time.time() - t0, 1)
        summary["ready"] = next((e for e in events if e["event"] == "ready"), None)
        if summary["ready"] is None:
            summary["console_tail"] = console[-40:]
            summary["errors"] = errors
            _finish(summary, args, page)
            browser.close()
            return 1

        canvas = page.locator("canvas").first
        try:
            canvas.click(timeout=5_000)
        except Exception:  # noqa: BLE001 - focus is best effort
            page.mouse.click(512, 320)
        page.wait_for_timeout(1_000)
        first = _last_state(events)
        for code, secs in parse_keys(args.keys):
            page.keyboard.down(code)
            page.wait_for_timeout(int(secs * 1000))
            page.keyboard.up(code)
        page.wait_for_timeout(int(args.settle * 1000))
        last = _last_state(events)

        summary.update(
            {
                "states": sum(1 for e in events if e["event"] == "state"),
                "first_state": first,
                "last_state": last,
                "errors": errors,
            }
        )
        moved = None
        if first and last and args.keys:
            dx = last["player"]["x"] - first["player"]["x"]
            dy = last["player"]["y"] - first["player"]["y"]
            moved = math.hypot(dx, dy)
            summary["player_moved_m"] = round(moved, 1)
            summary["speed_kn"] = last["player"]["speed_kn"]
        summary["ok"] = bool(last) and (moved is None or moved > 1.0)
        _finish(summary, args, page)
        browser.close()
    return 0 if summary["ok"] else 1


def _last_state(events: list[dict]) -> dict | None:
    for e in reversed(events):
        if e["event"] == "state":
            return e
    return None


def _finish(summary: dict, args, page) -> None:
    shot = Path(args.screenshot)
    shot.parent.mkdir(parents=True, exist_ok=True)
    try:
        page.screenshot(path=str(shot))
        summary["screenshot"] = str(shot)
    except Exception as exc:  # noqa: BLE001
        summary["screenshot_error"] = str(exc)
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n")
    print(json.dumps(summary, indent=2, sort_keys=True))


if __name__ == "__main__":
    sys.exit(main())
