# Untangling decision log

This log records structural findings and decisions for the Python worker and Go
CLI. Changes preserve their public protocols and compatibility requirements.

## Align the shared settings contract — implemented

- Go PDF profile colors used integer slices while Python persisted fractional RGB
  values, so a Python-written profile could not be loaded in Go.
- `R10N_CONFIG_DIR` expanded environment variables in Go but not in Python.
- Go accepted some PDF field values that Python's model would reject.

Go now retains fractional colors and validates the relevant fields; Python uses
the Go override expansion convention. Tests exercise a Python → Go → Python
round trip as well as invalid Go settings.

## Declare automation artifacts at their source — implemented

- The worker inferred artifacts from substrings in result keys, coupling every
  automation to an undocumented naming convention.

The registry declares result paths, including nested paths, while the worker
preserves artifact event ordering, deduplication, and existing-path checks.

## Share email delivery accounting — implemented

- Identical and personalized email workflows duplicated per-recipient delivery,
  error handling, and counters.

A shared delivery function retains the progress callbacks, credentials, retry
policy, and rate limiting of both workflows.

## Retain compatibility cases

- SMTP retries and throttling use delays to handle transient failures and service
  rate limits. Their final waits remain unchanged to preserve existing timing.
- The upgrade handshake supports older worker protocols; these branches are
  intentional compatibility requirements.
- Protocol version declarations cross the Go/Python process boundary and are
  covered by integration tests.

## Render Markdown options through a shared pipeline — implemented

- Markdown-to-PDF accepts a table-of-contents option, but the renderer does not
  produce one. Syntax highlighting and custom CSS styles are stripped before PDF
  rendering, and directory conversion drops the corresponding options.
- The renderer now builds linked, paginated contents and colored fenced code,
  applies a documented subset of CSS, and passes the same options to batch
  conversions. Tests inspect generated PDF text, links, and drawing commands;
  the native bundle smoke test verifies its dynamically loaded syntax lexers.

## Unify contact generation paths — implemented

- File and text entry points independently implement normalization, deduplication,
  sorting, serialization, and statistics. Delegate both to a shared path while
  preserving input errors and generated VCF content.

## Make automation outcomes explicit — implemented

- Worker completion assumed success when a result omitted `success`; image,
  color, website, and batch Markdown results could report failures that way.
  Their adapters now translate domain results into completion outcomes, and
  mixed logo and rename results report partial completion.

## Share settings defaults without breaking existing reads — implemented

- Go load and save paths duplicated version checks and defaults. They share
  normalization while retaining the stricter write-time checks, so older files
  remain readable. Numeric font-weight strings accepted by Python can be saved.

## Derive offline CLI flag types from the registry — implemented

- Go maintained a separate hand-written list of boolean inputs, which could drift
  from Python's authoritative schemas. Offline help and argument validation
  must continue to work without starting the backend.
- A generated Go snapshot provides offline types; a freshness check compares it
  with the Python registry in the test suite.

## Share credential-save cleanup — implemented, with a remaining limitation

- Profile creation and import duplicated credential writes and silently ignored
  cleanup failures. Cleanup also reused a potentially cancelled context.
- The operation now shares bounded cleanup and reports cleanup errors. Settings
  writes have an unambiguous atomic commit point. The existing credential API
  cannot restore a previously orphaned secret; preserving it requires a durable
  credential-store transaction and recovery design across all writers.

## Scope terminal preferences to an invocation — implemented

- Persisted preferences were written to process-wide environment variables,
  which could leak between invocations and obscure explicit caller overrides.
  UI consumers now receive a resolved preference value.
- Terminal streams are still process-wide; concurrent in-process CLI invocations
  would require a separate stream-injection redesign.
