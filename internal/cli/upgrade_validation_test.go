package cli

import (
	"archive/tar"
	"context"
	"errors"
	"os"
	"path/filepath"
	"runtime"
	"strings"
	"testing"
	"time"

	"github.com/pruthivithejan/r10n"
)

// The offline native double dispatches to its sidecar, writes real VCF output,
// and emits JSONL. No network, system Python, or checkout files are needed.
func releaseFixtureEntries() []archiveEntry {
	catalog := `{"protocol":2,"version":"99.0.0","automations":[{"id":"contacts","title":"Contacts","input_schema":{"properties":{"input_file":{"type":"string"},"output_file":{"type":"string"},"prefix":{"type":"string"}},"required":["input_file","output_file"]},"field_order":["input_file","output_file","prefix"]}]}`
	native := `#!/bin/sh
set -eu
app=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
test "${R10N_DISABLE_UPDATE_CHECK:-}" = 1
test -z "${R10N_BACKEND:-}${R10N_PROJECT:-}${R10N_PYTHON:-}${R10N_SOURCE:-}${R10N_MANAGED:-}${PYTHONPATH:-}${PYTHONHOME:-}"
test ! -e local/.env
case "$1" in
--version) printf 'r10n, version 99.0.0\n' ;;
list) test "$2" = --json; exec "$app/libexec/r10n-python/r10n-python" catalog ;;
run) test "$2" = contacts; test "$3" = --input-json; test "$5" = --json; test "$6" = --yes
     printf '%s' "$4" | "$app/libexec/r10n-python/r10n-python" worker contacts ;;
*) exit 2 ;;
esac
`
	sidecar := `#!/bin/sh
set -eu
case "$1" in
catalog) printf '%s\n' '` + catalog + `' ;;
worker)
  payload=$(cat)
  input=${payload#*'"input_file":"'}
  input=${input%%'"'*}
  output=${payload#*'"output_file":"'}
  output=${output%%'"'*}
  case "$input:$output" in /*:/*) ;; *) exit 2 ;; esac
  grep -q '+94771234567' "$input"
  printf 'BEGIN:VCARD\nVERSION:3.0\nFN:Upgrade 1\nTEL;TYPE=CELL:+94771234567\nEND:VCARD\n' > "$output"
  printf '{"type":"hello","protocol":2}\n{"type":"started","protocol":2,"automation":"contacts"}\n'
  printf '{"type":"progress","current":1,"total":1}\n{"type":"artifact","path":"%s"}\n' "$output"
  printf '{"type":"completed","automation":"contacts","success":true,"result":{"valid":1}}\n' ;;
*) exit 2 ;;
esac
`
	return []archiveEntry{
		{name: "r10n/r10n", body: native},
		{name: "r10n/libexec/r10n-python/r10n-python", body: sidecar},
		{name: "r10n/libexec/r10n-python/_internal/runtime", body: "offline runtime double"},
	}
}

func assertOldBundle(t *testing.T, native string) {
	t.Helper()
	data, err := os.ReadFile(native)
	if err != nil || string(data) != "old-native" {
		t.Fatalf("old executable changed: %q %v", data, err)
	}
	data, err = os.ReadFile(filepath.Join(filepath.Dir(native), "libexec", "r10n-python", "r10n-python"))
	if err != nil || string(data) != "old-backend" {
		t.Fatalf("old backend changed: %q %v", data, err)
	}
	stages, err := filepath.Glob(filepath.Join(filepath.Dir(filepath.Dir(native)), ".r10n-stage-*"))
	if err != nil || len(stages) != 0 {
		t.Fatalf("validation stage not cleaned: %v %v", stages, err)
	}
}

func TestReleaseValidationFailuresDoNotMutateInstallation(t *testing.T) {
	if runtime.GOOS == "windows" {
		t.Skip("Unix release helpers")
	}
	for _, test := range []struct {
		name string
		edit func([]archiveEntry) []archiveEntry
	}{
		{"missing sidecar", func(e []archiveEntry) []archiveEntry { return append(e[:1], e[2:]...) }},
		{"missing runtime", func(e []archiveEntry) []archiveEntry { return e[:2] }},
		{"sidecar symlink", func(e []archiveEntry) []archiveEntry {
			e[1].body, e[1].kind, e[1].target = "", tar.TypeSymlink, "../../../r10n"
			return e
		}},
		{"wrong version", func(e []archiveEntry) []archiveEntry {
			e[0].body = strings.ReplaceAll(e[0].body, "99.0.0", "98.0.0")
			return e
		}},
		{"wrong frozen version", func(e []archiveEntry) []archiveEntry {
			e[1].body = strings.ReplaceAll(e[1].body, "99.0.0", "98.0.0")
			return e
		}},
		{"corrupt catalog", func(e []archiveEntry) []archiveEntry {
			e[1].body = strings.Replace(e[1].body, `{"protocol":2`, `{broken "protocol":2`, 1)
			return e
		}},
		{"failed catalog", func(e []archiveEntry) []archiveEntry {
			e[1].body = strings.Replace(e[1].body, "catalog) printf", "catalog) exit 1; printf", 1)
			return e
		}},
		{"wrong protocol", func(e []archiveEntry) []archiveEntry {
			e[1].body = strings.ReplaceAll(e[1].body, `"protocol":2`, `"protocol":1`)
			return e
		}},
		{"invalid fields", func(e []archiveEntry) []archiveEntry {
			e[1].body = strings.Replace(e[1].body, `"field_order":["input_file","output_file","prefix"]`, `"field_order":[]`, 1)
			return e
		}},
		{"worker startup failure", func(e []archiveEntry) []archiveEntry {
			e[1].body = strings.Replace(e[1].body, "worker)\n", "worker) exit 1\n", 1)
			return e
		}},
		{"worker incomplete protocol", func(e []archiveEntry) []archiveEntry {
			e[1].body = strings.Replace(e[1].body, `"type":"completed"`, `"type":"log"`, 1)
			return e
		}},
		{"worker invalid artifact", func(e []archiveEntry) []archiveEntry {
			e[1].body = strings.ReplaceAll(e[1].body, "BEGIN:VCARD", "INVALID")
			return e
		}},
	} {
		t.Run(test.name, func(t *testing.T) {
			_, native := installedFixture(t)
			app, err := extractFixture(t, test.edit(releaseFixtureEntries()))
			if err == nil {
				err = replaceBundle(context.Background(), native, app, "v99.0.0")
			}
			if err == nil {
				t.Fatal("invalid release accepted")
			}
			assertOldBundle(t, native)
		})
	}
}

