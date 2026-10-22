#!/usr/bin/env python3
"""Drive a web build in headless Chromium the way an LLM agent would.

    uv run python scripts/agent_web_test.py https://pandazxx.github.io/jenesboat-v2/builds/abc1234/
    uv run python scripts/agent_web_test.py http://127.0.0.1:9000/ --keys W:0.3,D:2
    uv run python scripts/agent_web_test.py http://127.0.0.1:9000/ --mobile --keys "" --taps W,W,D:2

Loads the page, waits for the game's ``JENESBOAT {"event":"ready"}`` console line, presses
keys (and, with ``--mobile``, touches the on-screen buttons named by ``--taps``), collects
``state`` events, takes a screenshot and prints a JSON summary.  Exit code is 0 when the game
became ready, produced state events, the submarine moved if anything was pressed, and every
tap reached the game; 1 otherwise.  Requires ``uv run playwright install chromium``.
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

# An iPhone 16 held sideways: CSS px, pixel ratio and a Safari user agent so the page shows
# the touch buttons and the rotate hint logic sees a phone.
IPHONE_16 = {
    "viewport": {"width": 852, "height": 393},
    "device_scale_factor": 3.0,
    "is_mobile": True,
    "has_touch": True,
    "user_agent": (
        "Mozilla/5.0 (iPhone; CPU iPhone OS 18_0 like Mac OS X) AppleWebKit/605.1.15 "
        "(KHTML, like Gecko) Version/18.0 Mobile/15E148 Safari/604.1"
    ),
}


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


def parse_taps(spec: str) -> list[tuple[str, float]]:
    """``"W,W,D:2"`` -> button names (as in the page's ``data-key``) and seconds held."""
    out = []
    for item in filter(None, (s.strip() for s in spec.split(","))):
        key, _, secs = item.partition(":")
        out.append((key.strip().upper(), float(secs or 0.1)))
    return out


def touch_button(page, cdp, key: str, secs: float) -> dict:
    """Press the on-screen button ``key`` for ``secs`` with a real touch (CDP), so the page's
    pointer handlers see what a finger does."""
    box = page.locator(f'#touch button[data-key="{key}"]').bounding_box()
    if box is None:
        return {"key": key, "error": "button not visible"}
    x, y = box["x"] + box["width"] / 2, box["y"] + box["height"] / 2
    cdp.send("Input.dispatchTouchEvent", {"type": "touchStart", "touchPoints": [{"x": x, "y": y}]})
    page.wait_for_timeout(int(secs * 1000))
    cdp.send("Input.dispatchTouchEvent", {"type": "touchEnd", "touchPoints": []})
    return {"key": key, "seconds": secs, "x": round(x), "y": round(y)}


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("url")
    p.add_argument(
        "--keys",
        default="W:0.3,W:0.3,W:0.3,W:0.3,D:2",
        help="key:seconds sequence ('' for none); W steps the telegraph once per press",
    )
    p.add_argument("--settle", type=float, default=2.0, help="seconds to observe after keys")
    p.add_argument("--ready-timeout", type=float, default=240.0)
    p.add_argument("--screenshot", default="dist/agent/web.png")
    p.add_argument("--out", default="dist/agent/web.json", help="where to write the summary")
    p.add_argument("--headed", action="store_true")
    p.add_argument(
        "--mobile",
        action="store_true",
        help="emulate an iPhone 16 held sideways (852x393 CSS px, 3x pixels, touch screen)",
    )
    p.add_argument(
        "--taps",
        default="",
        help="on-screen buttons to touch after --keys, e.g. 'W,W,W,W,D:2' (name[:seconds])",
    )
    p.add_argument(
        "--dpr",
        type=float,
        default=1.0,
        help="device pixel ratio to emulate (2 reproduces a HiDPI laptop screen)",
    )
    p.add_argument(
        "--expect-difficulty",
        default=None,
        metavar="LEVEL",
        help="fail unless the game started at this level (e.g. after ?difficulty=veteran)",
    )
    args = p.parse_args()
    if args.url.startswith("http://localhost:8"):
        print(
            "warning: pygbag treats http://localhost:8xxx as its dev server and will look for "
            "wheels at http://localhost:8000/cdn/; serve on 127.0.0.1 or another port instead",
            file=sys.stderr,
        )

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

    device = dict(IPHONE_16) if args.mobile else {"viewport": {"width": 1024, "height": 640}}
    if not args.mobile:
        device["device_scale_factor"] = args.dpr
    summary: dict = {"url": args.url, "ok": False, "mobile": args.mobile, "device": device}
    with sync_playwright() as pw:
        browser = pw.chromium.launch(headless=not args.headed, args=["--use-gl=swiftshader"])
        context = browser.new_context(**device)
        page = context.new_page()
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
        taps = parse_taps(args.taps)
        summary["touch_overlay"] = page.evaluate("document.body.classList.contains('touch')")
        if taps:
            cdp = context.new_cdp_session(page)
            summary["taps"] = [touch_button(page, cdp, key, secs) for key, secs in taps]
        page.wait_for_timeout(int(args.settle * 1000))
        last = _last_state(events)

        touched = [e["key"] for e in events if e["event"] == "input" and e.get("source") == "touch"]
        summary.update(
            {
                "states": sum(1 for e in events if e["event"] == "state"),
                "viewport": next((e for e in reversed(events) if e["event"] == "viewport"), None),
                "first_state": first,
                "last_state": last,
                "touch_inputs": touched,
                "errors": errors,
            }
        )
        moved = None
        if first and last and (args.keys or taps):
            dx = last["player"]["x"] - first["player"]["x"]
            dy = last["player"]["y"] - first["player"]["y"]
            moved = math.hypot(dx, dy)
            summary["player_moved_m"] = round(moved, 1)
            summary["speed_kn"] = last["player"]["speed_kn"]
        # Every tapped button that the game logs (not A/D, the rudder keys) must have arrived.
        logged = {"W", "S", "Q", "P", "T", "SPACE", "C", "F", "R", "TIME"}
        expected = [key for key, _ in taps if key in logged]
        taps_ok = sorted(touched) == sorted(expected) if taps else True
        summary["taps_ok"] = taps_ok
        summary["difficulty"] = (last or summary["ready"]).get("difficulty")
        level_ok = args.expect_difficulty in (None, summary["difficulty"])
        summary["difficulty_ok"] = level_ok
        summary["ok"] = bool(last) and (moved is None or moved > 1.0) and taps_ok and level_ok
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
