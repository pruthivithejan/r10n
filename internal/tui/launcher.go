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

// stripe paints the dashed decoration used above and below the wordmark.
func stripe(palette brand.Palette, width int) string {
	const segment = 3
	var b strings.Builder
	for index := 0; index < width; index += segment {
		style := lipgloss.NewStyle().Foreground(palette.Accent())
		if (index/segment)%2 == 1 {
			style = lipgloss.NewStyle().Foreground(palette.Muted())
		}
		b.WriteString(style.Render(strings.Repeat("-", min(segment, width-index))))
	}
	return b.String()
}

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
			case "ctrl+c", "ctrl+d", "y":
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
	strong := lipgloss.NewStyle().Foreground(m.palette.Foreground()).Bold(true)
	chrome := lipgloss.NewStyle().Foreground(m.palette.Chrome())
	contentWidth := max(1, width-2)
	name := strong.Render("r10n")
	version := chrome.Render("v" + r10n.Version)
	gap := contentWidth - lipgloss.Width(name) - lipgloss.Width(version) - 2
	if gap < 1 {
		return lipgloss.NewStyle().Padding(0, 1).Render(name + " " + version)
	}
	rows := []string{name + " " + stripe(m.palette, gap) + " " + version}

	banner := strings.Split(m.palette.Banner(false), "\n")
	logoWidth := 0
	for _, line := range banner {
		logoWidth = max(logoWidth, ansi.StringWidth(line))
	}
	if m.height >= 14 && contentWidth >= logoWidth {
		for _, line := range banner {
			rows = append(rows, lipgloss.PlaceHorizontal(contentWidth, lipgloss.Center, line))
		}
	}
	rows = append(rows, stripe(m.palette, contentWidth))
	return lipgloss.NewStyle().Padding(0, 1).Render(lipgloss.JoinVertical(lipgloss.Left, rows...))
}

func (m launcherModel) columns() string {
	chrome := lipgloss.NewStyle().Foreground(m.palette.Chrome())
	column := chrome.Render("-   -   -")
	return strings.Join([]string{column, column, column}, "\n")
}

