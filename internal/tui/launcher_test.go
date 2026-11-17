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
	case "ctrl+c":
		msg.Type = tea.KeyCtrlC
	case "right":
		msg.Type = tea.KeyRight
	case "tab":
		msg.Type = tea.KeyTab
	default:
		msg.Type = tea.KeyRunes
		msg.Runes = []rune(key)
	}
	next, _ := model.Update(msg)
	return next.(launcherModel)
}

func TestLauncherHeaderShowsBrandLogoVersionAndField(t *testing.T) {
	model := newLauncher(nil, Preferences{})
	view := ansi.Strip(model.View())
	if !strings.Contains(view, "routine automation") || !strings.Contains(view, "v"+r10n.Version) {
		t.Fatalf("header should show the brand and version: %s", view)
	}
	if !strings.Contains(view, "·") {
		t.Fatalf("header should use ASCII fields: %s", view)
	}
	if strings.Contains(view, "─") {
		t.Fatalf("header should not use horizontal rules: %s", view)
	}
	if !strings.Contains(view, "/ commands") || !strings.Contains(view, "ctrl+c quit") {
		t.Fatalf("home footer missing: %s", view)
	}
}

func TestLauncherTypingOpensFilteredDialog(t *testing.T) {
	model := newLauncher([]launcherEntry{
		{id: "contacts", title: "Create contacts"},
		{id: "sms", title: "Router SMS"},
	}, Preferences{})
	model = launcherKey(model, "s")
	model = launcherKey(model, "m")
	view := ansi.Strip(model.View())
	if !strings.Contains(view, "Automations") || !strings.Contains(view, "/sms") {
		t.Fatalf("typing should open the filtered dialog: %s", view)
	}
	if strings.Contains(view, "/contacts") {
		t.Fatalf("typing should filter the dialog: %s", view)
	}
}

func TestLauncherCtrlCConfirmsQuit(t *testing.T) {
	model := newLauncher([]launcherEntry{{id: "sms", title: "Router SMS"}}, Preferences{})
	next, cmd := model.Update(tea.KeyMsg{Type: tea.KeyCtrlC})
	model = next.(launcherModel)
	if cmd != nil {
		t.Fatal("ctrl+c should ask before quitting")
	}
	if !strings.Contains(ansi.Strip(model.View()), "Quit r10n?") {
		t.Fatalf("quit confirmation missing: %s", ansi.Strip(model.View()))
	}
	next, _ = model.Update(tea.KeyMsg{Type: tea.KeyRunes, Runes: []rune("n")})
	if next.(launcherModel).confirmQuit {
		t.Fatal("n should cancel the quit dialog")
	}
	next, _ = model.Update(tea.KeyMsg{Type: tea.KeyCtrlC})
	model = next.(launcherModel)
	next, cmd = model.Update(tea.KeyMsg{Type: tea.KeyRight})
	model = next.(launcherModel)
	next, cmd = model.Update(tea.KeyMsg{Type: tea.KeyEnter})
	if cmd == nil {
		t.Fatal("enter on Yes should quit")
	}
}

func TestLauncherSlashOpensAndEscapeClosesDialog(t *testing.T) {
	model := newLauncher([]launcherEntry{{id: "contacts", title: "Create contacts"}}, Preferences{})
	opened := ansi.Strip(launcherKey(model, "/").View())
	if !strings.Contains(opened, "Automations") || !strings.Contains(opened, "╭") {
		t.Fatalf("slash should open the automation dialog: %s", opened)
	}
	if strings.Contains(opened, "/ commands") {
		t.Fatalf("dialog should replace the home input: %s", opened)
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

func TestLauncherShowsRecentAutomations(t *testing.T) {
	model := newLauncher([]launcherEntry{
		{id: "contacts", title: "Create contacts"},
		{id: "images", title: "Optimize images"},
		{id: "sms", title: "Router SMS"},
	}, Preferences{}, "images", "contacts")
	view := ansi.Strip(model.View())
	if !strings.Contains(view, "Recent") || !strings.Contains(view, "/images") || !strings.Contains(view, "/contacts") {
		t.Fatalf("recent automations missing: %s", view)
	}
	if strings.Contains(view, "/sms") {
		t.Fatalf("unused automation shown as recent: %s", view)
	}
}

func TestExitBannerPrintsPatternAndThanks(t *testing.T) {
	view := ansi.Strip(exitBanner(Preferences{}))
	if !strings.Contains(view, "Thanks for using r10n.") || !strings.Contains(view, "·") {
		t.Fatalf("exit banner missing pattern or greeting: %s", view)
	}
}
