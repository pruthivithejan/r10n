# Go integration and end-to-end tests

Run the standalone suite from the repository root:

```sh
go test ./tests/go/...
```

These tests build and execute the native command outside the checkout, with
isolated settings and no installed-app modifications. They cover the Go process
boundary rather than duplicating Python automation integration tests. They need
Go, not a Python environment or a downloaded release.

Keep unit tests beside their packages. Component workflows that need private
hooks also remain there: the CLI upgrade workflows inject executable paths and
HTTP clients, serve checksum-verified archives locally, replace temporary
installations twice, and validate the resulting native frontend and worker.
The compiled frontend in that component test is not a standalone upgrade test:
the upgrade itself runs in-process to use those private hooks. No production
APIs, overlays, or custom test runners are needed.

The genuine frozen-runtime checks remain opt-in in `internal/cli`:

```sh
# Probe an extracted host-native bundle directory containing r10n and libexec/.
R10N_TEST_BUNDLE=/absolute/path/to/r10n \
R10N_TEST_BUNDLE_VERSION=0.12.2 \
go test ./internal/cli -run '^TestFrozenReleaseProbe$' -count=1

# Exercise two upgrades using a genuine host-native release archive.
R10N_TEST_RELEASE_ARCHIVE=/absolute/path/to/release.tar.gz \
R10N_TEST_BUNDLE_VERSION=0.12.2 \
go test ./internal/cli -run '^TestUpgradeFrozenReleaseWorkflow$' -count=1
```

Use a trusted, checksum-verified archive matching the host OS/architecture;
these tests execute its binaries. The archive workflow is Unix-only. The version
defaults to the current source version; set it explicitly for older releases.
Fixtures and replacement installations are temporary, not the installed app.

`go test ./...` discovers all Go tests normally, including this directory.
Opt-in frozen checks skip when their environment variables are unset.
