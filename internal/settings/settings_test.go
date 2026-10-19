package settings

import (
	"os"
	"path/filepath"
	"strings"
	"testing"
)

func TestLoadMissingSettingsDoesNotCreateDirectory(t *testing.T) {
	root := filepath.Join(t.TempDir(), "user", "config")
	t.Setenv("R10N_CONFIG_DIR", root)
	document, err := Load()
	if err != nil {
		t.Fatal(err)
	}
	if document.Version != Version || document.Theme != "dark" {
		t.Fatalf("unexpected defaults: %#v", document)
	}
	if _, err := os.Stat(root); !os.IsNotExist(err) {
		t.Fatalf("reading default settings created %q", root)
	}
}

func TestDirectoryExpandsUserHomeOverride(t *testing.T) {
	home, err := os.UserHomeDir()
	if err != nil {
		t.Fatal(err)
	}
	t.Setenv("R10N_CONFIG_DIR", filepath.Join("~", "r10n-settings-test"))
	directory, err := Directory()
	if err != nil {
		t.Fatal(err)
	}
	if directory != filepath.Join(home, "r10n-settings-test") {
		t.Fatalf("expanded config directory = %q, want %q", directory, filepath.Join(home, "r10n-settings-test"))
	}
}

func TestSaveSettingsIsPrivateAndRoundTrips(t *testing.T) {
	root := filepath.Join(t.TempDir(), "user", "config")
	t.Setenv("R10N_CONFIG_DIR", root)
	document := defaults()
	document.Accessible = true
	document.OutputDirectory = filepath.Join(t.TempDir(), "results")
	document.SMTPProfiles["work"] = SMTPProfile{
		Server: "smtp.example.test", Port: 587, Email: "sender@example.test",
	}
	document.ActiveSMTPProfile = "work"

	path, err := Save(document)
	if err != nil {
		t.Fatal(err)
	}
	loaded, err := Load()
	if err != nil {
		t.Fatal(err)
	}
	if !loaded.Accessible || loaded.ActiveSMTPProfile != "work" {
		t.Fatalf("settings did not round-trip: %#v", loaded)
	}
	data, err := os.ReadFile(path)
	if err != nil {
		t.Fatal(err)
	}
	if strings.Contains(string(data), "password") {
		t.Fatal("settings file must never contain a credential")
	}
	if runtimeOS := os.PathSeparator; runtimeOS != '\\' {
		info, err := os.Stat(path)
		if err != nil {
			t.Fatal(err)
		}
		if info.Mode().Perm() != 0600 {
			t.Fatalf("settings permissions = %o, want 600", info.Mode().Perm())
		}
	}
}

func TestSaveRejectsDanglingProfileAndInvalidTheme(t *testing.T) {
	if _, err := Save(Document{
		Theme: "solarized", ActiveSMTPProfile: "missing",
	}); err == nil {
		t.Fatal("invalid theme should not be saved")
	}
	document := defaults()
	document.ActiveSMTPProfile = "missing"
	if _, err := Save(document); err == nil {
		t.Fatal("dangling active profile should not be saved")
	}
}

func TestLoadRejectsUnknownAndFutureSettings(t *testing.T) {
	root := t.TempDir()
	t.Setenv("R10N_CONFIG_DIR", root)
	path := filepath.Join(root, "config.json")
	if err := os.MkdirAll(root, 0700); err != nil {
		t.Fatal(err)
	}
	for _, contents := range []string{
		`{"version":999,"theme":"dark"}`,
		`{"version":1,"password":"must-not-be-persisted"}`,
	} {
		if err := os.WriteFile(path, []byte(contents), 0600); err != nil {
			t.Fatal(err)
		}
		if _, err := Load(); err == nil {
			t.Fatalf("expected invalid settings to be rejected: %s", contents)
		}
	}
}
