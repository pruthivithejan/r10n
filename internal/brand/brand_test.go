package brand

import (
	"encoding/json"
	"os"
	"strings"
	"testing"
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
	if tokens["brand_neon"] != Neon || tokens["brand_text_on_light"] != LightAccent {
		t.Fatalf("terminal accents differ from canonical tokens: %#v", tokens)
	}
}