func (m launcherModel) homeBody(width, height int) string {
	chrome := lipgloss.NewStyle().Foreground(m.palette.Chrome())
	accent := lipgloss.NewStyle().Foreground(m.palette.Accent())
	foreground := lipgloss.NewStyle().Foreground(m.palette.Foreground())
	contentWidth := max(1, width-2)

	input := m.input
	input.Width = max(1, contentWidth-2)
	footer := lipgloss.NewStyle().
		Width(contentWidth).
		Align(lipgloss.Center).
		Render(chrome.Render("/ commands  ·  ctrl+c quit"))

	bottomParts := []string{input.View(), ""}
	if height >= 14 {
		bottomParts = append(bottomParts, m.columns(), "")
	}
	bottomParts = append(bottomParts, footer)
	bottom := lipgloss.NewStyle().Padding(0, 1).Render(
		lipgloss.JoinVertical(lipgloss.Left, bottomParts...),
	)

	top := ""
	if entries := m.recentEntries(); len(entries) > 0 && height >= 9 {
		idWidth := 0
		for _, entry := range entries {
			idWidth = max(idWidth, ansi.StringWidth("/"+SafeText(entry.id)))
		}
		idWidth = min(idWidth, 18)
		lines := []string{chrome.Render("Recent")}
		for _, entry := range entries {
			name := ansi.Truncate("/"+SafeText(entry.id), idWidth, "…")
			line := "  " + accent.Render("●") + " " +
				chrome.Render(lipgloss.NewStyle().Width(idWidth).Render(name)) +
				"  " + foreground.Render(SafeText(entry.title))
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
	accent := lipgloss.NewStyle().Foreground(m.palette.Accent()).Bold(true)
	innerWidth := max(10, m.dialogWidth()-4)
	m.input.Width = max(8, innerWidth-4)

	var content strings.Builder
	title := accent.Render("Automations")
	fill := innerWidth - lipgloss.Width(title) - 1
	if fill > 0 {
		title += " " + stripe(m.palette, fill)
	}
	content.WriteString(title)
	content.WriteString("\n")
	content.WriteString(m.input.View())
	content.WriteString("\n\n")

	matches := m.matches()
	if len(matches) == 0 {
		content.WriteString(chrome.Render("No matching automations."))
	} else {
		idWidth := 0
		for _, entry := range matches {
			idWidth = max(idWidth, ansi.StringWidth("/"+SafeText(entry.id)))
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
			plain := prefix + fmt.Sprintf("%-*s", idWidth, name) + "  " + SafeText(entry.title)
			if innerWidth >= 56 {
				plain += "  " + SafeText(entry.description)
			}
			plain = ansi.Truncate(plain, innerWidth, "…")
			if index == m.active {
				content.WriteString(
					lipgloss.NewStyle().Width(innerWidth).
						Background(m.palette.Accent()).
						Foreground(m.palette.OnAccent()).
						Bold(true).
						Render(plain),
				)
			} else {
				line := prefix + chrome.Render(fmt.Sprintf("%-*s", idWidth, name)) +
					"  " + strong.Render(SafeText(entry.title))
				if innerWidth >= 56 {
					line += "  " + chrome.Render(SafeText(entry.description))
				}
				content.WriteString(ansi.Truncate(line, innerWidth, "…"))
			}
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
	content.WriteString(lipgloss.NewStyle().Width(innerWidth).Align(lipgloss.Center).Render(chrome.Render(dialogHelp)))

	dialog := lipgloss.NewStyle().
		Border(lipgloss.RoundedBorder()).
		BorderForeground(m.palette.Accent()).
		Padding(0, 1).
		Width(m.dialogWidth()).
		Render(content.String())
	return lipgloss.Place(width, max(1, height), lipgloss.Center, lipgloss.Center, dialog)
}

func (m launcherModel) quitButton(label, shortcut string, selected bool) string {
	text := lipgloss.NewStyle().Underline(true).Render(shortcut) + label[len(shortcut):]
	style := lipgloss.NewStyle().Padding(0, 1)
	if selected {
		style = style.
			Background(m.palette.Accent()).
			Foreground(m.palette.OnAccent()).
			Bold(true)
	} else {
		style = style.
			Background(m.palette.Panel()).
			Foreground(m.palette.Foreground())
	}
	return style.Render(text)
}

func (m launcherModel) quitView(width, height int) string {
	chrome := lipgloss.NewStyle().Foreground(m.palette.Chrome())
	strong := lipgloss.NewStyle().Foreground(m.palette.Foreground()).Bold(true)
	boxWidth := min(48, max(28, width-8))
	innerWidth := max(20, boxWidth-4)

	no := m.quitButton("Nope", "N", m.quitChoice == 0)
	yes := m.quitButton("Yep!", "Y", m.quitChoice == 1)
	buttons := lipgloss.PlaceHorizontal(innerWidth, lipgloss.Center, no+"  "+yes)
	title := "Are you sure you want to quit?"
	hints := []string{"To quit without confirmation", "press ctrl+c twice."}
	if innerWidth < 40 {
		title = "Quit r10n?"
		hints = []string{"ctrl+c twice to quit."}
	}
	helpLines := make([]string, 0, len(hints))
	for _, hint := range hints {
		helpLines = append(helpLines, lipgloss.PlaceHorizontal(innerWidth, lipgloss.Center, chrome.Render(hint)))
	}
	content := lipgloss.JoinVertical(
		lipgloss.Left,
		lipgloss.PlaceHorizontal(innerWidth, lipgloss.Center, strong.Render(title)),
		"",
		buttons,
		"",
		lipgloss.JoinVertical(lipgloss.Left, helpLines...),
	)
	dialog := lipgloss.NewStyle().
		Border(lipgloss.RoundedBorder()).
		BorderForeground(m.palette.Accent()).
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
	return header + "\n" + body
}
