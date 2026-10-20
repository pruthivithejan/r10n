package integration_test

import (
	"os"
	"os/exec"
	"path/filepath"
	"runtime"
	"strings"
	"testing"
	"time"

	"github.com/pruthivithejan/r10n"
)

// Exercise the installed command boundary, not cli.Run or private package hooks.
func TestNativeCommandsOutsideCheckout(t *testing.T) {
	name := "r10n"
	if runtime.GOOS == "windows" {
		name += ".exe"
	}
	native := filepath.Join(t.TempDir(), name)
	build := exec.CommandContext(t.Context(), "go", "build", "-o", native, "./cmd/r10n")
	build.Dir = filepath.Join("..", "..")
	if output, err := build.CombinedOutput(); err != nil {
		t.Fatalf("build frontend: %v\n%s", err, output)
	}
	directory := t.TempDir()
	t.Setenv("R10N_CONFIG_DIR", filepath.Join(directory, "settings"))
	t.Setenv("R10N_BACKEND", filepath.Join(directory, "missing-backend"))
	t.Setenv("R10N_DISABLE_UPDATE_CHECK", "1")
	run := func(args ...string) ([]byte, error) {
		t.Helper()
		command := exec.CommandContext(t.Context(), native, args...)
		command.Dir = directory
		command.WaitDelay = 5 * time.Second
		// A nil Stdin is the null device: these commands must never prompt.
		return command.CombinedOutput()
	}
	t.Run("version", func(t *testing.T) {
		output, err := run("--version")
		if err != nil || strings.TrimSpace(string(output)) != "r10n, version "+r10n.Version {
			t.Fatalf("version: %v\n%s", err, output)
		}
	})
	for _, args := range [][]string{
		{"--help"}, {"run", "--help"}, {"list", "--help"}, {"tui", "--help"},
		{"configure", "--help"}, {"status", "--help"}, {"upgrade", "--help"},
		{"contacts", "--help"}, {"fill-pdfs", "--help"}, {"images", "--help"},
		{"website-images", "--help"}, {"logos", "--help"}, {"email", "--help"},
		{"colors", "--help"}, {"rename", "--help"}, {"validate", "--help"}, {"md2pdf", "--help"},
	} {
		t.Run(strings.Join(args, " "), func(t *testing.T) {
			output, err := run(args...)
			if err != nil || len(output) == 0 {
				t.Fatalf("help without backend: %v\n%s", err, output)
			}
		})
	}
	t.Run("removed init", func(t *testing.T) {
		if output, err := run("init"); err == nil {
			t.Fatalf("removed init command accepted:\n%s", output)
		}
	})
	entries, err := os.ReadDir(directory)
	if err != nil {
		t.Fatal(err)
	}
	if len(entries) != 0 {
		t.Fatalf("commands created files outside checkout: %v", entries)
	}
}
