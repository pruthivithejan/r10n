// Package tui implements the native Charm interface over the Python contract.
package tui

import (
	"context"
	"fmt"
	"math"
	"strconv"
	"strings"
	"unicode/utf8"

	"github.com/charmbracelet/huh"
	"github.com/pruthivithejan/r10n/internal/backend"
	"github.com/pruthivithejan/r10n/internal/brand"
)

type fieldValue struct {
	text string
	flag bool
}

// parseField provides immediate scalar feedback. Python remains the final
// validation authority and applies any model-level or future constraints.
func parseField(field backend.Field, text string, required bool) (any, error) {
	field, nullable := field.Scalar()
	if text == "" && nullable {
		return nil, nil
	}
	if text == "" && (required || field.Type != "string") {
		return nil, fmt.Errorf("a value is required")
	}
	if len(field.Enum) > 0 {
		for _, option := range field.Enum {
			if option == text {
				return text, nil
			}
		}
		return nil, fmt.Errorf("choose one of %s", strings.Join(field.Enum, ", "))
	}
	if field.Type == "string" {
		if utf8.RuneCountInString(text) < field.MinLength {
			return nil, fmt.Errorf("use at least %d characters", field.MinLength)
		}
		return text, nil
	}
	var number float64
	var value any
	switch field.Type {
	case "integer":
		integer, err := strconv.ParseInt(text, 10, 64)
		if err != nil {
			return nil, fmt.Errorf("enter a whole number")
		}
		number, value = float64(integer), integer
	case "number":
		decimal, err := strconv.ParseFloat(text, 64)
		if err != nil || math.IsNaN(decimal) || math.IsInf(decimal, 0) {
			return nil, fmt.Errorf("enter a finite number")
		}
		number, value = decimal, decimal
	default:
		return nil, fmt.Errorf("unsupported input type %q; use r10n run --input-json", field.Type)
	}
	if field.Minimum != nil && number < *field.Minimum {
		return nil, fmt.Errorf("must be at least %g", *field.Minimum)
	}
	if field.Maximum != nil && number > *field.Maximum {
		return nil, fmt.Errorf("must be at most %g", *field.Maximum)
	}
	if field.ExclusiveMinimum != nil && number <= *field.ExclusiveMinimum {
		return nil, fmt.Errorf("must be greater than %g", *field.ExclusiveMinimum)
	}
	return value, nil
}

func inputForm(task backend.Automation) (*huh.Form, func() (map[string]any, error), error) {
	required := map[string]bool{}
	for _, name := range task.InputSchema.Required {
		required[name] = true
	}
	values := map[string]*fieldValue{}
	fields := make([]huh.Field, 0, len(task.FieldOrder))
	for _, name := range task.FieldOrder {
		schema := task.InputSchema.Properties[name]
		scalar, nullable := schema.Scalar()
		value := &fieldValue{}
		values[name] = value
		title := schema.Title
		if title == "" {
			title = strings.ReplaceAll(name, "_", " ")
		}
		description := schema.Description
		if nullable {
			description += " (optional; leave blank to omit)"
		}
		if scalar.Type == "boolean" {
			value.flag, _ = schema.Default.(bool)
			fields = append(fields, huh.NewConfirm().Key(name).Title(title).
				Description(description).Value(&value.flag).Affirmative("Yes").Negative("No"))
			continue
		}
		if schema.Default != nil {
			value.text = fmt.Sprint(schema.Default)
		}
		if len(scalar.Enum) > 0 {
			options := make([]huh.Option[string], 0, len(scalar.Enum))
			for _, option := range scalar.Enum {
				options = append(options, huh.NewOption(option, option))
			}
			fields = append(fields, huh.NewSelect[string]().Key(name).Title(title).
				Description(description).Options(options...).Value(&value.text))
			continue
		}
		if scalar.Type != "string" && scalar.Type != "integer" && scalar.Type != "number" {
			return nil, nil, fmt.Errorf("%s: unsupported form input %s; use r10n run --input-json", name, scalar.Type)
		}
		fields = append(fields, huh.NewInput().Key(name).Title(title).
			Description(description).Value(&value.text).Validate(func(text string) error {
			_, err := parseField(schema, text, required[name])
			return err
		}))
	}
	// One input per step keeps long descriptions usable in small terminals.
	groups := make([]*huh.Group, 0, len(fields))
	for index, field := range fields {
		groups = append(groups, huh.NewGroup(field).
			Title(fmt.Sprintf("%s · Step %d/%d", task.Title, index+1, len(fields))))
	}
	collect := func() (map[string]any, error) {
		payload := map[string]any{}
		for _, name := range task.FieldOrder {
			schema := task.InputSchema.Properties[name]
			scalar, _ := schema.Scalar()
			if scalar.Type == "boolean" {
				payload[name] = values[name].flag
				continue
			}
			value, err := parseField(schema, values[name].text, required[name])
			if err != nil {
				return nil, fmt.Errorf("%s: %w", name, err)
			}
			payload[name] = value
		}
		return payload, nil
	}
	return huh.NewForm(groups...), collect, nil
}

// RunForm runs a reusable Huh form with r10n's keyboard, accessibility and brand settings.
func RunForm(ctx context.Context, form *huh.Form) error {
	if !Interactive() {
		return fmt.Errorf("this action requires an interactive terminal")
	}
	if err := applySettings(); err != nil {
		return err
	}
	return runForm(ctx, form)
}

func runForm(ctx context.Context, form *huh.Form) error {
	if err := ctx.Err(); err != nil {
		return err
	}
	form.WithTheme(theme()).WithOutput(stderr).WithInput(stdin).WithAccessible(accessible())
	var err error
	if accessible() {
		// huh's plain-prompt runner does not observe context cancellation.
		// Allow the CLI to exit on a signal even while a prompt waits for input.
		finished := make(chan error, 1)
		go func() { finished <- form.RunWithContext(ctx) }()
		select {
		case <-ctx.Done():
			return ctx.Err()
		case err = <-finished:
		}
	} else {
		err = form.RunWithContext(ctx)
	}
	if ctx.Err() != nil {
		return ctx.Err()
	}
	if err == huh.ErrUserAborted {
		return context.Canceled
	}
	return err
}

func theme() *huh.Theme {
	colors := brand.Accent()
	onAccent := brand.OnAccent()
	t := huh.ThemeCharm()
	t.Focused.Base = t.Focused.Base.BorderForeground(colors)
	t.Focused.Title = t.Focused.Title.Foreground(colors).Bold(true)
	t.Focused.NoteTitle = t.Focused.NoteTitle.Foreground(colors).Bold(true)
	t.Focused.SelectSelector = t.Focused.SelectSelector.Foreground(colors)
	t.Focused.MultiSelectSelector = t.Focused.MultiSelectSelector.Foreground(colors)
	t.Focused.SelectedOption = t.Focused.SelectedOption.Foreground(colors)
	t.Focused.SelectedPrefix = t.Focused.SelectedPrefix.Foreground(colors)
	t.Focused.TextInput.Cursor = t.Focused.TextInput.Cursor.Foreground(colors)
	t.Focused.TextInput.Prompt = t.Focused.TextInput.Prompt.Foreground(colors)
	t.Focused.FocusedButton = t.Focused.FocusedButton.Foreground(onAccent).Background(colors)
	t.Group.Title = t.Focused.Title
	t.Group.Description = t.Focused.Description
	return t
}
