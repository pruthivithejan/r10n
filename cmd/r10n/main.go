// r10n is the native Charm shell around the Python automation worker.
package main

import (
	"context"
	"fmt"
	"os"
	"os/signal"
	"syscall"

	"github.com/pruthivithejan/r10n/internal/backend"
	"github.com/pruthivithejan/r10n/internal/shell"
)

func main() {
	ctx, stop := signal.NotifyContext(context.Background(), os.Interrupt, syscall.SIGTERM)
	defer stop()
	err := shell.Run(ctx, os.Args[1:])
	if err != nil {
		fmt.Fprintln(os.Stderr, "r10n:", shell.SafeText(err.Error()))
	}
	os.Exit(backend.ExitCode(err))
}
