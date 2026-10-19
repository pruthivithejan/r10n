package cli

import (
	"context"
	"encoding/json"
	"os"
	"path/filepath"
	"strings"
	"testing"

	"github.com/pruthivithejan/r10n/internal/settings"
)

func TestRemovedInitCommandDoesNotCreateProjectFolders(t *testing.T) {
	t.Chdir(t.TempDir())

	err := Run(context.Background(), []string{"init"})
	if err == nil {
		t.Fatal("removed init command was accepted")
	}
	if _, err := os.Stat("local"); !os.IsNotExist(err) {
		t.Fatalf("init created a project-local directory: %v", err)
	}
}

func TestStatusReportsSystemSettingsWithoutSecrets(t *testing.T) {
	configDirectory := t.TempDir()
	t.Setenv("R10N_CONFIG_DIR", configDirectory)
	document := settings.Document{
		Theme:             "dark",
		ActiveSMTPProfile: "work",
		SMTPProfiles: map[string]settings.SMTPProfile{
			"work": {Server: "smtp.example.com", Port: 587, Email: "person@example.com"},
		},
	}
	if _, err := settings.Save(document); err != nil {
		t.Fatal(err)
	}
	old := stdout
	t.Cleanup(func() { stdout = old })
	var output strings.Builder
	stdout = &output

	if err := status([]string{"--json"}); err != nil {
		t.Fatal(err)
	}
	var result struct {
		SettingsPath       string `json:"settings_path"`
		SettingsSaved      bool   `json:"settings_saved"`
		SMTPProfileCount   int    `json:"smtp_profile_count"`
		SecureSecretValues bool   `json:"secure_secret_values"`
	}
	if err := json.Unmarshal([]byte(output.String()), &result); err != nil {
		t.Fatal(err)
	}
	if result.SettingsPath != filepath.Join(configDirectory, "config.json") ||
		!result.SettingsSaved || result.SMTPProfileCount != 1 || result.SecureSecretValues {
		t.Fatalf("unexpected status response: %+v", result)
	}
	if strings.Contains(output.String(), "person@example.com") {
		t.Fatal("status leaked a profile's private details")
	}
}
