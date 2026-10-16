---
id: TC-004
title: Hydrophones give a bearing-only contact when slow at periscope depth or deeper
issue: 12
added_in: 15
---
## Preconditions

A fresh hunt (`R`), boat stopped (`THR +0.00`, `SPD 0.0 kn`), no visual contact.

## Steps

1. Press `Space` and wait until `DEPTH 12.0 m` and `PERISCOPE`.
2. Watch the map and the contact panel.
3. Press `W` three times (`AHEAD FULL`, 5.7 kn submerged) and wait for `SPD` above 4 kn.
4. Press `S` until `STOP`, wait for `SPD` to drop below 4 kn.

## Expected

- After step 1 a message `<ship>: hydrophone bearing NNN` appears per ship; dashed green lines
  run from the boat along each bearing and a faint green ghost hull sits at the end of each
  (the operator's estimate of position, course and speed). The panel shows the nearest as
  `SONAR <id>` with bearing, range, course and speed and the note that the periscope is needed
  to shoot: no fire-control markers on a sonar contact.
- During step 3 the lines, ghosts and panel entries disappear (`contact lost` messages): own
  noise masks the hydrophones above 4 kn.
- After step 4 they come back.
- On the surface (`Space` again) there are no hydrophone contacts.

## Automated

`tests/test_world.py::test_contacts_visual_then_hydrophone_then_none`.
