"""Difficulty levels: pluggable AI strategies and per-difficulty parameter sets.

A difficulty (``params.Difficulty``: cadet, patrol, veteran) is plain data: a name, a
``Rules`` bundle (every parameter the sim runs on) and a ``Strategies`` record naming, for
each AI decision point (a *slot*), the behaviour that fills it.  This module is the plug-in
mechanism: the AI modules register their behaviours with ``@strategy(slot, name)`` and ask
for the one the difficulty selected with ``pick(difficulty, slot)``.  ``check`` validates a
difficulty, so a typo in one fails when the hunt starts, not when an escort first needs
that behaviour.  The design and the balance tables are in ``docs/DIFFICULTY.md`` and
``docs/PARAMETERS.md``.

The slots and the signature a strategy of each must have:

``escort_search(world, ship, p: EscortAIParams) -> None``
    steer a hunter whose datum is stale (no fix younger than ``escort.FRESH_DATUM``).
``escort_evade(world, ship, dt) -> bool``
    react to the torpedoes in the water; ``True`` while the ship is busy dodging (its
    normal behaviour is skipped that tick).
``merchant_flee(ship, t, rules: Rules) -> None``
    steer an alerted merchant (``ship.shelter`` is set when an escort is covering it).

Adding a strategy: write the function in the module that owns the behaviour, decorate it,
name it in a difficulty.  Adding a slot: add a field to ``params.Strategies`` (its default
names the base behaviour), document the signature above and call ``pick`` where the
decision is made.  Adding a difficulty: an entry in ``params.DIFFICULTIES``.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import fields

from jenesboat_v2.sim.params import DEFAULT_DIFFICULTY, DIFFICULTIES, Difficulty, Strategies

SLOTS: tuple[str, ...] = tuple(f.name for f in fields(Strategies))
DIFFICULTY_NAMES: tuple[str, ...] = tuple(DIFFICULTIES)

_REGISTRY: dict[str, dict[str, Callable]] = {slot: {} for slot in SLOTS}


def strategy(slot: str, name: str) -> Callable[[Callable], Callable]:
    """Register the decorated function as strategy ``name`` of ``slot``."""
    if slot not in _REGISTRY:
        raise KeyError(f"unknown strategy slot {slot!r}; slots: {', '.join(SLOTS)}")

    def register(fn: Callable) -> Callable:
        if name in _REGISTRY[slot]:
            raise ValueError(f"strategy {slot}={name!r} is registered twice")
        _REGISTRY[slot][name] = fn
        fn.strategy = (slot, name)  # type: ignore[attr-defined]
        return fn

    return register


def _load() -> None:
    """Import the modules that register strategies (they import this one, so lazily)."""
    from jenesboat_v2.sim import ai, escort  # noqa: F401


def available() -> dict[str, tuple[str, ...]]:
    """Every slot and the strategies registered for it (for docs, tests and ``--help``)."""
    _load()
    return {slot: tuple(sorted(names)) for slot, names in _REGISTRY.items()}


def pick(difficulty: Difficulty, slot: str) -> Callable:
    """The strategy ``difficulty`` selected for ``slot``."""
    name = getattr(difficulty.strategies, slot)
    try:
        return _REGISTRY[slot][name]
    except KeyError:
        _load()
        if name in _REGISTRY.get(slot, {}):
            return _REGISTRY[slot][name]
        known = ", ".join(sorted(_REGISTRY.get(slot, ()))) or "none registered"
        raise LookupError(
            f"difficulty {difficulty.name!r}: no strategy {name!r} for slot {slot!r} "
            f"(known: {known})"
        ) from None


def check(difficulty: Difficulty) -> Difficulty:
    """``difficulty`` back, after making sure every slot names a registered strategy."""
    for slot in SLOTS:
        pick(difficulty, slot)
    return difficulty


def get(name: str | None = None) -> Difficulty:
    """The difficulty called ``name`` (the default when ``None``), checked."""
    if name is None:
        name = DEFAULT_DIFFICULTY
    try:
        found = DIFFICULTIES[name]
    except KeyError:
        raise KeyError(
            f"unknown difficulty {name!r}; levels: {', '.join(DIFFICULTY_NAMES)}"
        ) from None
    return check(found)


def describe() -> str:
    """One line per difficulty, for ``--help``."""
    return "; ".join(f"{lvl.name}: {lvl.description}" for lvl in DIFFICULTIES.values())
