package cli

import (
	"bytes"
	"context"
	"encoding/json"
	"flag"
	"fmt"
	"io"
	"os"
	"path/filepath"
	"strconv"
	"strings"

	"github.com/charmbracelet/huh"
	"github.com/pruthivithejan/r10n/internal/backend"
	"github.com/pruthivithejan/r10n/internal/settings"
	"github.com/pruthivithejan/r10n/internal/tui"
)

func settingsCommand(ctx context.Context, args []string) error {
	if len(args) == 0 {
		return usage(fmt.Errorf("usage: r10n config <path|edit|add-smtp-profile|edit-smtp-profile|set-secret|delete-secret|import|export>"))
	}
	switch args[0] {
	case "path":
		if len(args) != 1 {
			return usage(fmt.Errorf("usage: r10n config path"))
		}
		path, err := settings.Path()
		if err != nil {
			return err
		}
		fmt.Fprintln(stdout, path)
		return nil
	case "edit":
		if len(args) != 1 {
			return usage(fmt.Errorf("usage: r10n config edit"))
		}
		return editSettings(ctx)
	case "add-smtp-profile":
		if len(args) != 2 || strings.TrimSpace(args[1]) == "" {
			return usage(fmt.Errorf("usage: r10n config add-smtp-profile NAME"))
		}
		return promptSMTPProfile(ctx, strings.TrimSpace(args[1]), false)
	case "edit-smtp-profile":
		if len(args) != 2 || strings.TrimSpace(args[1]) == "" {
			return usage(fmt.Errorf("usage: r10n config edit-smtp-profile NAME"))
		}
		return promptSMTPProfile(ctx, strings.TrimSpace(args[1]), true)
	case "set-secret":
		if len(args) != 2 || strings.TrimSpace(args[1]) == "" {
			return usage(fmt.Errorf("usage: r10n config set-secret PROFILE"))
		}
		return setSMTPSecret(ctx, strings.TrimSpace(args[1]))
	case "delete-secret":
		if len(args) != 2 || strings.TrimSpace(args[1]) == "" {
			return usage(fmt.Errorf("usage: r10n config delete-secret PROFILE"))
		}
		return deleteSMTPSecret(ctx, strings.TrimSpace(args[1]))
	case "import":
		return importSettings(ctx, args[1:])
	case "export":
		return exportSettings(args[1:])
	default:
		return usage(fmt.Errorf("unknown r10n config action %q", args[0]))
	}
}

func editSettings(ctx context.Context) error {
	current, err := settings.Load()
	if err != nil {
		return err
	}
	theme, accessible, reducedMotion, outputDirectory := current.Theme,
		current.Accessible, current.ReducedMotion, current.OutputDirectory
	form := huh.NewForm(huh.NewGroup(
		huh.NewSelect[string]().Title("Terminal theme").
			Options(
				huh.NewOption("System", "system"),
				huh.NewOption("Dark", "dark"),
				huh.NewOption("Light", "light"),
			).Value(&theme),
		huh.NewConfirm().Title("Use screen-reader-friendly linear prompts?").
			Affirmative("Accessible").Negative("Standard").Value(&accessible),
		huh.NewConfirm().Title("Disable terminal animation?").
			Affirmative("Reduced motion").Negative("Allow motion").Value(&reducedMotion),
		huh.NewInput().Title("Default output directory").
			Description("Leave blank to use ./r10n-output. This path is never created until a run needs it.").
			Value(&outputDirectory),
	).Title("r10n terminal preferences"))
	if err := tui.RunForm(ctx, form); err != nil {
		return err
	}
	current.Theme = theme
	current.Accessible = accessible
	current.ReducedMotion = reducedMotion
	current.OutputDirectory = strings.TrimSpace(outputDirectory)
	path, err := settings.Save(current)
	if err != nil {
		return err
	}
	fmt.Fprintf(stdout, "Settings saved to %s\n", tui.SafeText(path))
	return nil
}

