# Difficulty levels

Milestone 3 (#21). Everywhere in this page and in the code, *difficulty* means how hard the
one hunt is (`cadet`, `patrol`, `veteran`). There are no game levels to progress through: the
same hunt is played easier or harder.

## What the player gets

- Three difficulties. `patrol` is the default and is the Milestone 2 game. `cadet` is easier
  (one destroyer, deaf and forgetful). `veteran` is harder (three destroyers that hear
  further and keep hunting longer). The numbers are in `docs/PARAMETERS.md`, "Difficulty
  levels".
- The difficulty is chosen before the hunt starts: on the build's start page (three
  buttons), on the game URL (`?difficulty=veteran`), or with `--difficulty` on the command
  line. The whole hunt runs on it; `R` (new hunt) keeps it.
- The HUD tag at the bottom right names it (`build fe9cedc  seed 12  Veteran`), the
  objective message names it (`Objective (Veteran): ...`), and the `ready`, `restart`,
  `state` and `final` events carry it as `difficulty`.

## What a difficulty is made of

A difficulty changes two kinds of things about the enemy:

1. **Parameters**: numbers. How far a sonar hears, how long escorts keep searching, how hard
   a depth charge hits, how long a torpedo reload takes.
2. **Strategies**: behaviours. What an escort does about a torpedo running at it, how it
   searches when it has lost the boat, how a merchant runs.

So a difficulty is one record with those two parts. This is the whole of `veteran`:

```python
VETERAN = Difficulty(
    name="veteran",
    title="Veteran",
    description="three destroyers with longer sonar reach and memory, heavier charges, ...",
    rules=Rules(  # the parameters: the base sheet with four blocks swapped
        torpedo=replace(G7E, reload_time=150.0),
        sonar=replace(SONAR_ASDIC, range=3_600.0),
        depth_charge=replace(DEPTH_CHARGE, damage=0.5, lethal_radius=15.0),
        escort_ai=replace(ESCORT_AI, lose_track_time=480.0),
        scenario=ScenarioParams(escorts=3),
    ),
    strategies=Strategies(),  # the behaviours: the base ones (#22 adds escort_evade="comb")
)
```

The pieces, all in `sim/params.py`:

| name | what it is |
| --- | --- |
| parameter block | a frozen dataclass of numbers for one part of the sim: `SonarParams`, `DepthChargeParams`, `EscortAIParams`, `TorpedoParams`, ... (as before this milestone) |
| `Rules` | all the blocks the sim uses, bundled in one object. `Rules()` with no arguments is the base sheet |
| slot | one decision point in the AI, as a field of `Strategies`: `escort_search`, `escort_evade`, `merchant_flee`. Each field holds the *name* of the behaviour to use |
| strategy | one behaviour that can fill a slot: a function in the AI module, registered under a name (`"box"`, `"none"`, `"zigzag"`, `"comb"`) |
| `Strategies` | the chosen strategy name for every slot. `Strategies()` with no arguments is the base behaviour |
| `Difficulty` | name, title, description, a `Rules` and a `Strategies` |
| `DIFFICULTIES` | the table of the three: `cadet`, `patrol`, `veteran` |

Two rules keep this simple:

- A difficulty is **data only**. It swaps whole parameter blocks with `dataclasses.replace`
  copies and names strategies as strings. Every number still lives on the parameter sheet.
- A strategy is **one function** that lives next to the code it replaces (`sim/escort.py`,
  `sim/ai.py`) and reads its numbers from `world.rules`. Switching a behaviour off is a
  strategy that does nothing (`escort_evade = "none"`), so on/off and multiple choice work
  the same way.

## How a hunt uses it

```
   player chooses                 start page button
                                  ?difficulty=veteran on the game URL
                                  --difficulty veteran on the command line
                                            |
                                            v
   look it up, check it           difficulty.get("veteran")
                                    = DIFFICULTIES["veteran"], after check():
                                      every slot names a registered strategy
                                            |
                                            v
   build the hunt on it           Game(difficulty="veteran")
                                    -> hunting_scenario(seed, difficulty)
                                    -> World.difficulty = VETERAN
                                            |
                          +-----------------+-------------------+
                          |                                     |
                          v                                     v
   numbers            world.rules                     behaviours   pick(world.difficulty, slot)
                      = VETERAN.rules                              = the function VETERAN.strategies
                                                                     names for that slot
   escort.py reads    rules.sonar.range (3,600 m)     escort.step   -> pick(.., "escort_evade")
                      rules.escort_ai.lose_track_time                 -> no_evasion() or comb_the_track()
   world.py reads     rules.merchant_ai.panic_range   escort._hunt  -> pick(.., "escort_search")
                      rules.detection.spot_time                       -> box_search()
   scenario.py reads  rules.scenario.escorts (3)      ai.merchant   -> pick(.., "merchant_flee")
                      rules.torpedo.reload_time                       -> flee()
```

