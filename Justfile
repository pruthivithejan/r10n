# Thin shortcuts over setup.sh and scripts/. No build logic lives here.
set shell := ["bash", "-euo", "pipefail", "-c"]

# List recipes
default:
    @just --list

# Install modules, hooks, and the locked dependency environment
setup:
    ./setup.sh setup

# Run the full shared check gate (Go, Python, docs, generated files)
check:
    ./setup.sh check

# Run both test suites
test:
    ./setup.sh test

# Run the Go CLI from source: just run list
run *args:
    go run ./cmd/r10n {{args}}

# Regenerate registry-derived Go flags, brand assets, and homepage cards
gen:
    uv run --locked python scripts/generate_flag_schema.py
    uv run --locked python scripts/generate_brand_assets.py
    uv run --locked python scripts/render_home_automations.py

# Preview the documentation with the generated home cards
serve:
    uv run --locked python scripts/render_home_automations.py
    uv run --locked zensical serve

# Build the documentation site
docs:
    ./setup.sh docs

# Build the native release bundle
build:
    ./setup.sh build
