// Package cli owns native routing and options; Python owns task models.
package cli

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

	"github.com/pruthivithejan/r10n"
	"github.com/pruthivithejan/r10n/internal/backend"
	"github.com/pruthivithejan/r10n/internal/tui"
)

var stdin = os.Stdin
var stdout io.Writer = os.Stdout
var stderr io.Writer = os.Stderr

const maxInputBytes = 8 * 1024 * 1024
const help = `r10n — routine automation
Usage:
  r10n | tui                 Open the native automation picker
  r10n <automation>           Open a native input form
  r10n <automation> [flags]   Run using command flags
  r10n list [--json]          List the Python registry
  r10n run <automation> [--input-json <object> | --input-file <path>]
  r10n configure --template PATH [--recipients PATH] [--name PROFILE]
  r10n setup                  Edit per-user terminal preferences
  r10n config <action>        Inspect profiles and system settings
  r10n status [--json]        Report system settings and runtime status
  r10n upgrade [--version VERSION] [--check] [--yes]
  r10n --version             Print version without Python
Execution: --yes/-y skips confirmation; --json streams JSON Lines.
Tasks: contacts, fill-pdfs, images, website-images, logos, email, colors,
       rename, validate, md2pdf. Use <command> --help for supported flags.
`

func usage(err error) error {
	if err == nil || errors.Is(err, context.Canceled) || errors.Is(err, context.DeadlineExceeded) {
		return err
	}
	return &backend.RunError{Code: 2, Message: err.Error()}
}

func Run(ctx context.Context, args []string) error {
	tui.SetIO(stdin, stdout, stderr)
	for len(args) > 0 {
		switch args[0] {
		case "--accessible":
			_ = os.Setenv("R10N_ACCESSIBLE", "1")
			args = args[1:]
		case "--no-motion":
			_ = os.Setenv("R10N_NO_MOTION", "1")
			args = args[1:]
		default:
			goto flagsParsed
		}
	}
flagsParsed:
	if len(args) == 1 && (args[0] == "--version" || args[0] == "-v") {
		fmt.Fprintf(stdout, "r10n, version %s\n", r10n.Version)
		return nil
	}
	if len(args) == 0 && !tui.Interactive() {
		fmt.Fprint(stdout, help)
		return nil
	}
	if len(args) > 0 && (args[0] == "--help" || args[0] == "-h") {
		if len(args) != 1 {
			return usage(fmt.Errorf("unexpected arguments"))
		}
		fmt.Fprint(stdout, help)
		return nil
	}
	if len(args) == 2 && (args[1] == "--help" || args[1] == "-h") {
		if _, ok := aliases[args[0]]; ok {
			printTaskHelp(args[0])
			return nil
		}
		switch args[0] {
		case "run", "list", "tui", "configure", "setup", "config", "status", "upgrade":
			fmt.Fprint(stdout, help)
			return nil
		}
	}
	if len(args) > 0 {
		switch args[0] {
		case "run":
			o, err := parseRun(ctx, args[1:])
			if errors.Is(err, flag.ErrHelp) {
				return nil
			}
			if err != nil {
				return usage(err)
			}
			return runJSON(ctx, o)
		case "setup":
			return editSettings(ctx)
		case "config":
			return settingsCommand(ctx, args[1:])
		case "init":
			return usage(fmt.Errorf("r10n init is no longer supported; use `r10n setup` to edit per-user preferences"))
		case "status":
			return status(args[1:])
		case "configure":
			return configure(ctx, args[1:])
		case "upgrade":
			return upgrade(ctx, args[1:])
		case "list":
			if len(args) > 2 || (len(args) == 2 && args[1] != "--json") {
				return usage(fmt.Errorf("usage: r10n list [--json]"))
			}
		case "tui":
			if len(args) != 1 {
				return usage(fmt.Errorf("usage: r10n tui"))
			}
			if !tui.Interactive() {
				return usage(fmt.Errorf("native forms require a terminal"))
			}
		default:
			if _, ok := aliases[args[0]]; !ok && len(args) > 1 {
				return usage(fmt.Errorf("unknown command or unsupported flag aliases: %s; use r10n run <automation> for registry-defined tasks", args[0]))
			}
			if len(args) > 1 {
				raw, err := parseFlags(args[0], args[1:])
				if errors.Is(err, flag.ErrHelp) {
					printTaskHelp(args[0])
					return nil
				}
				if err != nil {
					return usage(err)
				}
				if !raw.yes && !tui.Interactive() {
					return usage(fmt.Errorf("noninteractive execution requires --yes after reviewing inputs"))
				}
				engine, err := backend.Resolve()
				if err != nil {
					return err
				}
				catalog, err := engine.LoadCatalog(ctx)
				if err != nil {
					return err
				}
				task, err := findTask(catalog, args[0])
				if err != nil {
					return usage(err)
				}
				payload, err := raw.payload(task)
				if err != nil {
					return usage(err)
				}
				return tui.Execute(ctx, engine, task, payload, raw.yes, raw.json)
			}
			if !tui.Interactive() {
				return usage(fmt.Errorf("native forms require a terminal; supply command flags and --yes or use run --input-json"))
			}
		}
	}
	engine, err := backend.Resolve()
	if err != nil {
		return err
	}
	catalog, err := engine.LoadCatalog(ctx)
	if err != nil {
		return err
	}
	if len(args) > 0 && args[0] == "list" {
		if len(args) == 2 {
			_, err = fmt.Fprintf(stdout, "%s\n", catalog.Raw)
			return err
		}
		for _, task := range catalog.Automations {
			fmt.Fprintf(stdout, "%-16s %s — %s\n", tui.SafeText(task.ID), tui.SafeText(task.Title), tui.SafeText(task.Description))
		}
		return nil
	}
	if len(args) > 0 && args[0] != "tui" {
		task, err := findTask(catalog, args[0])
		if err != nil {
			return usage(err)
		}
		return tui.RunTask(ctx, engine, task)
	}
	return tui.Picker(ctx, engine, catalog)
}

