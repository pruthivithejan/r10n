//go:build !windows

package backend

import (
	"context"
	"testing"
)

func TestAllBackendCommandsUseIsolatedProcessGroups(t *testing.T) {
	engine := helperBackend(t, "blocking")
	configure := engine.Command(context.Background(), "configure", "--template", "template.pdf")
	if configure.SysProcAttr == nil || !configure.SysProcAttr.Setpgid {
		t.Fatal("backend subprocesses must use isolated groups for cancellation")
	}
	worker := engine.Command(context.Background(), "worker", "contacts")
	if worker.SysProcAttr == nil || !worker.SysProcAttr.Setpgid {
		t.Fatal("native workers need isolated groups for subtree cancellation")
	}
}
