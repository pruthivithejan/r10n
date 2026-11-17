package tui

import (
	tea "github.com/charmbracelet/bubbletea"
	"github.com/charmbracelet/huh"
	"github.com/charmbracelet/lipgloss"
	"github.com/charmbracelet/x/ansi"
	r10n "github.com/pruthivithejan/r10n"
	"github.com/pruthivithejan/r10n/internal/backend"
	"github.com/pruthivithejan/r10n/internal/brand"
)

// taskPage renders one automation form beside a compact brand rail.
type taskPage struct {
	task    backend.Automation
	form    *huh.Form
	palette brand.Palette
	width   int
	height  int
}

func newTaskPage(task backend.Automation, prefs Preferences) (*taskPage, *huh.Form, func() (map[string]any, error), error) {
	form, collect, err := inputForm(task)
	if err != nil {
		return nil, nil, nil, err
	}
	form.WithTheme(theme(prefs.Palette)).
		WithOutput(stderr).
		WithInput(stdin).
		WithAccessible(false)
	form.SubmitCmd = tea.Quit
	form.CancelCmd = tea.Quit
	page := &taskPage{task: task, form: form, palette: prefs.Palette, width: 80, height: 24}
	form.WithWidth(page.formWidth())
	return page, form, collect, nil
}

func (m *taskPage) Init() tea.Cmd { return m.form.Init() }

func (m *taskPage) railWidth() int {
	if m.width < 72 {
		return 0
	}
	return min(30, max(20, m.width/4))
}

func (m *taskPage) formWidth() int {
	if rail := m.railWidth(); rail > 0 {
		return max(20, m.width-rail-6)
	}
	return max(20, m.width-4)
}

func (m *taskPage) Update(msg tea.Msg) (tea.Model, tea.Cmd) {
	if size, ok := msg.(tea.WindowSizeMsg); ok {
		m.width, m.height = size.Width, size.Height
		m.form.WithWidth(m.formWidth())
	}
	model, cmd := m.form.Update(msg)
	if form, ok := model.(*huh.Form); ok {
		m.form = form
	}
	if m.form.State == huh.StateCompleted || m.form.State == huh.StateAborted {
		return m, tea.Quit
	}
	return m, cmd
}

func (m *taskPage) rail() string {
	strong := lipgloss.NewStyle().Foreground(m.palette.Foreground()).Bold(true)
	chrome := lipgloss.NewStyle().Foreground(m.palette.Chrome())
	width := m.railWidth()
	lines := []string{
		hatch(m.palette, max(1, width-2), 0),
		strong.Render("r10n"),
		hatch(m.palette, max(1, width-2), 1),
		"",
		chrome.Render("v" + r10n.Version),
		chrome.Render(ansi.Truncate(currentLocation(), max(1, width-2), "…")),
	}
	return lipgloss.NewStyle().Width(width).Padding(0, 1).Render(lipgloss.JoinVertical(lipgloss.Left, lines...))
}

func (m *taskPage) View() string {
	strong := lipgloss.NewStyle().Foreground(m.palette.Foreground()).Bold(true)
	chrome := lipgloss.NewStyle().Foreground(m.palette.Chrome())
	body := strong.Render(SafeText(m.task.Title))
	if m.task.Description != "" {
		body += "\n" + chrome.Render(SafeText(m.task.Description))
	}
	body += "\n\n" + m.form.View()
	right := lipgloss.NewStyle().Width(m.formWidth()).Render(body)

	if rail := m.railWidth(); rail > 0 {
		return lipgloss.NewStyle().Padding(1, 1).Render(
			lipgloss.JoinHorizontal(lipgloss.Top, right, "  ", m.rail()),
		)
	}
	return lipgloss.NewStyle().Padding(1, 1).Render(right)
}
