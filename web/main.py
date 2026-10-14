# /// script
# dependencies = [
#     "cffi",
#     "raylib",
# ]
# ///
"""pygbag entry point.  The runtime is CPython 3.12 compiled to WebAssembly."""

import asyncio

import pyray  # noqa: F401  (declares the raylib wheel to pygbag's import scanner)

from jenesboat_v2.app import run

asyncio.run(run())
