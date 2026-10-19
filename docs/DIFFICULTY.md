# Difficulty levels: strategies, parameters, levels

Milestone 3 (#21). A difficulty level is a named set of **strategies** (which AI behaviour
fills each decision point) and **parameters** (the numbers the sim runs on). The player
starts a hunt at a level and the whole hunt, restarts included, runs on it. This page is the
design; the numbers are on the parameter sheet (`docs/PARAMETERS.md`, "Difficulty levels").

## The three concepts

| concept | what it is | where |
| --- | --- | --- |
| **parameter block** | a frozen dataclass of numbers for one part of the sim (`SonarParams`, `DepthChargeParams`, `EscortAIParams`, `TorpedoParams`, ...) | `sim/params.py`, as today |
| **`Rules`** | every block the sim uses, bundled: `submarine`, `torpedo`, `detection`, `merchant_ai`, `sonar`, `depth_charge`, `escort_ai`, `scenario`. `Rules()` is the base sheet | `sim/params.py` |
| **strategy slot** | one AI decision point with a name and a call signature, e.g. `escort_evade`: "what an escort does about a torpedo running at it" | a field of `Strategies` in `sim/params.py`; signature documented in `sim/difficulty.py` |
| **strategy** | one behaviour that can fill a slot, a plain function registered under a name | the module that owns the behaviour (`sim/escort.py`, `sim/ai.py`), `@strategy(slot, name)` |
| **`Strategies`** | the strategy name chosen for every slot; the defaults are the M1/M2 behaviours | `sim/params.py` |
| **`Level`** | `name`, `title`, `description`, `rules: Rules`, `strategies: Strategies` | `sim/params.py`, the `LEVELS` table |

Rules of thumb:

- A level is **plain data**. It never contains code; it names strategies and swaps whole
  parameter blocks with `dataclasses.replace(...)` copies. So every tunable number still
  lives on the parameter sheet, and a level is readable as a table.
- A strategy is **one function** with the slot's signature, living next to the code it
  replaces, decorated with `@strategy("<slot>", "<name>")`. It reads its numbers from
  `world.rules`, never from module constants.
- The sim reads **`world.rules`**, not `params.ESCORT_AI` and friends. The module constants
  remain as the base values the `Rules` defaults point at (and as defaults for pure helper
  functions that tests call directly).
- Decisions with alternatives are **slots**; a strategy that does nothing (`escort_evade =
  none`) is how an optional behaviour is switched off, so on/off and multi-choice are the
  same mechanism.

## Slots today

