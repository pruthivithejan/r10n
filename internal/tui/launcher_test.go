package tui

import (
	"strings"
	"testing"

	tea "github.com/charmbracelet/bubbletea"
	"github.com/charmbracelet/x/ansi"
	r10n "github.com/pruthivithejan/r10n"
)

func TestLauncherDiscoversFiltersAndOpensCommands(t *testing.T) {
	model := newLauncher([]launcherEntry{
		{id: "contacts", title: "Create contacts", description: "Build a contact list"},
		{id: "sms", title: "Router SMS", description: "Read and send messages"},
	}, Preferences{ReducedMotion: true})
	initial := ansi.Strip(model.View())
	if strings.Contains(initial, "/contacts") || strings.Contains(initial, "/sms") {
		t.Fatalf("commands should be hidden until requested: %s", initial)
	}
	model = launcherKey(model, "/")
	opened := ansi.Strip(model.View())
	if !strings.Contains(opened, "/contacts") || !strings.Contains(opened, "/sms") {
		t.Fatalf("slash should show both commands: %s", opened)
	}
	model = launcherKey(model, "s")
	model = launcherKey(model, "m")
	model = launcherKey(model, "s")
	filtered := ansi.Strip(model.View())
	if !strings.Contains(filtered, "/sms") || strings.Contains(filtered, "/contacts") {
		t.Fatalf("search should filter commands: %s", filtered)
	}
	model = launcherKey(model, "enter")
	if model.selected != "sms" {
		t.Fatalf("selected %q, expected sms", model.selected)
	}
}

func TestLauncherKeyboardNavigationAndClearing(t *testing.T) {
	model := newLauncher([]launcherEntry{{id: "first", title: "First"}, {id: "second", title: "Second"}}, Preferences{})
	model = launcherKey(model, "/")
	model = launcherKey(model, "down")
	model = launcherKey(model, "enter")
	if model.selected != "second" {
		t.Fatalf("down and enter selected %q", model.selected)
	}
	model = newLauncher([]launcherEntry{{id: "first", title: "First"}}, Preferences{})
	model = launcherKey(model, "/")
	model = launcherKey(model, "x")
	model = launcherKey(model, "enter")
	if model.selected != "" || !strings.Contains(model.View(), "No matching") {
		t.Fatal("an unknown command should not run")
	}
	model = launcherKey(model, "esc")
	if strings.Contains(model.View(), "/first") || model.input.Value() != "" {
		t.Fatal("escape should clear the search and close the menu")
	}
}

func launcherKey(model launcherModel, key string) launcherModel {
	var msg tea.KeyMsg
	switch key {
	case "enter":
		msg.Type = tea.KeyEnter
	case "down":
		msg.Type = tea.KeyDown
	case "esc":
		msg.Type = tea.KeyEsc
	default:
		msg.Type = tea.KeyRunes
		msg.Runes = []rune(key)
	}
	next, _ := model.Update(msg)
	return next.(launcherModel)
}

func TestLauncherHeaderShowsBrandVersionAndRules(t *testing.T) {
	model := newLauncher(nil, Preferences{})
	view := ansi.Strip(model.View())
	if !strings.Contains(view, "routine automation") || !strings.Contains(view, "v"+r10n.Version) {
		t.Fatalf("header should show the brand and version: %s", view)
	}
	if !strings.Contains(view, "─") {
		t.Fatalf("header should use horizontal rules: %s", view)
	}
	if !strings.Contains(view, "What would you like to automate?") {
		t.Fatalf("home prompt missing: %s", view)
	}
}

func TestLauncherSlashOpensAndEscapeClosesDialog(t *testing.T) {
	model := newLauncher([]launcherEntry{{id: "contacts", title: "Create contacts"}}, Preferences{})
	opened := ansi.Strip(launcherKey(model, "/").View())
	if !strings.Contains(opened, "Automations") || !strings.Contains(opened, "╭") {
		t.Fatalf("slash should open the automation dialog: %s", opened)
	}
	if strings.Contains(opened, "What would you like to automate?") {
		t.Fatalf("dialog should replace the home prompt: %s", opened)
	}
	closed := ansi.Strip(launcherKey(launcherKey(model, "/"), "esc").View())
	if strings.Contains(closed, "Automations") {
		t.Fatalf("escape should close the dialog: %s", closed)
	}
}

func TestLauncherCompactHeaderFitsSmallTerminal(t *testing.T) {
	model := newLauncher(nil, Preferences{})
	next, _ := model.Update(tea.WindowSizeMsg{Width: 32, Height: 10})
	model = next.(launcherModel)
	view := ansi.Strip(model.View())
	if !strings.Contains(view, "r10n") || !strings.Contains(view, "v"+r10n.Version) {
		t.Fatalf("compact header should keep the brand and version: %s", view)
	}
}
