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
	entries     []launcherEntry
	recent      []string
	input       textinput.Model
	palette     brand.Palette
	width       int
	height      int
	active      int
	selected    string
	message     string
	dialog      bool
	confirmQuit bool
	quitChoice  int
}

func newLauncher(entries []launcherEntry, prefs Preferences, recent ...string) launcherModel {
	input := textinput.New()
	input.Prompt = "› "
	input.CharLimit = 128
	chrome := lipgloss.NewStyle().Foreground(prefs.Palette.Chrome())
	input.PromptStyle = chrome
	input.PlaceholderStyle = chrome
	input.TextStyle = lipgloss.NewStyle().Foreground(prefs.Palette.Foreground())
	input.Cursor.Style = lipgloss.NewStyle().Foreground(brand.FocusAccent())
	input.Focus()
	// A steady cursor avoids distracting animation and respects reduced motion.
	input.Cursor.SetMode(cursor.CursorStatic)
	return launcherModel{
		entries: entries,
		recent:  recent,
		input:   input,
		palette: prefs.Palette,
		width:   80,
		height:  24,
	}
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

func (m launcherModel) recentEntries() []launcherEntry {
	recent := make([]launcherEntry, 0, 5)
	seen := map[string]bool{}
	for _, id := range m.recent {
		if seen[id] {
			continue
		}
		for _, entry := range m.entries {
			if entry.id == id {
				recent = append(recent, entry)
				seen[id] = true
				break
			}
		}
		if len(recent) == 5 {
			break
		}
	}
	return recent
}

func (m launcherModel) openDialog(query string) launcherModel {
	m.dialog = true
	m.input.SetValue(query)
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
		return m, nil
	case tea.KeyMsg:
		if m.confirmQuit {
			switch msg.String() {
			case "y":
				return m, tea.Quit
			case "n", "esc":
				m.confirmQuit = false
				return m, nil
			case "left", "shift+tab", "h":
				m.quitChoice = 0
				return m, nil
			case "right", "tab", "l":
				m.quitChoice = 1
				return m, nil
			case "enter":
				if m.quitChoice == 1 {
					return m, tea.Quit
				}
				m.confirmQuit = false
				return m, nil
			}
			return m, nil
		}
		switch msg.String() {
		case "ctrl+c", "ctrl+d":
			m.confirmQuit, m.quitChoice = true, 0
			return m, nil
		}
		if !m.dialog {
			switch msg.String() {
			case "/", "ctrl+p":
				return m.openDialog(""), nil
			case "esc":
				m.message = ""
				return m, nil
			}
			if msg.Type == tea.KeyRunes && len(msg.Runes) > 0 {
				return m.openDialog(string(msg.Runes)), nil
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

func (m launcherModel) header(width int) string {
	chrome := lipgloss.NewStyle().Foreground(m.palette.Chrome())
	contentWidth := max(1, width-2)
	metaLeft := chrome.Render("r10n")
	if contentWidth >= 54 {
		metaLeft = chrome.Render("r10n  ·  routine automation")
	}
	metaRight := chrome.Render("v" + r10n.Version)
	gap := max(1, contentWidth-lipgloss.Width(metaLeft)-lipgloss.Width(metaRight))
	meta := metaLeft + strings.Repeat(" ", gap) + metaRight

	banner := strings.Split(m.palette.Banner(false), "\n")
	logoWidth := 0
	for _, line := range banner {
		logoWidth = max(logoWidth, lipgloss.Width(line))
	}
	const fieldWidth = 6
	rightWidth := contentWidth - fieldWidth - logoWidth - 2
	if m.height < 12 || rightWidth < 1 {
		return lipgloss.NewStyle().Padding(0, 1).Render(meta)
	}

	rows := []string{meta}
	for index, line := range banner {
		left := chrome.Render(strings.Repeat("·", fieldWidth))
		right := chrome.Render(strings.Repeat("·", max(0, rightWidth-index)))
		logo := lipgloss.NewStyle().Width(logoWidth).Align(lipgloss.Center).Render(
			lipgloss.NewStyle().Foreground(m.palette.Accent()).Render(line),
		)
		rows = append(rows, left+" "+logo+" "+right)
	}
	return lipgloss.NewStyle().Padding(0, 1).Render(lipgloss.JoinVertical(lipgloss.Left, rows...))
}

func (m launcherModel) homeBody(width, height int) string {
	chrome := lipgloss.NewStyle().Foreground(m.palette.Chrome())
	input := m.input
	input.Width = max(1, width-4)
	footer := chrome.Render("/ commands  ·  ctrl+c quit")
	bottom := lipgloss.NewStyle().Padding(0, 1).Render(
		lipgloss.JoinVertical(lipgloss.Left, input.View(), "", footer),
	)

	top := ""
	if entries := m.recentEntries(); len(entries) > 0 && height >= 9 {
		idWidth := 0
		for _, entry := range entries {
			idWidth = max(idWidth, lipgloss.Width("/"+SafeText(entry.id)))
		}
		idWidth = min(idWidth, 18)
		lines := []string{chrome.Render("Recent")}
		for _, entry := range entries {
			name := ansi.Truncate("/"+SafeText(entry.id), idWidth, "…")
			line := "  " + lipgloss.NewStyle().Width(idWidth).Render(chrome.Render(name)) +
				"  " + chrome.Render(SafeText(entry.title))
			lines = append(lines, line)
		}
		top = lipgloss.NewStyle().Padding(0, 1).Render(strings.Join(lines, "\n"))
	}

	topHeight := 0
	if top != "" {
		topHeight = lipgloss.Height(top)
	}
	bottomHeight := lipgloss.Height(bottom)
	if topHeight+bottomHeight+1 > height {
		top, topHeight = "", 0
	}
	gap := max(1, height-topHeight-bottomHeight)
	if top == "" {
		return strings.Repeat("\n", gap) + bottom
	}
	return top + strings.Repeat("\n", gap) + bottom
}

func (m launcherModel) dialogView(width, height int) string {
	chrome := lipgloss.NewStyle().Foreground(m.palette.Chrome())
	strong := lipgloss.NewStyle().Foreground(m.palette.Foreground()).Bold(true)
	innerWidth := max(10, m.dialogWidth()-4)
	m.input.Width = max(8, innerWidth-4)

	var content strings.Builder
	content.WriteString(strong.Render("Automations"))
	content.WriteString("\n")
	content.WriteString(m.input.View())
	content.WriteString("\n\n")

	matches := m.matches()
	if len(matches) == 0 {
		content.WriteString(chrome.Render("No matching automations."))
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
			line := prefix + lipgloss.NewStyle().Width(idWidth).Render(chrome.Render(name)) +
				"  " + chrome.Render(SafeText(entry.title))
			if innerWidth >= 56 {
				line += "  " + chrome.Render(SafeText(entry.description))
			}
			line = ansi.Truncate(line, innerWidth, "…")
			if index == m.active {
				line = strong.Render(line)
			}
			content.WriteString(line)
			content.WriteString("\n")
		}
		if len(matches) > limit {
			content.WriteString(chrome.Render(fmt.Sprintf("%d of %d automations", m.active+1, len(matches))))
			content.WriteString("\n")
		}
	}
	if m.message != "" {
		content.WriteString("\n")
		content.WriteString(chrome.Render(m.message))
	}
	content.WriteString("\n")
	dialogHelp := "↑/↓ choose  ·  enter open  ·  esc close"
	if innerWidth < 44 {
		dialogHelp = "↑/↓  ·  enter  ·  esc"
	}
	content.WriteString(chrome.Render(dialogHelp))

	dialog := lipgloss.NewStyle().
		Border(lipgloss.RoundedBorder()).
		BorderForeground(m.palette.Chrome()).
		Padding(0, 1).
		Width(m.dialogWidth()).
		Render(content.String())
	return lipgloss.Place(width, max(1, height), lipgloss.Center, lipgloss.Center, dialog)
}

func (m launcherModel) quitView(width, height int) string {
	chrome := lipgloss.NewStyle().Foreground(m.palette.Chrome())
	strong := lipgloss.NewStyle().Foreground(m.palette.Foreground()).Bold(true)
	no, yes := chrome.Render("No"), chrome.Render("Yes")
	if m.quitChoice == 0 {
		no = strong.Render("❯ No")
	} else {
		yes = strong.Render("❯ Yes")
	}
	boxWidth := min(52, max(24, width-8))
	help := "←/→ choose  ·  enter confirm  ·  esc cancel"
	if boxWidth-4 < 40 {
		help = "←/→  ·  enter  ·  esc"
	}
	content := lipgloss.JoinVertical(
		lipgloss.Left,
		strong.Render("Quit r10n?"),
		no+"    "+yes,
		chrome.Render(help),
	)
	dialog := lipgloss.NewStyle().
		Border(lipgloss.RoundedBorder()).
		BorderForeground(m.palette.Chrome()).
		Padding(0, 1).
		Width(boxWidth).
		Render(content)
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
	if m.confirmQuit {
		body = m.quitView(width, bodyHeight)
	}
	return header + "\n\n" + body
}
