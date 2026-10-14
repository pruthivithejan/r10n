//go:build !windows

package backend

import (
	"os"
	"os/exec"
	"syscall"
	"time"
)

func configureProcess(cmd *exec.Cmd, foreground bool) {
	if foreground {
		// The browser configuration service remains in the foreground group.
		// It receives terminal signals alongside the Go launcher.
		cmd.Cancel = func() error { return cmd.Process.Signal(os.Interrupt) }
		cmd.WaitDelay = 2 * time.Second
		return
	}
	// uv and automations can spawn children. Cancel the entire worker group,
	// not just the launcher, so Ctrl+C cannot leave an automation running.
	cmd.SysProcAttr = &syscall.SysProcAttr{Setpgid: true}
	cmd.Cancel = func() error {
		err := syscall.Kill(-cmd.Process.Pid, syscall.SIGKILL)
		if err == syscall.ESRCH {
			return nil
		}
		return err
	}
}
