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

func themeColor(light, dark string) lipgloss.Color {
	switch os.Getenv("R10N_THEME") {
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

// Accent resolves the configured theme at render time, including progress bars.
func Accent() lipgloss.Color { return themeColor(LightAccent, Neon) }

// FocusAccent returns a high-visibility control indicator for the current theme.
func FocusAccent() lipgloss.Color { return lipgloss.Color(ElectricBlue) }

// Foreground returns readable body text without painting the terminal background.
func Foreground() lipgloss.Color { return themeColor(DarkBackground, LightForeground) }

// Muted returns the supporting palette color for descriptions and inactive controls.
func Muted() lipgloss.Color { return themeColor(LightAccent, Secondary) }

// Surface returns the background for inactive buttons.
func Surface() lipgloss.Color { return themeColor(LightForeground, DarkBackground) }

// OnAccent returns readable text for a brand-colored button.
func OnAccent() lipgloss.Color { return themeColor(LightForeground, DarkBackground) }

// ASCII contains the canonical foreground-only terminal logo.
//
//go:embed logo.txt
var ASCII string

// Banner returns a decorative neon wordmark or a concise screen-reader title.
func Banner(accessible bool) string {
	if accessible {
		return "r10n · routine automation"
	}
	return lipgloss.NewStyle().
		Foreground(Accent()).
		Render(strings.TrimSpace(ASCII))
}
