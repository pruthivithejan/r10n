//go:build !windows

package backend

import (
	"os/exec"
	"syscall"
)

func configureProcess(cmd *exec.Cmd) {
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
