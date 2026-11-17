package tui

import (
	"testing"

	"github.com/charmbracelet/huh"
	"github.com/charmbracelet/lipgloss"
	"github.com/pruthivithejan/r10n/internal/brand"
)

func TestThemeAppliesPaletteToFocusedAndBlurredStates(t *testing.T) {
	for _, mode := range []string{"dark", "light"} {
		t.Run(mode, func(t *testing.T) {
			t.Setenv("R10N_THEME", mode)
			styles := theme()
			for name, field := range map[string]huh.FieldStyles{
				"focused": styles.Focused, "blurred": styles.Blurred,
			} {
				for role, style := range map[string]lipgloss.Style{
					"title": field.Title, "note": field.NoteTitle,
					"selected option": field.SelectedOption,
				} {
					if style.GetForeground() != brand.Foreground() {
						t.Errorf("%s %s does not use the body foreground: %v", name, role, style.GetForeground())
					}
				}
				if field.TextInput.Prompt.GetForeground() != brand.Palette(mode).Chrome() {
					t.Errorf("%s prompt is not gray", name)
				}
				for role, style := range map[string]lipgloss.Style{
					"selector": field.SelectSelector, "selected prefix": field.SelectedPrefix,
					"multiselector": field.MultiSelectSelector, "cursor": field.TextInput.Cursor,
				} {
					if style.GetForeground() != brand.FocusAccent() {
						t.Errorf("%s %s does not use focus accent", name, role)
					}
				}
				if field.Description.GetForeground() != brand.Palette(mode).Chrome() ||
					field.TextInput.Placeholder.GetForeground() != brand.Palette(mode).Chrome() ||
					field.Option.GetForeground() != brand.Foreground() {
					t.Errorf("%s text colors do not match theme", name)
				}
			}
			if styles.Focused.FocusedButton.GetBackground() != brand.Accent() ||
				styles.Focused.FocusedButton.GetForeground() != brand.OnAccent() ||
				styles.Focused.Next.GetBackground() != brand.Accent() {
				t.Fatal("active buttons or next action retained default colors")
			}
			if styles.Blurred.FocusedButton.GetBackground() != brand.Surface() {
				t.Fatal("inactive button looks focused")
			}
		})
	}
}

func TestProgressAndSpinnerUseResolvedTheme(t *testing.T) {
	for _, mode := range []string{"dark", "light"} {
		t.Run(mode, func(t *testing.T) {
			t.Setenv("R10N_THEME", mode)
			bar := NewProgress(24)
			if bar.FullColor != string(brand.Accent()) || bar.EmptyColor != string(brand.Muted()) {
				t.Fatal("progress bar retained default purple or ignored explicit theme")
			}
			if newSpinner().Style.GetForeground() != brand.Accent() ||
				heading().GetForeground() != brand.Accent() {
				t.Fatal("spinner/heading ignored explicit theme")
			}
		})
	}
}
