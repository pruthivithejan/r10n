package shell

import (
	"bytes"
	"context"
	"encoding/json"
	"errors"
	"flag"
	"fmt"
	"io"
	"os"
	"strings"

	"github.com/charmbracelet/huh"
	"github.com/pruthivithejan/r10n"
	"github.com/pruthivithejan/r10n/internal/backend"
	"golang.org/x/term"
)

var stdin = os.Stdin
var stdout io.Writer = os.Stdout
var stderr io.Writer = os.Stderr

const maxInputBytes = 8 * 1024 * 1024

const help = `r10n — routine automation

Usage:
  r10n                         Open the native automation picker
  r10n tui                     Open the native automation picker
  r10n <automation>             Complete a guided input form
  r10n list [--json]            List tasks from the Python registry
  r10n run <automation> [flags] Run using a JSON input object
  r10n <command> [flags]        Use existing Python CLI flags unchanged
  r10n legacy [args]            Use the original Python interface explicitly
  r10n --version                Print the shared release version

Run flags:
  --input-json <object>         Input values matching the task's Pydantic model
  --input-file <path>           Read input JSON from a file; "-" reads stdin
  --json                       Stream protocol v1 JSON Lines without UI output
  --yes                        Skip confirmation (required without a terminal)

Examples:
  r10n contacts --input numbers.txt --output contacts.vcf
  r10n run contacts --input-json '{"input_file":"numbers.txt"}' --json --yes
  r10n configure               Open the existing PDF configuration tool
  r10n upgrade                 Upgrade a standalone installation

Native forms: arrows navigate, / filters the picker, Enter selects, Ctrl+C exits.
Set R10N_ACCESSIBLE=1 for plain prompts and static progress output.
Legacy flags retain their original prompts; use run --yes for headless jobs.
Python/uvx entry points remain available and retain their original interface.
`

func accessible() bool { return os.Getenv("R10N_ACCESSIBLE") == "1" }

func interactive() bool {
	return term.IsTerminal(int(stdin.Fd())) && term.IsTerminal(int(os.Stderr.Fd()))
}

func formatValue(value any) string {
	if value == nil {
		return "(none)"
	}
	switch value.(type) {
	case map[string]any, []any:
		raw, _ := json.Marshal(value)
		return string(raw)
	default:
		return fmt.Sprint(value)
	}
}

