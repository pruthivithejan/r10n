package tui

import (
	"context"
	"fmt"
	"io"
	"math"
	"os"
	"sort"
	"strings"
	"unicode"

	"github.com/charmbracelet/bubbles/progress"
	"github.com/charmbracelet/bubbles/spinner"
	tea "github.com/charmbracelet/bubbletea"
	"github.com/charmbracelet/lipgloss"
	"github.com/charmbracelet/lipgloss/table"
	"github.com/charmbracelet/x/ansi"
	"github.com/pruthivithejan/r10n/internal/backend"
	"golang.org/x/term"
)

var heading = lipgloss.NewStyle().Bold(true)

// SafeText removes terminal control sequences from untrusted automation output.
func SafeText(text string) string {
	return strings.Map(func(char rune) rune {
		if unicode.IsControl(char) && char != '\n' && char != '\t' {
			return -1
		}
		return char
	}, ansi.Strip(text))
}

func writeTable(writer io.Writer, title string, values map[string]any) error {
	keys := make([]string, 0, len(values))
	for key := range values {
		keys = append(keys, key)
	}
	sort.Strings(keys)
	rows := make([][]string, 0, len(keys))
	for _, key := range keys {
		rows = append(rows, []string{SafeText(strings.ReplaceAll(key, "_", " ")), SafeText(formatValue(values[key]))})
	}
	width := 80
	if file, ok := writer.(*os.File); ok {
		if columns, _, err := term.GetSize(int(file.Fd())); err == nil {
			width = max(20, columns)
		}
	}
	rendered := table.New().Border(lipgloss.NormalBorder()).Headers("Field", "Value").
		Rows(rows...).Width(width).Wrap(true).StyleFunc(func(row, column int) lipgloss.Style {
		style := lipgloss.NewStyle().Padding(0, 1)
		if row == table.HeaderRow {
			style = style.Bold(true)
		}
		return style
	})
	if _, err := fmt.Fprintln(writer, heading.Render(title)); err != nil {
		return err
	}
	_, err := fmt.Fprintln(writer, rendered.String())
	return err
}

func printEvent(writer io.Writer, event backend.Event, jsonOutput bool) error {
	if jsonOutput {
		_, err := fmt.Fprintf(writer, "%s\n", event.Raw)
		return err
	}
	switch event.Type {
	case "started":
		_, err := fmt.Fprintln(writer, "Started")
		return err
	case "log", "progress":
		if event.Message != "" {
			_, err := fmt.Fprintln(writer, SafeText(event.Message))
			return err
		}
	case "artifact":
		_, err := fmt.Fprintln(writer, "Artifact:", SafeText(event.Path))
		return err
	case "completed":
		return writeTable(writer, "Results", event.Result)
	}
	return nil
}

type finishedMsg struct{ err error }

type executionModel struct {
	title      string
	status     string
	spinner    spinner.Model
	progress   progress.Model
	percent    float64
	hasTotal   bool
	logs       []string
	artifacts  []string
	result     map[string]any
	events     <-chan backend.Event
	resultErr  <-chan error
	cancel     context.CancelFunc
	err        error
	done       bool
	cancelling bool
	width      int
}

func (m executionModel) nextEvent() tea.Cmd {
	return func() tea.Msg {
		if event, ok := <-m.events; ok {
			return event
		}
		return finishedMsg{<-m.resultErr}
	}
}

func (m executionModel) Init() tea.Cmd {
	return tea.Batch(m.spinner.Tick, m.nextEvent())
}

func (m executionModel) Update(message tea.Msg) (tea.Model, tea.Cmd) {
	switch msg := message.(type) {
	case tea.KeyMsg:
		if msg.String() == "ctrl+c" || msg.String() == "esc" {
			m.cancel()
			m.status, m.cancelling = "Cancelling…", true
		}
	case tea.WindowSizeMsg:
		m.width = max(20, msg.Width-4)
		m.progress.Width = min(60, m.width)
	case backend.Event:
		switch msg.Type {
		case "started":
			m.status = "Running"
		case "progress":
			if msg.Message != "" {
				m.status = SafeText(msg.Message)
			}
			if msg.Total > 0 && !math.IsNaN(msg.Total) && !math.IsInf(msg.Total, 0) {
				m.hasTotal = true
				m.percent = max(0, min(1, msg.Current/msg.Total))
			}
		case "log":
			m.logs = append(m.logs, SafeText(msg.Message))
			if len(m.logs) > 6 {
				m.logs = m.logs[len(m.logs)-6:]
			}
		case "artifact":
			m.artifacts = append(m.artifacts, SafeText(msg.Path))
		case "completed":
			m.result = msg.Result
		}
		if m.cancelling {
			m.status = "Cancelling…"
		}
		return m, m.nextEvent()
	case finishedMsg:
		m.done, m.err = true, msg.err
		m.status = "Completed"
		if msg.err != nil {
			m.status = "Failed: " + SafeText(msg.err.Error())
			if backend.ExitCode(msg.err) == 130 {
				m.status = "Cancelled"
			}
		}
		return m, tea.Quit
	case spinner.TickMsg:
		var command tea.Cmd
		m.spinner, command = m.spinner.Update(msg)
		return m, command
	}
	return m, nil
}

func (m executionModel) View() string {
	status := m.status
	if !m.done {
		status = m.spinner.View() + " " + status
	}
	lines := []string{heading.Render(m.title), status}
	if m.hasTotal {
		lines = append(lines, m.progress.ViewAs(m.percent))
	}
	if len(m.logs) > 0 {
		lines = append(lines, "", strings.Join(m.logs, "\n"))
	}
	if !m.done {
		lines = append(lines, "", "Ctrl+C or Esc: cancel the active automation")
	}
	return lipgloss.NewStyle().Width(m.width).Render(strings.Join(lines, "\n")) + "\n"
}

func executeInteractive(ctx context.Context, engine backend.Backend, task backend.Automation, payload map[string]any) error {
	if accessible() {
		return engine.Stream(ctx, task.ID, payload, func(event backend.Event) error {
			return printEvent(stdout, event, false)
		})
	}
	parentCtx := ctx
	ctx, cancel := context.WithCancel(parentCtx)
	defer cancel()
	events := make(chan backend.Event, 16)
	resultErr := make(chan error, 1)
	finished := make(chan struct{})
	go func() {
		err := engine.Stream(ctx, task.ID, payload, func(event backend.Event) error {
			select {
			case events <- event:
				return nil
			case <-ctx.Done():
				return ctx.Err()
			}
		})
		resultErr <- err
		close(events)
		close(finished)
	}()
	s := spinner.New(spinner.WithSpinner(spinner.Dot))
	model := executionModel{
		title: task.Title, status: "Starting Python worker…", spinner: s,
		progress: progress.New(), events: events, resultErr: resultErr, cancel: cancel, width: 76,
	}
	final, err := tea.NewProgram(model, tea.WithContext(parentCtx), tea.WithInput(stdin), tea.WithOutput(stderr)).Run()
	cancel()
	<-finished
	if err != nil {
		if parentCtx.Err() != nil {
			return context.Canceled
		}
		return err
	}
	completed := final.(executionModel)
	if completed.result != nil {
		if err := writeTable(stdout, "Results", completed.result); err != nil {
			return err
		}
	}
	for _, path := range completed.artifacts {
		if _, err := fmt.Fprintln(stdout, "Artifact:", path); err != nil {
			return err
		}
	}
	return completed.err
}
