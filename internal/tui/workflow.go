package tui

import (
	"context"
	"encoding/json"
	"fmt"
	"io"
	"os"
	"strings"

	"github.com/charmbracelet/huh"
	"github.com/pruthivithejan/r10n/internal/backend"
	"github.com/pruthivithejan/r10n/internal/brand"
	"github.com/pruthivithejan/r10n/internal/settings"
	"golang.org/x/term"
)

var stdin = os.Stdin
var stdout io.Writer = os.Stdout
var stderr io.Writer = os.Stderr

// SetIO connects the terminal UI to the command's streams.
func SetIO(in *os.File, out, diagnostics io.Writer) { stdin, stdout, stderr = in, out, diagnostics }

// Preferences hold display choices for one command invocation.
type Preferences struct {
	Accessible    bool
	ReducedMotion bool
	Palette       brand.Palette
}

type preferenceKey struct{}
type overrideKey struct{}

// WithOverrides applies command-line flags to this invocation only.
func WithOverrides(ctx context.Context, accessible, reducedMotion bool) context.Context {
	return context.WithValue(ctx, overrideKey{}, Preferences{Accessible: accessible, ReducedMotion: reducedMotion})
}

// ResolveSettings loads persisted preferences and applies environment and CLI overrides.
func ResolveSettings(ctx context.Context) (context.Context, error) {
	if _, ok := ctx.Value(preferenceKey{}).(Preferences); ok {
		return ctx, nil
	}
	document, err := settings.Load()
	if err != nil {
		return ctx, fmt.Errorf("load r10n settings: %w", err)
	}
	prefs := Preferences{Accessible: document.Accessible, ReducedMotion: document.ReducedMotion, Palette: brand.Palette(document.Theme)}
	if value := os.Getenv("R10N_ACCESSIBLE"); value != "" {
		prefs.Accessible = value == "1"
	}
	if value := os.Getenv("R10N_NO_MOTION"); value != "" {
		prefs.ReducedMotion = value == "1"
	}
	if value := os.Getenv("R10N_THEME"); value != "" {
		prefs.Palette = brand.Palette(value)
	}
	if flags, ok := ctx.Value(overrideKey{}).(Preferences); ok {
		prefs.Accessible = prefs.Accessible || flags.Accessible
		prefs.ReducedMotion = prefs.ReducedMotion || flags.ReducedMotion
	}
	return context.WithValue(ctx, preferenceKey{}, prefs), nil
}

// DisplayPreferences returns the preferences resolved for this invocation.
func DisplayPreferences(ctx context.Context) Preferences {
	if prefs, ok := ctx.Value(preferenceKey{}).(Preferences); ok {
		return prefs
	}
	flags, _ := ctx.Value(overrideKey{}).(Preferences)
	return Preferences{Accessible: flags.Accessible || os.Getenv("R10N_ACCESSIBLE") == "1", ReducedMotion: flags.ReducedMotion || os.Getenv("R10N_NO_MOTION") == "1", Palette: brand.Palette(os.Getenv("R10N_THEME"))}
}
func Interactive() bool {
	return term.IsTerminal(int(stdin.Fd())) && term.IsTerminal(int(os.Stderr.Fd()))
}
func formatValue(value any) string {
	if value == nil {
		return "(none)"
	}
	switch value.(type) {
	case map[string]any, []any:
		raw, _ := json.Marshal(value)
		return string(raw)
	default:
		return fmt.Sprint(value)
	}
}

// ParseField shares schema-driven scalar validation between forms and flags.
func ParseField(field backend.Field, text string, required bool) (any, error) {
	return parseField(field, text, required)
}
func PrintEvent(out io.Writer, event backend.Event, jsonOutput bool) error {
	return printEvent(out, event, jsonOutput)
}

