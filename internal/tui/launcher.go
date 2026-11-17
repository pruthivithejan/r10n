package tui

import (
	"context"
	"fmt"
	"strings"

	"github.com/charmbracelet/bubbles/cursor"
	"github.com/charmbracelet/bubbles/textinput"
	tea "github.com/charmbracelet/bubbletea"
	"github.com/charmbracelet/lipgloss"
	"github.com/charmbracelet/x/ansi"
	r10n "github.com/pruthivithejan/r10n"
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
	dialog   bool
}

func newLauncher(entries []launcherEntry, prefs Preferences) launcherModel {
	input := textinput.New()
	input.Prompt = "› "
	input.Placeholder = "Filter automations"
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
	if !m.dialog {
		return nil
	}
	query := strings.ToLower(strings.TrimSpace(m.input.Value()))
	query = strings.TrimSpace(strings.TrimPrefix(query, "/"))
	var matches []launcherEntry
	for _, entry := range m.entries {
		haystack := strings.ToLower(entry.id + " " + entry.title + " " + entry.description)
		if strings.Contains(haystack, query) {
			matches = append(matches, entry)
		}
	}
	return matches
}

func (m launcherModel) openDialog() launcherModel {
	m.dialog = true
	m.input.SetValue("")
	m.active, m.message = 0, ""
	return m
}

func (m launcherModel) closeDialog() launcherModel {
	m.dialog = false
	m.input.SetValue("")
	m.active, m.message = 0, ""
	return m
}

func (m launcherModel) Update(msg tea.Msg) (tea.Model, tea.Cmd) {
	switch msg := msg.(type) {
	case tea.WindowSizeMsg:
		m.width, m.height = msg.Width, msg.Height
		m.input.Width = max(1, m.dialogWidth()-8)
	case tea.KeyMsg:
		switch msg.String() {
		case "ctrl+c", "ctrl+d":
			return m, tea.Quit
		}
		if !m.dialog {
			switch msg.String() {
			case "/", "ctrl+p":
				return m.openDialog(), nil
			case "esc":
				m.message = ""
			}
			return m, nil
		}
		switch msg.String() {
		case "esc":
			return m.closeDialog(), nil
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
			m.message = "No matching automations. Try another search."
			return m, nil
		}
	}
	previous := m.input.Value()
	var cmd tea.Cmd
	m.input, cmd = m.input.Update(msg)
	if m.dialog && m.input.Value() != previous {
		m.active, m.message = 0, ""
	}
	return m, cmd
}

func (m launcherModel) dialogWidth() int {
	return min(m.width, min(72, max(24, m.width-6)))
}

func (m launcherModel) bannerVisible(width int) bool {
	return m.height >= 20 && width >= 38
}

func (m launcherModel) header(width int) string {
	accent := lipgloss.NewStyle().Foreground(m.palette.Accent()).Bold(true)
	muted := lipgloss.NewStyle().Foreground(m.palette.Muted())
	contentWidth := max(1, width-2)
	rule := muted.Render(strings.Repeat("─", contentWidth))
	version := "v" + r10n.Version
	metaLeft := muted.Render("routine automation")
	metaRight := muted.Render(version)
	gap := max(1, contentWidth-lipgloss.Width(metaLeft)-lipgloss.Width(metaRight))
	meta := metaLeft + strings.Repeat(" ", gap) + metaRight

	var header string
	if m.bannerVisible(width) {
		banner := lipgloss.PlaceHorizontal(contentWidth, lipgloss.Center, m.palette.Banner(false))
		header = lipgloss.JoinVertical(
			lipgloss.Left,
			meta,
			rule,
			"",
			banner,
			"",
			rule,
		)
	} else {
		brandLine := accent.Render("r10n") + muted.Render("  ·  "+version)
		header = lipgloss.JoinVertical(
			lipgloss.Left,
			rule,
			lipgloss.PlaceHorizontal(contentWidth, lipgloss.Center, brandLine),
			rule,
		)
	}
	return lipgloss.NewStyle().Padding(0, 1).Render(header)
}

