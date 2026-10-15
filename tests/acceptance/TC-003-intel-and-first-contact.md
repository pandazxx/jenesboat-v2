---
id: TC-003
title: The hunt starts with an intel report and the group is sighted far away
issue: 14
added_in: 15
---
## Preconditions

Open the build URL in a desktop browser; wait until the HUD shows `TUBES 4/4` and the message
line `BdU: 3 merchants reported bearing NNN, NN km, course ~NNN` at the bottom left.

## Steps

1. Press `-` twice (zoom out to 40 m/px; the `1 km` scale bar at the bottom left shrinks).
2. Press `4` (time x8). Press `W` four times (`AHEAD FLANK`); use `A`/`D` (then `Q`) to turn
   so that `HDG` equals the reported bearing.
3. Wait (about a minute real time) while the boat closes the reported position.

## Expected

- The contact panel (top right) reads `no contact` at the start, followed by
  `intel: bearing NNN, NN.N km` and `course ~NNN`. While the reported position is off screen an
  orange arrow sits on the edge of the map area pointing toward it with the same bearing/range
  text; once it is on screen (zoom out to 40 m/px, or close in) the arrow is replaced by a
  blurred orange disc (2 km radius, the uncertainty of the report) with a tick showing the
  reported course.
- The bearing/range on the arrow update as the boat moves.
- When the group is about 12 km away a message `<ship>: sighted NNN` appears per ship, grey hull
  boxes with wakes appear on the map, and the panel shows the nearest one:
  `TGT <id>`, `BRG`, `RNG` in km, `CRS`, `SPD` in kn and `AOB`.
- The sighting position is within a few km of the intel position and the ships' course is within
  about 15 degrees of the reported course. Once a ship is held (in sight or on the
  hydrophones) the disc and arrow disappear; if all contact is lost again (e.g. go deep at
  more than 4 kn), the arrow or disc comes back as `LAST SEEN <ship>` at where that ship should
  be now on its last course and speed.

## Automated

`tests/test_scenario.py` checks the intel error bounds; `tests/test_world.py` the contact
events.
