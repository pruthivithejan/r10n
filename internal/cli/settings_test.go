package cli

import (
	"context"
	"os"
	"path/filepath"
	"strings"
	"testing"

	"github.com/pruthivithejan/r10n/internal/settings"
)

func TestConfigPathIsReadOnly(t *testing.T) {
	configDirectory := filepath.Join(t.TempDir(), "system-settings")
	t.Setenv("R10N_CONFIG_DIR", configDirectory)
	old := stdout
	t.Cleanup(func() { stdout = old })
	var output strings.Builder
	stdout = &output

	if err := settingsCommand(context.Background(), []string{"path"}); err != nil {
		t.Fatal(err)
	}
	if strings.TrimSpace(output.String()) != filepath.Join(configDirectory, "config.json") {
		t.Fatalf("settings path = %q", output.String())
	}
	if _, err := os.Stat(configDirectory); !os.IsNotExist(err) {
		t.Fatalf("config path inspection created the settings directory: %v", err)
	}
}

func TestSettingsFormsRequireATerminalWithoutCreatingFiles(t *testing.T) {
	configDirectory := filepath.Join(t.TempDir(), "system-settings")
	t.Setenv("R10N_CONFIG_DIR", configDirectory)
	for _, args := range [][]string{
		{"edit"},
		{"add-smtp-profile", "work"},
	} {
		if err := settingsCommand(context.Background(), args); err == nil ||
			!strings.Contains(err.Error(), "interactive terminal") {
			t.Errorf("%v should require a terminal, got %v", args, err)
		}
	}
	if _, err := os.Stat(configDirectory); !os.IsNotExist(err) {
		t.Fatalf("attempting a cancelled setup created files: %v", err)
	}
}

func TestEditSMTPProfileRequiresAnExistingProfile(t *testing.T) {
	t.Setenv("R10N_CONFIG_DIR", t.TempDir())
	err := settingsCommand(context.Background(), []string{"edit-smtp-profile", "missing"})
	if err == nil || !strings.Contains(err.Error(), "does not exist") {
		t.Fatalf("edit missing SMTP profile error = %v", err)
	}
}

func TestSetSMTPSecretRequiresTerminal(t *testing.T) {
	t.Setenv("R10N_CONFIG_DIR", t.TempDir())
	document, err := settings.Load()
	if err != nil {
		t.Fatal(err)
	}
	document.SMTPProfiles["work"] = settings.SMTPProfile{
		Server: "smtp.example.test", Port: 587, Email: "sender@example.test",
	}
	if _, err := settings.Save(document); err != nil {
		t.Fatal(err)
	}
	err = settingsCommand(context.Background(), []string{"set-secret", "work"})
	if err == nil || !strings.Contains(err.Error(), "interactive terminal") {
		t.Fatalf("setting a secret without a terminal error = %v", err)
	}
}
