"""The ocean: a flat, wrapping rectangle holding the player and enemy ships."""

from __future__ import annotations

from dataclasses import dataclass, field

from jenesboat_v2.sim import ai
from jenesboat_v2.sim.params import DESTROYER, FREIGHTER
from jenesboat_v2.sim.submarine import Submarine, new_submarine
from jenesboat_v2.sim.vessel import KNOT, Vessel

MERCHANT_PARAMS = FREIGHTER.vessel
DESTROYER_PARAMS = DESTROYER.vessel


@dataclass
class Ship(Vessel):
    ship_id: str = ""
    kind: str = "merchant"  # "merchant" or "military"
    course: float = 90.0
    cruise_speed: float = 8.0 * KNOT

    def snapshot(self) -> dict:
        data = super().snapshot()
        data["id"] = self.ship_id
        data["kind"] = self.kind
        return data


@dataclass
class World:
    width: float
    height: float
    player: Submarine
    ships: list[Ship] = field(default_factory=list)
    time: float = 0.0

    def step(self, dt: float) -> None:
        self.time += dt
        self.player.step(dt)
        for ship in self.ships:
            ai.cruise(ship)
            ship.step(dt)
        for vessel in (self.player, *self.ships):
            self._wrap(vessel)

    def _wrap(self, vessel: Vessel) -> None:
        vessel.x %= self.width
        vessel.y %= self.height

    def snapshot(self) -> dict:
        return {
            "t": round(self.time, 2),
            "world": {"width": self.width, "height": self.height},
            "player": self.player.snapshot(),
            "ships": [ship.snapshot() for ship in self.ships],
        }


def default_world() -> World:
    """A small convoy steaming east across the middle; the player waits to the south."""
    width, height = 4000.0, 2250.0
    convoy_y = height * 0.62
    ships: list[Ship] = []
    for i, x in enumerate((600.0, 900.0, 1200.0)):
        ships.append(
            Ship(
                params=MERCHANT_PARAMS,
                x=x,
                y=convoy_y,
                heading=90.0,
                speed=8.0 * KNOT,
                ship_id=f"merchant-{i + 1}",
                kind="merchant",
                course=90.0,
                cruise_speed=8.0 * KNOT,
            )
        )
    ships.append(
        Ship(
            params=DESTROYER_PARAMS,
            x=900.0,
            y=convoy_y + 350.0,
            heading=90.0,
            speed=8.0 * KNOT,
            ship_id="escort-1",
            kind="military",
            course=90.0,
            cruise_speed=8.0 * KNOT,
        )
    )
    player = new_submarine(x=width * 0.5, y=height * 0.2, heading=0.0)
    return World(width=width, height=height, player=player, ships=ships)
