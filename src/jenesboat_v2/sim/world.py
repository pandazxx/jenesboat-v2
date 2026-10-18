"""The ocean: a bounded flat rectangle holding the player, the ships and what they know."""

from __future__ import annotations

import math
import random
from dataclasses import dataclass, field

from jenesboat_v2.sim import ai, detection
from jenesboat_v2.sim import escort as escort_ai
from jenesboat_v2.sim.detection import Contact
from jenesboat_v2.sim.escort import Datum, EscortState
from jenesboat_v2.sim.geo import bearing, clamp, distance, project
from jenesboat_v2.sim.params import DETECTION, FREIGHTER, KNOT, MERCHANT_AI, ShipType
from jenesboat_v2.sim.submarine import Submarine, new_submarine
from jenesboat_v2.sim.vessel import Vessel
from jenesboat_v2.sim.weapons import DepthCharge, Torpedo

HIT_MARGIN = 2.0  # m, forgiveness on the hull box for the torpedo point
TRACK_SPACING = 50.0  # m between points of the boat's own track
TRACK_POINTS = 600  # kept (30 km of track)
THREAT_BEHIND_TORPEDO = 2_000.0  # m, where a hit merchant assumes the boat is


@dataclass
class Ship(Vessel):
    ship_id: str = ""
    type: ShipType = FREIGHTER
    course: float = 90.0
    cruise_speed: float = 8.0 * KNOT
    spread: float = 0.0  # -1, 0, +1 ...: which way this one fans out when the group runs
    hits: int = 0
    sunk: bool = False
    escaped: bool = False
    alert_until: float = -math.inf  # sim time until which the ship keeps running
    alert_since: float = 0.0
    threat_x: float = 0.0
    threat_y: float = 0.0
    spot_timer: float = 0.0  # seconds the boat has been in sight
    shelter: tuple[float, float] | None = None  # merchants: the spot behind an escort
    escort: EscortState = field(default_factory=EscortState)  # military only

    @property
    def kind(self) -> str:
        return self.type.kind

    @property
    def active(self) -> bool:
        return not (self.sunk or self.escaped)

    def alerted(self, t: float) -> bool:
        return t < self.alert_until

    def alert(self, t: float, x: float, y: float, duration: float) -> None:
        if not self.alerted(t):
            self.alert_since = t
        self.alert_until = t + duration
        self.threat_x, self.threat_y = x, y

    def snapshot(self) -> dict:
        data = super().snapshot()
        data["id"] = self.ship_id
        data["kind"] = self.kind
        data["type"] = self.type.name
        data["hits"] = self.hits
        data["sunk"] = self.sunk
        data["escaped"] = self.escaped
        data["alerted"] = self.alert_until > -math.inf
        if self.kind == "military":
            data["mode"] = self.escort.mode
            data["charges"] = self.escort.charges
            data["sonar_m"] = round(self.escort.sonar_range)
        return data


def new_ship(
    ship_id: str,
    type: ShipType,
    x: float,
    y: float,
    course: float,
    spread: float = 0.0,
    speed: float | None = None,
) -> Ship:
    """A ship already under way on its route."""
    cruise = type.cruise_speed if speed is None else speed
    return Ship(
        params=type.vessel,
        x=x,
        y=y,
        heading=course,
        speed=cruise,
        throttle=cruise / type.vessel.max_speed,
        ship_id=ship_id,
        type=type,
        course=course,
        cruise_speed=cruise,
        spread=spread,
    )


