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
3. Hold `W` until `SPD` is above 4 kn.
4. Release `W`, press `S` until `THR 0.00`, wait for `SPD` to drop below 4 kn.

## Expected

- After step 1 the panel reads `hydrophone: 3 contact(s)` with one bearing per ship, a message
  `<ship>: hydrophone bearing NNN` appears per ship, and dashed green lines run from the boat
  along each bearing. No hull boxes (the ships are far beyond periscope range).
- During step 3 the lines and the panel entries disappear (`contact lost` messages): own noise
  masks the hydrophones above 4 kn.
- After step 4 they come back.
- On the surface (`Space` again) there are no hydrophone contacts.

## Automated

`tests/test_world.py::test_contacts_visual_then_hydrophone_then_none`.
