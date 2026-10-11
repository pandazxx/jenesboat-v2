# Web (WASM) build inputs

- `main.py` — pygbag entry point. It only imports the `jenesboat_v2` package, which
  `scripts/build_web.py` copies next to it at build time.
- `noctx.tmpl` — the pygbag 0.9 `noctx` index.html template, vendored from
  `https://pygame-web.github.io/archives/0.9/noctx.tmpl` so builds are reproducible.

Build with `just build-web [build-id]`; output lands in `dist/web/`.
