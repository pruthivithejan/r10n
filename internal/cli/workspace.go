package cli

import (
	"context"
	"encoding/json"
	"flag"
	"fmt"
	"io"
	"os"
	"path/filepath"
	"strings"

	"github.com/pruthivithejan/r10n"
	"github.com/pruthivithejan/r10n/internal/backend"
	"github.com/pruthivithejan/r10n/internal/tui"
)

func initialize(ctx context.Context, args []string) error {
	if len(args) != 0 {
		return usage(fmt.Errorf("usage: r10n init"))
	}
	for _, name := range []string{"contacts", "fill-pdfs", "images", "website-images", "logos", "email", "colors", "rename", "validate", "md2pdf", "markdown", "pdf"} {
		for _, kind := range []string{"inputs", "outputs"} {
			if err := ctx.Err(); err != nil {
				return err
			}
			if err := os.MkdirAll(filepath.Join("local", kind, name), 0755); err != nil {
				return err
			}
		}
	}
	if err := os.MkdirAll(filepath.Join("local", "configs"), 0755); err != nil {
		return err
	}
	entries, err := r10n.WorkspaceTemplates.ReadDir("configs")
	if err != nil {
		return err
	}
	for _, entry := range entries {
		data, err := r10n.WorkspaceTemplates.ReadFile("configs/" + entry.Name())
		if err != nil {
			return err
		}
		path := filepath.Join("local", "configs", strings.Replace(entry.Name(), ".default.json", ".json", 1))
		file, err := os.OpenFile(path, os.O_WRONLY|os.O_CREATE|os.O_EXCL, 0600)
		if os.IsExist(err) {
			continue
		}
		if err != nil {
			return err
		}
		_, writeErr := file.Write(data)
		closeErr := file.Close()
		if writeErr != nil {
			return writeErr
		}
		if closeErr != nil {
			return closeErr
		}
		fmt.Fprintln(stdout, "Created", path)
	}
	fmt.Fprintln(stdout, "Local workspace ready. Existing files were preserved.")
	return nil
}

func status(args []string) error {
	if len(args) > 1 || (len(args) == 1 && args[0] != "--json") {
		return usage(fmt.Errorf("usage: r10n status [--json]"))
	}
	paths := []string{"local", "local/configs", "local/inputs", "local/outputs", "configs", "local/.env", ".env"}
	for _, dir := range []string{"local/configs", "configs"} {
		entries, _ := os.ReadDir(dir)
		for _, entry := range entries {
			if !entry.IsDir() {
				// JSON status keys are stable across hosts, like the base paths above.
				paths = append(paths, filepath.ToSlash(filepath.Join(dir, entry.Name())))
			}
		}
	}
	result := map[string]bool{}
	for _, path := range paths {
		_, err := os.Stat(path)
		result[path] = err == nil
	}
	if len(args) == 1 {
		return json.NewEncoder(stdout).Encode(result)
	}
	for _, path := range paths {
		fmt.Fprintf(stdout, "%-44s %t\n", tui.SafeText(path), result[path])
	}
	return nil
}

func configure(ctx context.Context, args []string) error {
	fs := flag.NewFlagSet("configure", flag.ContinueOnError)
	fs.SetOutput(io.Discard)
	var template, recipients string
	output := "local/configs/fill-pdfs.json"
	for _, name := range []string{"template", "t"} {
		fs.StringVar(&template, name, "", "")
	}
	for _, name := range []string{"recipients", "r"} {
		fs.StringVar(&recipients, name, "", "")
	}
	for _, name := range []string{"output", "o"} {
		fs.StringVar(&output, name, output, "")
	}
	if err := fs.Parse(args); err != nil {
		return usage(err)
	}
	if fs.NArg() != 0 || template == "" || output == "" {
		return usage(fmt.Errorf("usage: r10n configure --template/-t PATH [--recipients/-r PATH] [--output/-o PATH]"))
	}
	if info, err := os.Stat(template); err != nil || info.IsDir() {
		return usage(fmt.Errorf("template file not found: %s", template))
	}
	if recipients != "" {
		if info, err := os.Stat(recipients); err != nil || info.IsDir() {
			return usage(fmt.Errorf("recipients file not found: %s", recipients))
		}
	}
	engine, err := backend.Resolve()
	if err != nil {
		return err
	}
	commandArgs := []string{"configure", "--template", template, "--output", output}
	if recipients != "" {
		commandArgs = append(commandArgs, "--recipients", recipients)
	}
	cmd := engine.Command(ctx, commandArgs...)
	cmd.Stdin, cmd.Stdout, cmd.Stderr = stdin, stdout, stderr
	err = cmd.Run()
	if ctx.Err() != nil {
		return ctx.Err()
	}
	return err
}
