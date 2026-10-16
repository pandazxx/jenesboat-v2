# Web (WASM) build inputs

- `main.py` — pygbag entry point. It only imports the `jenesboat_v2` package, which
  `scripts/build_web.py` copies next to it at build time.
- `noctx.tmpl` — the pygbag 0.9 `noctx` index.html template, vendored from
  `https://pygame-web.github.io/archives/0.9/noctx.tmpl` so builds are reproducible.
  Local changes: `config.user_canvas = 1` and a `canvas.emscripten` rule that centres the
  canvas and scales it to the largest 16:9 box in the viewport (pygbag's own placement put it
  at the bottom left at 80 % in some browsers); the page background is the ocean colour.

Build with `just build-web [build-id]`; output lands in `dist/web/`.
