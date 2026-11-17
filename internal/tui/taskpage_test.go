package tui

import (
	"strings"
	"testing"

	"github.com/charmbracelet/x/ansi"
	"github.com/pruthivithejan/r10n/internal/backend"
)

func TestTaskPageShowsBrandRailAndForm(t *testing.T) {
	task := backend.Automation{
		ID:          "demo",
		Title:       "Demo automation",
		Description: "Does something useful.",
		FieldOrder:  []string{"name"},
		InputSchema: backend.Schema{
			Properties: map[string]backend.Field{"name": {Type: "string", Title: "Name"}},
			Required:   []string{"name"},
		},
	}
	page, _, _, err := newTaskPage(task, Preferences{})
	if err != nil {
		t.Fatal(err)
	}
	page.width, page.height = 100, 30
	page.form.WithWidth(page.formWidth())
	_ = page.Init()

	view := ansi.Strip(page.View())
	for _, want := range []string{"r10n", "Demo automation", "Does something useful.", "Step 1/1", "Name"} {
		if !strings.Contains(view, want) {
			t.Fatalf("task page missing %q: %s", want, view)
		}
	}
}
