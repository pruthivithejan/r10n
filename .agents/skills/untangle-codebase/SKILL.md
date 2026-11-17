---
name: untangle-codebase
description: Refactor the r10n Go + Python codebase without breaking protocol v2, registry schemas, generated artifacts, or the published docs.
disable-model-invocation: true
argument-hint: "[optional area or concern to focus on]"
---

Start a thorough refactor of this codebase and finish it. Preserve observable
behavior except for bugs fixed by the structural changes. Work in small,
independently verified units.

## 1. Agree on scope

Ask which optional work to include, and do only what is selected:

| Addition | What it does |
| --- | --- |
| **Comments** | Remove comments that only restate the code. |
| **Tests** | Remove tests that cannot catch a real bug; repair tests that fail without one. |

The area to untangle may come from the argument hint.

## 2. Ownership boundaries

| Layer | Owns | Never |
| --- | --- | --- |
| Go (`cmd/r10n/`, `internal/`) | routing and flags, Bubble Tea/Huh/Lip Gloss UI, settings file UI, upgrades and downloads, worker process lifecycle and cancellation | business logic, PDF/image work, keyring secrets, external tool installation |
| Python (`src/r10n_backend/`) | registry and Pydantic models, protocol v2 worker, automations, keyring access, on-demand tool resolution (`deps.py`) | importing the Go CLI, or prompting interactively inside worker execution |
| Transport | `catalog` JSON and v2 JSON Lines: `hello → started → progress|log|artifact → completed|error|cancelled` | changing event fields, exit codes (`0`, `1`, `2`, `130`), or redaction on one side only |
| Docs | Zensical Markdown and MiniJinja templates | putting templates or decision logs under `docs/` |

Python is the single source of truth for schemas. Go must not read Python
runtime state directly; it only calls `catalog`, `worker`, and the other backend
modes through `internal/backend`.

## 3. Generated artifacts

Do not hand-edit generated files. Regenerate after changing the source:

| Source of truth | Generator | Output |
| --- | --- | --- |
| `src/r10n_backend/registry.py` | `scripts/generate_flag_schema.py` | `internal/cli/flag_schema_generated.go` |
| `src/r10n_backend/registry.py` | `scripts/render_home_automations.py` | `overrides/partials/home-automations.html` |
| `assets/brand/r10n-wordmark.txt` + `assets/brand/tokens.json` | `scripts/generate_brand_assets.py` | `internal/brand/logo.txt`, brand SVGs, docs SVGs, installer banner |

`scripts/check.py` runs each generator with `--check`; CI fails on drift.

## 4. Placement rules

- `docs/`: published Markdown and static assets only.
- `overrides/`: root-level Zensical `custom_dir` templates.
- `src/`: the Python package only; no site templates or build scripts.
- `scripts/`: build, packaging, codegen, and checks. No loose root scripts.
- Go tests beside packages; compiled CLI integration in `tests/go/`; Python
  tests in `tests/test_<module>.py`.

## 5. Audit before editing

Record, before changing anything:

- hidden dependencies, duplicated rules, implicit ordering, and scattered code;
- unnecessary dependencies on internals or volatile details;
- unused wrappers, extension points, and dead code;
- special cases: single-value branches, caller-specific parameters, swallowed
  exceptions, retries, sleeps, and disabled tests.

Check whether each serves a real requirement. Use import graphs and Git history
as evidence. Document each proposed fix above the problems it addresses in
`.agents/skills/untangle-codebase/references/decisions.md`.

## 6. Redesign around change

- Put rules that change together together; separate those that change independently.
- Depend on stable contracts: registry schemas, protocol v2, settings JSON.
- Keep Go process control and Python execution separate.
- Preserve cancellation, redaction, artifact ordering, exit codes, and bounded
  output guarantees.
- Keep `setup.sh`, `scripts/check.py`, and packaging assumptions working.

## 7. Verify

```bash
uv run --locked python scripts/check.py all
```

This covers Go format/vet/tests, `uv` lock and versions, generated-artifact
drift, Black, Ruff, `ty`, `pytest`, and the Zensical build. For packaging or
bundling changes, also run `./setup.sh build` and confirm the Unix
`libexec/r10n-python/` sidecar and Windows `-tags bundled` payload assumptions.

Nix only supplies an optional development shell; it must not become a build or
release dependency.
