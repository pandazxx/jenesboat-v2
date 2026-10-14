"""Window-free game logic: vessel kinematics, submarine depth model, world and ship AI."""

from jenesboat_v2.sim.submarine import PERISCOPE_DEPTH, Submarine
from jenesboat_v2.sim.vessel import KNOT, Vessel, VesselParams
from jenesboat_v2.sim.world import Ship, World, default_world

__all__ = [
    "KNOT",
    "PERISCOPE_DEPTH",
    "Ship",
    "Submarine",
    "Vessel",
    "VesselParams",
    "World",
    "default_world",
]
