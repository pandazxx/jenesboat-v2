set positional-arguments
set shell := ["bash", "-euo", "pipefail", "-c"]

# List available recipes
default:
    @just --list

# Update flake inputs
update:
    nix flake update
    uv lock --upgrade

# Install/sync dependencies
sync:
    uv sync

# Run tests
test *args:
    uv run pytest "$@"

# Lint and check formatting
lint:
    uv run ruff check .
    uv run ruff format --check .

# Auto-fix lint issues and format
fmt:
    uv run ruff check --fix .
    uv run ruff format .

# Run the game in a native window
run *args:
    uv run jenesboat-v2 "$@"

# Run the simulation headless and print JENESBOAT JSON events (agent friendly)
sim *args:
    uv run jenesboat-v2 --headless "$@"

# Build the browser (WASM) bundle into dist/web with the given build id
build-web build_id="dev" *args:
    uv run python scripts/build_web.py --build-id "$1" "${@:2}"

# Serve dist/web on http://127.0.0.1:9000 (not localhost:8xxx: pygbag treats that as its dev server)
serve-web port="9000":
    uv run python -m http.server {{port}} --bind 127.0.0.1 --directory dist/web

# One-time: download the headless browser used by agent-web-test
agent-setup:
    uv run playwright install chromium

# Drive a web build (URL) in headless Chromium, capture state events and a screenshot
agent-web-test url *args:
    uv run python scripts/agent_web_test.py "$1" "${@:2}"

# Regenerate the Pages build index for a gh-pages checkout
build-index site="site":
    uv run python scripts/gen_build_index.py {{site}} --repo pandazxx/jenesboat-v2

# Create an annotated release tag after checking it matches pyproject version
tag version:
    #!/usr/bin/env bash
    set -euo pipefail
    v="{{version}}"; [[ "$v" == v* ]] || { echo "version must look like v1.2.3"; exit 1; }
    pv=$(uv run python -c "import tomllib;print(tomllib.load(open('pyproject.toml','rb'))['project']['version'])")
    [[ "${v#v}" == "$pv"* ]] || { echo "pyproject version $pv does not match $v"; exit 1; }
    git tag -a "$v" -m "Release $v"
    echo "created $v; push with: git push origin $v"

# Pull latest template changes
template-update:
    copier update --trust
