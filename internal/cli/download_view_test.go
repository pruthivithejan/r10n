package cli

import (
	"strings"
	"testing"

	"github.com/charmbracelet/lipgloss"
	"github.com/charmbracelet/x/ansi"
	"github.com/muesli/termenv"
)

func TestDownloadViewUsesBrandColorsAndFitsTerminal(t *testing.T) {
	profile := lipgloss.ColorProfile()
	t.Cleanup(func() { lipgloss.SetColorProfile(profile) })
	lipgloss.SetColorProfile(termenv.TrueColor)
	t.Setenv("R10N_THEME", "dark")
	t.Setenv("R10N_ACCESSIBLE", "")
	for _, width := range []int{40, 80, 120} {
		view := downloadProgressView("r10n-macos-arm64.tar.gz", 12_000_000, 24_000_000, width)
		if lipgloss.Width(view) >= width {
			t.Fatalf("progress wraps at width %d: %q", width, view)
		}
		if !strings.Contains(view, "12.0 MB / 24.0 MB · 50%") {
			t.Fatalf("progress lost numeric status at width %d: %q", width, view)
		}
	}
	view := downloadProgressView("bundle", 12_000_000, 24_000_000, 120)
	if !strings.Contains(view, "\x1b[38;2;18;247;214m") ||
		strings.Contains(view, "117;113;249") {
		t.Fatalf("download did not use brand palette: %q", view)
	}
}

func TestDownloadViewIsLinearForAccessibilityAndSanitizesLabels(t *testing.T) {
	t.Setenv("R10N_ACCESSIBLE", "1")
	view := downloadProgressView("bundle\x1b[31m\n\t", 12_000_000, 24_000_000, 80)
	if view != ansi.Strip(view) || strings.ContainsAny(view, "\r\n\t[]") ||
		!strings.Contains(view, "50%") {
		t.Fatalf("accessible progress is not plain linear text: %q", view)
	}
}

func TestDownloadViewNeverWrapsKnownOrUnknownTotals(t *testing.T) {
	for _, total := range []int64{0, 24_000_000} {
		for width := 1; width <= 120; width++ {
			view := downloadProgressView("r10n-macos-arm64.tar.gz", 12_000_000, total, width)
			if lipgloss.Width(view) >= width {
				t.Fatalf("progress wraps at width %d with total %d: %q", width, total, view)
			}
			if total == 0 && width >= 30 && !strings.Contains(view, "total unknown") {
				t.Fatalf("unknown-total status lost at width %d: %q", width, view)
			}
			if total > 0 && width >= 4 && !strings.Contains(view, "50%") {
				t.Fatalf("known-total status lost at width %d: %q", width, view)
			}
		}
	}
}
