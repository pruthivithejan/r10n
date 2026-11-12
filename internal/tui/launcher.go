package tui

import (
	"context"
	"fmt"
	"strings"

	"github.com/charmbracelet/bubbles/cursor"
	"github.com/charmbracelet/bubbles/textinput"
	tea "github.com/charmbracelet/bubbletea"
	"github.com/charmbracelet/lipgloss"
	"github.com/pruthivithejan/r10n/internal/brand"
)

// LauncherCommand adds a native interactive workflow to the automation launcher.
// Registry automations remain the source of truth for schema-driven tasks.
type LauncherCommand struct {
	ID, Title, Description string
	Run                    func(context.Context) error
}

type launcherEntry struct {
	id, title, description string
}

type launcherModel struct {
	entries  []launcherEntry
	input    textinput.Model
	palette  brand.Palette
	width    int
	height   int
	active   int
	selected string
	message  string
}

func newLauncher(entries []launcherEntry, prefs Preferences) launcherModel {
	input := textinput.New()
	input.Prompt = "› "
	input.Placeholder = "Type / to browse automations"
	input.CharLimit = 128
	input.PromptStyle = lipgloss.NewStyle().Foreground(prefs.Palette.Accent()).Bold(true)
	input.PlaceholderStyle = lipgloss.NewStyle().Foreground(prefs.Palette.Muted())
	input.TextStyle = lipgloss.NewStyle().Foreground(prefs.Palette.Foreground())
	input.Cursor.Style = lipgloss.NewStyle().Foreground(brand.FocusAccent())
	input.Focus()
	// A steady cursor avoids distracting animation and respects reduced motion.
	input.Cursor.SetMode(cursor.CursorStatic)
	return launcherModel{entries: entries, input: input, palette: prefs.Palette, width: 80, height: 24}
}

func (m launcherModel) Init() tea.Cmd { return nil }

func (m launcherModel) matches() []launcherEntry {
	query := strings.TrimSpace(m.input.Value())
	if !strings.HasPrefix(query, "/") {
		return nil
	}
	query = strings.ToLower(strings.TrimSpace(strings.TrimPrefix(query, "/")))
	var matches []launcherEntry
	for _, entry := range m.entries {
		haystack := strings.ToLower(entry.id + " " + entry.title + " " + entry.description)
		if strings.Contains(haystack, query) {
			matches = append(matches, entry)
		}
	}
	return matches
}

func (m launcherModel) Update(msg tea.Msg) (tea.Model, tea.Cmd) {
	switch msg := msg.(type) {
	case tea.WindowSizeMsg:
		m.width, m.height = msg.Width, msg.Height
		m.input.Width = max(1, msg.Width-8)
	case tea.KeyMsg:
		switch msg.String() {
		case "ctrl+c", "ctrl+d":
			return m, tea.Quit
		case "esc":
			m.input.SetValue("")
			m.active, m.message = 0, ""
			return m, nil
		case "up", "shift+tab":
			if m.active > 0 {
				m.active--
			}
			return m, nil
		case "down", "tab":
			if matches := m.matches(); m.active+1 < len(matches) {
				m.active++
			}
			return m, nil
		case "enter":
			matches := m.matches()
			if len(matches) > 0 {
				m.selected = matches[min(m.active, len(matches)-1)].id
				return m, tea.Quit
			}
			if strings.HasPrefix(strings.TrimSpace(m.input.Value()), "/") {
				m.message = "No matching commands. Try another search."
			} else {
				m.message = "Type / to choose an automation."
			}
			return m, nil
		}
	}
	previous := m.input.Value()
	var cmd tea.Cmd
	m.input, cmd = m.input.Update(msg)
	if m.input.Value() != previous {
		m.active, m.message = 0, ""
	}
	return m, cmd
}

func (m launcherModel) View() string {
	width := max(1, m.width-2)
	accent := lipgloss.NewStyle().Foreground(m.palette.Accent()).Bold(true)
	muted := lipgloss.NewStyle().Foreground(m.palette.Muted())
	bar := accent.Render("r10n") + muted.Render("  /  routine automation")
	var b strings.Builder
	b.WriteString(lipgloss.NewStyle().Width(width).MaxWidth(width).Padding(0, 1).Background(m.palette.Surface()).Render(bar))
	b.WriteString("\n\n")
	if m.height >= 22 && width >= 42 && !strings.HasPrefix(strings.TrimSpace(m.input.Value()), "/") {
		b.WriteString(m.palette.Banner(false))
		b.WriteString("\n\n")
	}
	b.WriteString(lipgloss.NewStyle().MaxWidth(width).Render(accent.Render("What would you like to automate?")))
	b.WriteString("\n")
	b.WriteString(lipgloss.NewStyle().MaxWidth(width).Render(muted.Render("Start with / to find a command.")))
	b.WriteString("\n\n")
	b.WriteString(m.input.View())
	if m.message != "" {
		b.WriteString("\n" + muted.Render(m.message))
	}
	if strings.HasPrefix(strings.TrimSpace(m.input.Value()), "/") {
		matches := m.matches()
		if len(matches) == 0 {
			b.WriteString("\n  No commands found")
		} else {
			limit := max(1, min(6, m.height-12))
			start := max(0, m.active-limit+1)
			end := min(len(matches), start+limit)
			for index := start; index < end; index++ {
				entry := matches[index]
				prefix := "  "
				if index == m.active {
					prefix = "❯ "
				}
				line := prefix + "/" + strings.Join(strings.Fields(SafeText(entry.id)), " ") + "  " + strings.Join(strings.Fields(SafeText(entry.title)), " ")
				if index == m.active {
					line = accent.Render(line)
				}
				b.WriteString("\n" + lipgloss.NewStyle().MaxWidth(width).Render(line))
			}
			if len(matches) > limit {
				b.WriteString("\n" + muted.Render(fmt.Sprintf("  %d of %d commands", m.active+1, len(matches))))
			}
		}
	}
	help := "↑/↓ select  ·  enter open  ·  esc clear  ·  ctrl+c quit"
	if width < 55 {
		help = "↑↓ select  enter open  ^C quit"
	}
	b.WriteString("\n\n" + lipgloss.NewStyle().MaxWidth(width).Render(muted.Render(help)))
	return b.String()
}
