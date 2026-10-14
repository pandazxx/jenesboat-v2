"""The player's submarine: a vessel with a depth axis, a battery and sensors."""

from __future__ import annotations

from dataclasses import dataclass

from jenesboat_v2.sim.params import HOUR, TYPE_VIIC, SubmarineParams
from jenesboat_v2.sim.vessel import Vessel, clamp

SURFACED_DEPTH = 0.5  # shallower than this counts as surfaced
PERISCOPE_DEPTH = TYPE_VIIC.periscope_depth


@dataclass
class Submarine(Vessel):
    spec: SubmarineParams = TYPE_VIIC
    depth: float = 0.0
    target_depth: float = 0.0
    battery: float = 1.0  # 0 (flat) .. 1 (full)

    # --- depth -----------------------------------------------------------------------------

    @property
    def surfaced(self) -> bool:
        return self.depth < SURFACED_DEPTH

    @property
    def periscope_usable(self) -> bool:
        """At periscope depth (give or take the band) and not on the surface."""
        return SURFACED_DEPTH <= self.depth <= self.spec.periscope_depth + self.spec.periscope_band

    @property
    def hydrophone_usable(self) -> bool:
        return self.depth >= self.spec.hydrophone_min_depth and (
            abs(self.speed) <= self.spec.hydrophone_max_speed
        )

    @property
    def depth_band(self) -> str:
        if self.surfaced:
            return "surfaced"
        if self.depth <= self.spec.periscope_depth + self.spec.periscope_band:
            return "periscope"
        return "deep"

    def set_target_depth(self, depth: float) -> None:
        self.target_depth = clamp(depth, 0.0, self.spec.max_depth)

    def toggle_dive(self) -> None:
        """One step shallower, or dive to periscope depth from the surface.

        surfaced -> periscope depth; periscope depth -> surface; deeper -> periscope depth.
        """
        if self.target_depth > self.spec.periscope_depth + 1e-6:
            self.set_target_depth(self.spec.periscope_depth)
        elif self.target_depth > 0.0:
            self.set_target_depth(0.0)
        else:
            self.set_target_depth(self.spec.periscope_depth)

    def order_deep(self) -> None:
        self.set_target_depth(self.spec.deep_depth)

    # --- propulsion ------------------------------------------------------------------------

    @property
    def submerged_fraction(self) -> float:
        """0 on the surface, 1 once the hull is fully under (at periscope depth)."""
        return clamp(self.depth / self.spec.periscope_depth, 0.0, 1.0)

    def max_speed_now(self) -> float:
        # Diesels on the surface, electric motors under; a flat battery leaves a creep.
        surfaced_speed = self.params.max_speed
        electric = self.spec.submerged_speed
        if self.battery <= 0.0:
            electric *= self.spec.battery_empty_speed_fraction
        f = self.submerged_fraction
        return surfaced_speed * (1.0 - f) + electric * f

    def battery_rate(self) -> float:
        """Battery change per second: negative when submerged on the motors."""
        if self.surfaced:
            return 1.0 / (self.spec.recharge_hours * HOUR)
        load = abs(self.throttle) ** 3  # propeller power grows with the cube of speed
        creep = 1.0 / (self.spec.battery_creep_hours * HOUR)
        full = 1.0 / (self.spec.battery_full_speed_hours * HOUR)
        return -(creep + (full - creep) * load)

    # --- stepping --------------------------------------------------------------------------

    def step(self, dt: float) -> None:
        delta = self.spec.dive_rate * dt
        if abs(self.target_depth - self.depth) <= delta:
            self.depth = self.target_depth
        elif self.target_depth > self.depth:
            self.depth += delta
        else:
            self.depth -= delta
        self.battery = clamp(self.battery + self.battery_rate() * dt, 0.0, 1.0)
        super().step(dt)

    def snapshot(self) -> dict[str, float]:
        data = super().snapshot()
        data["depth"] = round(self.depth, 1)
        data["target_depth"] = round(self.target_depth, 1)
        data["surfaced"] = self.surfaced
        data["band"] = self.depth_band
        data["battery"] = round(self.battery, 3)
        return data


def new_submarine(
    x: float = 0.0, y: float = 0.0, heading: float = 0.0, spec: SubmarineParams = TYPE_VIIC
) -> Submarine:
    return Submarine(params=spec.vessel, spec=spec, x=x, y=y, heading=heading)