@dataclass
class World:
    width: float
    height: float
    player: Submarine
    ships: list[Ship] = field(default_factory=list)
    torpedoes: list[Torpedo] = field(default_factory=list)
    time: float = 0.0
    light: float = 1.0  # 1 = day; night scales the visual ranges
    tonnage: int = 0  # GRT of merchants sunk so far (the score)
    bonus: int = 0  # GRT of escorts sunk (not part of the score the hunt is about)
    mission_over: bool = False
    intel: dict | None = None  # the radio report: x, y, course, ships (rough)
    contacts: list[Contact] = field(default_factory=list)
    last_seen: dict[str, dict] = field(default_factory=dict)  # ship id -> last visual fix
    player_track: list[tuple[float, float]] = field(default_factory=list)
    player_log: float = 0.0  # m travelled by the boat (the ship's log)
    _last_pos: tuple[float, float] | None = None
    events: list[dict] = field(default_factory=list)  # pending, drained by the game loop
    _known: dict[str, str] = field(default_factory=dict)  # ship id -> contact method
    datum: Datum | None = None  # where the escorts think the boat is
    depth_charges: list[DepthCharge] = field(default_factory=list)
    next_charge_id: int = 0
    rng: random.Random = field(default_factory=lambda: random.Random(0))

    # --- queries ---------------------------------------------------------------------------

    @property
    def active_ships(self) -> list[Ship]:
        return [s for s in self.ships if s.active]

    @property
    def merchants(self) -> list[Ship]:
        return [s for s in self.ships if s.kind == "merchant"]

    def ship(self, ship_id: str) -> Ship:
        return next(s for s in self.ships if s.ship_id == ship_id)

    @property
    def torpedoes_left(self) -> int:
        tubes = self.player.tubes
        return tubes.loaded + tubes.reserves + len(self.torpedoes)

    def mission(self) -> dict:
        """The hunt: over when every merchant is sunk or escaped, or the torpedoes are gone."""
        merchants = self.merchants
        sunk = [s.ship_id for s in merchants if s.sunk]
        escaped = [s.ship_id for s in merchants if s.escaped]
        remaining = [s.ship_id for s in merchants if s.active]
        if self.player.destroyed:
            status = "boat_lost"
            reason = "the boat was sunk"
        elif not remaining:
            status = "complete"
            reason = "all merchants sunk" if not escaped else "no merchants left in range"
        elif self.torpedoes_left == 0:
            status = "out_of_torpedoes"
            reason = "no torpedoes left"
        else:
            status = "active"
            reason = ""
        return {
            "status": status,
            "reason": reason,
            "total": len(merchants),
            "sunk": sunk,
            "escaped": escaped,
            "remaining": remaining,
            "tonnage": self.tonnage,
            "escorts_sunk": [s.ship_id for s in self.ships if s.kind == "military" and s.sunk],
            "bonus": self.bonus,
            "torpedoes_left": self.torpedoes_left,
        }

    def emit(self, event: str, **data) -> None:
        self.events.append({"event": event, "t": round(self.time, 2), **data})

    def report_intel(self, x: float, y: float, course: float, ships: int) -> None:
        """The radio report at the start of a hunt: a rough position and course."""
        sub = self.player
        self.intel = {"x": x, "y": y, "course": course, "ships": ships, "t": self.time}
        self.emit(
            "intel",
            ships=ships,
            bearing=round(bearing(sub.x, sub.y, x, y)),
            range=round(distance(sub.x, sub.y, x, y), -2),
            course=round(course),
            x=round(x),
            y=round(y),
        )

    def cue(self) -> dict | None:
        """Where to look when there is no contact at all: the dead-reckoned position of the
        ship fixed last (if still in play), else the intel report.  ``None`` while any ship is
        held visually or on the hydrophones, or when there is nothing to go on."""
        sub = self.player
        if self.contacts:
            return None
        fixes = [
            (fix, ship_id) for ship_id, fix in self.last_seen.items() if self.ship(ship_id).active
        ]
        if fixes:
            fix, ship_id = max(fixes, key=lambda f: f[0]["t"])
            x, y = project(
                fix["x"], fix["y"], fix["heading"], fix["speed"] * (self.time - fix["t"])
            )
            kind, course, ship = "last_seen", fix["heading"], ship_id
        elif self.intel is not None:
            x, y = self.intel["x"], self.intel["y"]
            kind, course, ship = "intel", self.intel["course"], None
        else:
            return None
        return {
            "kind": kind,
            "ship": ship,
            "x": round(x, 1),
            "y": round(y, 1),
            "course": round(course, 1),
            "bearing": round(bearing(sub.x, sub.y, x, y), 1),
            "range": round(distance(sub.x, sub.y, x, y), 0),
        }

    # --- orders ----------------------------------------------------------------------------

    def fire(self) -> Torpedo | None:
        torpedo = self.player.fire()
        if torpedo is None:
            self.emit("fire_refused", reason="deep" if self.player.tubes.can_fire else "empty")
            return None
        self.torpedoes.append(torpedo)
        self.emit("fire", torpedo=torpedo.torpedo_id, heading=round(torpedo.heading, 1))
        return torpedo

    # --- stepping --------------------------------------------------------------------------

    def step(self, dt: float) -> None:
        self.time += dt
        self.player.step(dt)
        self._keep_in_bounds(self.player)
        self._record_track()
        self._sense()
        self._lookouts(dt)
        escort_ai.step(self, dt)
        for ship in self.ships:
            if ship.active:
                if ship.kind == "merchant":
                    ai.merchant(ship, self.time)
            else:
                ship.set_throttle(0.0)
                ship.set_rudder(0.0)
            ship.step(dt)
            if ship.active:
                self._check_escaped(ship)
        self._run_torpedoes(dt)
        self._run_depth_charges(dt)
        if not self.mission_over:
            mission = self.mission()
            if mission["status"] != "active":
                self.mission_over = True
                self.emit("mission_end", **mission)

    def _record_track(self) -> None:
        sub = self.player
        if self._last_pos is not None:
            self.player_log += distance(*self._last_pos, sub.x, sub.y)
        self._last_pos = (sub.x, sub.y)
        if not self.player_track or (
            distance(sub.x, sub.y, *self.player_track[-1]) >= TRACK_SPACING
        ):
            self.player_track.append((sub.x, sub.y))
            del self.player_track[:-TRACK_POINTS]

    def _keep_in_bounds(self, vessel: Vessel) -> None:
        vessel.x = clamp(vessel.x, 0.0, self.width)
        vessel.y = clamp(vessel.y, 0.0, self.height)

    def _sense(self) -> None:
        """Rebuild the boat's contact list and report gained/lost contacts."""
        contacts = []
        for ship in self.active_ships:
            contact = detection.observe(self.player, ship, self.light)
            if contact is not None:
                contacts.append(contact)
                if contact.x is not None:  # a fix: visual, or the sonar's estimate
                    self.last_seen[ship.ship_id] = {
                        "x": ship.x,
                        "y": ship.y,
                        "heading": ship.heading,
                        "speed": ship.speed,
                        "t": self.time,
                    }
        self.contacts = contacts
        known = {c.ship_id: c.method for c in contacts}
        for ship_id, method in known.items():
            if self._known.get(ship_id) != method:
                self.emit(
                    "contact",
                    ship=ship_id,
                    method=method,
                    bearing=round(known_bearing(contacts, ship_id), 1),
                )
        for ship_id in self._known:
            if ship_id not in known:
                self.emit("contact_lost", ship=ship_id)
        self._known = known

    def _lookouts(self, dt: float) -> None:
        """Ships that keep the boat in sight for ``spot_time`` raise the alarm."""
        sub = self.player
        for ship in self.active_ships:
            if detection.ship_sees_sub(sub, ship, self.light):
                ship.spot_timer = min(ship.spot_timer + dt, DETECTION.spot_time)
                if ship.spot_timer >= DETECTION.spot_time - 1e-9:
                    fresh = not ship.alerted(self.time)
                    self.alert_group(
                        sub.x, sub.y, reason="sighted", by=ship.ship_id, quiet=not fresh
                    )
                    escort_ai.report(self, sub.x, sub.y, "sighted", ship.ship_id)
            else:
                ship.spot_timer = max(0.0, ship.spot_timer - dt)

    def alert_group(
        self,
        x: float,
        y: float,
        reason: str,
        by: str,
        quiet: bool = False,
        radius: float = math.inf,
    ) -> None:
        """Every active merchant within ``radius`` of (x, y) starts running from that point."""
        newly = []
        for ship in self.active_ships:
            if ship.kind != "merchant" or distance(x, y, ship.x, ship.y) > radius:
                continue
            if not ship.alerted(self.time):
                newly.append(ship.ship_id)
            ship.alert(self.time, x, y, MERCHANT_AI.alert_duration)
        if newly and not quiet:
            self.emit("alert", reason=reason, by=by, ships=newly)

    def _check_escaped(self, ship: Ship) -> None:
        """A merchant has got away once it is beyond the escape range from the boat (the hunt
        area) or off the map, whether or not it ever saw the boat."""
        out = not (0.0 <= ship.x <= self.width and 0.0 <= ship.y <= self.height)
        far = distance(ship.x, ship.y, self.player.x, self.player.y) > MERCHANT_AI.escape_range
        if ship.kind == "merchant" and (out or far):
            ship.escaped = True
            self.emit("escaped", ship=ship.ship_id)

    def _run_torpedoes(self, dt: float) -> None:
        for torpedo in self.torpedoes:
            torpedo.step(dt)
            if not torpedo.alive:
                self.emit("torpedo_lost", torpedo=torpedo.torpedo_id)
                continue
            if not torpedo.armed:
                continue
            for ship in self.active_ships:
                if ship.contains(torpedo.x, torpedo.y, HIT_MARGIN):
                    self._hit(torpedo, ship)
                    break
        self.torpedoes = [t for t in self.torpedoes if t.alive]

    def _hit(self, torpedo: Torpedo, ship: Ship) -> None:
        torpedo.alive = False
        ship.hits += 1
        self.emit("hit", torpedo=torpedo.torpedo_id, ship=ship.ship_id, hits=ship.hits)
        if ship.hits >= ship.type.hits_to_sink:
            ship.sunk = True
            if ship.kind == "merchant":
                self.tonnage += ship.type.tonnage
            else:
                self.bonus += ship.type.tonnage
            self.emit(
                "sunk",
                ship=ship.ship_id,
                kind=ship.kind,
                tonnage=ship.type.tonnage,
                total=self.tonnage,
                bonus=self.bonus,
            )
        # The others only know which way the torpedo came from.
        tx, ty = project(torpedo.x, torpedo.y, torpedo.heading + 180.0, THREAT_BEHIND_TORPEDO)
        self.alert_group(tx, ty, "torpedo", by=ship.ship_id, radius=MERCHANT_AI.panic_range)
        escort_ai.report(self, tx, ty, "torpedo", ship.ship_id)

    def _run_depth_charges(self, dt: float) -> None:
        sub = self.player
        for charge in self.depth_charges:
            if not charge.step(dt):
                continue
            hurt = charge.effect_on(sub.x, sub.y, sub.depth)
            self.emit(
                "depth_charge",
                charge=charge.charge_id,
                x=round(charge.x),
                y=round(charge.y),
                depth=round(charge.set_depth),
                damage=round(hurt, 2),
            )
            if hurt > 0.0 and not sub.destroyed:
                sub.damage = min(1.0, sub.damage + hurt)
                self.emit("damage", level=round(sub.damage, 2), destroyed=sub.destroyed)
        self.depth_charges = [c for c in self.depth_charges if not c.burst]

    # --- output ----------------------------------------------------------------------------

    def snapshot(self) -> dict:
        return {
            "t": round(self.time, 2),
            "world": {"width": self.width, "height": self.height, "light": self.light},
            "player": self.player.snapshot(),
            "ships": [ship.snapshot() for ship in self.ships],
            "contacts": [c.snapshot() for c in self.contacts],
            "torpedoes": [t.snapshot() for t in self.torpedoes],
            "depth_charges": [c.snapshot() for c in self.depth_charges],
            "datum": (
                {
                    "x": round(self.datum.x),
                    "y": round(self.datum.y),
                    "age": round(self.time - self.datum.t),
                }
                if self.datum
                else None
            ),
            "tonnage": self.tonnage,
            "bonus": self.bonus,
            "mission": self.mission(),
            "cue": self.cue(),
            "log_nm": round(self.player_log / 1852.0, 3),
        }


def known_bearing(contacts: list[Contact], ship_id: str) -> float:
    return next(c.bearing for c in contacts if c.ship_id == ship_id)


def default_world() -> World:
    """A small unescorted group steaming east across the middle; the boat waits to the south."""
    width, height = 4000.0, 2250.0
    convoy_y = height * 0.62
    ships = [
        new_ship(f"merchant-{i + 1}", FREIGHTER, x, convoy_y, course=90.0, spread=i - 1)
        for i, x in enumerate((600.0, 900.0, 1200.0))
    ]
    player = new_submarine(x=width * 0.5, y=height * 0.2, heading=0.0)
    return World(width=width, height=height, player=player, ships=ships)
