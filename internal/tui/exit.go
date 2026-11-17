package tui

import (
	"strings"

	"github.com/charmbracelet/lipgloss"
	r10n "github.com/pruthivithejan/r10n"
)

// exitBanner is the quiet pattern printed once the launcher closes.
func exitBanner(prefs Preferences) string {
	chrome := lipgloss.NewStyle().Foreground(prefs.Palette.Chrome())
	width := 72
	pattern := chrome.Render(strings.Repeat("·", width))
	return strings.Join(
		[]string{
			pattern,
			"  " + chrome.Render("r10n  ·  v"+r10n.Version),
			"  " + chrome.Render("Thanks for using r10n."),
			pattern,
		},
		"\n",
	)
}