func (m launcherModel) homeBody(width, height int) string {
	accent := lipgloss.NewStyle().Foreground(m.palette.Accent()).Bold(true)
	muted := lipgloss.NewStyle().Foreground(m.palette.Muted())
	headingText := "What would you like to automate?"
	if width < 34 {
		headingText = "Choose an automation"
	}
	heading := accent.Render(headingText)
	helpText := "↑/↓ select  ·  enter open  ·  esc close  ·  ctrl+c quit"
	if width < 56 {
		helpText = "↑/↓  ·  enter  ·  esc  ·  ^C"
	}
	help := muted.Render(helpText)
	if height < 10 || width < 40 {
		hint := muted.Render("/") + muted.Render("  browse automations")
		body := lipgloss.JoinVertical(lipgloss.Center, heading, "", hint, "", help)
		return lipgloss.Place(width, max(1, height), lipgloss.Center, lipgloss.Center, body)
	}
	browse := lipgloss.NewStyle().
		Border(lipgloss.RoundedBorder()).
		BorderForeground(m.palette.Muted()).
		Padding(0, 2).
		Render(muted.Render("/") + muted.Render("  browse automations"))
	body := lipgloss.JoinVertical(lipgloss.Center, heading, "", browse, "", help)
	return lipgloss.Place(width, max(1, height), lipgloss.Center, lipgloss.Center, body)
}

func (m launcherModel) dialogView(width, height int) string {
	accent := lipgloss.NewStyle().Foreground(m.palette.Accent()).Bold(true)
	muted := lipgloss.NewStyle().Foreground(m.palette.Muted())
	innerWidth := max(10, m.dialogWidth()-4)
	m.input.Width = max(8, innerWidth-4)

	var content strings.Builder
	content.WriteString(accent.Render("Automations"))
	content.WriteString("\n")
	content.WriteString(m.input.View())
	content.WriteString("\n\n")

	matches := m.matches()
	if len(matches) == 0 {
		content.WriteString(muted.Render("No matching automations."))
	} else {
		idWidth := 0
		for _, entry := range matches {
			idWidth = max(idWidth, lipgloss.Width("/"+SafeText(entry.id)))
		}
		idWidth = min(idWidth, 18)
		limit := max(1, min(9, height-8))
		start := max(0, m.active-limit+1)
		end := min(len(matches), start+limit)
		for index := start; index < end; index++ {
			entry := matches[index]
			prefix := "  "
			if index == m.active {
				prefix = "❯ "
			}
			name := ansi.Truncate("/"+SafeText(entry.id), idWidth, "…")
			line := prefix + lipgloss.NewStyle().Width(idWidth).Render(name) + "  " + SafeText(entry.title)
			if innerWidth >= 56 {
				description := SafeText(entry.description)
				line += "  " + muted.Render(description)
			}
			line = ansi.Truncate(line, innerWidth, "…")
			if index == m.active {
				line = accent.Render(line)
			}
			content.WriteString(line)
			content.WriteString("\n")
		}
		if len(matches) > limit {
			content.WriteString(muted.Render(fmt.Sprintf("%d of %d automations", m.active+1, len(matches))))
			content.WriteString("\n")
		}
	}
	if m.message != "" {
		content.WriteString("\n")
		content.WriteString(muted.Render(m.message))
	}
	content.WriteString("\n")
	dialogHelp := "↑/↓ choose  ·  enter open  ·  esc close"
	if innerWidth < 44 {
		dialogHelp = "↑/↓  ·  enter  ·  esc"
	}
	content.WriteString(muted.Render(dialogHelp))

	dialog := lipgloss.NewStyle().
		Border(lipgloss.RoundedBorder()).
		BorderForeground(m.palette.Muted()).
		Padding(0, 1).
		Width(m.dialogWidth()).
		Render(content.String())
	return lipgloss.Place(width, max(1, height), lipgloss.Center, lipgloss.Center, dialog)
}

func (m launcherModel) View() string {
	width := max(1, m.width)
	header := m.header(width)
	bodyHeight := max(1, m.height-lipgloss.Height(header)-1)
	body := m.homeBody(width, bodyHeight)
	if m.dialog {
		body = m.dialogView(width, bodyHeight)
	}
	return header + "\n" + body
}