// Run dispatches native workflows and preserves old CLI flags through the bridge.
func Run(ctx context.Context, args []string) error {
	if len(args) == 1 && (args[0] == "--version" || args[0] == "-v") {
		fmt.Fprintf(stdout, "r10n, version %s\n", r10n.Version)
		return nil
	}
	if len(args) == 1 && (args[0] == "--help" || args[0] == "-h") {
		fmt.Fprint(stdout, help)
		return nil
	}
	if len(args) == 2 && (args[0] == "list" || args[0] == "tui") &&
		(args[1] == "--help" || args[1] == "-h") {
		fmt.Fprint(stdout, help)
		return nil
	}
	if len(args) == 0 && !interactive() {
		fmt.Fprint(stdout, help)
		return nil
	}
	if len(args) > 0 && args[0] == "run" {
		// Parse before backend discovery, so --help and invalid input work even
		// when a source installation has not yet run uv sync.
		options, err := parseRun(ctx, args[1:])
		if errors.Is(err, flag.ErrHelp) {
			return nil
		}
		if err != nil {
			if errors.Is(err, context.Canceled) {
				return err
			}
			return &backend.RunError{Code: 2, Message: err.Error()}
		}
		return runJSON(ctx, options)
	}
	engine, err := backend.Resolve()
	if err != nil {
		return err
	}
	if len(args) > 0 && args[0] == "legacy" {
		return runLegacy(ctx, engine, args[1:])
	}
	if len(args) > 0 && args[0] != "list" && args[0] != "tui" && len(args) > 1 {
		return runLegacy(ctx, engine, args)
	}
	catalog, err := engine.LoadCatalog(ctx)
	if err != nil {
		return err
	}
	if len(args) > 0 && args[0] == "list" {
		if len(args) == 2 && args[1] == "--json" {
			_, err := fmt.Fprintf(stdout, "%s\n", catalog.Raw)
			return err
		}
		if len(args) != 1 {
			return &backend.RunError{Code: 2, Message: "usage: r10n list [--json]"}
		}
		for _, task := range catalog.Automations {
			fmt.Fprintf(stdout, "%-16s %s — %s\n", task.ID, task.Title, task.Description)
		}
		return nil
	}
	if len(args) > 0 && args[0] != "tui" {
		for _, task := range catalog.Automations {
			if task.ID == args[0] {
				return runTask(ctx, engine, task)
			}
		}
		return runLegacy(ctx, engine, args)
	}
	if len(args) > 1 {
		return &backend.RunError{Code: 2, Message: "usage: r10n tui"}
	}
	if !interactive() {
		return &backend.RunError{Code: 2, Message: "native forms require a terminal; use r10n run <automation> --input-json '<object>' --yes"}
	}
	for {
		options := make([]huh.Option[string], 0, len(catalog.Automations))
		for _, task := range catalog.Automations {
			label := task.ID + " · " + task.Title + " · " + task.Category + " — " + task.Description
			if len(task.Roles) > 0 {
				label += " (" + strings.Join(task.Roles, ", ") + ")"
			}
			options = append(options, huh.NewOption(label, task.ID))
		}
		var selected string
		form := huh.NewForm(huh.NewGroup(huh.NewSelect[string]().
			Title("r10n · Routine automation").Description("Choose a task. Press / to filter.").
			Options(options...).Value(&selected)))
		if err := runForm(ctx, form); err != nil {
			return err
		}
		for _, task := range catalog.Automations {
			if task.ID == selected {
				if err := runTask(ctx, engine, task); err != nil {
					return err
				}
				break
			}
		}
		var again bool
		if err := runForm(ctx, huh.NewForm(huh.NewGroup(huh.NewConfirm().
			Title("Run another automation?").Value(&again)))); err != nil {
			return err
		}
		if !again {
			return nil
		}
	}
}

func runLegacy(ctx context.Context, engine backend.Backend, args []string) error {
	cmd := engine.Command(ctx, append([]string{"legacy"}, args...)...)
	cmd.Stdin, cmd.Stdout, cmd.Stderr = stdin, stdout, stderr
	err := cmd.Run()
	if ctx.Err() != nil {
		return ctx.Err()
	}
	return err
}

func runTask(ctx context.Context, engine backend.Backend, task backend.Automation) error {
	if !interactive() {
		return &backend.RunError{Code: 2, Message: "native forms require a terminal; supply existing CLI flags or use r10n run --input-json with --yes"}
	}
	fmt.Fprintln(stderr, heading.Render(task.Title), "\n"+task.Description)
	form, collect, err := inputForm(task)
	if err != nil {
		return err
	}
	if err := runForm(ctx, form); err != nil {
		return err
	}
	payload, err := collect()
	if err != nil {
		return err
	}
	if err := confirm(ctx, task, payload, false); err != nil {
		return err
	}
	return executeInteractive(ctx, engine, task, payload)
}

type runOptions struct {
	id         string
	payload    map[string]any
	jsonOutput bool
	yes        bool
}

