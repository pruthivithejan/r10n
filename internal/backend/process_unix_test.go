//go:build !windows

package backend

import (
	"context"
	"testing"
)

func TestLegacyKeepsTerminalForegroundGroup(t *testing.T) {
	engine := helperBackend(t, "blocking")
	legacy := engine.Command(context.Background(), "legacy", "contacts")
	if legacy.SysProcAttr != nil && legacy.SysProcAttr.Setpgid {
		t.Fatal("legacy prompts would be stopped by SIGTTIN in a background group")
	}
	worker := engine.Command(context.Background(), "worker", "contacts")
	if worker.SysProcAttr == nil || !worker.SysProcAttr.Setpgid {
		t.Fatal("native workers need isolated groups for subtree cancellation")
	}
}
