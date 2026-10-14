// r10n is the native command interface and Charm UI for Python automations.
package main

import (
	"context"
	"fmt"
	"os"
	"os/signal"
	"syscall"

	"github.com/pruthivithejan/r10n/internal/backend"
	"github.com/pruthivithejan/r10n/internal/cli"
	"github.com/pruthivithejan/r10n/internal/tui"
)

func main() {
	ctx, stop := signal.NotifyContext(context.Background(), os.Interrupt, syscall.SIGTERM)
	defer stop()
	err := cli.Run(ctx, os.Args[1:])
	if err != nil {
		fmt.Fprintln(os.Stderr, "r10n:", tui.SafeText(err.Error()))
	}
	os.Exit(backend.ExitCode(err))
}
