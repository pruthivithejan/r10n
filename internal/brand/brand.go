// Package brand defines r10n's generated, shared terminal identity.
package brand

import (
	_ "embed"
	"os"
	"strings"

	"github.com/charmbracelet/lipgloss"
)

const (
	// Neon is the r10n wordmark's accessible foreground on dark surfaces.
	Neon = "#67D5FF"
	// LightAccent is its text/link variant for light backgrounds.
	LightAccent = "#006B87"
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

// OnAccent returns readable text for a brand-colored button.
func OnAccent() lipgloss.TerminalColor {
	switch os.Getenv("R10N_THEME") {
	case "dark":
		return lipgloss.Color("#062A38")
	case "light":
		return lipgloss.Color("#FFFFFF")
	default:
		return lipgloss.AdaptiveColor{Light: "#FFFFFF", Dark: "#062A38"}
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