func promptSMTPProfile(ctx context.Context, name string, edit bool) error {
	current, err := settings.Load()
	if err != nil {
		return err
	}
	profile, exists := current.SMTPProfiles[name]
	if edit && !exists {
		return usage(fmt.Errorf("SMTP profile %q does not exist", name))
	}
	if !edit && exists {
		return usage(fmt.Errorf("SMTP profile %q already exists; use `r10n config edit-smtp-profile %s`", name, name))
	}
	server, port, sender, subject := profile.Server, strconv.Itoa(profile.Port),
		profile.Email, profile.Subject
	if !edit {
		server, port = "smtp.gmail.com", "587"
	}
	useTLS := profile.UseTLS
	if !edit {
		useTLS = true
	}
	password := ""
	fields := []huh.Field{
		huh.NewInput().Title("SMTP server").Value(&server),
		huh.NewInput().Title("SMTP port").Value(&port).Validate(func(value string) error {
			portNumber, err := strconv.Atoi(value)
			if err != nil || portNumber < 1 || portNumber > 65535 {
				return fmt.Errorf("enter a port between 1 and 65535")
			}
			return nil
		}),
		huh.NewInput().Title("Sender email address").Value(&sender),
		huh.NewInput().Title("Default message subject").Value(&subject),
		huh.NewConfirm().Title("Connect with TLS?").Value(&useTLS),
	}
	if !edit {
		fields = append(fields,
			huh.NewInput().Title("SMTP password").EchoMode(huh.EchoModePassword).Value(&password))
	}
	form := huh.NewForm(huh.NewGroup(fields...).Title("SMTP profile: " + tui.SafeText(name)))
	if err := tui.RunForm(ctx, form); err != nil {
		return err
	}
	portNumber, _ := strconv.Atoi(port)
	current.SMTPProfiles[name] = settings.SMTPProfile{
		Server: server, Port: portNumber, Email: sender, Subject: subject, UseTLS: useTLS,
	}
	if !edit {
		if password == "" {
			return fmt.Errorf("password cannot be empty")
		}
		current.ActiveSMTPProfile = name
		if err := setSecret(ctx, name, password); err != nil {
			return err
		}
	}
	path, err := settings.Save(current)
	if err != nil && !edit {
		_ = deleteSecret(ctx, name)
	}
	if err != nil {
		return err
	}
	if edit {
		fmt.Fprintf(stdout, "SMTP profile %q updated in %s. Rotate its password with `r10n config set-secret %s`.\n",
			tui.SafeText(name), tui.SafeText(path), tui.SafeText(name))
	} else {
		fmt.Fprintf(stdout, "SMTP profile %q saved securely in %s\n", tui.SafeText(name), tui.SafeText(path))
	}
	return nil
}

func setSMTPSecret(ctx context.Context, profile string) error {
	current, err := settings.Load()
	if err != nil {
		return err
	}
	if _, exists := current.SMTPProfiles[profile]; !exists {
		return usage(fmt.Errorf("SMTP profile %q does not exist; add it with r10n config add-smtp-profile", profile))
	}
	password := ""
	form := huh.NewForm(huh.NewGroup(
		huh.NewInput().Title("SMTP password").EchoMode(huh.EchoModePassword).Value(&password),
	).Title("Update secure SMTP credential"))
	if err := tui.RunForm(ctx, form); err != nil {
		return err
	}
	if password == "" {
		return fmt.Errorf("password cannot be empty")
	}
	if err := setSecret(ctx, profile, password); err != nil {
		return err
	}
	fmt.Fprintf(stdout, "Secure SMTP credential saved for %q.\n", tui.SafeText(profile))
	return nil
}

func deleteSMTPSecret(ctx context.Context, profile string) error {
	current, err := settings.Load()
	if err != nil {
		return err
	}
	if _, exists := current.SMTPProfiles[profile]; !exists {
		return usage(fmt.Errorf("SMTP profile %q does not exist", profile))
	}
	confirmed := false
	form := huh.NewForm(huh.NewGroup(
		huh.NewConfirm().Title("Delete the secure credential for " + tui.SafeText(profile) + "?").
			Affirmative("Delete").Negative("Keep").Value(&confirmed),
	))
	if err := tui.RunForm(ctx, form); err != nil {
		return err
	}
	if !confirmed {
		fmt.Fprintln(stdout, "Cancelled; the credential was not changed.")
		return nil
	}
	if err := deleteSecret(ctx, profile); err != nil {
		return err
	}
	fmt.Fprintf(stdout, "Deleted secure credential for %q.\n", tui.SafeText(profile))
	return nil
}

func setSecret(ctx context.Context, profile, secret string) error {
	return callCredentialBackend(ctx, "secret-set", profile, secret)
}

func deleteSecret(ctx context.Context, profile string) error {
	return callCredentialBackend(ctx, "secret-delete", profile, "")
}

func callCredentialBackend(ctx context.Context, operation, profile, secret string) error {
	engine, err := backend.Resolve()
	if err != nil {
		return err
	}
	request, err := json.Marshal(map[string]string{"profile": profile, "secret": secret})
	if err != nil {
		return err
	}
	command := engine.Command(ctx, operation)
	command.Stdin = bytes.NewReader(request)
	var output, diagnostic bytes.Buffer
	command.Stdout, command.Stderr = &output, &diagnostic
	if err := command.Run(); err != nil {
		message := strings.TrimSpace(diagnostic.String())
		if message == "" {
			message = err.Error()
		}
		return fmt.Errorf("secure credential store: %s", tui.SafeText(message))
	}
	var result struct {
		Saved bool `json:"saved"`
	}
	if err := json.Unmarshal(output.Bytes(), &result); err != nil {
		return fmt.Errorf("secure credential service returned an invalid response")
	}
	if !result.Saved {
		return fmt.Errorf("secure credential service did not confirm the operation")
	}
	return nil
}

