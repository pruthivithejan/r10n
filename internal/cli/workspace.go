package cli

import (
	"context"
	"encoding/json"
	"fmt"
	"os"

	"github.com/pruthivithejan/r10n/internal/settings"
	"github.com/pruthivithejan/r10n/internal/tui"
)

func status(args []string) error {
	if len(args) > 1 || (len(args) == 1 && args[0] != "--json") {
		return usage(fmt.Errorf("usage: r10n status [--json]"))
	}
	path, err := settings.Path()
	if err != nil {
		return err
	}
	document, err := settings.Load()
	if err != nil {
		return err
	}
	_, statErr := os.Stat(path)
	result := map[string]any{
		"settings_path":        path,
		"settings_saved":       statErr == nil,
		"output_directory":     document.OutputDirectory,
		"accessible":           document.Accessible,
		"reduced_motion":       document.ReducedMotion,
		"smtp_profile_count":   len(document.SMTPProfiles),
		"pdf_profile_count":    len(document.PDFProfiles),
		"secure_secret_values": false,
	}
	if len(args) == 1 {
		return json.NewEncoder(stdout).Encode(result)
	}
	state := "using built-in defaults"
	if statErr == nil {
		state = "saved"
	}
	fmt.Fprintf(stdout, "Settings: %s (%s)\n", tui.SafeText(path), state)
	fmt.Fprintf(stdout, "Theme: %s\n", tui.SafeText(document.Theme))
	fmt.Fprintf(stdout, "Accessible prompts: %t\n", document.Accessible)
	fmt.Fprintf(stdout, "Reduced motion: %t\n", document.ReducedMotion)
	fmt.Fprintf(stdout, "SMTP profiles: %d\n", len(document.SMTPProfiles))
	fmt.Fprintf(stdout, "PDF profiles: %d\n", len(document.PDFProfiles))
	if document.OutputDirectory != "" {
		fmt.Fprintf(stdout, "Default output directory: %s\n", tui.SafeText(document.OutputDirectory))
	}
	return nil
}

func configure(ctx context.Context, args []string) error {
	return configurePDF(ctx, args)
}
