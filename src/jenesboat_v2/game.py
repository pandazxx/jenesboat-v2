"""Frontend-agnostic game session: turns control intents into orders and ticks the world.

The session owns the things a frontend needs that are not physics: time compression, the
map zoom, the message log, the selected target and its fire-control solution, and the
restart.  It never imports raylib.
"""

from __future__ import annotations

import math
import random
from dataclasses import dataclass

from jenesboat_v2 import events
from jenesboat_v2.sim import World, hunting_scenario
from jenesboat_v2.sim.detection import VISUAL, Contact
from jenesboat_v2.sim.params import MERCHANT_AI, RUDDER_RATE
from jenesboat_v2.sim.weapons import Solution, solution

TIME_SCALES = (1, 2, 4, 8, 16, 32)
ZOOM_LEVELS = (2.0, 5.0, 10.0, 20.0, 40.0)  # metres per pixel
DEFAULT_ZOOM = 3  # index: 20 m/px, about 19 km across a 960 px window
MAX_SUBSTEP = 0.1  # s of sim time per physics step
MESSAGE_LIMIT = 6


@dataclass
class Controls:
    """What the player is doing this frame.  ``port``/``starboard`` are held keys (the rudder
    keeps moving while held and stays where it is let go); everything else is an edge."""

    throttle_up: bool = False  # one telegraph position ahead
    throttle_down: bool = False  # one telegraph position astern
    port: bool = False
    starboard: bool = False
    rudder_center: bool = False  # rudder amidships
    dive_toggle: bool = False
    deep: bool = False
    fire: bool = False
    zoom_in: bool = False
    zoom_out: bool = False
    time_scale: int | None = None  # one of TIME_SCALES: switch to that compression
    next_target: bool = False  # select the next contact
    legend: bool = False  # toggle the symbol legend
    pause: bool = False  # toggle pause
    restart: bool = False  # R: asks first unless the hunt is over; R or Y again confirms
    confirm: bool = False  # Y
    cancel: bool = False  # N


class Game:
    def __init__(
        self,
        world: World | None = None,
        state_interval: float = 1.0,
        seed: int | None = None,
    ) -> None:
        self.state_interval = state_interval
        self.seed = seed if seed is not None else random.randrange(1_000_000)
        self.world = world if world is not None else hunting_scenario(self.seed)
        self._since_state = 0.0
        self.state_events = 0
        self.time_scale = TIME_SCALES[0]
        self.zoom_index = DEFAULT_ZOOM
        self.messages: list[tuple[float, str]] = []
        self.restarts = 0
        self.show_legend = False  # off until the player asks for it with L
        self.paused = False
        self.confirming_restart = False  # the 'restart? Y/N' prompt is up; the world is frozen
        self.selected: str | None = None  # ship id chosen with T, else the nearest contact
        self.messages.append((0.0, objective(self.world)))
        self._drain()

    # --- orders ----------------------------------------------------------------------------

    def apply(self, controls: Controls, dt: float) -> None:
        if self.confirming_restart:
            if controls.confirm or controls.restart:
                self.restart()
            elif controls.cancel:
                self.confirming_restart = False
            return
        if controls.restart:
            if self.world.mission_over:  # nothing to lose
                self.restart()
            else:
                self.confirming_restart = True
            return
        sub = self.world.player
        if controls.throttle_up:
            sub.telegraph_step(+1)
        if controls.throttle_down:
            sub.telegraph_step(-1)
        if controls.port:
            sub.set_rudder(sub.rudder - RUDDER_RATE * dt)
        if controls.starboard:
            sub.set_rudder(sub.rudder + RUDDER_RATE * dt)
        if controls.rudder_center:
            sub.set_rudder(0.0)
        if controls.dive_toggle:
            sub.toggle_dive()
        if controls.deep:
            sub.order_deep()
        if controls.fire:
            self.fire()
        if controls.zoom_in:
            self.zoom_index = max(0, self.zoom_index - 1)
        if controls.zoom_out:
            self.zoom_index = min(len(ZOOM_LEVELS) - 1, self.zoom_index + 1)
        if controls.time_scale is not None:
            self.set_time_scale(controls.time_scale)
        if controls.next_target:
            self.next_target()
        if controls.legend:
            self.show_legend = not self.show_legend
        if controls.pause:
            self.toggle_pause()

    def toggle_pause(self) -> None:
        """Freeze the world (orders still apply; they take effect on resume)."""
        self.paused = not self.paused
        events.emit("pause", paused=self.paused, t=round(self.world.time, 2))

    def fire(self) -> bool:
        torpedo = self.world.fire()
        self._drain()
        return torpedo is not None

    def set_time_scale(self, scale: int) -> None:
        """Switch to one of ``TIME_SCALES``; anything else is ignored."""
        if scale in TIME_SCALES:
            self.time_scale = scale

    def restart(self, seed: int | None = None) -> None:
        self.restarts += 1
        self.seed = seed if seed is not None else self.seed + 1
        self.world = hunting_scenario(self.seed)
        self.messages.clear()
        self.paused = False
        self.confirming_restart = False
        self.selected = None
        self._since_state = 0.0
        events.emit("restart", seed=self.seed)
        self.messages.append((0.0, objective(self.world)))
        self._drain()

    # --- time ------------------------------------------------------------------------------

    @property
    def zoom(self) -> float:
        return ZOOM_LEVELS[self.zoom_index]

    def update(self, dt: float) -> None:
        """Advance the game by ``dt`` real seconds (times the time compression)."""
        if self.paused or self.confirming_restart:
            return
        remaining = dt * self.time_scale
        while remaining > 1e-9:
            step = min(MAX_SUBSTEP, remaining)
            self.world.step(step)
            remaining -= step
        self._drain()
        self._since_state += dt * self.time_scale
        if self._since_state >= self.state_interval - 1e-9:
            self._since_state = 0.0
            self.emit_state()

    def _drain(self) -> None:
        """Publish the world's pending events and keep the human-readable ones as messages."""
        for ev in self.world.events:
            data = dict(ev)
            name = data.pop("event")
            t = data.pop("t", self.world.time)
            events.emit(name, t=t, **data)
            text = describe(name, data)
            if text:
                self.messages.append((t, text))
        self.world.events.clear()
        del self.messages[:-MESSAGE_LIMIT]

    # --- what the HUD shows ----------------------------------------------------------------

    def contacts_by_range(self) -> list[Contact]:
        """Visual contacts first, each group nearest first."""
        return sorted(self.world.contacts, key=lambda c: (c.method != VISUAL, c.range or math.inf))

    def target(self) -> Contact | None:
        """The contact chosen with T while it is still held, else the nearest visual contact
        (the fire-control helper tracks it), else the nearest hydrophone contact (an
        estimate, no solution)."""
        pool = self.contacts_by_range()
        if not pool:
            return None
        chosen = next((c for c in pool if c.ship_id == self.selected), None)
        return chosen or pool[0]

    def select_target(self, ship_id: str | None) -> bool:
        """Pick a contact by id (``None`` returns to automatic); ``False`` if not held."""
        if ship_id is not None and all(c.ship_id != ship_id for c in self.world.contacts):
            return False
        self.selected = ship_id
        return True

    def next_target(self) -> Contact | None:
        """Cycle through the current contacts (nearest first, visual before sonar)."""
        pool = self.contacts_by_range()
        if not pool:
            self.selected = None
            return None
        current = self.target()
        ids = [c.ship_id for c in pool]
        index = ids.index(current.ship_id) if current else -1
        self.selected = ids[(index + 1) % len(ids)]
        return self.target()

    def solution(self) -> Solution | None:
        target = self.target()
        sub = self.world.player
        if target is None or target.x is None or target.method != VISUAL:
            return None
        return solution(
            sub.x,
            sub.y,
            sub.heading,
            sub.tubes.params,
            target.x,
            target.y,
            target.heading or 0.0,
            target.speed or 0.0,
        )

    def snapshot(self) -> dict:
        data = self.world.snapshot()
        data["seed"] = self.seed
        data["time_scale"] = self.time_scale
        data["paused"] = self.paused
        data["confirming_restart"] = self.confirming_restart
        data["zoom"] = self.zoom
        sol = self.solution()
        data["solution"] = sol.snapshot() if sol else None
        target = self.target()
        data["target"] = target.ship_id if target else None
        return data

    def emit_state(self) -> None:
        self.state_events += 1
        events.emit("state", **self.snapshot())