| slot | signature | strategies | chosen by |
| --- | --- | --- | --- |
| `escort_search` | `(world, ship, p: EscortAIParams) -> None`: steer a hunter whose datum is older than `FRESH_DATUM` | `box` (widening square around the datum, M2) | all levels: `box` |
| `escort_evade` | `(world, ship, dt) -> bool`: react to the torpedoes in the water; `True` while dodging (the ship's normal behaviour is skipped that tick) | `none` (M2), `comb` (hear a torpedo that will pass too close, turn hard to comb its track at full speed until it has gone by; #22) | `cadet`: `none`; `patrol`, `veteran`: `comb` |
| `merchant_flee` | `(ship, t, rules: Rules) -> None`: steer an alerted merchant; `ship.shelter` is set when an escort covers it | `zigzag` (run away zigzagging, or for the shelter point, M1/M2) | all levels: `zigzag` |

## The mechanism (`sim/difficulty.py`)

```python
from jenesboat_v2.sim.difficulty import pick, strategy


@strategy("escort_evade", "comb")  # register: slot, name
def comb_the_track(world, ship, dt) -> bool: ...


pick(world.level, "escort_evade")(world, ship, dt)  # use: the one the level selected
```

- `strategy(slot, name)` registers; unknown slots and duplicate names raise at import time.
- `pick(level, slot)` returns the function the level names, or raises `LookupError` naming
  the level, the slot and the registered names.
- `check(level)` picks every slot once; `level(name)` returns a checked level (`KeyError` for
  an unknown name). `hunting_scenario`, `Game` and the CLI go through `level()`, so a typo in
  a level fails when the hunt starts, not twenty minutes in.
- `available()` lists every slot and its strategies (tests assert every level resolves).
- The registry fills when `sim/escort.py` and `sim/ai.py` are imported; `pick`/`available`
  import them lazily so the module is usable on its own.

Why a registry and not a dict per module: the level only needs a *name*, so the parameter
sheet stays free of imports from the AI modules, and the same `pick` works for every slot.
Why typed slots (a `Strategies` dataclass) and not free strings: a slot is a real interface
with a signature; adding one is a deliberate change (a field, a docstring, a `pick` call),
and the defaults document the base game.

## Where the level lives at run time

```
cli --difficulty / page ?difficulty=  ->  difficulty.level(name)  ->  Game.level
                                                                      |
                             hunting_scenario(seed, level=...) -> World.level (rules via world.rules)
                                                                      |
                     escort.step / ai.merchant / world._hit ... read world.rules.* and pick(world.level, slot)
```

- `World.level` defaults to the `patrol` level, so tests that build a `World` by hand run
  on the base sheet.
- `Game.restart()` keeps the level and takes the next seed.
- `hunting_scenario(seed, escorts=N)` still overrides the escort count for tests.
- The level name is in the `ready`, `restart`, `state` and `final` events (`difficulty`), in
  the HUD tag (`build ... seed ... Patrol`) and in the objective message.

## Selecting a level

| where | how |
| --- | --- |
| native window | `just run -- --difficulty veteran` |
| headless sim | `just sim --difficulty cadet --trace` |
| web build | `.../builds/<id>/?difficulty=veteran` (the page copies the query into `jb_difficulty`, the game reads it once at start; an unknown name is reported as a `warning` event and ignored) |
| in the game | not yet: issue #26 (a key and a touch button that step through the levels for the next hunt) |

The CI smoke test's phone step loads the build with `?difficulty=veteran` and fails unless
the game reports that level, so the web path is checked on every build.

## The levels

`patrol` is the base sheet (Milestone 2 balance plus the #22 torpedo evasion) and the
default. `cadet` and `veteran` change a handful of blocks; the table and the reasons are in
`docs/PARAMETERS.md`. Nothing in the player's boat changes between levels except the torpedo
reload time: the difficulty is in the enemy, so what a player learns at one level carries
over.

The first optional strategy, `escort_evade = comb` (#22), shows the two halves of the
framework together: the behaviour (dodging) is a strategy that `cadet` leaves off, and the
rule it pairs with (a bow-on torpedo is a glancing blow that may not detonate) is a parameter
block, `TorpedoHitParams`, whose `glance_chance` the levels dial from 1.0 to 0.25.

## How to extend

**A new strategy for an existing slot.** Write the function in the owning module with the
slot's signature, decorate it, name it in a level (or in `Strategies` defaults if it should
become the base behaviour), add a test under `tests/` and a row to the table above.

**A new slot.** Add a field to `Strategies` whose default names the base behaviour, document
the signature in `sim/difficulty.py`, register the base behaviour, and replace the hard-coded
call with `pick(world.level, "<slot>")(...)`. Candidates: `merchant_flee = dodge` (merchants
comb a seen torpedo track), `escort_search = creeping` (one ship holds contact while another
attacks), `escort_screen` placement.

**A new level.** One `Level(...)` in `sim/params.py`, added to `LEVELS`; `--difficulty`'s
choices, the docs line (`difficulty.describe()`) and the tests pick it up. Keep the deltas
to whole blocks via `replace`, and explain each number in `docs/PARAMETERS.md`.

**A per-level number the sim does not read from `world.rules` yet.** Thread it: give the
function the block (or the `Rules`) as an argument, with the base constant as default so
existing tests keep working, and read it from `world.rules` at the call site.
