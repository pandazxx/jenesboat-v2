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
    uv run pytest {{args}}

# Lint and check formatting
lint:
    uv run ruff check .
    uv run ruff format --check .

# Auto-fix lint issues and format
fmt:
    uv run ruff check --fix .
    uv run ruff format .

# Run the package
run *args:
    uv run jenesboot-v2 {{args}}

# Pull latest template changes
template-update:
    copier update --trust
