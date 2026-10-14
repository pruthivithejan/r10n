package cli

import (
	"context"
	"encoding/json"
	"os"
	"path/filepath"
	"strings"
	"testing"

	"github.com/pruthivithejan/r10n"
)

func TestInitStatusPreserveExistingFiles(t *testing.T) {
	t.Chdir(t.TempDir())
	old := stdout
	defer func() { stdout = old }()
	var output strings.Builder
	stdout = &output
	if err := os.MkdirAll("local/configs", 0755); err != nil {
		t.Fatal(err)
	}
	if err := os.WriteFile("local/configs/email.json", []byte("private configuration"), 0600); err != nil {
		t.Fatal(err)
	}
	for i := 0; i < 2; i++ {
		if err := initialize(context.Background(), nil); err != nil {
			t.Fatal(err)
		}
	}
	data, _ := os.ReadFile("local/configs/email.json")
	if string(data) != "private configuration" {
		t.Fatal("overwrote existing config")
	}
	entries, _ := r10n.WorkspaceTemplates.ReadDir("configs")
	for _, entry := range entries {
		if entry.Name() == "email.default.json" {
			continue
		}
		data, err := os.ReadFile(filepath.Join("local/configs", strings.Replace(entry.Name(), ".default.json", ".json", 1)))
		if err != nil {
			t.Fatal(err)
		}
		expected, _ := r10n.WorkspaceTemplates.ReadFile("configs/" + entry.Name())
		if string(data) != string(expected) {
			t.Fatalf("template drift: %s", entry.Name())
		}
	}
	if err := os.WriteFile("local/.env", []byte("secret"), 0600); err != nil {
		t.Fatal(err)
	}
	output.Reset()
	if err := status([]string{"--json"}); err != nil {
		t.Fatal(err)
	}
	var result map[string]bool
	if err := json.Unmarshal([]byte(output.String()), &result); err != nil {
		t.Fatal(err)
	}
	if !result["local/configs/email.json"] || !result["local/.env"] || !result["local/outputs"] {
		t.Fatal(result)
	}
	if strings.Contains(output.String(), "private configuration") || strings.Contains(output.String(), "secret") {
		t.Fatal("status leaked config contents")
	}
}
