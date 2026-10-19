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

// Accent returns the configured terminal-safe accent or adapts to the terminal.
func Accent() lipgloss.TerminalColor {
	switch os.Getenv("R10N_THEME") {
	case "dark":
		return lipgloss.Color(Neon)
	case "light":
		return lipgloss.Color(LightAccent)
	default:
		return lipgloss.AdaptiveColor{Light: LightAccent, Dark: Neon}
	}
}

// FocusAccent returns a high-visibility control indicator for the current theme.
func FocusAccent() lipgloss.TerminalColor {
	switch os.Getenv("R10N_THEME") {
	case "dark":
		return lipgloss.Color(Neon)
	case "light":
		return lipgloss.Color(ElectricBlue)
	default:
		return lipgloss.AdaptiveColor{Light: ElectricBlue, Dark: Neon}
	}
}

// OnAccent returns readable text for a brand-colored button.
func OnAccent() lipgloss.TerminalColor {
	switch os.Getenv("R10N_THEME") {
	case "dark":
		return lipgloss.Color(DarkBackground)
	case "light":
		return lipgloss.Color(LightForeground)
	default:
		return lipgloss.AdaptiveColor{Light: LightForeground, Dark: DarkBackground}
	}
}

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