Left column: the sim never reads `params.ESCORT_AI` and friends directly any more; it reads
`world.rules.<block>`, which is the base block or the difficulty's copy of it. Right column:
wherever the AI has a choice of behaviour it asks `pick` for the function and calls it.

Details:

- `World.difficulty` defaults to `patrol`, so a `World` built by hand in a test runs on the
  base sheet.
- `Game.restart()` keeps the difficulty and takes the next seed.
- `hunting_scenario(seed, escorts=N)` still overrides the escort count, for tests.

## The mechanism, step by step (`sim/difficulty.py`)

**Registering.** In the module that owns the behaviour:

```python
from jenesboat_v2.sim.difficulty import strategy


@strategy("escort_evade", "comb")
def comb_the_track(world, ship, dt) -> bool: ...
```

The decorator puts `comb_the_track` into a registry under slot `escort_evade`, name `comb`.
It refuses an unknown slot (the slots are the fields of `Strategies`) and a name registered
twice. The registry fills when `sim/escort.py` and `sim/ai.py` are imported.

**Choosing.** A difficulty names the strategy: `Strategies(escort_evade="comb")`.

**Using.** Where the escort AI needs the behaviour:

```python
from jenesboat_v2.sim.difficulty import pick

evade = pick(world.difficulty, "escort_evade")  # the function the difficulty named
if evade(world, ship, dt):  # here: comb_the_track(world, ship, dt)
    continue
```

`pick` reads `world.difficulty.strategies.escort_evade` (the string `"comb"`), looks that
name up in the registry for the slot, and returns the function. If the name is not
registered it raises `LookupError` saying which difficulty, which slot and which names
exist, so a typo in a difficulty cannot silently do nothing.

**Checking.** `check(difficulty)` calls `pick` for every slot once. `get(name)` returns the
checked difficulty for a name (`KeyError` for an unknown name). `Game`, `hunting_scenario`
and the CLI all go through `get`, so a bad difficulty fails before the hunt starts.
`available()` lists every slot with its registered names; a test asserts every difficulty in
`DIFFICULTIES` resolves.

**Each slot has a signature.** A strategy for a slot is called with the same arguments
whatever its name, so the caller does not care which one it got:

| slot | called as | strategies today | chosen by |
| --- | --- | --- | --- |
| `escort_search` | `(world, ship, p: EscortAIParams) -> None`: steer a hunter whose fix on the boat is older than `FRESH_DATUM` | `box`: a square around the last fix that widens with time | all: `box` |
| `escort_evade` | `(world, ship, dt) -> bool`: react to torpedoes in the water; `True` while dodging (the ship's normal behaviour is skipped that tick) | `none`: never notices a torpedo (M2) | all: `none` until #22 (`comb` for `patrol` and `veteran`) |
| `merchant_flee` | `(ship, t, rules: Rules) -> None`: steer an alerted merchant; `ship.shelter` is set when an escort covers it | `zigzag`: run away zigzagging, or for the spot behind an escort | all: `zigzag` |

Why a registry rather than importing the functions into the difficulty table: the table in
`sim/params.py` then only holds strings and numbers, and never imports the AI modules. Why
typed slots (fields on `Strategies`) rather than free-form strings: a slot is an interface
with a signature, adding one is a deliberate change, and the field defaults document the
base game.

## Choosing a difficulty

| where | how |
| --- | --- |
| web build, start page | `builds/<id>/start.html`: one button per difficulty. The build index links here |
| web build, game page | `builds/<id>/?difficulty=veteran`. The page copies the query into `jb_difficulty`; the game reads it once at start. An unknown name is reported as a `warning` event and ignored |
| native window | `just run -- --difficulty veteran` |
| headless sim | `just sim --difficulty cadet --trace` |
| in the game | not yet: issue #26 (a key and a touch button that step through the difficulties for the next hunt) |

The CI smoke test's phone step loads the game page with `?difficulty=veteran` and fails
unless the game reports that difficulty, so the web path is checked on every build.

## How to extend

**A new strategy for an existing slot.** Write the function in the owning module with the
slot's signature, decorate it with `@strategy(slot, name)`, name it in a difficulty (or in
the `Strategies` defaults if it should become the base behaviour), add a test and a row to
the slot table above.

**A new slot.** Add a field to `Strategies` whose default names the base behaviour, document
the signature in `sim/difficulty.py`, register the base behaviour under that name, and
replace the hard-coded call with `pick(world.difficulty, "<slot>")(...)`. Candidates:
`merchant_flee = "dodge"` (merchants comb a seen torpedo track), `escort_search =
"creeping"` (one ship holds contact while another attacks), an `escort_screen` placement.

**A new difficulty.** One `Difficulty(...)` in `sim/params.py`, added to `DIFFICULTIES`.
`--difficulty`'s choices, the start page, `--help` and the tests pick it up. Change whole
blocks with `replace`, and explain each number in `docs/PARAMETERS.md`.

**A per-difficulty number the sim does not read from `world.rules` yet.** Give the function
the block (or the whole `Rules`) as an argument, with the base constant as the default so
existing tests keep working, and pass `world.rules.<block>` at the call site.