func TestUpgradeValidationCancellation(t *testing.T) {
	if runtime.GOOS == "windows" {
		t.Skip("Unix release helpers")
	}
	for _, during := range []bool{false, true} {
		t.Run(map[bool]string{false: "before", true: "during"}[during], func(t *testing.T) {
			_, native := installedFixture(t)
			entries := releaseFixtureEntries()
			if during {
				entries[0].body = strings.Replace(entries[0].body, "--version) printf", "--version) sleep 30; printf", 1)
			}
			app, err := extractFixture(t, entries)
			if err != nil {
				t.Fatal(err)
			}
			ctx, cancel := context.WithCancel(context.Background())
			defer cancel()
			if during {
				time.AfterFunc(100*time.Millisecond, cancel)
			} else {
				cancel()
			}
			start := time.Now()
			if err := replaceBundle(ctx, native, app, "99.0.0"); !errors.Is(err, context.Canceled) {
				t.Fatalf("cancellation not preserved: %v", err)
			}
			if time.Since(start) > 3*time.Second {
				t.Fatal("probe ignored cancellation")
			}
			assertOldBundle(t, native)
		})
	}
}

func TestInstalledValidationFailureRollsBack(t *testing.T) {
	if runtime.GOOS == "windows" {
		t.Skip("Unix release helpers")
	}
	_, native := installedFixture(t)
	entries := releaseFixtureEntries()
	entries[0].body = strings.Replace(entries[0].body, `case "$1" in`, `case "$app" in */.r10n) exit 1 ;; esac
case "$1" in`, 1)
	app, err := extractFixture(t, entries)
	if err != nil {
		t.Fatal(err)
	}
	if err := replaceBundle(context.Background(), native, app, "99.0.0"); err == nil || !strings.Contains(err.Error(), "restored") {
		t.Fatal(err)
	}
	assertOldBundle(t, native)
}

func TestUpgradeCleanValidationEnvironment(t *testing.T) {
	if runtime.GOOS == "windows" {
		t.Skip("Unix release helpers")
	}
	for _, key := range []string{"R10N_BACKEND", "R10N_PROJECT", "R10N_PYTHON", "R10N_SOURCE", "R10N_MANAGED", "PYTHONPATH", "PYTHONHOME"} {
		t.Setenv(key, "/invalid/override")
	}
	app, err := extractFixture(t, releaseFixtureEntries())
	if err != nil {
		t.Fatal(err)
	}
	if err := validateReleaseBundle(context.Background(), app, "99.0.0"); err != nil {
		t.Fatal(err)
	}
}

func TestUpgradeConfirmationAndHelp(t *testing.T) {
	old := stdin
	input, err := os.Open(os.DevNull)
	if err != nil {
		t.Fatal(err)
	}
	defer input.Close()
	stdin = input
	defer func() { stdin = old }()
	if err := confirmUpgrade(context.Background(), false); err == nil || !strings.Contains(err.Error(), "--yes") {
		t.Fatalf("headless upgrade allowed: %v", err)
	}
	if err := confirmUpgrade(context.Background(), true); err != nil {
		t.Fatal(err)
	}
	for _, help := range []string{"--help", "-h"} {
		if err := upgrade(context.Background(), []string{help}); err != nil {
			t.Fatal(err)
		}
	}
}

func TestFrozenReleaseProbe(t *testing.T) {
	app := os.Getenv("R10N_TEST_BUNDLE")
	if app == "" {
		t.Skip("set R10N_TEST_BUNDLE to verify a real host-native release bundle")
	}
	absolute, err := filepath.Abs(app)
	if err != nil {
		t.Fatal(err)
	}
	t.Setenv("R10N_PROJECT", "/not-a-source-checkout")
	t.Setenv("R10N_BACKEND", "/not-a-backend")
	if err := validateReleaseBundle(t.Context(), absolute, r10n.Version); err != nil {
		t.Fatal(err)
	}
}
