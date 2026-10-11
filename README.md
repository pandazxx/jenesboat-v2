# jenesboot-v2

This is a 2d submarine hunting simulation game. The background is set on WWII. The player controls the submarine searching and hunting enemy ships in the open ocean.
The submarine must leverage it's stealth, limited speed and fire power to deal maxiumn damage to enemy naval power and economic.
The major enemy ship types are merchant and military ships. They offen comes in fleets, with military ships escorting the merchant ships to their destination.

## Key factors

- Submarine depth: affects
  * submarine speed
  * periscope availability
  * visibility of both sides (different visibility for surface vessels and submarines)
  * submarine weapon availability
  * weapon damage to the submarine
- Day / night: affects the visual visiblity of both sides
- Submarine battery: how long can submarine stay submerged
- Propeller speed: affects visibility

## Controls

- All vessels (including both player and enemy ships) use classic ship maneuver, accelerate / decelerate by propeller, turn by rudder.
- Different types of vessels have different maneuver parameters
- Player uses WASD to control submarine's propeller and rudder. Another key to controll submerging / emerging.


## Weapons

- Deck gun: equiped by enemy military ships and submarine. Can only fire on surface.
- Depth charges: equiped by enemy military ships.
- Torpedo: equiped by submarine. Can be fired on submerged or emerged status. Once fired, keep it's speed and course.


## Art style

- Simplest 2d lines / boxes / circles / dots repersentation.


## Strategies

### Player (submarine)

- Locate the fleet as far as possibile
- Prefer ambush the fleet on the projected route
- Approach the fleet stealthly
- Look for openings in the formation unprotected merchant ships. Prioritize them as attack target
- If the formation is tight, try to lure the military ships out of the formation.
- Always avoid facing military vessels directly. Hit, run, hide and hit again is the golden rule

### Merchant ships

- When attacked, dodge the immediate attack, keep distance with enemy, spread out
- Keep close to military otherwise.

### Military ships

- When cruising, keep in the outter rim to protect the convoy.
- When under thread, dispatch portion of military force to try to elimitate the thread, while keeping the rest to protect the convoy.
- Return to formation as soon as the thread is elimiated or lost.

## Development

Use pyraylib, compile and deploy wasm on static webpages such as github pages / s3.

Requires [Nix](https://nixos.org) (with flakes) and [direnv](https://direnv.net).

```bash
direnv allow   # enters the devshell automatically
just           # list available tasks
```


