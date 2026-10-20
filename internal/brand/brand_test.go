package brand

import (
	"encoding/json"
	"os"
	"strings"
	"testing"

	"github.com/charmbracelet/lipgloss"
)

func TestEmbeddedLogoMatchesCanonicalSource(t *testing.T) {
	canonical, err := os.ReadFile("../../assets/brand/r10n-ascii.txt")
	if err != nil {
		t.Fatal(err)
	}
	if strings.TrimSpace(ASCII) != strings.TrimSpace(string(canonical)) {
		t.Fatal("embedded terminal wordmark differs from its canonical source")
	}
}

func TestAccessibleBannerUsesReadableText(t *testing.T) {
	if got := Banner(true); got != "r10n · routine automation" {
		t.Fatalf("accessible banner = %q", got)
	}
}

func TestAccentColorsMatchCanonicalTokens(t *testing.T) {
	data, err := os.ReadFile("../../assets/brand/tokens.json")
	if err != nil {
		t.Fatal(err)
	}
	var tokens map[string]string
	if err := json.Unmarshal(data, &tokens); err != nil {
		t.Fatal(err)
	}
	if tokens["brand_neon"] != Neon ||
		tokens["brand_secondary"] != Secondary ||
		tokens["electric_blue"] != ElectricBlue ||
		tokens["dark_background"] != DarkBackground ||
		tokens["light_foreground"] != LightForeground ||
		tokens["brand_text_on_light"] != LightAccent {
		t.Fatalf("terminal accents differ from canonical tokens: %#v", tokens)
	}
}

func TestPaletteHonorsExplicitThemeAndSystemBackground(t *testing.T) {
	background := lipgloss.HasDarkBackground()
	t.Cleanup(func() { lipgloss.SetHasDarkBackground(background) })
	for _, test := range []struct {
		theme string
		dark  bool
		want  string
		text  string
	}{
		{"dark", false, Neon, LightForeground},
		{"light", true, LightAccent, DarkBackground},
		{"system", true, Neon, LightForeground},
		{"system", false, LightAccent, DarkBackground},
	} {
		t.Run(test.theme+"/"+test.want, func(t *testing.T) {
			t.Setenv("R10N_THEME", test.theme)
			lipgloss.SetHasDarkBackground(test.dark)
			if got := string(Accent()); got != test.want {
				t.Fatalf("accent = %s, want %s", got, test.want)
			}
			if got := string(Foreground()); got != test.text {
				t.Fatalf("foreground = %s, want %s", got, test.text)
			}
			if FocusAccent() != lipgloss.Color(ElectricBlue) {
				t.Fatal("focus indicator does not use electric blue")
			}
		})
	}
}
