# Web (WASM) build inputs

- `main.py` — pygbag entry point. It only imports the `jenesboat_v2` package, which
  `scripts/build_web.py` copies next to it at build time.
- `noctx.tmpl` — the pygbag 0.9 `noctx` index.html template, vendored from
  `https://pygame-web.github.io/archives/0.9/noctx.tmpl` so builds are reproducible.
  Local changes: `config.user_canvas = 1` and a `canvas.emscripten` rule that makes the
  canvas span the window's width and as much height as keeps it at least 16:9 (pygbag's own
  placement put it at the bottom left at 80 % in some browsers); the page background is the
  ocean colour. The game reads the canvas CSS size every frame and draws at a matching
  logical resolution (`app.logical_size`), so a wide phone screen shows more map.
  The `#touch` block holds the on-screen buttons for touch screens and the script at the end
  of the page keeps the `jb_*` globals that `jenesboat_v2/touch.py` polls (one bit per key;
  `JB_KEYS` must match `touch.KEYS`, a test checks it); `jb_fit(w, h)` lets the game size the
  GL buffer to CSS px x devicePixelRatio for sharp text. `#rotate` covers the page in portrait.

Build with `just build-web [build-id]`; output lands in `dist/web/`.
