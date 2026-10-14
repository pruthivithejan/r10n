//go:build !windows

package backend

import (
	"context"
	"testing"
)

func TestConfigureKeepsTerminalForegroundGroup(t *testing.T) {
	engine := helperBackend(t, "blocking")
	configure := engine.Command(context.Background(), "configure", "--template", "template.pdf")
	if configure.SysProcAttr != nil && configure.SysProcAttr.Setpgid {
		t.Fatal("configuration service must share terminal foreground signals")
	}
	worker := engine.Command(context.Background(), "worker", "contacts")
	if worker.SysProcAttr == nil || !worker.SysProcAttr.Setpgid {
		t.Fatal("native workers need isolated groups for subtree cancellation")
	}
}
