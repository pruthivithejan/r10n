package brand

import (
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
