# Archetype stories: how a hunt should go (imagined, 2026-11-01)

Five stories, one per player archetype from #37, written **by hand from the agreed rules**, not
from the sim. They are the specification: once agreed, the study gets one scripted recipe per
archetype and the sim has to reproduce their shape; the parameter sheet is written from what
they need. Numbers are computed from the rules below and rounded; treat them as +-10 %.

## The rules the stories use

All from `docs/ESCAPE_BALANCE.md` sections 3.1, 7 to 10, as decided on #34 and #37:

- **Effective reach** per ping, `R_eff = 3,000 m x f_aspect x f_speed x f_layer x f_set`,
  zero in a noise shadow. `f_aspect` = 0.4 + 0.6 |sin(aspect)| (beam 1.0, end-on 0.4);
  `f_speed` 0.7 at 2.5 kn or less; `f_layer` 0.5 below the thermocline, which lies at **70 m**
  in these hunts; `f_set` 1.0 settled, 0.5 in a hard turn, 0.25 sprinting, 0 settling (20 s).
  An echo comes back inside `R_eff`, outside the blind zone (3 x depth, at least 150 m) and the
  baffles (50 deg either side of the stern), sure inside 40 % of `R_eff`, with a chance
  falling to zero at `R_eff`.
- **Ring** of a fix: 25 m + 150 m x (d / R_eff). A sighting or radar contact is exact.
- **Shadows**: friendly ships (150 m + 30 m/kn noise radius), the **explosion cloud** of a
  pattern (150 m radius, 3 min), a destroyer's own wake and baffles.
- **Attack**: the hunter steers for the predicted position (least-squares track through the
  last 45 s of fixes) at 14 kn inside 1.5 km, 20 kn beyond; a run starts within 150 m of the
  prediction; six charges released as the ship reaches each aim point; **depth bands** shallow
  15 to 40 m, medium 40 to 80 m, deep 80 to 150 m; the first band comes from the opening
  (sighting: shallow), the band moves on after a pattern that did under 10 % damage; the rack
  reloads in 120 s. *New rule the stories needed:* a hunter whose fix is 60 to 180 s old still
  attacks the dead-reckoned position once (a "datum attack") before it searches.
- **Search**: box around the last prediction, 400 m widening 1 m/s, 12 kn; `track lost` after
  300 s without a fix; the leash (10 km from the convoy) and 30 min are the backstop.
- **Boat**: dive 1 m/s; 7.6 kn flank, 5.7 kn AHEAD FULL, 3.8 kn HALF, 1.9 kn SLOW; the
  periscope raised or lowered by order (lowered: invisible to lookouts, blind); **safe depth**
  = 150 m x (1 - damage), below it the hull loses 1 % per 10 s for every 20 m of excess.
- **Convoy**: a sighting, a sonar fix or an observed torpedo alerts the merchants within 8 km;
  they run directly away from the datum (a torpedo: away from its line) at 11 kn, zigzagging
  +-30 deg every 90 s, for 600 s after the last alarm, then resume their route at 8 kn. One
  escort hunts, the other screens between the convoy and the datum.

## The common opening (stories 2 to 5)

