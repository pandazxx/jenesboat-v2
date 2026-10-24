# Escape balance: a found boat should be able to get away

Status: brainstorm and proposal, 2026-10-24. Requirement issue #34 (decisions go there), bug
#35 (the stern chase stalemate found on the way). Nothing in this page is implemented yet;
the numbers come from `scripts/escape_study.py`, a headless harness that plays a found boat
against the escorts with fixed evasion recipes, under the current rules and under a
monkeypatched prototype of the proposed ones (`--proposal`).

## 1. The problem

Once a destroyer has the boat on sonar, the hunt is a certain death. The player's report:
higher speed, accurate sonar and powerful depth charges, no way out. Measured (`patrol`,
12 seeds, the destroyer has just got a fix at 1, 2 or 3 km, the boat is at periscope depth):

| recipe after being found | 1 km | 2 km | 3 km | how it ended (36 hunts) |
| --- | --- | --- | --- | --- |
| stay at periscope depth, stop | lost 1.00 | 1.00 | 1.00 | lost 36 |
| go deep, stop | 1.00 | 1.00 | 1.00 | lost 36 |
| go deep, creep away (AHEAD SLOW) | 1.00 | 1.00 | 1.00 | lost 36 |
| go deep, sprint 90 s across, then creep on a new course | 0.92 | 1.00 | 0.92 | lost 34, still hunted after 30 min 2 |
| go deep, flank across the line of sight | 0.92 | 1.00 | 0.92 | lost 34, hunted 2 |
| go deep, a minute of sprint across, a minute of creep away, repeat | 0.92 | 0.83 | 0.50 | lost 27, hunted 9 |
| go deep, flank straight away | 0.00 | 0.00 | 0.00 | hunted 36 (stalemate, see #35) |

`cadet` and `veteran` look the same (appendix). Two things stand out:

- **The escorts never lose the track.** In 252 hunts under the current rules the escorts
  stood down 5 times (all at `cadet`, 3 km). Distance does not help: being found at 3 km
  is as fatal as at 1 km, only three minutes later.
- **The one "escape" is a degenerate stalemate.** Running straight away deep at flank, the
  hunter sits 100 m astern inside its own sonar minimum range, aims every charge beyond its
  throw range (so most are never thrown) and the rest land behind the boat. Nobody is hurt,
  nobody gives up, the destroyer is out of charges after two hours and the boat's battery is
  flat. That is #35.

### Why (in the code)

1. `escort._ping`: a ping inside `sonar_range` is a **certain** fix with 40 m of noise. No
   blind arc, no depth effect, no probability. A deep boat at 7.6 kn (3.9 m/s) cannot open
   the 3,000 m reach on a 14 kn (7.2 m/s) hunter, so the datum is refreshed every 5 s forever.
2. `escort._drop`: charges are layered around `sub.depth`, the boat's **true** depth, over
   `depth_error` = +-25 m. Going deep buys nothing but the longer sink time; changing depth
   between runs buys nothing at all.
3. `DEPTH_CHARGE.pattern_cooldown` = 45 s: the rack is ready again before the hunter has
   turned round. With a 3D damage radius of 45 m and six charges per run, two runs on a boat
   that has not moved far are the end.
4. The only end of a hunt is `lose_track_time` (300 s at `patrol`) without a fix. There is
   no leash to the convoy and no time limit, so an escort hunts for hours and the convoy
   steams on alone.
5. Sprinting at 20 kn deafens the set to x0.4 but the datum's prediction (`lead_limit` 90 s)
   carries the hunter to the boat anyway; once it slows inside 1.5 km the full reach is back
   at once.

## 2. The goal

A destroyer hunt is **critical, not fatal**. Concretely, at `patrol`:

| situation | target (lost fraction over 12 seeds) |
| --- | --- |
| does nothing at periscope depth | ~1.0 at every level |
| found at 3 km, goes deep and creeps away on a new course | <= 0.25 |
| found at 1 km, same | ~0.5 |
| goes deep and sits still | between the two above, worse than creeping away |
| sprints straight away at flank | not a free escape: either costly (battery, damage) or hit (#35) |
| ordering | `cadet` survives more than `patrol`, `patrol` more than `veteran`, for every recipe |

And the player must be able to *see* the rules at work: the log says when a ping was lost
and why, the depth the charges were set to, and why the escorts broke off.

## 3. Candidate rules

Each rule is a parameter (a field on a block in `sim/params.py`, explained in
`docs/PARAMETERS.md`) or a strategy (a function on a slot, `docs/DIFFICULTY.md`), dialled
per difficulty. The player's suggestions were sonar blind spots, sonar at speed, rack reload
and depth-dependent damage; the list below includes them and what the study found necessary
besides.

### 3.1 Sonar limits (`SonarParams`)

| rule | what | why | dial |
| --- | --- | --- | --- |
| **stern baffles** `baffle_angle` | no echo from a boat within this angle of the destroyer's stern | the ASDIC dome is forward; the hull and the wake block the stern arc. A hunter that overruns the boat loses it until it turns | cadet 60, patrol 50, veteran 40 deg |
| **depth blind zone** `depth_blind_ratio` | the echo is lost inside `max(min_range, depth x ratio)` | the beam cannot be tilted down; a deep boat is lost further out, so the last run-in is blind for longer and the pattern is aimed on dead reckoning. The historical reason deep diving worked, and why Hedgehog was built | cadet 4, patrol 3, veteran 2.5 (a 60 m boat is lost inside 240 / 180 / 150 m; a 150 m boat inside 600 / 450 / 375 m) |
| **detection probability** `sure_fraction` | a ping inside this fraction of the reach is a sure fix; beyond it the chance falls linearly to 0 at the edge of the reach | an echo at the edge of the range is a faint one the operator misses more often than not. Also makes the course estimate (three fixes in 45 s) harder to get on a distant boat | cadet 0.4, patrol 0.4, veteran 0.5 |
| **sprint deafness** `own_noise_factor` 0.4 -> 0.25, new `settle_time` | nearly deaf above `own_noise_speed`, and the set needs this long after slowing before it hears | the player's "sonar availability at high speed"; the settle time is what gives a boat that turned during the charge its chance | settle 20 s |
| **loud boat** `loud_speed`, `loud_factor` | a boat faster than this is heard x1.3 further | the mirror of the creep bonus (`quiet_factor`); sprinting must cost something besides battery | 5 kn, 1.3 |
| *(optional)* **thermal layer** `layer_depth`, `layer_factor` | a layer depth per hunt (say 40 to 90 m, from the seed); below it the reach is halved | gives "go deep" a reason beyond invisibility to lookouts, and a reason to look at the depth gauge; a classic of the genre | cadet always has one, veteran rarely |

The HUD already shows each destroyer's current reach (`sonar_m`); the log should add
`destroyer-N lost the echo (baffles / under the keel / out of reach)`.

### 3.2 Depth estimate (`Datum.depth`, `EscortAIParams`, `DepthChargeParams`)

The escorts set their charges around what they **think** the depth is:

- A sighting (surfaced or periscope) says the boat was shallow: estimate = periscope depth.
- A sonar-only alarm gives no depth: estimate = `assumed_depth` (cadet 30, patrol 40 m).
- After each run that did no damage the estimate walks deeper by `depth_step` (25 m; veteran
  20 m and so more runs near the right depth). A near miss (`damage` event) confirms it.
- The pattern is layered over estimate +- `layer_spread` = 15 m (today +-25 m around the
  true depth). With the 3D damage model (lethal 12 m, damage out to 45 m) a pattern set
  35 m too shallow does at most a third of its damage even when horizontally dead on.

So a boat that dives promptly after being sighted sees the first pattern burst above it,
has about two minutes (the rack reload) before a deeper one, and gains something from
changing depth again. The log should say `destroyer-N drops a pattern set to 25 m` so
the player can read the estimate.

### 3.3 Weapon cycle (`DepthChargeParams`, `escort._drop`)

| rule | what | why | dial |
| --- | --- | --- | --- |
| **rack reload** `pattern_cooldown` 45 -> 120 s | time between two runs by the same ship | the player's "reload time"; throwers were reloaded by hand and the ship had to run off and come back | cadet 150, patrol 120, veteran 90 s |
| **run-over release** (`_drop`) | each charge is released when the ship reaches its aim point (within `throw_range`), not on a 1 s timer from wherever the ship is; a run that cannot reach its aim points in `run_max_time` (40 s) is abandoned | fixes #35: an overtaking hunter steams on and drops instead of throwing short | - |

In the prototype the reload time stopped mattering once the baffles and the blind zone were
in: the hunter's turn-round and re-acquisition already takes longer than 120 s. Keep it
anyway for the case where the hunter hovers over a boat that sits still.

### 3.4 Hunt control (`EscortAIParams`)

| rule | what | why | dial |
| --- | --- | --- | --- |
| **leash** `hunt_leash` | a hunter does not follow the boat further than this from the convoy centre; the group stands down | escorts exist to protect the convoy; with the merchants running at 11 kn away from the datum, a 30 min chase leaves them unprotected | cadet 6, patrol 10, veteran 15 km |
| **time limit** `max_hunt_time` | the escorts give up this long after the alarm | the same reason, and the end condition #24 (escape to win) needs | cadet 15, patrol 30, veteran 60 min |
| **lose-track clock** | `lose_track_time` should count from the hunter's arrival at the datum, not from the last fix | at `cadet` (180 s) a hunter approaching from 3 km at 20 kn gives up before it arrives (appendix); the clock should run while it searches, not while it steams | - |
| `escort_stand_down` gets a `reason` | `lost`, `leash`, `time`, `charges` | the log and the escape-to-win rule read it | - |

### 3.5 Boat side (later issues)

- **Safe depth shrinks with damage**: below `max_depth x (1 - damage)` the hull takes damage
  per minute. Today 150 m is free; with the depth blind zone it would become the universal
  answer. This makes it a gamble after a near miss.
- **Decoys** (Bold): a canister that gives a false echo for ~15 min, four per patrol, a new
  key. Historically the main active counter; a good `veteran`-only or later feature.
- **Battery** stays as it is: a 30 min hunt at flank costs a third of it, which is the price
  of the sprint recipes.
- A **`creeping` attack strategy** for the `escort_search` slot (one ship holds contact
  from outside the blind zone and talks a second one in silently) as the `veteran` answer to
  the blind zone, once it exists.

## 4. Prototype results

`scripts/escape_study.py --proposal --difficulty all --seeds 12`. The prototype patches
`escort._ping`, `escort._drop` and `escort.step` with 3.1 to 3.4 (without the thermal
layer and the lose-track clock change). "how it ended": `lost` the boat, `gave_up` leash or
time limit, `lost_track` 300 s without a fix, `timeout` still hunted after 30 min.

**patrol** (2 escorts, sonar 3,000 m, leash 10 km / 30 min):

| recipe | 1 km | 2 km | 3 km | how it ended (36) |
| --- | --- | --- | --- | --- |
| stay at periscope depth, stop | 1.00 | 1.00 | 1.00 | lost 36 |
| go deep, stop | 0.83 | 0.67 | 0.67 | lost 26, gave_up 10 |
| go deep, creep away | 0.58 | 0.42 | 0.17 | lost 14, gave_up 22 |
| go deep, sprint 90 s across, then creep | 0.50 | 0.17 | 0.17 | lost 10, gave_up 26 |
| go deep, flank across | 0.17 | 0.08 | 0.08 | lost 4, gave_up 18, lost_track 14 |
| sprint across / creep away, alternating | 0.08 | 0.25 | 0.08 | lost 5, gave_up 31 |
| go deep, flank straight away | 0.08 | 0.08 | 0.00 | lost 2, gave_up 34 |

**cadet** (1 escort, sonar 2,400 m, leash 6 km / 15 min): the boat is lost only when it sits
still deep 1 km from the destroyer (3 of 12); every other recipe at every range survives
(the escort gives up or loses the track). **veteran** (3 escorts, sonar 3,600 m, leash
15 km / 60 min): still 0.75 to 0.92 lost for sitting, creeping and sprint-then-creep, 0.33
to 0.75 for the flank recipes; the appendix has the full tables.

What the numbers say:

- The shape is right at `patrol`: doing nothing is fatal, going deep and still is bad, going
  deep and moving off is a coin toss at 1 km and a likely escape at 3 km. Distance now buys
  survival, which is what the report asked for.
- **Hunts end mostly because the escorts give up**, not because the boat is lost by stealth
  (`gave_up` 22 to 34 of 36 for the sensible recipes, `lost_track` only for the flank-across
  recipe). The leash and the time limit are doing the work; the sonar limits make the
  difference between being hit and not being hit meanwhile. Whether stealth alone should be
  able to break contact at `patrol` is question 1 in #34.
- **Fast running is still too safe** (0.00 to 0.08 for a straight flank run). The run-over
  release helps less than expected because the hunter, approaching from astern, is in the
  blind zone for the last 180 m and the boat moves 80 m while the charges sink. Either the
  stern chase needs a dedicated fix (a hunter that overruns from astern turns and attacks
  from the quarter) or the battery has to be the price; question 4 in #34.
- **`veteran` is still very harsh**. Three sonar sets ping the same datum, so the
  probability rule is defeated by numbers. Question 3 in #34.
- `cadet` at 3 km shows the lose-track clock problem (section 3.4): the escort gives up at
  180 s, before it has arrived.

## 5. Suggested phasing

1. **PR 1, sonar and depth estimate** (#34): `SonarParams` baffles, blind zone, probability,
   settle time, loud boat; `Datum.depth` and the estimate walk; narrower layers; the
   lose-track clock; `escort_stand_down` reasons; log lines. Unit tests per rule
   (`tests/test_escort.py`), level ordering in `tests/test_difficulty.py`, the study script
   loses its `--proposal` patch and becomes the balance check it already is (kept out of the
   default pytest run for time: one table is 30 to 40 s).
2. **PR 2, weapon cycle and hunt control** (#35, #34): run-over release, rack reload, leash,
   time limit. Could be merged into PR 1 if small.
3. **PR 3+**: thermal layer, safe depth vs damage, decoys, `creeping` strategy, each its own
   requirement issue.

Acceptance cases to write with PR 1 and 2: the first pattern after a sighting bursts shallow
(TC), a hunter in the baffles loses and regains the echo (TC), the escorts break off and the
log says why (TC), a 3 km escape at `patrol` (TC, with the study as the automated twin).

## 6. Open questions

Listed in #34 so the answers land on GitHub: (1) give up vs. stealth as the main way a hunt
ends; (2) how the escorts form their depth estimate; (3) whether the target table and the
`veteran` numbers feel right; (4) whether a straight flank run away may stay a battery-costly
escape or the stern chase must be made deadly.

## Appendix: the study

```sh
uv run python scripts/escape_study.py                         # current rules, patrol
uv run python scripts/escape_study.py --difficulty all        # the three levels
uv run python scripts/escape_study.py --proposal --seeds 20   # the prototype
uv run python scripts/escape_study.py --recipes deep_flank_away --ranges 2000   # #35
```

Setup: the boat at periscope depth with a random heading; the nearest destroyer `range` m
away, steaming at 12 kn toward it with a fresh sonar fix (hunting); the other destroyers of
the level a little behind it; three freighters 2 km behind the destroyers, crossing. 30 min
of game time at 0.5 s steps, or until the boat is lost or the escorts stand down. Recipes:
`sit` (nothing), `deep_sit` (60 m, stop), `deep_creep_away` (60 m, AHEAD SLOW, straight
away from the hunter), `deep_flank_away` (60 m, flank, straight away), `deep_flank_90`
(60 m, flank, 90 deg off the start heading), `deep_sprint_then_creep` (60 m, flank across
for 90 s, then AHEAD SLOW 60 deg further round), `knuckle` (60 m, alternate a minute of
flank across the bearing and a minute of creep away).

Full tables, 12 seeds, lost fraction (dmg = mean hull damage, runs = depth charge runs):

```
## cadet, CURRENT rules, 1 escorts, sonar 2400 m
recipe                   range  lost   dmg  runs  t_end  how it ended
sit                       1000  1.00  1.00   1.0    124  lost 12
sit                       2000  1.00  1.00   1.0    242  lost 12
sit                       3000  1.00  1.00   1.0    387  lost 12
deep_sit                  1000  1.00  1.00   3.2    537  lost 12
deep_sit                  2000  1.00  1.00   3.0    627  lost 12
deep_sit                  3000  1.00  1.00   3.3    865  lost 12
deep_creep_away           1000  1.00  1.00   2.9    521  lost 12
deep_creep_away           2000  1.00  1.00   2.9    653  lost 12
deep_creep_away           3000  0.75  0.75   1.8    524  lost 9, lost_track 3
deep_flank_away           1000  0.00  0.00  10.8   1800  timeout 12
deep_flank_away           2000  0.00  0.00   8.8   1800  timeout 12
deep_flank_away           3000  0.00  0.00   8.7   1800  timeout 12
deep_flank_90             1000  0.92  0.94   5.7    887  lost 11, timeout 1
deep_flank_90             2000  1.00  1.00   4.0    710  lost 12
deep_flank_90             3000  0.75  0.96   5.3   1131  lost 9, timeout 3
deep_sprint_then_creep    1000  0.83  0.92   4.2    820  lost 10, timeout 2
deep_sprint_then_creep    2000  1.00  1.00   3.4    670  lost 12
deep_sprint_then_creep    3000  0.75  0.77   3.1    711  lost 9, lost_track 2, timeout 1
knuckle                   1000  0.75  0.93   7.2   1177  lost 9, timeout 3
knuckle                   2000  0.50  0.83   6.8   1316  lost 6, timeout 6
knuckle                   3000  0.42  0.62   7.7   1506  lost 5, timeout 7

## patrol, CURRENT rules, 2 escorts, sonar 3000 m
recipe                   range  lost   dmg  runs  t_end  how it ended
sit                       1000  1.00  1.00   1.0    124  lost 12
sit                       2000  1.00  1.00   1.0    242  lost 12
sit                       3000  1.00  1.00   1.0    376  lost 12
deep_sit                  1000  1.00  1.00   2.4    404  lost 12
deep_sit                  2000  1.00  1.00   2.7    556  lost 12
deep_sit                  3000  1.00  1.00   2.5    633  lost 12
deep_creep_away           1000  1.00  1.00   2.8    474  lost 12
deep_creep_away           2000  1.00  1.00   2.2    546  lost 12
deep_creep_away           3000  1.00  1.00   1.8    548  lost 12
deep_flank_away           1000  0.00  0.00  10.8   1800  timeout 12
deep_flank_away           2000  0.00  0.00   8.8   1800  timeout 12
deep_flank_away           3000  0.00  0.00   8.5   1800  timeout 12
deep_flank_90             1000  0.92  0.95   4.8    732  lost 11, timeout 1
deep_flank_90             2000  1.00  1.00   3.2    650  lost 12
deep_flank_90             3000  0.92  0.99   4.0    908  lost 11, timeout 1
deep_sprint_then_creep    1000  0.92  0.93   3.2    596  lost 11, timeout 1
deep_sprint_then_creep    2000  1.00  1.00   2.6    532  lost 12
deep_sprint_then_creep    3000  0.92  0.94   3.4    804  lost 11, timeout 1
knuckle                   1000  0.92  0.97   6.2   1032  lost 11, timeout 1
knuckle                   2000  0.83  0.89   5.8   1144  lost 10, timeout 2
knuckle                   3000  0.50  0.71   7.7   1435  lost 6, timeout 6

## veteran, CURRENT rules, 3 escorts, sonar 3600 m
recipe                   range  lost   dmg  runs  t_end  how it ended
sit                       1000  1.00  1.00   1.0    124  lost 12
sit                       2000  1.00  1.00   1.0    242  lost 12
sit                       3000  1.00  1.00   1.0    371  lost 12
deep_sit                  1000  1.00  1.00   2.2    384  lost 12
deep_sit                  2000  1.00  1.00   2.5    573  lost 12
deep_sit                  3000  1.00  1.00   1.7    519  lost 12
deep_creep_away           1000  1.00  1.00   2.2    368  lost 12
deep_creep_away           2000  1.00  1.00   2.5    499  lost 12
deep_creep_away           3000  1.00  1.00   1.8    566  lost 12
deep_flank_away           1000  0.17  0.34  10.1   1597  lost 2, timeout 10
deep_flank_away           2000  0.00  0.00   9.3   1800  timeout 12
deep_flank_away           3000  0.00  0.00   8.8   1800  timeout 12
deep_flank_90             1000  1.00  1.00   2.5    311  lost 12
deep_flank_90             2000  0.92  0.94   2.8    591  lost 11, timeout 1
deep_flank_90             3000  1.00  1.00   2.4    680  lost 12
deep_sprint_then_creep    1000  1.00  1.00   2.7    478  lost 12
deep_sprint_then_creep    2000  1.00  1.00   1.9    458  lost 12
deep_sprint_then_creep    3000  0.92  0.94   3.0    739  lost 11, timeout 1
knuckle                   1000  0.58  0.74   6.9   1184  lost 7, timeout 5
knuckle                   2000  0.67  0.78   5.6   1093  lost 8, timeout 4
knuckle                   3000  0.67  0.94   7.2   1419  lost 8, timeout 4

## cadet, PROPOSED rules, 1 escorts, sonar 2400 m, leash 6 km / 15 min, blind x4.0, baffle 60 deg
recipe                   range  lost   dmg  runs  t_end  how it ended
sit                       1000  1.00  1.00   1.0    124  lost 12
sit                       2000  1.00  1.00   1.0    242  lost 12
sit                       3000  0.00  0.00   0.0    180  lost_track 12
deep_sit                  1000  0.25  0.52   2.8    647  gave_up 9, lost 3
deep_sit                  2000  0.00  0.17   1.9    522  gave_up 12
deep_sit                  3000  0.00  0.00   0.0    180  lost_track 12
deep_creep_away           1000  0.00  0.38   2.8    735  gave_up 11, lost_track 1
deep_creep_away           2000  0.00  0.07   1.5    492  gave_up 12
deep_creep_away           3000  0.00  0.01   0.2    219  gave_up 2, lost_track 10
deep_flank_away           1000  0.00  0.04   1.8    585  gave_up 12
deep_flank_away           2000  0.00  0.00   0.0    366  gave_up 12
deep_flank_away           3000  0.00  0.00   0.0    347  gave_up 12
deep_flank_90             1000  0.00  0.06   1.1    350  lost_track 12
deep_flank_90             2000  0.00  0.01   0.8    453  gave_up 7, lost_track 5
deep_flank_90             3000  0.00  0.00   0.3    378  gave_up 12
deep_sprint_then_creep    1000  0.00  0.30   2.3    658  gave_up 11, lost_track 1
deep_sprint_then_creep    2000  0.00  0.07   1.3    493  gave_up 11, lost_track 1
deep_sprint_then_creep    3000  0.00  0.01   0.2    330  gave_up 10, lost_track 2
knuckle                   1000  0.00  0.02   2.7    753  gave_up 10, lost_track 2
knuckle                   2000  0.00  0.02   1.2    495  gave_up 12
knuckle                   3000  0.00  0.02   0.5    382  gave_up 12

## patrol, PROPOSED rules, 2 escorts, sonar 3000 m, leash 10 km / 30 min, blind x3.0, baffle 50 deg
recipe                   range  lost   dmg  runs  t_end  how it ended
sit                       1000  1.00  1.00   1.0    124  lost 12
sit                       2000  1.00  1.00   1.0    242  lost 12
sit                       3000  1.00  1.00   1.0    388  lost 12
deep_sit                  1000  0.83  0.89   3.9    828  gave_up 2, lost 10
deep_sit                  2000  0.67  0.83   3.5    868  gave_up 4, lost 8
deep_sit                  3000  0.67  0.82   3.8   1046  gave_up 4, lost 8
deep_creep_away           1000  0.58  0.81   4.9   1203  gave_up 5, lost 7
deep_creep_away           2000  0.42  0.75   3.5    970  gave_up 7, lost 5
deep_creep_away           3000  0.17  0.31   3.2    996  gave_up 10, lost 2
deep_flank_away           1000  0.08  0.31   3.9   1294  gave_up 11, lost 1
deep_flank_away           2000  0.08  0.20   2.0    922  gave_up 11, lost 1
deep_flank_away           3000  0.00  0.00   0.3    661  gave_up 12
deep_flank_90             1000  0.17  0.25   1.8    922  gave_up 4, lost 2, lost_track 6
deep_flank_90             2000  0.08  0.15   1.2    732  gave_up 5, lost 1, lost_track 6
deep_flank_90             3000  0.08  0.15   1.3    933  gave_up 9, lost 1, lost_track 2
deep_sprint_then_creep    1000  0.50  0.64   4.0    955  gave_up 6, lost 6
deep_sprint_then_creep    2000  0.17  0.43   3.5   1069  gave_up 10, lost 2
deep_sprint_then_creep    3000  0.17  0.34   2.6    932  gave_up 10, lost 2
knuckle                   1000  0.08  0.34   5.2   1442  gave_up 11, lost 1
knuckle                   2000  0.25  0.36   4.0   1170  gave_up 9, lost 3
knuckle                   3000  0.08  0.25   3.2   1065  gave_up 11, lost 1

## veteran, PROPOSED rules, 3 escorts, sonar 3600 m, leash 15 km / 60 min, blind x2.5, baffle 40 deg
recipe                   range  lost   dmg  runs  t_end  how it ended
sit                       1000  1.00  1.00   1.0    124  lost 12
sit                       2000  1.00  1.00   1.0    242  lost 12
sit                       3000  1.00  1.00   1.0    384  lost 12
deep_sit                  1000  0.92  0.99   4.2    910  lost 11, timeout 1
deep_sit                  2000  0.92  0.95   5.0   1179  lost 11, timeout 1
deep_sit                  3000  0.83  0.92   5.7   1452  lost 10, timeout 2
deep_creep_away           1000  0.75  0.94   5.2   1230  lost 9, timeout 3
deep_creep_away           2000  0.83  0.97   4.3   1129  lost 10, timeout 2
deep_creep_away           3000  0.92  0.99   4.1   1195  lost 11, timeout 1
deep_flank_away           1000  0.67  0.88   4.9   1309  lost 8, timeout 4
deep_flank_away           2000  0.67  0.87   3.8   1410  lost 8, timeout 4
deep_flank_away           3000  0.50  0.79   3.7   1582  gave_up 1, lost 6, timeout 5
deep_flank_90             1000  0.75  0.86   3.1   1104  gave_up 1, lost 9, timeout 2
deep_flank_90             2000  0.33  0.56   3.4   1603  gave_up 2, lost 4, timeout 6
deep_flank_90             3000  0.33  0.58   2.7   1498  gave_up 3, lost 4, timeout 5
deep_sprint_then_creep    1000  0.92  1.00   4.2    958  lost 11, timeout 1
deep_sprint_then_creep    2000  0.92  0.98   4.4   1160  lost 11, timeout 1
deep_sprint_then_creep    3000  0.83  0.97   4.3   1273  lost 10, timeout 2
knuckle                   1000  0.75  0.87   4.8   1136  lost 9, timeout 3
knuckle                   2000  0.42  0.58   6.1   1556  lost 5, timeout 7
knuckle                   3000  0.33  0.59   5.1   1619  lost 4, timeout 8
```
