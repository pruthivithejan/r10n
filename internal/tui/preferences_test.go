package tui

import (
	"context"
	"os"
	"testing"

	"github.com/pruthivithejan/r10n/internal/brand"
	"github.com/pruthivithejan/r10n/internal/settings"
)

func TestPreferencesAreScopedToAnInvocation(t *testing.T) {
	t.Setenv("R10N_CONFIG_DIR", t.TempDir())
	for _, key := range []string{"R10N_ACCESSIBLE", "R10N_NO_MOTION", "R10N_THEME"} {
		t.Setenv(key, "")
	}
	document, err := settings.Load()
	if err != nil {
		t.Fatal(err)
	}
	document.Accessible, document.ReducedMotion, document.Theme = true, true, "light"
	if _, err := settings.Save(document); err != nil {
		t.Fatal(err)
	}
	first, err := ResolveSettings(context.Background())
	if err != nil {
		t.Fatal(err)
	}
	if got := DisplayPreferences(first); !got.Accessible || !got.ReducedMotion || got.Palette != brand.Palette("light") {
		t.Fatalf("saved preferences not applied: %#v", got)
	}
	for _, key := range []string{"R10N_ACCESSIBLE", "R10N_NO_MOTION", "R10N_THEME"} {
		if value := os.Getenv(key); value != "" {
			t.Fatalf("preference resolution changed %s to %q", key, value)
		}
	}
	document.Accessible, document.ReducedMotion, document.Theme = false, false, "dark"
	if _, err := settings.Save(document); err != nil {
		t.Fatal(err)
	}
	second, err := ResolveSettings(context.Background())
	if err != nil {
		t.Fatal(err)
	}
	if got := DisplayPreferences(second); got.Accessible || got.ReducedMotion || got.Palette != brand.Palette("dark") {
		t.Fatalf("next invocation retained old settings: %#v", got)
	}
	if got := DisplayPreferences(first); !got.Accessible || got.Palette != brand.Palette("light") {
		t.Fatalf("earlier invocation changed: %#v", got)
	}
}

func TestPreferencesRespectEnvironmentAndFlagPrecedence(t *testing.T) {
	t.Setenv("R10N_CONFIG_DIR", t.TempDir())
	document, err := settings.Load()
	if err != nil {
		t.Fatal(err)
	}
	document.Accessible, document.ReducedMotion, document.Theme = true, true, "dark"
	if _, err := settings.Save(document); err != nil {
		t.Fatal(err)
	}
	t.Setenv("R10N_ACCESSIBLE", "0")
	t.Setenv("R10N_NO_MOTION", "0")
	t.Setenv("R10N_THEME", "light")
	ctx, err := ResolveSettings(context.Background())
	if err != nil {
		t.Fatal(err)
	}
	if got := DisplayPreferences(ctx); got.Accessible || got.ReducedMotion || got.Palette != brand.Palette("light") {
		t.Fatalf("environment overrides not applied: %#v", got)
	}
	ctx, err = ResolveSettings(WithOverrides(context.Background(), true, true))
	if err != nil {
		t.Fatal(err)
	}
	if got := DisplayPreferences(ctx); !got.Accessible || !got.ReducedMotion || got.Palette != brand.Palette("light") {
		t.Fatalf("command flags not applied: %#v", got)
	}
}
