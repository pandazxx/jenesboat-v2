"""The player's submarine: a vessel with a depth axis."""

from __future__ import annotations

from dataclasses import dataclass

from jenesboat_v2.sim.params import TYPE_VIIC_SURFACED
from jenesboat_v2.sim.vessel import Vessel, clamp

PERISCOPE_DEPTH = 12.0  # metres
SURFACED_DEPTH = 0.5  # shallower than this counts as surfaced

TYPE_VII_PARAMS = TYPE_VIIC_SURFACED


@dataclass
class Submarine(Vessel):
    depth: float = 0.0
    target_depth: float = 0.0
    dive_rate: float = 1.0  # m/s vertical
    max_depth: float = 150.0
    submerged_speed_fraction: float = 0.42  # ~7 kn submerged for a 17 kn boat

    @property
    def surfaced(self) -> bool:
        return self.depth < SURFACED_DEPTH

    def set_target_depth(self, depth: float) -> None:
        self.target_depth = clamp(depth, 0.0, self.max_depth)

    def toggle_dive(self) -> None:
        """Order periscope depth when surfaced (or surfacing), otherwise surface."""
        if self.target_depth > 0.0:
            self.set_target_depth(0.0)
        else:
            self.set_target_depth(PERISCOPE_DEPTH)

    def max_speed_now(self) -> float:
        # Full speed on the surface, electric-motor speed once the hull is under.
        submerged = min(1.0, self.depth / PERISCOPE_DEPTH)
        factor = 1.0 - (1.0 - self.submerged_speed_fraction) * submerged
        return self.params.max_speed * factor

    def step(self, dt: float) -> None:
        delta = self.dive_rate * dt
        if abs(self.target_depth - self.depth) <= delta:
            self.depth = self.target_depth
        elif self.target_depth > self.depth:
            self.depth += delta
        else:
            self.depth -= delta
        super().step(dt)

    def snapshot(self) -> dict[str, float]:
        data = super().snapshot()
        data["depth"] = round(self.depth, 1)
        data["target_depth"] = round(self.target_depth, 1)
        data["surfaced"] = self.surfaced
        return data


def new_submarine(x: float = 0.0, y: float = 0.0, heading: float = 0.0) -> Submarine:
    return Submarine(params=TYPE_VII_PARAMS, x=x, y=y, heading=heading)