func findTask(c backend.Catalog, id string) (backend.Automation, error) {
	for _, task := range c.Automations {
		if task.ID == id {
			return task, nil
		}
	}
	return backend.Automation{}, fmt.Errorf("unknown automation: %s", id)
}

type runOptions struct {
	id              string
	payload         map[string]any
	jsonOutput, yes bool
}

func parseRun(ctx context.Context, args []string) (runOptions, error) {
	o := runOptions{}
	if len(args) == 0 {
		return o, fmt.Errorf("usage: r10n run <automation> [--input-json <object> | --input-file <path>] [--json] [--yes]")
	}
	if args[0] == "--help" || args[0] == "-h" {
		fmt.Fprint(stdout, help)
		return o, flag.ErrHelp
	}
	o.id = args[0]
	fs := flag.NewFlagSet("run", flag.ContinueOnError)
	fs.SetOutput(io.Discard)
	var inline, file string
	fs.StringVar(&inline, "input-json", "", "")
	fs.StringVar(&file, "input-file", "", "")
	fs.BoolVar(&o.jsonOutput, "json", false, "")
	fs.BoolVar(&o.yes, "yes", false, "")
	fs.BoolVar(&o.yes, "y", false, "")
	if err := fs.Parse(args[1:]); err != nil {
		if errors.Is(err, flag.ErrHelp) {
			fmt.Fprint(stdout, help)
		}
		return o, err
	}
	if fs.NArg() != 0 {
		return o, fmt.Errorf("unexpected arguments: %s", strings.Join(fs.Args(), " "))
	}
	hasInline, hasFile := false, false
	fs.Visit(func(f *flag.Flag) {
		hasInline = hasInline || f.Name == "input-json"
		hasFile = hasFile || f.Name == "input-file"
	})
	if hasInline && hasFile {
		return o, fmt.Errorf("use either --input-json or --input-file, not both")
	}
	raw := []byte("{}")
	var err error
	if hasFile {
		raw, err = readInput(ctx, file)
	} else if hasInline {
		raw = []byte(inline)
	}
	if err != nil {
		return o, err
	}
	if len(raw) > maxInputBytes {
		return o, fmt.Errorf("input JSON exceeds 8 MiB")
	}
	d := json.NewDecoder(bytes.NewReader(raw))
	d.UseNumber()
	if err := d.Decode(&o.payload); err != nil || o.payload == nil {
		return o, fmt.Errorf("input must be a valid JSON object")
	}
	var extra any
	if d.Decode(&extra) != io.EOF {
		return o, fmt.Errorf("input must contain exactly one JSON object")
	}
	return o, nil
}

func readInput(ctx context.Context, file string) ([]byte, error) {
	type result struct {
		data []byte
		err  error
	}
	done := make(chan result, 1)
	input := stdin
	go func() {
		reader := input
		if file != "-" {
			var err error
			reader, err = os.Open(file)
			if err != nil {
				done <- result{err: err}
				return
			}
			defer reader.Close()
		}
		data, err := io.ReadAll(io.LimitReader(reader, maxInputBytes+1))
		done <- result{data, err}
	}()
	select {
	case r := <-done:
		return r.data, r.err
	case <-ctx.Done():
		return nil, ctx.Err()
	}
}

func runJSON(ctx context.Context, o runOptions) error {
	if !o.yes && !tui.Interactive() {
		return usage(fmt.Errorf("noninteractive execution requires --yes after reviewing inputs"))
	}
	engine, err := backend.Resolve()
	if err != nil {
		return err
	}
	if o.yes {
		return engine.Stream(ctx, o.id, o.payload, func(e backend.Event) error { return tui.PrintEvent(stdout, e, o.jsonOutput) })
	}
	catalog, err := engine.LoadCatalog(ctx)
	if err != nil {
		return err
	}
	task, err := findTask(catalog, o.id)
	if err != nil {
		return usage(err)
	}
	return tui.Execute(ctx, engine, task, o.payload, false, o.jsonOutput)
}
