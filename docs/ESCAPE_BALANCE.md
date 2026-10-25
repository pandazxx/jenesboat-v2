# Escape balance: a found boat should be able to get away

Status: brainstorm and proposal, 2026-10-24; detection section reworked to the owner's
direction on 2026-10-25 (section 3.1); after the owner's review of the second-prototype
stories the brainstorm went back to mental models (section 7), which is where it stands. Requirement issue #34 (decisions go there), bug
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

### 3.1 Detection (reworked to the owner's direction, 2026-10-25)

The owner's comment on #34 (2026-10-25) replaces the first draft of this section. The sonar
rules of the prototype that survive are marked *kept*; two are *dropped* unless the open
questions below bring them back; the rest is new. Nothing here is implemented or measured
yet: the prototype numbers in section 4 were taken with the first draft.

**Active sonar (`SonarParams`)**

| rule | what | why | status / dial |
| --- | --- | --- | --- |
| **uncertainty area** `area_base`, `area_per_km` | a ping inside the reach returns a fix that is a random point inside a circle around the boat whose radius grows with range: `area_base + area_per_km x range` (sketch 25 m + 50 m/km: 75 m at 1 km, 175 m at 3 km). The AI works from that point as it does today from the +-40 m fix | an echo at long range gives a bearing and a rough range; the course estimate from the 45 s window only becomes usable close in | new; numbers open (Q2) |
| **HUD fix ring** | the player sees the escorts' fix on the boat: a ring of the area's diameter centred on the random point, fading with the fix's age, gone when the echo is lost | the player can read *that* they are held and *how well*; today the only trace of a ping is a log line | new (`render.py`, from `world.datum`); Q6 |
| **noise shadows** `noise_base`, `noise_per_knot` | every friendly ship casts a sector of noise behind it as seen from the pinging destroyer, half-angle `atan(noise_radius / range to that ship)`, `noise_radius = noise_base + noise_per_knot x speed`, never zero (sketch 150 m + 30 m/kn: a freighter at 8 kn shadows 390 m, at 11 kn 480 m). A boat inside a sector and beyond the ship gives no echo | the convoy's own screws mask the sea behind it: the boat can shelter in the fleet, and a running convoy shelters it more. Replaces the "-12 % reach per ship within 2.5 km" rule (`interference_*`) | new; replaces `interference_radius / per_ship / floor`; Q3 |
| **stern baffles** `baffle_angle` | no echo within this angle of the destroyer's stern | the dome is forward; the hull and wake block the stern arc | *kept*: cadet 60, patrol 50, veteran 40 deg |
| **depth blind zone** `depth_blind_ratio` | echo lost inside `max(min_range, depth x ratio)` | the beam cannot tilt down; a deep boat is lost further out and the last run-in is blind | *kept*: cadet 4, patrol 3, veteran 2.5 |
| **sprint deafness** `own_noise_factor`, `settle_time` | nearly deaf above `own_noise_speed`, 20 s to settle after slowing | the player's "sonar at high speed" | *kept* (settle time to confirm) |
| detection probability `sure_fraction` | a chance of missing a faint echo near the edge of the reach | | *dropped* unless Q1 keeps it: the area model carries the range penalty instead |
| loud boat `loud_speed`, `loud_factor` | a sprinting boat heard x1.3 further | | *dropped*; could return as a smaller area for a loud boat (Q2) |
| *(optional)* thermal layer | reach halved below a layer depth | | parked |

**Other sensors**

| sensor | rule | code |
| --- | --- | --- |
| **visual** (lookouts) | unchanged: the detection table in `docs/PARAMETERS.md`; a sighting gives an exact fix | `sim/detection.py`, as today |
| **radar** | new, optional by difficulty (`RadarParams`: range, levels). Long range, detects *surfaced vessels only*: a surfaced boat, never a periscope or a submerged boat. Gives a continuous exact track while the boat is up. With no night yet (`light` = 1) its first effect is that a surfaced approach against a radar level is spotted long before the 9 km lookouts | new block in `sim/params.py`, a check in `world._lookouts` or beside it; Q4 |
| **hydrophone** | boat only, unchanged (bearing-only contacts, needs depth >= 11 m and <= 4 kn). The escorts' 1,200 m torpedo hearing for the `comb` evasion stays as it is | `sim/detection.py`, `sim/escort.py` |
| **torpedo trace** | a torpedo hit (or a seen wake) gives the escorts the torpedo's *track line* and the knowledge that the boat is somewhere on it within the torpedo's run (5,000 m for a G7e), not a point 2 km back (`THREAT_BEHIND_TORPEDO`). The datum becomes a line: hunters sweep down the track from the target outward, pinging; the convoy turns away from the line; the HUD can draw it | `Datum` gains a line kind (`sim/escort.py`), `world._torpedo_alarm`; Q5 |

