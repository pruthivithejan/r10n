package tui

import (
	"strings"
	"testing"

	tea "github.com/charmbracelet/bubbletea"
	"github.com/charmbracelet/x/ansi"
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
