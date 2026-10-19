package tui

import (
	"bytes"
	"context"
	"encoding/json"
	"strings"
	"testing"

	"github.com/charmbracelet/bubbles/spinner"
	tea "github.com/charmbracelet/bubbletea"
	"github.com/charmbracelet/x/ansi"
	"github.com/pruthivithejan/r10n/internal/backend"
)

func pointer(value float64) *float64 { return &value }

func TestParseScalarFields(t *testing.T) {
	for _, test := range []struct {
		name  string
		field backend.Field
		text  string
		valid bool
	}{
		{"string", backend.Field{Type: "string", MinLength: 2}, "Hi", true},
		{"short", backend.Field{Type: "string", MinLength: 2}, "a", false},
		{"unicode-length", backend.Field{Type: "string", MinLength: 2}, "é", false},
		{"enum", backend.Field{Type: "string", Enum: []string{"A4", "Letter"}}, "A4", true},
		{"bad-enum", backend.Field{Type: "string", Enum: []string{"A4"}}, "Legal", false},
		{"integer", backend.Field{Type: "integer", Minimum: pointer(1), Maximum: pointer(100)}, "85", true},
		{"decimal-integer", backend.Field{Type: "integer"}, "1.5", false},
		{"below-minimum", backend.Field{Type: "integer", Minimum: pointer(1)}, "0", false},
		{"above-maximum", backend.Field{Type: "integer", Maximum: pointer(100)}, "101", false},
		{"number", backend.Field{Type: "number", ExclusiveMinimum: pointer(0)}, "1.5", true},
		{"exclusive-minimum", backend.Field{Type: "number", ExclusiveMinimum: pointer(0)}, "0", false},
		{"nan", backend.Field{Type: "number"}, "NaN", false},
		{"infinite", backend.Field{Type: "number"}, "Inf", false},
		{"unknown-type", backend.Field{Type: "array"}, "value", false},
	} {
		t.Run(test.name, func(t *testing.T) {
			_, err := parseField(test.field, test.text, true)
			if (err == nil) != test.valid {
				t.Fatalf("valid=%v, error=%v", test.valid, err)
			}
		})
	}
	field := backend.Field{AnyOf: []backend.Field{{Type: "string"}, {Type: "null"}}}
	if value, err := parseField(field, "", false); value != nil || err != nil {
		t.Fatalf("optional blank should map to null, got %v %v", value, err)
	}
}

func TestInputFormDefaults(t *testing.T) {
	task := backend.Automation{Title: "Test", FieldOrder: []string{"path", "quality", "enabled", "optional", "format"},
		InputSchema: backend.Schema{Properties: map[string]backend.Field{
			"path": {Type: "string", Default: "input.txt"}, "quality": {Type: "integer", Default: float64(85)},
			"enabled":  {Type: "boolean", Default: true},
			"optional": {AnyOf: []backend.Field{{Type: "string"}, {Type: "null"}}},
			"format":   {Type: "string", Enum: []string{"webp", "png"}, Default: "webp"},
		}}}
	_, collect, err := inputForm(task)
	if err != nil {
		t.Fatal(err)
	}
	payload, err := collect()
	if err != nil {
		t.Fatal(err)
	}
	if payload["path"] != "input.txt" || payload["quality"] != int64(85) ||
		payload["enabled"] != true || payload["optional"] != nil || payload["format"] != "webp" {
		t.Fatal(payload)
	}
}

func TestProgressStateAndCancellation(t *testing.T) {
	cancelled := false
	model := executionModel{width: 50, cancel: func() { cancelled = true }}
	next, _ := model.Update(backend.Event{Type: "progress", Current: 5, Total: 10, Message: "Halfway"})
	model = next.(executionModel)
	if !model.hasTotal || model.percent != 0.5 || model.status != "Halfway" {
		t.Fatal(model)
	}
	for index := 0; index < 20; index++ {
		next, _ = model.Update(backend.Event{Type: "log", Message: "a log"})
		model = next.(executionModel)
	}
	if len(model.logs) != 6 {
		t.Fatal("logs must be bounded")
	}
	next, _ = model.Update(tea.KeyMsg{Type: tea.KeyCtrlC})
	model = next.(executionModel)
	if !cancelled || !model.cancelling {
		t.Fatal("Ctrl+C must cancel the worker, not just leave the view")
	}
	next, _ = model.Update(finishedMsg{context.Canceled})
	model = next.(executionModel)
	if !model.done || model.status != "Cancelled" || backend.ExitCode(model.err) != 130 {
		t.Fatal(model)
	}
}

func TestReducedMotionOmitsTheAnimatedSpinner(t *testing.T) {
	indicator := spinner.New(spinner.WithSpinner(spinner.Dot))
	model := executionModel{
		title: "Contacts", status: "Running", spinner: indicator, animate: false, width: 40,
	}
	view := model.View()
	if !strings.Contains(view, "Running") || strings.Contains(view, indicator.View()) {
		t.Fatalf("reduced-motion view should show static status without a spinner: %q", view)
	}
	model.animate = true
	if !strings.Contains(model.View(), indicator.View()) {
		t.Fatal("standard motion should show the spinner")
	}
}

func TestRawJSONOutputAndTerminalSanitization(t *testing.T) {
	var output bytes.Buffer
	event := backend.Event{Type: "log", Raw: json.RawMessage(`{"type":"log","message":"hello"}`)}
	if err := printEvent(&output, event, true); err != nil ||
		output.String() != string(event.Raw)+"\n" {
		t.Fatal("JSON mode must not insert UI decoration")
	}
	if got := SafeText("\x1b[31mred\x1b[0m\x00"); got != "red" {
		t.Fatalf("terminal controls not removed: %q", got)
	}
	if got := SafeText("error\x1b]0;foreign window title\x07"); got != "error" {
		t.Fatalf("terminal OSC sequences not removed: %q", got)
	}
}

func TestResultTableWrapsLongPaths(t *testing.T) {
	var output bytes.Buffer
	if err := writeTable(&output, "Review", map[string]any{"output_file": strings.Repeat("long-path/", 20)}); err != nil {
		t.Fatal(err)
	}
	for _, line := range strings.Split(output.String(), "\n") {
		if ansi.StringWidth(line) > 80 {
			t.Fatalf("table exceeds terminal width: %q", line)
		}
	}
}
