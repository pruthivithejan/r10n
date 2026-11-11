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

## Rendering options need a separate design

- Markdown-to-PDF accepts a table-of-contents option, but the renderer does not
  produce one. Syntax highlighting and custom CSS styles are stripped before PDF
  rendering, and directory conversion drops the corresponding options.
- A complete fix needs a rendering contract for headings, page references,
  code-token styles, and supported CSS, plus consistent single-file and batch
  behavior. This changes output and potentially dependencies; it is not solved
  by forwarding flags. Existing tests that only asserted conversion success did
  not demonstrate these features and have been replaced with output checks.
