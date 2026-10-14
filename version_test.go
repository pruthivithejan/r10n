package r10n

import (
	"regexp"
	"testing"
)

func TestVersionUsesProjectMetadata(t *testing.T) {
	if !regexp.MustCompile(`^\d+\.\d+\.\d+$`).MatchString(Version) {
		t.Fatalf("invalid release version %q", Version)
	}
}