`patrol`, day. Three merchants (freighter-1, tanker-2, freighter-3) steam east at 8 kn;
destroyer-1 is 1.2 km ahead of the convoy centre, destroyer-2 1.5 km off its starboard beam.
The boat, undamaged, battery 85 %, is at periscope depth with the scope up, heading 090 at
2 kn, working into a firing position: 1,500 m from destroyer-1, which bears 045 from it (the
boat is on destroyer-1's port quarter). At 0:03 destroyer-1's lookouts have held the feather
for 3 s: `destroyer-1 sighted our periscope`. The fix is exact, the depth band shallow.
destroyer-1 turns toward it at 14 kn (inside 1.5 km it does not sprint), destroyer-2 moves to
screen between the convoy and the boat, the merchants turn away to the north-east at 11 kn.

Columns as agreed: time; boat (depth, telegraph, speed, scope); hunter (state, speed); range
and the boat's bearing off the hunter's bow; boat does; hunter does; the hunter's sonar; the
hunter's track on the boat.

---

## Story 1, top-notch: the torpedo as a lure (own opening)

Convoy as above. The boat has been ahead of the convoy for an hour and sits 3.0 km east and
1.5 km north of the convoy centre (on the port bow of the lead ship), periscope depth, scope
down, 2 kn, battery 85 %. The player's plan: fire one long torpedo at the lead freighter from
here; the escorts will get the torpedo's line and sweep it *away* from the convoy toward this
point; the merchants will run away from the line, splitting north and south, for ten minutes,
then resume east on tracks displaced 3.4 km; destroyer-2 will screen toward the line. The
southern pair's resumed track will pass a point 4 km east and 3.4 km south of the present
convoy centre at about minute 26, with no escort on that side. The boat will be there.

**Outcome:** never pinged; tanker-2 torpedoed at 27:10 from 800 m; battery 60 %; the hunt that
follows starts with the escorts 2 to 3 km away and the boat already under the layer.

| time | boat | hunter (destroyer-1) | range / bearing | boat does | hunter does | hunter's sonar | hunter's track on the boat |
|---|---|---|---|---|---|---|---|
| 0:00 | 12 m, SLOW 2.0 kn, scope down | formation 12 kn | 2,300 m / 150 deg | raises the scope; freighter-1 at 3,300 m, 8 kn, AOB 80 | - | none (not hunting) | - |
| 0:10 | 12 m, scope up | formation | 2,300 | fires one G7e along 247, run 3,300 m, 215 s; scope down | - | - | - |
| 0:15 | 14 m, FLANK 1.2 kn, heading 168 | formation | 2,290 | orders 90 m, rings AHEAD FLANK, turns to 168 (south-south-east, toward the ambush point) | - | - | - |
| 1:50 | 90 m... (at 1:23 reaches 90 m, below the layer), FLANK 7.6 kn | alarm | 2,600 / 160 deg | - | hears the torpedo at 1,200 m: `destroyer-1 heard torpedo 1`; CPA 400 m, no comb; the **line** (track 247, origin within 5 km) is the datum; split: destroyer-1 hunts, destroyer-2 screens toward the line; merchants run away from the line, freighter-1 north, tanker-2 and freighter-3 south | - | line datum, 5 s old |
| 2:00 | 90 m, FLANK | sprint 20 kn | 2,700 / 165 deg | - | steers for the line 1 km east of the convoy, to sweep it outward (east-north-east) | no echo: sprinting (R_eff x0.25; and the boat is end-on, below the layer) | line |
| 3:45 | 90 m, FLANK | sweeping the line 14 kn | 3,100 / 170 deg | - | on the line, slows to 14 kn, pings both sides as it sweeps toward the origin | no echo: out of reach (end-on, flank, below layer: 600 m) | line |
| 3:45 | - | - | - | the torpedo passes 60 m astern of freighter-1, which turned away at 1:55: `torpedo 1 missed` | - | - | - |
| 8:00 | 90 m, FLANK, 1.9 km south-south-east of the firing point | sweeping 14 kn | 2,000 / 165 deg | - | reaches the firing point (the line's likely origin, 3 km out), box search 400 m around it | no echo: out of reach (600 m) | line, search box |
| 10:00 | 90 m, FLANK | searching 12 kn | 2,500 / 170 deg | - | box 520 m; nothing | no echo | - |
| 10:00 | - | - | - | - | the merchants' 600 s are up: freighter-1 resumes east 3.4 km north of the old track, tanker-2 and freighter-3 resume east 3.4 km south of it, 8 kn, no zigzag; destroyer-2 holds its screen toward the line (north-east of the southern pair) | - | - |
| 13:00 | 90 m, FLANK | searching 12 kn | 3,600 | - | box 700 m; `destroyer-1 lost the track` (no fix since the alarm, 300 s of search), stands down, returns at 12 kn to its station 1.2 km ahead of the convoy centre, which lies between the two groups, 1.7 km north of the southern pair | - | - |
| 21:00 | 90 m, SLOW 1.9 kn | formation, 3.5 km north-west of the boat | 3,500 / 100 deg | reaches the ambush point (4.0 km east, 3.4 km south of the old centre), slows, turns to 000 (bow to the southern pair's track) | - | no echo: out of reach (beam-on to destroyer-1 now, creeping, below the layer: 1,050 m) | - |
| 24:00 | 12 m, SLOW, scope down | formation | 3,200 / 95 deg | comes up to periscope depth, scope down; hydrophones: two sets of screws bearing 270, closing | - | - | - |
| 26:30 | 12 m, scope up 15 s | formation | 3,000 | tanker-2 at 1,100 m, AOB 85, 8 kn; freighter-3 800 m beyond; destroyer-2 2.6 km north-east, stern-on; solution: fire later | - | destroyer-2 sees nothing: 2.6 km, periscope range 1.5 km | - |
| 27:10 | 12 m, scope up | formation | 2,900 | fires two G7e at tanker-2 at 800 m, track angle 88; scope down; orders 90 m, FLANK, turns to 135 (stern to destroyer-2) | - | - | - |
| 27:45 | 45 m, FLANK | alarm, sprint 20 kn | 2,900 | - | both torpedoes hit: `tanker-2 sunk, 9,000 GRT`; torpedo datum line through the boat's position; destroyer-1 and destroyer-2 both 2.5 to 3 km away; the escape chapter begins with the boat already crossing the layer, end-on to both | no echo: sprinting | line |

**What decided it.** The player used four predictable facts: an observed torpedo gives the
escorts its line and the hunter sweeps it outward; merchants run away from the line for exactly
600 s and resume their route displaced; the screen stands toward the datum; a hunter searches
the likely firing point and gives up after 300 s. All four must be visible to the player (the
line and the hunter's intention on the HUD, the merchants' turn-away on the map) for the plan
to be plannable. The boat's run under the layer, end-on to the sweep, was never inside
`R_eff`. Cost: 21 min at flank, a quarter of the battery.

---

## Story 2, veteran: lose the hunter, then follow it home

**Outcome:** never damaged; `track lost` at 6:10; battery 72 %; follows destroyer-1 back in
its wake and resumes the attack on the convoy's rear 20 minutes later.

| time | boat | hunter (destroyer-1) | range / bearing | boat does | hunter does | hunter's sonar | hunter's track on the boat |
|---|---|---|---|---|---|---|---|
| 0:03 | 12 m, SLOW 2.0 kn, scope up, heading 090 | closing 12 -> 14 kn | 1,500 m / 135 deg | - | sights the feather: exact fix, band shallow; turns to 225; merchants run north-east; destroyer-2 screens | visual: periscope seen | exact, 0 s, shallow |
| 0:05 | 12 m | closing 14 kn | 1,490 | scope down; orders 90 m; rings AHEAD FLANK; rudder starboard to 135 (across the hunter's bearing, deliberately: a track for the hunter to believe) | - | no echo: faint echo missed (aspect 45 deg, creeping: R_eff 1,720 m, 21 % at 1,490 m) | exact, 2 s |
| 0:30 | 37 m, FLANK 6.5 kn, heading 135 | closing 14 kn | 1,350 / 10 deg | - | - | echo (beam-on, moving: R_eff 3,000 m, 92 %); ring 90 m | fix 0 s, ring 90 m |
| 1:00 | 67 m, FLANK 7.6 kn | closing 14 kn | 1,150 / 5 deg | - | three fixes: track 135 at 7 kn; steers for the prediction | echo, ring 85 m | fix 0 s, course 135 / 7 kn |
| 1:03 | 70 m | - | - | crosses the layer | - | - | - |
| 1:05 | 72 m, FLANK | closing | 1,120 | rudder port to 220 (stern to the hunter); rings AHEAD SLOW | - | echo, ring 80 m | fix 0 s |
| 1:15 | 82 m, SLOW 4.5 kn (slowing), heading 205 | closing 14 kn | 1,060 / 8 deg | - | loses the echo: faint (end-on, moving, below the layer: R_eff 600 m) | no echo: out of reach (600 m) | fix 10 s |
| 1:23 | 90 m, SLOW 1.9 kn, heading 220 | closing | 1,020 | reaches 90 m; from here R_eff against a settled set is 420 m | - | no echo: out of reach (420 m) | fix 18 s |
| 2:05 | 90 m, SLOW | closing 14 kn | 700 / 30 deg | - | fix 60 s old: **datum attack**, keeps steering for the prediction (which runs on at 135 / 7 kn for 90 s, then stops) | no echo: out of reach | fix 60 s, prediction 135 / 7 kn |
| 2:40 | 90 m, SLOW | dropping 14 kn | 420 / 80 deg | - | run 1 on dead reckoning: shallow band 15 to 40 m, 6 charges, 410 m from the boat | no echo | fix 95 s |
| 2:50 | 90 m | turning hard | 450 / 120 deg | keeps the pattern's cloud between itself and the hunter (the cloud is 150 m wide for 3 min) | pattern bursts 15 to 40 m, nearest 410 m: nothing | no echo: boat behind the cloud | fix 105 s |
| 3:50 | 90 m, SLOW, heading 220 | searching 12 kn | 520 / 95 deg | - | settled; box search 400 m around the prediction | no echo: boat behind the cloud | fix 2:45 old |
| 4:30 | 90 m | searching | 380 / 40 deg | turns 15 deg to stay stern-on to the leg | the south-west leg passes 380 m from the boat: R_eff 420 m, 16 % per ping, two pings: nothing | no echo: faint echo missed (16 %) | fix 3:25 old |
| 5:30 | 90 m | searching | 620 / 170 deg | - | next leg: the boat is astern of the hunter | no echo: boat in the baffles astern | fix 4:25 |
| 6:10 | 90 m, SLOW | formation 12 kn | 900 / 150 deg | - | `escorts lost the track` (300 s without a fix): stand down; destroyer-1 turns north-east for its station | - | - |
| 6:20 | 90 m -> 14 m | returning 12 kn | 850 | orders 14 m, rings AHEAD FULL, steers for destroyer-1's wake | - | - | - |
| 7:36 | 14 m, FULL 5.7 kn, scope down | returning 12 kn | 500 / 178 deg | sits in the wake, dead astern | destroyer-2, 2.5 km to the east, pings: the boat is behind destroyer-1's noise (510 m radius at 12 kn, 11 deg half-angle at 2.5 km) | destroyer-1: no echo: boat in the baffles astern; destroyer-2: no echo: behind destroyer-1's noise | - |
| 10:00 | 14 m -> 90 m | returning, 1.8 km ahead | 1,800 / 179 deg | destroyer-1 has drawn ahead; the wake sector is thinning (16 deg): orders 90 m, rings AHEAD SLOW, holds course toward the convoy's track | - | destroyer-2: no echo: out of reach (end-on, creep, below layer: 420 m) | - |
| 25:00 | 12 m, SLOW, scope up 10 s | formation, 4 km north-west | 4,000 | the convoy resumed east at 15:00; its spread put freighter-3 1.8 km behind the others: the attack resumes on freighter-3 from its quarter | - | - | - |

**What decided it.** Three moves inside the first 80 seconds: a short run *across* the
hunter's bearing to give it a track to believe, then stern-on, slow and under the layer before
the hunter came within 1,100 m; `R_eff` fell from 3,000 m to 420 m while the hunter was still
closing, so it attacked a dead-reckoned point 400 m off. After that the cloud, the boat's own
aspect and the baffles kept it hidden through the box search. The follow-back works because the
escort's wake is a shadow and its baffles are deaf: a boat at periscope depth with the scope
down, dead astern, is invisible to its own escort and to the other one. Numbers worth tuning
from this story: the 16 % leg (two unlucky pings would have made it an *average* story), and
the fact that a boat at 150 m under the layer, end-on and creeping would have been unpingable
by one set at any range (blind zone 450 m > `R_eff` 420 m): deep + model 1 overlap and the
blind zone probably wants a cap (say 300 m).

---

## Story 3, average: trial and error, the attack interrupted

**Outcome:** `track lost` at 14:10 with 33 % hull damage and the convoy 5 km away; the
attack must be set up again. In a second roll of the 7:30 ping it is a lost boat.

| time | boat | hunter (destroyer-1) | range / bearing | boat does | hunter does | hunter's sonar | hunter's track on the boat |
|---|---|---|---|---|---|---|---|
| 0:03 | 12 m, SLOW 2.0 kn, scope up | closing 14 kn | 1,500 m / 135 deg | - | sights the feather: exact fix, band shallow | visual | exact, shallow |
| 0:08 | 12 m | closing | 1,480 | orders 60 m (the `C` order; the layer at 70 m is unknown to this player); rings AHEAD FLANK; rudder to 315 (90 deg off the hunter's bearing, beam-on) | - | echo (R_eff 1,720 m: 23 %): a lucky one; ring 150 m | fix 0 s, ring 150 m |
| 0:40 | 44 m, FLANK 7.6 kn, heading 315 | closing 14 kn | 1,300 / 15 deg | - | fixes every ping (beam-on, moving: 3,000 m), track 315 / 7.5 kn | echo, ring 90 m | fix 0 s, course 315 / 7.5 kn |
| 0:56 | 60 m | closing | 1,200 | reaches 60 m, above the layer | - | echo | - |
| 2:30 | 60 m, FLANK | dropping 14 kn | 160 / 5 deg | - | run 1: shallow band 15 to 40 m, on a good track | no echo: under the keel (180 m) | fix 5 s, ring 35 m |
| 2:42 | 60 m | turning | 90 | - | bursts 15 to 40 m, nearest 28 m off the hull, 20 m above: hull 0 -> 8 %; cloud | no echo: under the keel | fix 17 s |
| 2:50 | 60 m, FLANK | turning hard | 150 / 150 deg | reads `pattern set 15-40 m` and the ring: orders 100 m, rings AHEAD HALF, holds 315 | - | no echo: baffles | fix 25 s |
| 3:30 | 100 m, HALF 3.8 kn | searching 12 kn (fix 65 s) | 420 / 160 deg | crossed the layer at 3:00 | box search from the prediction | no echo: baffles, then out of reach (end-on by luck, moving, below layer: 600 m... the boat is on 315, the hunter astern: stern-on) | fix 65 s |
| 4:40 | 100 m, HALF | closing 14 kn | 380 / 20 deg | - | the north leg brings the hunter onto the boat's quarter: aspect 60 deg, below layer, 3.8 kn: R_eff 1,300 m; echo, ring 70 m; track 315 / 3.8 kn | echo | fix 0 s, ring 70 m |
| 5:10 | 100 m | dropping 14 kn | 150 | - | run 2: band moves to medium 40 to 80 m (run 1 did under 10 %) | no echo: under the keel (300 m) | fix 10 s |
| 5:25 | 100 m | turning | 120 | - | bursts 40 to 80 m, nearest 25 m off horizontally but 20 to 60 m above: hull 8 -> 9 %; cloud | no echo | fix 25 s |
| 5:30 | 100 m, HALF | turning | 150 / 140 deg | the burst depths read 40 to 80: *they are coming down to me*; tries the other thing: rings AHEAD SLOW, turns 180 deg to 135 (stern to the hunter's turn) | - | no echo: baffles | - |
| 7:30 | 100 m, SLOW 1.9 kn, heading 135 | searching 12 kn | 300 / 30 deg | - | a leg passes 300 m off: end-on, creeping, below layer: R_eff 420 m, 48 %: **echo**, ring 130 m | echo | fix 0 s, ring 130 m |
| 7:45 | 100 m | closing 14 kn | 250 | - | two more fixes, rings 120 m: a poor track, 110 / 2 kn | echo | course 110 / 2 kn (rough) |
| 8:30 | 100 m | dropping 14 kn | 140 | - | run 3: band deep 80 to 150 m | no echo: under the keel | fix 10 s |
| 8:55 | 100 m | turning | 100 | - | bursts 80 to 150 m: the two set at 95 and 110 m fall 35 m off the hull: hull 9 -> 33 %; safe depth now 100 m | no echo | - |
| 9:00 | 100 m, SLOW | turning | 130 / 160 deg | `hull damage 33 %, safe depth 100 m` on the HUD: orders 90 m, keeps 135, stern-on, cloud between | - | no echo: behind the cloud | - |
| 11:00 | 90 m, SLOW | searching 12 kn | 480 / 150 deg | - | box 400 to 500 m; legs pass 450 and 520 m: beyond 420 m | no echo: out of reach (420 m) | fix 3:15 old |
| 14:10 | 90 m, SLOW | formation 12 kn | 1,100 | - | `escorts lost the track`; destroyer-1 returns to the convoy, now 5 km north-east | - | - |

**What decided it.** The player learned the rules one pattern at a time, which is what the
HUD and the log are for (the set depth of each pattern, the ring, the safe depth). Two things
cost the hull: diving to 60 m above an unknown layer, and running beam-on for two minutes.
The hunt turned on one ping at 7:30 (48 %): with a second echo the track would have been good
and run 3 would have fallen 10 m off instead of 35. That is the 50 / 50 the archetype asks
for. The attack is over for now: the convoy has 5 km and 14 minutes.

---

## Story 4, reckless: stays up to fight

**Outcome:** boat lost at 2:50.

| time | boat | hunter (destroyer-1) | range / bearing | boat does | hunter does | hunter's sonar | hunter's track on the boat |
|---|---|---|---|---|---|---|---|
| 0:03 | 12 m, SLOW 2.0 kn, scope up | closing 14 kn | 1,500 m / 135 deg | - | sights the feather: exact fix, shallow | visual | exact |
| 0:10 | 12 m, scope up | closing | 1,460 | rudder to 045: bow to the destroyer, selects it (`TGT destroyer-1`, AOB 0) | - | visual: the scope is up; a fix every frame | exact |
| 1:10 | 12 m, STOP, heading 045 | closing 14 kn | 950 / 0 deg | fires one G7e down the throat | - | visual | exact |
| 1:15 | 12 m | evading | 920 | - | `destroyer-1 heard torpedo 1`: after 5 s turns hard to comb the track at full speed | - | - |
| 1:48 | 12 m | evading 20 kn | 700 / 30 deg | - | the torpedo passes 90 m off its side: `torpedo 1 missed`; swings back onto the boat | visual | exact |
| 2:00 | 12 m, scope up | closing 14 kn | 600 / 5 deg | fires a second torpedo; `GLANCE` warning on the panel (track angle 10 deg) | - | visual | exact |
| 2:35 | 12 m | dropping 14 kn | 150 | - | run 1: shallow band 15 to 40 m, on an exact track (the scope has been up the whole time) | visual, then under the keel | exact |
| 2:40 | 12 m | - | 100 | - | the second torpedo glances off the bow (10 deg): no detonation | - | - |
| 2:50 | 12 m | - | - | **boat lost** | bursts 15 to 40 m: the first charge, set 15 m, 6 m off the hull | - | - |

**What decided it.** The scope stayed up: the hunter never needed its sonar. The `comb`
evasion (#22) and the glance rule made the down-the-throat shot a coin toss at best; the
first pattern, set shallow on an exact fix, needs no second try. Nothing in the proposal
changes this story and nothing should.

---

## Story 5, panic: deeper and deeper

**Outcome:** boat lost at 12:55 (45 % from the third pattern at 10:40, the rest from the sea
below the safe depth); battery 71 %.

| time | boat | hunter (destroyer-1) | range / bearing | boat does | hunter does | hunter's sonar | hunter's track on the boat |
|---|---|---|---|---|---|---|---|
| 0:03 | 12 m, SLOW 2.0 kn, scope up | closing 14 kn | 1,500 m / 135 deg | - | sights the feather: exact fix, shallow | visual | exact |
| 0:05 | 12 m | closing | 1,490 | scope down; orders 150 m; rings AHEAD FLANK; rudder to 225 (straight away from the hunter) | - | no echo: faint echo missed (stern-on 0.4, creeping 0.7: R_eff 840 m, nothing at 1,490 m) | exact, 2 s |
| 1:00 | 67 m, FLANK 7.6 kn, heading 225 | closing 14 kn | 1,330 / 0 deg | - | the exact fix is a minute old and the boat was last seen heading 090 at 2 kn: the prediction is wrong by 250 m already | no echo: out of reach (stern-on, flank, above the layer: 1,200 m) | fix 57 s |
| 1:03 | 70 m | - | - | crosses the layer; R_eff against a settled set now 600 m | - | no echo: out of reach (600 m) | - |
| 2:05 | 130 m, FLANK | closing 14 kn | 1,100 / 2 deg | - | datum attack on the sighting point and the 090 / 2 kn track: run 1, shallow band, 1,100 m from the boat; cloud | no echo | fix 2:02 |
| 2:18 | 150 m, FLANK | turning | 1,150 | reaches 150 m (safe depth 150 m: no groaning yet); keeps 225 at flank: 235 m a minute, straight | - | no echo | - |
| 3:30 | 150 m, FLANK | searching 12 kn | 1,300 / 10 deg | - | box search around the sighting: the boat's wake noise... no: the hunter has only the sonar, and `R_eff` is 600 m: nothing | no echo: out of reach (600 m) | fix 3:27 |
| 5:00 | 150 m, FLANK | searching 12 kn | 2,000 | - | the box has widened to 490 m; the boat is 2 km down its straight line | no echo | fix 5:00: **track lost**? no: the sighting's 300 s run out at 5:03 and destroyer-1 stands down... | - |

*Stop.* Written straight from the rules, the panic flight **escapes**: stern-on at flank under
the layer is 600 m of reach, the hunter never gets within it, and the straight line is never
tested because nothing is tracking it. That is the story the rules as written tell, and it is
the one you said must never end well. Two readings:

1. **The straight line is the tell, and someone must be reading it.** The second escort.
   destroyer-2, screening 2 km north-east, has the boat *beam-on* (the boat runs 225, destroyer-2
   bears 045 from it): `R_eff` = 3,000 x 1.0 x 1.0 x 0.5 = 1,500 m above... below the layer; at
   2.5 to 3.5 km it never hears it either. So within the rules only a hunter *ahead of* the boat
   on its line would hear it, and none is there.
2. **Speed must cost the stern-on bonus.** Historically a boat at flank was loud enough to be
   heard on the hydrophones regardless of aspect; the sonar's aspect rule applies to the *echo*,
   not to the boat's own noise. A `f_speed` above 1.0 at flank (say 1.5, on the hydrophone
   rather than the echo) gives 900 m above and 450 m below... still not enough against a hunter
   1.5 km behind.

So the panic flight is beaten not by detection but by **being led**: the hunter must assume
the boat ran straight from the sighting at its best speed when it has no echo, and attack
*that* point, not the sighting. A **"blind lead" rule**: with no fix for 60 s, the hunter's
prediction is the boat's last known position carried along the boat's last known course *or*,
if the first run found nothing, along the bearing *away from the hunter at 7 kn* (the panic
assumption), and the datum attacks and the search box follow that assumption. With it the story
continues:

| time | boat | hunter (destroyer-1) | range / bearing | boat does | hunter does | hunter's sonar | hunter's track on the boat |
|---|---|---|---|---|---|---|---|
| 2:30 | 150 m, FLANK, heading 225 | closing 14 kn | 1,150 / 0 deg | - | run 1 found nothing: assumes a boat running straight away at 7 kn from the sighting (the panic assumption), sprints to 20 kn down the bearing 225 | no echo: sprinting | assumed track 225 / 7 kn |
| 5:00 | 150 m, FLANK | closing 14 kn | 600 / 0 deg | - | closes the assumed point; slows to 14 kn, settles at 5:20 | no echo: out of reach (600 m) and then under the keel (450 m) | assumed |
| 5:40 | 150 m, FLANK | dropping 14 kn | 420 / 0 deg | - | datum attack 2 on the assumed point: band medium 40 to 80 m; the aim points are 195 m ahead of the boat (50 s sink time at 7 kn): the charges fall 30 m off the boat's line but 70 to 110 m above it | no echo: under the keel | assumed, 5 s |
| 6:30 | 150 m, FLANK | turning | 300 / 150 deg | holds flank and 225 | bursts 40 to 80 m: nothing; cloud; the hunter overruns, turns | no echo: baffles | - |
| 8:30 | 150 m, FLANK | closing 14 kn | 500 / 0 deg | - | the assumption still holds (nothing else to go on): runs down 225 again, to the point the boat reaches at 10:30 | no echo | assumed |
| 10:30 | 150 m, FLANK | dropping 14 kn | 400 / 0 deg | - | datum attack 3: band deep 80 to 150 m, aimed 195 m ahead; the straight-running boat arrives under the sinking charges | no echo: under the keel | assumed |
| 10:40 | 150 m | turning | 150 | - | bursts 80 to 150 m: the ones set 130 and 145 m fall 18 and 25 m off the hull: hull 0 -> 45 %; **safe depth now 82 m** | no echo | - |
| 10:50 | 150 m, FLANK | - | 300 / 160 deg | `hull groaning at 150 m, safe depth 82 m`: the player holds depth and flank | the hull loses 1 % per 10 s per 20 m of excess: 68 m over, 3.4 % per 10 s | no echo: baffles | - |
| 12:55 | 150 m | searching | 700 | **boat lost**: the sea finished what the pattern started | - | - | - |

**What decided it.** Not the sonar: the boat at 150 m, stern-on, under the layer, was out of
reach of a single settled set the whole way. It was led: a hunter with nothing to go on assumes
the straight flight and attacks along it, and a boat that never turns is where the assumption
says it is. The depth bands reached the deep band on the third pattern; one near miss made
150 m a place the hull could not stay. The player could read every step (`set 40-80 m`, `set
80-150 m`, `hull groaning`) and did nothing with it. **Rule needed:** the blind lead (the
hunter's assumption when it has no echo); without it this archetype wins.

---

## Rules the stories needed that are not yet on the list

1. **Datum attack**: a hunter whose fix is 60 to 180 s old attacks the dead-reckoned position
   once before searching (stories 2, 5).
2. **Blind lead**: when a datum attack finds nothing and there is no echo, the hunter assumes
   the boat is running straight away from it at 7 kn and leads that (story 5). This is what
   makes the panic flight fail; it also makes "turn after every pattern" the right habit.
3. **Blind zone cap**: at 150 m the 3 x depth blind zone (450 m) exceeds a quiet boat's `R_eff`
   (420 m); a cap around 300 m keeps deep from being absolute (story 2).
4. **The layer on the HUD** only once the boat has crossed it (story 3's player did not know it
   was there). A thermometer reading at the depth gauge.
5. **The hunter's intention** as a state the HUD and log show: `hunting`, `sweeping the
   torpedo track`, `searching`, `returning` (story 1 is unplannable without it).
6. **Alerted merchants resume their route** after 600 s on a track displaced by their run
   (today they do; story 1 relies on it being predictable, which it is).

## Numbers the stories put a finger on

| number | value used | why it matters |
| --- | --- | --- |
| `f_aspect` end-on | 0.4 | sets the veteran's 420 m; at 0.5 it is 525 m and story 2's 16 % leg becomes 30 % |
| `f_layer` | 0.5 | with it, deep + end-on + creep is below the blind zone; without it 840 m and the veteran needs the cloud every time |
| cloud | 150 m, 3 min | covers one box leg; 2 min would not |
| datum attack age | 180 s | 120 s and story 2's run 1 does not happen at all |
| blind lead speed | 7 kn | the panic assumption; a boat at HALF (3.8 kn) is led wrong by 100 m a minute, which is the *average* player's accidental defence |
| safe depth damage | 1 % / 10 s per 20 m | story 5 dies in 2 min at 150 m with 45 % damage; 0.5 % and it has 4 min to think |
