// Package brand defines r10n's generated, shared terminal identity.
package brand

import (
	_ "embed"
	"os"
	"strings"

	"github.com/charmbracelet/lipgloss"
)

const (
	// Neon is r10n's primary foreground from the user-supplied palette.
	Neon = "#12F7D6"
	// Secondary is the palette's electric-cyan supporting accent.
	Secondary = "#00D1FF"
	// ElectricBlue is the palette's focus and active-control accent.
	ElectricBlue = "#007BFF"
	// DarkBackground and LightForeground are the palette's surface/text pair.
	DarkBackground  = "#0B1320"
	LightForeground = "#F8FAFF"
	// LightAccent is a contrast-safe text/link shade derived from ElectricBlue.
	LightAccent = "#0058B8"
)

// Palette resolves colors for one invocation without changing process state.
type Palette string

func (p Palette) themeColor(light, dark string) lipgloss.Color {
	switch p {
	case "dark":
		return lipgloss.Color(dark)
	case "light":
		return lipgloss.Color(light)
	default:
		if lipgloss.HasDarkBackground() {
			return lipgloss.Color(dark)
		}
		return lipgloss.Color(light)
	}
}

// Accent returns the primary foreground for the palette.
func (p Palette) Accent() lipgloss.Color { return p.themeColor(LightAccent, Neon) }

// Foreground returns the body text color for the palette.
func (p Palette) Foreground() lipgloss.Color { return p.themeColor(DarkBackground, LightForeground) }

// Muted returns the supporting text color for the palette.
func (p Palette) Muted() lipgloss.Color { return p.themeColor(LightAccent, Secondary) }

// Surface returns the inactive control background for the palette.
func (p Palette) Surface() lipgloss.Color { return p.themeColor(LightForeground, DarkBackground) }

// OnAccent returns the text color for a primary-colored control.
func (p Palette) OnAccent() lipgloss.Color { return p.themeColor(LightForeground, DarkBackground) }

func environmentPalette() Palette { return Palette(os.Getenv("R10N_THEME")) }

// Accent resolves the configured theme at render time, including progress bars.
func Accent() lipgloss.Color { return environmentPalette().Accent() }

// FocusAccent returns a high-visibility control indicator for the current theme.
func FocusAccent() lipgloss.Color { return lipgloss.Color(ElectricBlue) }

// Foreground returns readable body text without painting the terminal background.
func Foreground() lipgloss.Color { return environmentPalette().Foreground() }

// Muted returns the supporting palette color for descriptions and inactive controls.
func Muted() lipgloss.Color { return environmentPalette().Muted() }

// Surface returns the background for inactive buttons.
func Surface() lipgloss.Color { return environmentPalette().Surface() }

// OnAccent returns readable text for a brand-colored button.
func OnAccent() lipgloss.Color { return environmentPalette().OnAccent() }

// ASCII contains the canonical foreground-only terminal logo.
//
//go:embed logo.txt
var ASCII string

// Banner returns a decorative neon wordmark or a concise screen-reader title.
func Banner(accessible bool) string {
	return environmentPalette().Banner(accessible)
}

// Banner returns the wordmark or a concise screen-reader title for this palette.
func (p Palette) Banner(accessible bool) string {
	if accessible {
		return "r10n · routine automation"
	}
	return lipgloss.NewStyle().
		Foreground(p.Accent()).
		Render(strings.TrimSpace(ASCII))
}