func importSettings(ctx context.Context, args []string) error {
	fs := flag.NewFlagSet("config import", flag.ContinueOnError)
	fs.SetOutput(io.Discard)
	profileName := fs.String("profile", "imported", "")
	if err := fs.Parse(args); err != nil {
		return usage(err)
	}
	if fs.NArg() != 1 {
		return usage(fmt.Errorf("usage: r10n config import PATH [--profile NAME]"))
	}
	source, err := filepath.Abs(fs.Arg(0))
	if err != nil {
		return err
	}
	data, err := os.ReadFile(source)
	if err != nil {
		return err
	}
	var imported map[string]json.RawMessage
	if err := json.Unmarshal(data, &imported); err != nil {
		return fmt.Errorf("import must be a JSON object: %w", err)
	}
	current, err := settings.Load()
	if err != nil {
		return err
	}
	_, hasPDF := imported["template_pdf"]
	_, hasSMTP := imported["smtp_server"]
	secret, hasSecret := imported["password"]

	if hasPDF {
		profile, err := decodePDFProfile(data, source)
		if err != nil {
			return err
		}
		current.PDFProfiles[*profileName] = profile
		current.ActivePDFProfile = *profileName
		fmt.Fprintf(stderr, "Preview: import PDF profile %q for %s\n", tui.SafeText(*profileName), filepath.Base(profile.TemplatePDF))
	}
	if hasSMTP {
		if _, exists := current.SMTPProfiles[*profileName]; exists {
			return fmt.Errorf("SMTP profile %q already exists; import to another profile name", *profileName)
		}
		profile, err := decodeSMTPProfile(data)
		if err != nil {
			return err
		}
		current.SMTPProfiles[*profileName] = profile
		current.ActiveSMTPProfile = *profileName
		fmt.Fprintf(stderr, "Preview: import SMTP profile %q for %s\n", tui.SafeText(*profileName), tui.SafeText(profile.Email))
	} else if !hasPDF {
		settingsData, err := settings.Decode(data)
		if err != nil {
			return fmt.Errorf("unsupported settings import: %w", err)
		}
		current = settingsData
	}
	confirmed := false
	form := huh.NewForm(huh.NewGroup(
		huh.NewConfirm().Title("Save these reviewed non-secret settings?").
			Affirmative("Import").Negative("Cancel").Value(&confirmed),
	))
	if err := tui.RunForm(ctx, form); err != nil {
		return err
	}
	if !confirmed {
		return nil
	}
	if hasSMTP && hasSecret {
		var password string
		if err := json.Unmarshal(secret, &password); err != nil {
			return fmt.Errorf("legacy SMTP password must be a string")
		}
		if err := setSecret(ctx, *profileName, password); err != nil {
			return err
		}
	}
	path, err := settings.Save(current)
	if err != nil {
		if hasSMTP && hasSecret {
			_ = deleteSecret(ctx, *profileName)
		}
		return err
	}
	fmt.Fprintf(stdout, "Imported reviewed settings to %s\n", tui.SafeText(path))
	if hasSMTP && !hasSecret {
		fmt.Fprintf(stdout, "Store the SMTP password with `r10n config set-secret %s`.\n", tui.SafeText(*profileName))
	}
	return nil
}

func decodePDFProfile(data []byte, source string) (settings.PDFProfile, error) {
	var profile settings.PDFProfile
	if err := json.Unmarshal(data, &profile); err != nil {
		return profile, fmt.Errorf("invalid PDF profile: %w", err)
	}
	for _, path := range []*string{&profile.TemplatePDF, &profile.OutputDirectory} {
		if !filepath.IsAbs(*path) {
			*path = filepath.Join(filepath.Dir(source), *path)
		}
		absolute, err := filepath.Abs(*path)
		if err != nil {
			return profile, err
		}
		*path = absolute
	}
	return profile, nil
}

func decodeSMTPProfile(data []byte) (settings.SMTPProfile, error) {
	var profile settings.SMTPProfile
	if err := json.Unmarshal(data, &profile); err != nil {
		return profile, fmt.Errorf("invalid SMTP profile: %w", err)
	}
	return profile, nil
}

func exportSettings(args []string) error {
	if len(args) != 1 {
		return usage(fmt.Errorf("usage: r10n config export NEW-PATH"))
	}
	path, err := filepath.Abs(args[0])
	if err != nil {
		return err
	}
	file, err := os.OpenFile(path, os.O_WRONLY|os.O_CREATE|os.O_EXCL, 0600)
	if err != nil {
		return err
	}
	defer file.Close()
	document, err := settings.Load()
	if err != nil {
		return err
	}
	encoder := json.NewEncoder(file)
	encoder.SetIndent("", "  ")
	if err := encoder.Encode(document); err != nil {
		_ = os.Remove(path)
		return err
	}
	fmt.Fprintf(stdout, "Exported non-secret settings to %s\n", tui.SafeText(path))
	return nil
}
