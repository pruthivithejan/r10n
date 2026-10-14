//go:build windows

package backend

import (
	"os/exec"
	"strconv"
)

func configureProcess(cmd *exec.Cmd, legacy bool) {
	cmd.Cancel = func() error {
		// Kill the frozen runtime's children as well as its onefile launcher.
		err := exec.Command("taskkill", "/PID", strconv.Itoa(cmd.Process.Pid), "/T", "/F").Run()
		if err != nil {
			return cmd.Process.Kill()
		}
		return nil
	}
}