def describe(name: str, data: dict) -> str | None:
    """One HUD line per event worth telling the player about."""
    if name == "intel":
        return (
            f"BdU: {data['ships']} merchants reported bearing {data['bearing']:03d}, "
            f"{data['range'] / 1000:.0f} km, course ~{data['course']:03d}"
        )
    if name == "contact":
        how = "hydrophone bearing" if data["method"] == "hydrophone" else "sighted"
        return f"{data['ship']}: {how} {data['bearing']:03.0f}"
    if name == "contact_lost":
        return f"{data['ship']}: contact lost"
    if name == "alert":
        why = "we were sighted" if data["reason"] == "sighted" else "torpedo"
        return f"{', '.join(data['ships'])} running: {why}"
    if name == "fire":
        return f"torpedo {data['torpedo']} away, course {data['heading']:03.0f}"
    if name == "fire_refused":
        return "cannot fire: " + ("too deep" if data["reason"] == "deep" else "tubes empty")
    if name == "hit":
        return f"HIT {data['ship']}"
    if name == "sunk":
        if data.get("kind") == "military":
            return f"{data['ship']} SUNK: escort bonus {data['tonnage']:,} GRT"
        return f"{data['ship']} SUNK, {data['tonnage']:,} GRT"
    if name == "torpedo_lost":
        return f"torpedo {data['torpedo']} missed"
    if name == "escort_alarm":
        how = {"sonar": "pinged us", "sighted": "sighted us", "torpedo": "was torpedoed"}
        return f"ESCORT: {data['by']} {how.get(data['reason'], data['reason'])}"
    if name == "escort_split":
        return (
            f"escort splits: {', '.join(data['hunters'])} hunting, "
            f"{', '.join(data['screens']) or 'none'} screening"
        )
    if name == "escort_stand_down":
        return "escort lost the track, back to formation"
    if name == "depth_charge_run":
        return f"{data['ship']} is making a depth charge run"
    if name == "depth_charge" and data["damage"] > 0:
        return "DEPTH CHARGE close!"
    if name == "damage":
        return f"hull damage {data['level'] * 100:.0f}%"
    if name == "escaped":
        return f"{data['ship']} got away"
    if name == "mission_end":
        return (
            f"mission over ({data['reason']}): {len(data['sunk'])} sunk "
            f"({data['tonnage']:,} GRT), {len(data['escaped'])} got away"
        )
    return None


def objective(world: World) -> str:
    """The rule of the hunt, told once at the start."""
    n = len(world.merchants)
    km = MERCHANT_AI.escape_range / 1000
    return (
        f"Objective: sink the {n} merchants (a destroyer is a bonus). The hunt ends when all "
        f"are sunk or more than {km:.0f} km away, your torpedoes are gone, or the boat is lost"
    )