func confirm(ctx context.Context, task backend.Automation, payload map[string]any, yes bool) error {
	if yes {
		return nil
	}
	if !Interactive() {
		return &backend.RunError{Code: 2, Message: "confirmation requires a terminal; review inputs and add --yes"}
	}
	resolved := map[string]any{}
	for name, field := range task.InputSchema.Properties {
		resolved[name] = field.Default
	}
	for name, value := range payload {
		resolved[name] = value
	}
	if err := writeTable(stderr, "Review "+task.Title, resolved, DisplayPreferences(ctx).Palette); err != nil {
		return err
	}
	if task.Confirmation != "" {
		fmt.Fprintln(stderr, SafeText(task.Confirmation))
	}
	var approved bool
	if err := runForm(ctx, huh.NewForm(huh.NewGroup(huh.NewConfirm().Title("Run this automation?").
		Description("Outputs may be overwritten. Review paths and options.").Affirmative("Run").Negative("Cancel").Value(&approved)))); err != nil {
		return err
	}
	if !approved {
		return context.Canceled
	}
	return nil
}

func Execute(ctx context.Context, engine backend.Backend, task backend.Automation, payload map[string]any, yes, jsonOutput bool) error {
	if Interactive() {
		var err error
		if ctx, err = ResolveSettings(ctx); err != nil {
			return err
		}
	}
	if err := confirm(ctx, task, payload, yes); err != nil {
		return err
	}
	if Interactive() && !jsonOutput {
		return executeInteractive(ctx, engine, task, payload)
	}
	return engine.Stream(ctx, task.ID, payload, func(e backend.Event) error { return printEvent(stdout, e, jsonOutput, DisplayPreferences(ctx).Palette) })
}

func RunTask(ctx context.Context, engine backend.Backend, task backend.Automation) error {
	if !Interactive() {
		return &backend.RunError{Code: 2, Message: "native forms require a terminal; supply command flags and --yes or use run --input-json"}
	}
	var err error
	if ctx, err = ResolveSettings(ctx); err != nil {
		return err
	}
	if task.SetupHint != "" {
		return &backend.RunError{Code: 2, Message: task.SetupHint}
	}
	prefs := DisplayPreferences(ctx)
	fmt.Fprintln(stderr, prefs.Palette.Banner(prefs.Accessible))
	fmt.Fprintln(stderr, heading(prefs.Palette).Render(SafeText(task.Title)), SafeText(task.Description))
	form, collect, err := inputForm(task)
	if err != nil {
		return err
	}
	if err = runForm(ctx, form); err != nil {
		return err
	}
	payload, err := collect()
	if err != nil {
		return err
	}
	return Execute(ctx, engine, task, payload, false, false)
}

func Picker(ctx context.Context, engine backend.Backend, catalog backend.Catalog) error {
	if !Interactive() {
		return &backend.RunError{Code: 2, Message: "native forms require a terminal"}
	}
	var err error
	if ctx, err = ResolveSettings(ctx); err != nil {
		return err
	}
	for {
		options := make([]huh.Option[string], 0, len(catalog.Automations))
		for _, task := range catalog.Automations {
			label := task.ID + " · " + task.Title + " · " + task.Category + " — " + task.Description
			if len(task.Roles) > 0 {
				label += " (" + strings.Join(task.Roles, ", ") + ")"
			}
			options = append(options, huh.NewOption(SafeText(label), task.ID))
		}
		var selected string
		prefs := DisplayPreferences(ctx)
		title := prefs.Palette.Banner(prefs.Accessible) + "\nr10n · Routine automation"
		if err := runForm(ctx, huh.NewForm(huh.NewGroup(huh.NewSelect[string]().Title(title).
			Description("Choose a task. Press / to filter.").Options(options...).Value(&selected)))); err != nil {
			return err
		}
		for _, task := range catalog.Automations {
			if task.ID == selected {
				if err := RunTask(ctx, engine, task); err != nil {
					return err
				}
			}
		}
		var again bool
		if err := runForm(ctx, huh.NewForm(huh.NewGroup(huh.NewConfirm().Title("Run another automation?").Value(&again)))); err != nil {
			return err
		}
		if !again {
			return nil
		}
	}
}