func parseRun(ctx context.Context, args []string) (runOptions, error) {
	options := runOptions{}
	if len(args) == 0 {
		return options, fmt.Errorf("usage: r10n run <automation> [--input-json <object> | --input-file <path>] [--json] [--yes]")
	}
	if args[0] == "--help" || args[0] == "-h" {
		fmt.Fprint(stdout, help)
		return options, flag.ErrHelp
	}
	options.id = args[0]
	flags := flag.NewFlagSet("run "+options.id, flag.ContinueOnError)
	// Report errors once through the sanitized top-level diagnostic path.
	flags.SetOutput(io.Discard)
	var inline, file string
	flags.StringVar(&inline, "input-json", "", "JSON input object")
	flags.StringVar(&file, "input-file", "", "JSON input file; - reads stdin")
	flags.BoolVar(&options.jsonOutput, "json", false, "stream original JSON Lines events")
	flags.BoolVar(&options.yes, "yes", false, "skip confirmation")
	if err := flags.Parse(args[1:]); err != nil {
		if errors.Is(err, flag.ErrHelp) {
			fmt.Fprint(stdout, help)
		}
		return options, err
	}
	if flags.NArg() > 0 {
		return options, fmt.Errorf("unexpected arguments: %s", strings.Join(flags.Args(), " "))
	}
	suppliedInline, suppliedFile := false, false
	flags.Visit(func(value *flag.Flag) {
		suppliedInline = suppliedInline || value.Name == "input-json"
		suppliedFile = suppliedFile || value.Name == "input-file"
	})
	if suppliedInline && suppliedFile {
		return options, fmt.Errorf("use either --input-json or --input-file, not both")
	}
	raw := []byte("{}")
	var err error
	if suppliedFile {
		raw, err = readInput(ctx, file)
		if err != nil {
			return options, fmt.Errorf("read input JSON: %w", err)
		}
	} else if suppliedInline {
		raw = []byte(inline)
	}
	if len(raw) > maxInputBytes {
		return options, fmt.Errorf("input JSON exceeds 8 MiB")
	}
	decoder := json.NewDecoder(bytes.NewReader(raw))
	decoder.UseNumber()
	if err := decoder.Decode(&options.payload); err != nil || options.payload == nil {
		return options, fmt.Errorf("input must be a valid JSON object")
	}
	var extra any
	if err := decoder.Decode(&extra); err != io.EOF {
		return options, fmt.Errorf("input must contain exactly one JSON object")
	}
	return options, nil
}

func readInput(ctx context.Context, file string) ([]byte, error) {
	type inputResult struct {
		data []byte
		err  error
	}
	finished := make(chan inputResult, 1)
	reader := stdin
	// A pipe or terminal may wait indefinitely for EOF. Cancellation can exit
	// this one-shot CLI even when the underlying file read cannot be interrupted.
	go func() {
		if file != "-" {
			var err error
			reader, err = os.Open(file)
			if err != nil {
				finished <- inputResult{err: err}
				return
			}
			defer reader.Close()
		}
		data, err := io.ReadAll(io.LimitReader(reader, maxInputBytes+1))
		finished <- inputResult{data, err}
	}()
	select {
	case result := <-finished:
		return result.data, result.err
	case <-ctx.Done():
		return nil, ctx.Err()
	}
}

func confirm(ctx context.Context, task backend.Automation, payload map[string]any, yes bool) error {
	if yes {
		return nil
	}
	if !interactive() {
		return &backend.RunError{Code: 2, Message: "confirmation requires a terminal; review inputs and add --yes for noninteractive execution"}
	}
	resolved := map[string]any{}
	for name, field := range task.InputSchema.Properties {
		resolved[name] = field.Default
	}
	for name, value := range payload {
		resolved[name] = value
	}
	if err := writeTable(stderr, "Review "+task.Title, resolved); err != nil {
		return err
	}
	if task.Confirmation != "" {
		fmt.Fprintln(stderr, SafeText(task.Confirmation))
	}
	approved := false
	form := huh.NewForm(huh.NewGroup(huh.NewConfirm().Title("Run this automation?").
		Description("Outputs may be overwritten. Review paths and options before continuing.").
		Affirmative("Run").Negative("Cancel").Value(&approved)))
	if err := runForm(ctx, form); err != nil {
		return err
	}
	if !approved {
		return context.Canceled
	}
	return nil
}

func runJSON(ctx context.Context, options runOptions) error {
	if !options.yes && !interactive() {
		return &backend.RunError{Code: 2, Message: "noninteractive execution requires --yes after reviewing inputs"}
	}
	engine, err := backend.Resolve()
	if err != nil {
		return err
	}
	// --yes is an explicit opt-in for direct worker execution. Avoid loading the
	// catalog in scripted runs: worker validation already owns the input model.
	if !options.yes {
		catalog, err := engine.LoadCatalog(ctx)
		if err != nil {
			return err
		}
		found := false
		for _, task := range catalog.Automations {
			if task.ID == options.id {
				found = true
				if err := confirm(ctx, task, options.payload, false); err != nil {
					return err
				}
				break
			}
		}
		if !found {
			return &backend.RunError{Code: 2, Message: "unknown automation: " + options.id}
		}
	}
	return engine.Stream(ctx, options.id, options.payload, func(event backend.Event) error {
		return printEvent(stdout, event, options.jsonOutput)
	})
}