The log should still say why an echo was lost (`destroyer-N lost the echo: baffles / under the
keel / behind merchant-2 / out of reach`), and the HUD ring shows the result.

**Decisions (owner, #34, 2026-10-25)**: Q1 the chance of missing a faint echo stays, as a
parameter (`sure_fraction`). Q2 the area ignores the boat's speed for now. Q3 a stopped or
sunk ship casts the base shadow; today's fleet-noise reach rule is obsolete. Q4 radar: 20 km
(to be tuned), exact fix handled like a sighting, `veteran` only. Q5 the torpedo line is given
as soon as a torpedo is observed (heard, wake seen, or a hit). Q6 location indicators on the
HUD: one indicator per subject; an exact position when known (sighting, radar) hides every
estimate; otherwise the best estimate, i.e. the smallest ring. This rule applies to how the
boat's own contacts are drawn as well as to the escorts' fix on the boat.

**Expected effect on the balance**: with a certain echo inside the reach the escape odds no
longer come from missed pings; they come from the shadows (a boat that works the convoy's
noise), the blind zone and the baffles (the hunter's attack cycle), and the leash. The study
got that second pass on 2026-10-25 (section 4, "second prototype"): the shape at `patrol`
is the same as with the first draft, a little harsher at 1 km (the area fix and no
loud-boat penalty) and a little kinder at 3 km. One finding needs a decision (Q7 in section
6): **the shelter in the fleet is mostly undone by the merchants themselves**. A sonar alarm
alerts every merchant within 8 km and they run away from the boat, so the ships that were
between the hunter and the boat clear out within a few minutes and the shadows go with them;
a boat found inside the convoy (`--placement inside`) then fares *worse* than one found
outside, because the hunter stays near its convoy and the leash never trips.

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

`scripts/escape_study.py --proposal --difficulty all --seeds 12`, first draft of 2026-10-24
(detection probability, loud boat, +-40 m fix; the second prototype with the reworked
detection follows below). The prototype patches `escort._ping`, `escort._drop` and
`escort.step` with 3.1 to 3.4 (without the thermal layer and the lose-track clock change). "how it ended": `lost` the boat, `gave_up` leash or
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

### Second prototype (2026-10-25): uncertainty area and noise shadows

`scripts/escape_study.py --proposal` now carries the reworked detection: the fix is a random
point in a circle of radius 25 m + 50 m/km of range, friendly ships (afloat or sunk, 150 m +
30 m/kn) cast noise shadows and the old fleet-noise reach rule is gone, the faint-echo chance
stays, the loud-boat rule is dropped. `--placement inside` starts the boat 600 m beyond the
convoy centre as seen from the hunter (found while attacking) so the shadows are in play.

`patrol`, lost fraction, 12 seeds:

| recipe | outside 1 km | outside 3 km | inside 1 km | inside 3 km |
| --- | --- | --- | --- | --- |
| stay at periscope depth, stop | 1.00 | 1.00 | 1.00 | 1.00 |
| go deep, stop | 1.00 | 0.33 | 0.67 | 0.58 |
| go deep, creep away | 0.75 | 0.17 | 0.92 | 0.50 |
| go deep, sprint 90 s across, then creep | 0.67 | 0.08 | 0.83 | 0.33 |
| go deep, flank across | 0.25 | 0.08 | 0.25 | 0.00 |
| sprint across / creep away, alternating | 0.00 | 0.00 | 0.00 | 0.00 |
| go deep, flank straight away | 0.25 | 0.00 | 0.42 | 0.25 |

Against the first draft (outside, 1 km / 3 km): deep and still 0.83 / 0.67 -> 1.00 / 0.33;
creep away 0.58 / 0.17 -> 0.75 / 0.17; sprint then creep 0.50 / 0.17 -> 0.67 / 0.08. The
target table in section 2 holds at 3 km (creep away 0.17 <= 0.25) and at 1 km the coin toss
has become 3 in 4, which the area numbers (Q2) can tune. `cadet` is unchanged in character
(1 to 5 of 12 lost only when sitting or creeping from 1 km); `veteran` is unchanged (0.75 to
1.00 for the still and creeping recipes, 0.25 to 0.58 for the fast ones). Full tables in the
appendix.

The inside placement does not show the shelter the shadows were meant to give (see Q7): the
merchants run from the boat and take their shadows with them, and the hunter, staying close
to its convoy, is never leashed, so more hunts end as `timeout` (alive after 30 min, still
hunted) and more as `lost`. The shelter will only work for a boat that is found without the
merchants being told, or if the merchants' flee rule changes.

## 5. Suggested phasing

1. **PR 1, detection** (#34, after the Q1 to Q6 answers): `SonarParams` uncertainty area,
   noise shadows, baffles, blind zone, settle time; the HUD fix ring; the torpedo track line
   datum; `escort_stand_down` reasons; log lines. **PR 1b, radar** (`RadarParams` per level).
   Then the depth estimate: `Datum.depth` and the estimate walk; narrower layers; the
   lose-track clock. Unit tests per rule
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
escape or the stern chase must be made deadly. Q1 to Q6 on the detection rework are
answered (section 3.1).

Assumptions taken on 2026-10-25 so that the implementation can start (recorded on #34; the
owner can overrule any of them there): (1) the leash and the time limit are the hard end of a
hunt, and losing the track by stealth stays possible but is not tuned to be common at
`patrol`; (2) the depth estimate walks 25 m deeper after a run and is confirmed only by a run
that does 10 % or more damage; (3) the target table of section 2 stands, `veteran` is meant
to be this harsh; (4) the stern chase is made deadly by the run-over release (#35) and the
battery is the price of sprinting. Sections 3.2 to 3.4 stand as proposed.

**Q7 (new)**: should a sonar alarm still send every merchant within 8 km running from the
boat? It undoes the shelter in the fleet (section 4, second prototype). Options: merchants
hold course until an escort has a sighting or a torpedo is observed; or they run only when
the fix is within some distance of them; or keep today's rule and accept that shelter only
helps a boat that has not been alarmed on. Not blocking PR 1.

## 7. Mental models for a silent escape (brainstorm, 2026-10-25)

Status: posted on #34 for agreement; nothing here is decided or measured. It supersedes the
*expected effect* paragraphs of sections 3.1 and 4 as the direction of the next prototype.

The owner's review of the second-prototype stories (#34, 2026-10-25) made three points: the stories' opening was inconsistent, the depth charges never changed depth, and once pinned the boat never escapes by stealth, it only survives until the hunter gives up. The third is the one that matters and sends the brainstorm back to first principles. First the two defects, then the diagnosis, then the mental models, then imagined stories of how a hunt *should* go, then what I would check next (no implementation yet).

#### The two defects in the stories

1. **"Found by sonar at 3 km" with a 2,100 m reach is a contradiction.** The study plants a fix at the boat's position and calls it a sonar contact whatever the range. That is not an opening that can happen. A hunt opens in one of four ways and each gives the hunter different knowledge; the stories must start from a real one (section "Openings" below). The 3 km cases should have been "periscope sighted at 1.5 km" or "boat seen diving at 5 km".
2. **The charges stayed at 15 to 27 m for four runs** because the prototype's rule was "walk the estimate deeper only after a run with *no* damage", and a shallow pattern 35 m above the boat still scratches it (3 to 10 %), which the rule read as "right depth". A hunter would not do that. Depth has to be a search of its own (model 4 below).

#### Diagnosis: a budget the boat can never meet

Strip the hunt to one question: *after each attack, is the boat outside the hunter's reach when the hunter looks again?* Every attack ends with the hunter blind for 60 to 120 s (under the keel, then the boat in its baffles while it turns). In that window the boat moves:

| boat | in 60 s | in 120 s |
| --- | --- | --- |
| creeping, 1.9 kn | 60 m | 120 m |
| AHEAD HALF, 3.8 kn | 120 m | 235 m |
| flank, 7.6 kn | 235 m | 470 m |

The hunter's reach when it looks again is 2,100 m for a creeping boat and 3,000 m for a moving one, and its search starts at the predicted position with a 400 m box. The boat is never further than a few hundred metres from where it is expected and never outside the reach. **Nothing the boat does changes the reach by more than 30 %** (the creep bonus). So the only ways a hunt ends are the hunter finding the depth or the hunter giving up, exactly what you saw. The leash and the time limit are not wrong, but they must be the backstop, not the ending.

The historical boats that got away did so because the escort *lost the echo*: a slow, deep, end-on boat under a temperature layer, in the disturbed water left by the explosions, gave an echo the operator could not hold, and the escort then searched the wrong patch of sea. Every one of those factors is a lever the player can pull, and none exists in the sim today.

#### Mental models

**1. Contact is a quality, not a range.** The echo the hunter gets back is a number, *echo strength*, and the fix exists only while it is above the set's threshold. Echo strength falls with range, and is multiplied by what the boat is doing:

| factor | strong echo | weak echo | why |
| --- | --- | --- | --- |
| aspect | beam-on to the hunter (x1.0) | bow-on or stern-on (x0.4) | a hull broadside returns far more sound than a bow; end-on was the classic evasion |
| speed | flank (x1.0) | creep (x0.7, as today) | screw noise and wake |
| depth | above the layer (x1.0) | below the layer (x0.5), a layer depth per hunt | sound bends away at the thermocline |
| water | clear | behind a merchant's noise (x0), in an explosion cloud (x0), behind a knuckle (x0 for a minute) | your noise shadows, extended to two more sources |
| the set | 14 kn, settled | sprinting (x0.25), settling (x0), turning hard (x0.5) | the set hears nothing through its own screws and wake |

The hunter's *effective reach* is the range at which this product drops under the threshold. A creeping, deep, end-on boat under the layer gives 3,000 x 0.7 x 0.4 x 0.5 = **420 m**. Now the budget closes: the boat opens 235 m at flank in a 60 s blind window, turns end-on, slows, and the hunter looking again at 420 m reach from a prediction that is 100 to 200 m wrong has a real chance of hearing nothing. Without the layer it is 840 m, which the explosion cloud (next model) covers.

The player must *see* this: a **stealth gauge** on the HUD, the boat's current echo strength (or the range at which a settled set would hold it), next to the escorts' ring. The ring says what they know; the gauge says how loud you are. Turning the bow toward the hunter and watching the gauge fall is the skill the game is about.

**2. The attack cycle has a blind window and the sea boils afterwards.** Each run is: hold contact at 14 kn, lose it under the keel at 180 m, hold course, drop, overrun, turn. From the drop, the pattern leaves a **cloud** of disturbed water 100 to 150 m across that is a noise shadow for 2 to 3 minutes (the ASDIC was useless through it). The hunter's own hard turn leaves a short knuckle. The boat's one move per cycle happens in that window: change course (end-on to where the hunter will come back from), change depth, change speed, and if possible put the cloud between itself and the hunter. A boat that uses the window well is heard again only by luck; one that does not (holds course, or sits) is re-acquired exactly as today.

**3. Openings: four ways to be found, four different starts.** What the hunter knows at t = 0 decides the whole hunt:

| opening | position | depth | course | the boat's lead |
| --- | --- | --- | --- | --- |
| periscope sighted (1.5 km by day) | exact | 12 m, known | no | 2 to 3 min until the first charges; the boat is 200 to 400 m from the sighting |
| seen diving at long range (lookouts 9 km, radar 20 km at `veteran`) | the dive point, exact, but minutes old | unknown, deeper every minute | the last surface course | 5 to 15 min; the hunter comes to a point the boat left long ago and must search |
| torpedo observed | a line, up to 5 km long | unknown | no | the hunter sweeps the line from the target outward; a boat that fired from 2 km and turned off the line has 5 min or more |
| sonar contact (inside the screen, under 1 km typically) | an area ring, 75 m | unknown | after 3 fixes | none; this is the dangerous one, and the one the shadows and the layer are for |

The study's "found at 3 km" cases are really the second and third openings, and they should be modelled as such.

**4. Depth is a search of its own.** The escorts never measure depth. They hold a *band* guess (shallow 15 to 40 m, medium 40 to 80 m, deep 80 to 150 m) from the opening: periscope sighting -> shallow; dived N minutes ago -> the band the boat could have reached; sonar only -> medium. Each pattern is set in one band. Evidence moves the guess: a pattern that does real damage (10 % or more) confirms the band; one that does nothing moves to the next band in a fixed order (shallow, medium, deep, then back to shallow); oil or debris would confirm (later). Damage falls off faster in depth than it does today (narrower lethal/damage radii in the vertical, or simply a 25 m band spacing with 15 m layers), so a wrong band is a miss, not a scratch. The player can read the set depth in the log and the HUD and act on it: *they are set shallow, go deep now; they have found 60 m, change depth before the next run*.

**5. The convoy comes first.** One ship hunts, the rest screen, and the hunt ends when the convoy's safety says so: the leash (10 km) and the time limit (30 min) stay as a backstop and as the end condition for #24. But with model 1 and 2 in place, most escapes should be *track lost* (the hunter searched and heard nothing for 5 min), and give-up should be the exception. That is the target I would write: at `patrol`, periscope sighted at 1.5 km, a boat that uses the blind window (turn end-on, change depth, creep, cloud between) is lost by the hunter in most hunts; one that holds course or sits is found again every time.

**6. The boat's verbs.** Everything above gives the player a vocabulary: *slow* (creep), *deep* (and under the layer), *end-on* (aspect), *shadow* (merchant, cloud, knuckle), *move in the window* (course and depth change during the attack), later *decoy* (Bold) and *surface and run* (at night, when a surfaced boat at 17 kn outruns the search and radar is the counter at `veteran`). The HUD gauge makes each verb visible as it is used.

#### Imagined stories under these models

**A. Periscope seen, the boat gets away (the hunt we want).** Day, `patrol`. The boat is at periscope depth 1,400 m off the convoy's bow when the lead destroyer's lookouts see the feather. Log: `destroyer-1 sighted our periscope`. The ring on the HUD is a dot: they know exactly where the boat is, and that it is shallow. The player orders 90 m (below the layer at 70 m this hunt) and AHEAD FULL, and turns 60° off, toward the convoy's wake. The hunter arrives in 2 min 20 s and drops where the periscope was, shallow band; the boat is 450 m away and 60 m down, hears the pattern go off behind it, and the HUD shows the cloud. The player slows to creep and turns the stern to the hunter. The hunter comes out of its turn, settles, and listens: the boat is end-on, creeping, under the layer, 600 m away behind its own explosion cloud: echo strength under the threshold. Log: `destroyer-1 lost the echo`. It searches a box around the sighting, hears nothing for five minutes, and the log says `escorts lost the track`. The gauge was in the green from the moment the boat went end-on; the player watched it and never saw a second ring.

**B. The same opening, lost.** The player dives to 60 m (above the layer) and runs straight away at flank. The hunter's first pattern falls short, but the boat is beam-on to the hunter during its turn, loud at flank, above the layer: the echo is strong at 900 m, the ring reappears at 100 m radius, and the course estimate is good because the boat is running straight. Second run: medium band, bracketed, 40 % damage. The player now goes deep and slows, but the hunter has a fresh fix and a band that works: third run, lost. Lesson the HUD taught: the gauge was red the whole time it ran straight.

**C. Seen diving at 6 km.** Dawn, the boat surfaced, running in on the diesels; `destroyer-2` sees it at 6 km. The player dives. The escorts know the dive point exactly, but the hunter needs 9 min at 20 kn to get there, deaf all the way, and the boat has made 1,000 m under the layer at AHEAD HALF, then crept and turned end-on. The hunter's search box starts at the dive point with a 400 m radius and widens 1 m/s. If the boat is beyond the box and quiet, the search runs out at 5 min; if the player kept running at flank above the layer, the box catches the wake noise at 1,500 m and the hunt is on. Here the opening gives the boat a head start and the models decide whether it keeps it.

**D. Torpedo seen.** The boat fires from 2,200 m on the beam; the escorts hear the torpedo and get the track line. The hunter sweeps the line from the target outward at 14 kn, pinging each side; the boat that turned 90° off the line immediately after firing and crept is 300 m off the line, end-on, deep, when the hunter passes 1 km later; echo weak, the sweep continues to 5 km and finds nothing. The boat that stayed on the line to watch the hit through the periscope is caught in the sure zone with a shallow-band first pattern.

**E. Caught in the screen (the one that should be deadly).** The boat crept into the convoy's gap at periscope depth and `destroyer-1`, 700 m away and settled at 12 kn, gets a strong echo: a 60 m ring. There is no window before the first run and the band guess is shallow because the sonar reach says the boat is near the surface (a deep boat at 700 m would be in the blind zone soon). The boat's only play is the merchants: inside the convoy the hunter's pings are blocked by freighters half the time (your shadows), and a boat that uses the 2 minutes a shadow buys to go deep and end-on has a chance; one that stays shallow is lost in the first pattern, as it should be.

#### What I would do next (still no implementation)

1. Agree the mental models, or strike the ones you do not want. The ones that do the work for silent escape are 1 (echo strength with aspect and layer), 2 (the explosion cloud as a shadow), and 4 (depth bands). The HUD gauge is the player's half of model 1.
2. Rebuild the study's openings from model 3 (periscope sighted, seen diving, torpedo line, sonar contact in the screen) and make the stories start from those, so the first row is consistent with the hunter's sonar.
3. Prototype models 1, 2 and 4 in the study and render the five stories above from the sim, then compare against the imagined versions: where they differ is where the numbers (aspect factor, layer factor, cloud duration, threshold) need tuning or where the model is wrong.
4. Only then write the requirement's acceptance criteria and the parameter sheet.


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

Full tables, 12 seeds, lost fraction (dmg = mean hull damage, runs = depth charge runs). The
first three blocks are the current rules; the next three the first-draft prototype of
2026-10-24 (`PROPOSED rules` without a `found ...` tag); the last six the second prototype of
2026-10-25 with the uncertainty area and the noise shadows, found outside and inside:

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

## cadet, PROPOSED rules, found outside, 1 escorts, sonar 2400 m, leash 6 km / 15 min, blind x4.0, baffle 60 deg, area 25 m + 50 m/km, shadows
recipe                   range  lost   dmg  runs  t_end  how it ended
sit                       1000  1.00  1.00   1.0    124  lost 12
sit                       2000  1.00  1.00   1.0    242  lost 12
sit                       3000  0.00  0.00   0.0    180  lost_track 12
deep_sit                  1000  0.17  0.51   2.9    666  gave_up 10, lost 2
deep_sit                  2000  0.00  0.13   1.7    487  gave_up 12
deep_sit                  3000  0.00  0.00   0.0    180  lost_track 12
deep_creep_away           1000  0.17  0.41   2.6    646  gave_up 10, lost 2
deep_creep_away           2000  0.00  0.04   1.4    509  gave_up 12
deep_creep_away           3000  0.00  0.01   0.2    219  gave_up 2, lost_track 10
deep_flank_away           1000  0.00  0.06   1.7    564  gave_up 11, lost_track 1
deep_flank_away           2000  0.00  0.00   0.0    368  gave_up 12
deep_flank_away           3000  0.00  0.00   0.0    315  gave_up 9, lost_track 3
deep_flank_90             1000  0.00  0.08   1.2    399  lost_track 12
deep_flank_90             2000  0.00  0.05   0.8    463  gave_up 7, lost_track 5
deep_flank_90             3000  0.00  0.01   0.3    362  gave_up 10, lost_track 2
deep_sprint_then_creep    1000  0.08  0.35   2.3    645  gave_up 11, lost 1
deep_sprint_then_creep    2000  0.00  0.09   1.3    489  gave_up 12
deep_sprint_then_creep    3000  0.00  0.01   0.2    277  gave_up 6, lost_track 6
knuckle                   1000  0.00  0.02   2.8    749  gave_up 11, lost_track 1
knuckle                   2000  0.00  0.02   1.3    518  gave_up 12
knuckle                   3000  0.00  0.02   0.6    386  gave_up 12

## patrol, PROPOSED rules, found outside, 2 escorts, sonar 3000 m, leash 10 km / 30 min, blind x3.0, baffle 50 deg, area 25 m + 50 m/km, shadows
recipe                   range  lost   dmg  runs  t_end  how it ended
sit                       1000  1.00  1.00   1.0    124  lost 12
sit                       2000  1.00  1.00   1.0    242  lost 12
sit                       3000  1.00  1.00   1.0    375  lost 12
deep_sit                  1000  1.00  1.00   4.2    873  lost 12
deep_sit                  2000  0.75  0.88   3.8    939  gave_up 3, lost 9
deep_sit                  3000  0.33  0.53   3.4    991  gave_up 8, lost 4
deep_creep_away           1000  0.75  0.86   4.6   1125  gave_up 3, lost 9
deep_creep_away           2000  0.58  0.75   3.8    973  gave_up 5, lost 7
deep_creep_away           3000  0.17  0.55   2.8    968  gave_up 10, lost 2
deep_flank_away           1000  0.25  0.48   3.6   1273  gave_up 9, lost 3
deep_flank_away           2000  0.00  0.13   1.7    964  gave_up 12
deep_flank_away           3000  0.00  0.00   0.3    662  gave_up 12
deep_flank_90             1000  0.25  0.38   1.7    751  gave_up 5, lost 3, lost_track 3, timeout 1
deep_flank_90             2000  0.08  0.27   1.7    871  gave_up 6, lost 1, lost_track 5
deep_flank_90             3000  0.08  0.19   1.4    894  gave_up 8, lost 1, lost_track 3
deep_sprint_then_creep    1000  0.67  0.81   3.8    904  gave_up 4, lost 8
deep_sprint_then_creep    2000  0.42  0.68   3.4    978  gave_up 7, lost 5
deep_sprint_then_creep    3000  0.08  0.39   2.8    983  gave_up 11, lost 1
knuckle                   1000  0.00  0.17   5.3   1449  gave_up 12
knuckle                   2000  0.08  0.28   4.1   1157  gave_up 11, lost 1
knuckle                   3000  0.00  0.16   2.8   1006  gave_up 12

## veteran, PROPOSED rules, found outside, 3 escorts, sonar 3600 m, leash 15 km / 60 min, blind x2.5, baffle 40 deg, area 25 m + 50 m/km, shadows
recipe                   range  lost   dmg  runs  t_end  how it ended
sit                       1000  1.00  1.00   1.0    124  lost 12
sit                       2000  1.00  1.00   1.0    242  lost 12
sit                       3000  1.00  1.00   1.0    360  lost 12
deep_sit                  1000  1.00  1.00   4.3    893  lost 12
deep_sit                  2000  0.92  0.99   4.5   1065  lost 11, timeout 1
deep_sit                  3000  0.83  0.98   4.3   1139  lost 10, timeout 2
deep_creep_away           1000  0.83  0.98   5.2   1209  lost 10, timeout 2
deep_creep_away           2000  0.83  0.94   4.1   1126  lost 10, timeout 2
deep_creep_away           3000  0.75  0.93   4.3   1284  lost 9, timeout 3
deep_flank_away           1000  0.83  0.99   4.7   1355  lost 10, timeout 2
deep_flank_away           2000  0.67  0.85   3.8   1382  lost 8, timeout 4
deep_flank_away           3000  0.33  0.65   3.5   1686  gave_up 1, lost 4, timeout 7
deep_flank_90             1000  0.42  0.76   3.5   1527  gave_up 1, lost 5, timeout 6
deep_flank_90             2000  0.25  0.59   3.2   1582  gave_up 2, lost 3, timeout 7
deep_flank_90             3000  0.25  0.56   2.8   1468  gave_up 4, lost 3, timeout 5
deep_sprint_then_creep    1000  1.00  1.00   4.3    999  lost 12
deep_sprint_then_creep    2000  0.75  0.88   4.6   1230  lost 9, timeout 3
deep_sprint_then_creep    3000  0.58  0.88   5.2   1494  lost 7, timeout 5
knuckle                   1000  0.33  0.64   5.8   1546  lost 4, timeout 8
knuckle                   2000  0.42  0.47   5.6   1509  lost 5, timeout 7
knuckle                   3000  0.42  0.71   4.7   1518  lost 5, timeout 7

## cadet, PROPOSED rules, found inside, 1 escorts, sonar 2400 m, leash 6 km / 15 min, blind x4.0, baffle 60 deg, area 25 m + 50 m/km, shadows
recipe                   range  lost   dmg  runs  t_end  how it ended
sit                       1000  1.00  1.00   1.0    124  lost 12
sit                       2000  1.00  1.00   1.0    242  lost 12
sit                       3000  1.00  1.00   1.0    339  lost 12
deep_sit                  1000  0.42  0.54   3.8    834  gave_up 7, lost 5
deep_sit                  2000  0.17  0.44   3.0    872  gave_up 10, lost 2
deep_sit                  3000  0.00  0.00   0.0    180  lost_track 12
deep_creep_away           1000  0.33  0.56   2.8    714  gave_up 6, lost 4, lost_track 2
deep_creep_away           2000  0.08  0.46   3.0    872  gave_up 10, lost 1, lost_track 1
deep_creep_away           3000  0.00  0.00   0.0    180  lost_track 12
deep_flank_away           1000  0.00  0.14   2.3    839  gave_up 11, lost_track 1
deep_flank_away           2000  0.00  0.02   1.1    729  gave_up 8, lost_track 4
deep_flank_away           3000  0.00  0.00   0.1    235  gave_up 1, lost_track 11
deep_flank_90             1000  0.00  0.04   1.2    397  lost_track 12
deep_flank_90             2000  0.00  0.06   1.0    519  lost_track 12
deep_flank_90             3000  0.00  0.02   0.2    297  lost_track 12
deep_sprint_then_creep    1000  0.33  0.63   2.9    769  gave_up 7, lost 4, lost_track 1
deep_sprint_then_creep    2000  0.00  0.34   2.9    859  gave_up 11, lost_track 1
deep_sprint_then_creep    3000  0.00  0.00   0.0    180  lost_track 12
knuckle                   1000  0.00  0.02   3.0    823  gave_up 10, lost_track 2
knuckle                   2000  0.00  0.01   2.1    704  gave_up 7, lost_track 5
knuckle                   3000  0.00  0.00   0.0    180  lost_track 12

## patrol, PROPOSED rules, found inside, 2 escorts, sonar 3000 m, leash 10 km / 30 min, blind x3.0, baffle 50 deg, area 25 m + 50 m/km, shadows
recipe                   range  lost   dmg  runs  t_end  how it ended
sit                       1000  1.00  1.00   1.0    124  lost 12
sit                       2000  1.00  1.00   1.0    242  lost 12
sit                       3000  1.00  1.00   1.0    339  lost 12
deep_sit                  1000  0.67  0.91   5.1   1136  lost 8, timeout 4
deep_sit                  2000  0.83  0.89   4.7   1103  lost 10, timeout 2
deep_sit                  3000  0.58  0.63   3.5   1028  lost 7, lost_track 4, timeout 1
deep_creep_away           1000  0.92  0.95   4.3   1042  lost 11, timeout 1
deep_creep_away           2000  0.92  0.95   4.9   1285  lost 11, timeout 1
deep_creep_away           3000  0.50  0.66   3.4   1138  gave_up 1, lost 6, lost_track 3, timeout 2
deep_flank_away           1000  0.42  0.58   4.2   1448  gave_up 4, lost 5, timeout 3
deep_flank_away           2000  0.33  0.56   3.4   1465  gave_up 5, lost 4, timeout 3
deep_flank_away           3000  0.25  0.37   1.8   1108  gave_up 6, lost 3, lost_track 3
deep_flank_90             1000  0.25  0.40   2.7   1068  gave_up 6, lost 3, lost_track 3
deep_flank_90             2000  0.08  0.25   2.0   1147  gave_up 4, lost 1, lost_track 6, timeout 1
deep_flank_90             3000  0.00  0.06   1.2    984  gave_up 5, lost_track 6, timeout 1
deep_sprint_then_creep    1000  0.83  0.94   4.8   1173  lost 10, timeout 2
deep_sprint_then_creep    2000  0.83  0.88   4.8   1309  lost 10, timeout 2
deep_sprint_then_creep    3000  0.33  0.49   2.8    999  gave_up 1, lost 4, lost_track 5, timeout 2
knuckle                   1000  0.00  0.17   6.8   1796  gave_up 1, timeout 11
knuckle                   2000  0.17  0.39   5.8   1618  gave_up 1, lost 2, timeout 9
knuckle                   3000  0.00  0.14   4.8   1505  gave_up 4, lost_track 2, timeout 6

## veteran, PROPOSED rules, found inside, 3 escorts, sonar 3600 m, leash 15 km / 60 min, blind x2.5, baffle 40 deg, area 25 m + 50 m/km, shadows
recipe                   range  lost   dmg  runs  t_end  how it ended
sit                       1000  1.00  1.00   1.0    124  lost 12
sit                       2000  1.00  1.00   1.0    242  lost 12
sit                       3000  1.00  1.00   1.0    339  lost 12
deep_sit                  1000  0.75  0.96   5.3   1168  lost 9, timeout 3
deep_sit                  2000  0.92  1.00   4.8   1136  lost 11, timeout 1
deep_sit                  3000  0.92  0.98   4.4   1185  lost 11, timeout 1
deep_creep_away           1000  0.75  0.95   5.2   1260  lost 9, timeout 3
deep_creep_away           2000  0.75  0.98   4.2   1160  lost 9, timeout 3
deep_creep_away           3000  0.83  0.95   4.7   1409  lost 10, timeout 2
deep_flank_away           1000  0.58  0.79   5.2   1654  lost 7, timeout 5
deep_flank_away           2000  0.58  0.81   4.3   1593  lost 7, timeout 5
deep_flank_away           3000  0.50  0.71   3.5   1588  lost 6, timeout 6
deep_flank_90             1000  0.42  0.71   3.8   1501  lost 5, timeout 7
deep_flank_90             2000  0.42  0.73   3.5   1639  lost 5, timeout 7
deep_flank_90             3000  0.25  0.64   2.8   1639  lost 3, timeout 9
deep_sprint_then_creep    1000  0.92  0.98   4.2   1000  lost 11, timeout 1
deep_sprint_then_creep    2000  0.67  0.91   5.0   1352  lost 8, timeout 4
deep_sprint_then_creep    3000  0.83  0.94   4.0   1249  lost 10, timeout 2
knuckle                   1000  0.42  0.62   5.2   1406  lost 5, timeout 7
knuckle                   2000  0.25  0.48   5.8   1630  lost 3, timeout 9
knuckle                   3000  0.50  0.65   4.8   1452  lost 6, timeout 6
```
