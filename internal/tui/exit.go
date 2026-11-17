package tui

import (
	"strings"

	"github.com/charmbracelet/lipgloss"
	"github.com/charmbracelet/x/ansi"
	r10n "github.com/pruthivithejan/r10n"
)

// exitBanner is the quiet brand block printed once the launcher closes.
func exitBanner(prefs Preferences) string {
	strong := lipgloss.NewStyle().Foreground(prefs.Palette.Foreground()).Bold(true)
	chrome := lipgloss.NewStyle().Foreground(prefs.Palette.Chrome())
	const width = 68
	name := strong.Render("r10n")
	version := chrome.Render("v" + r10n.Version)
	gap := width - ansi.StringWidth(name) - ansi.StringWidth(version) - 2

	rows := []string{name + " " + hatch(prefs.Palette, max(1, gap), 0) + " " + version}
	banner := strings.Split(prefs.Palette.Banner(false), "\n")
	logoWidth := 0
	for _, line := range banner {
		logoWidth = max(logoWidth, ansi.StringWidth(line))
	}
	const sideWidth = 6
	rightWidth := width - sideWidth*2 - logoWidth - 2
	if rightWidth > 0 {
		for index, line := range banner {
			logo := lipgloss.PlaceHorizontal(logoWidth, lipgloss.Center, line)
			rows = append(rows,
				hatch(prefs.Palette, sideWidth, index)+" "+logo+" "+hatch(prefs.Palette, rightWidth, index),
			)
		}
	}
	rows = append(rows, hatch(prefs.Palette, width, 0), "")
	rows = append(rows, "  "+chrome.Render("Thanks for using r10n."))
	return lipgloss.NewStyle().Padding(0, 1).Render(strings.Join(rows, "\n"))
}
