package cli

import (
	"context"
	"encoding/json"
	"fmt"
	"os"
	"reflect"
	"strings"
	"testing"

	"github.com/pruthivithejan/r10n/internal/backend"
)

func TestFlagAliasMatrix(t *testing.T) {
	tests := []struct {
		task     string
		flags    []string
		expected map[string]string
	}{
		{"contacts", []string{"-i", "numbers.txt", "-o", "out.vcf", "-p", "Friend"}, map[string]string{"input_file": "numbers.txt", "output_file": "out.vcf", "prefix": "Friend"}},
		{"fill-pdfs", []string{"-c", "config.json", "-r", "data.csv"}, map[string]string{"config_file": "config.json", "recipients_file": "data.csv"}},
		{"images", []string{"-i", "in", "-o", "out", "-q", "80", "-s", "1.5", "-p", "img", "--preserve-names=false"}, map[string]string{"input_directory": "in", "output_directory": "out", "quality": "80", "max_size_mb": "1.5", "prefix": "img", "preserve_filenames": "false"}},
		{"website-images", []string{"-u", "https://example.test", "-o", "out", "-f", "jpeg", "-q", "80", "--timeout", "7", "--max-pages", "0"}, map[string]string{"url": "https://example.test", "output_directory": "out", "output_format": "jpeg", "quality": "80", "timeout": "7", "max_pages": "0"}},
		{"logos", []string{"-n", "A,B", "-o", "out", "--timeout", "7", "--max-candidates", "10", "--overwrite", "--no-manifest"}, map[string]string{"names": "A,B", "output_directory": "out", "timeout": "7", "max_candidates": "10", "overwrite": "true", "write_manifest": "false"}},
		{"email", []string{"-c", "config", "-r", "recipients", "-b", "body", "-d", "attachments"}, map[string]string{"config_file": "config", "recipients_file": "recipients", "body_file": "body", "attachments_directory": "attachments"}},
		{"colors", []string{"-p", "src", "-f", "a.css", "--no-backup", "-a", "--no-dry-run"}, map[string]string{"path": "src", "file": "a.css", "create_backups": "false", "dry_run": "false"}},
		{"rename", []string{"-i", "in", "-p", "{name}", "--prefix", "p", "--suffix", "s", "--replace-from", "a", "--replace-to", "b", "--lowercase", "--uppercase=false", "--add-date", "--add-sequence", "-r", "-n", "--file-pattern", "*.txt"}, map[string]string{"input_directory": "in", "pattern": "{name}", "prefix": "p", "suffix": "s", "replace_from": "a", "replace_to": "b", "lowercase": "true", "uppercase": "false", "add_date": "true", "add_sequence": "true", "recursive": "true", "dry_run": "true", "file_pattern": "*.txt"}},
		{"validate", []string{"-i", "a.csv", "-s", "schema", "-o", "report", "--strict", "--clean", "-f", "json"}, map[string]string{"input_file": "a.csv", "schema_file": "schema", "report_file": "report", "strict": "true", "clean_invalid": "true", "report_format": "json"}},
		{"md2pdf", []string{"-i", "a.md", "-o", "a.pdf", "-c", "style.css", "--page-size", "Letter", "--toc", "--syntax-highlight=false", "-r"}, map[string]string{"input_path": "a.md", "output_path": "a.pdf", "css_file": "style.css", "page_size": "Letter", "include_toc": "true", "syntax_highlighting": "false", "recursive": "true"}},
	}
	for _, test := range tests {
		t.Run(test.task, func(t *testing.T) {
			parsed, err := parseFlags(test.task, append(test.flags, "-y", "--json"))
			if err != nil {
				t.Fatal(err)
			}
			if !reflect.DeepEqual(parsed.values, test.expected) || !parsed.yes || !parsed.json {
				t.Fatalf("wrong translation: %+v", parsed)
			}
			// Each long spelling and short spelling must map to the same input.
			for name, field := range flagMap(test.task) {
				args := []string{"--" + name + "=value"}
				if booleanFields[strings.TrimPrefix(field, "!")] {
					args = []string{"--" + name + "=true"}
				}
				if _, err := parseFlags(test.task, args); err != nil {
					t.Errorf("%s: %v", name, err)
				}
			}
		})
	}
}

func TestSchemaDrivenValuesAndDefaults(t *testing.T) {
	min, max := float64(1), float64(100)
	task := backend.Automation{ID: "website-images", InputSchema: backend.Schema{
		Required: []string{"url"},
		Properties: map[string]backend.Field{
			"url":           {Type: "string", MinLength: 1},
			"quality":       {Type: "integer", Minimum: &min, Maximum: &max, Default: 85},
			"timeout":       {Type: "integer", Minimum: &min},
			"output_format": {Type: "string", Enum: []string{"jpg", "webp", "png"}},
		},
	}}
	o, err := parseFlags(task.ID, []string{"-u", "https://example.test", "-q", "90", "-f", "jpeg"})
	if err != nil {
		t.Fatal(err)
	}
	payload, err := o.payload(task)
	if err != nil {
		t.Fatal(err)
	}
	if payload["quality"] != int64(90) || payload["output_format"] != "jpg" || len(payload) != 3 {
		t.Fatalf("wrong payload/default injection: %v", payload)
	}
	for _, args := range [][]string{{"-u", "x", "-q", "101"}, {"-u", "x", "-q", "1.5"}, {"-u", "x", "--timeout", "0"}, {"-u", "x", "-f", "gif"}, {"-q", "80"}} {
		o, err := parseFlags(task.ID, args)
		if err == nil {
			_, err = o.payload(task)
		}
		if err == nil {
			t.Errorf("invalid values accepted: %v", args)
		}
	}
}

func TestWrongArgumentsBeforePython(t *testing.T) {
	t.Setenv("R10N_BACKEND", "/does/not/exist")
	for _, args := range [][]string{
		{"legacy"}, {"unknown"}, {"contacts", "extra"}, {"contacts", "--unknown"}, {"images", "-q"}, {"logos", "--overwrite=maybe"}, {"contacts", "--yes=maybe"},
		{"list", "extra"}, {"tui", "extra"}, {"init", "extra"}, {"status", "extra"}, {"upgrade", "--version", "v1.2.bad"},
		{"contacts", "-i", "numbers.txt"}, {"run", "contacts", "--input-json", "{}"},
		{"contacts"}, {"tui"},
	} {
		if code := backend.ExitCode(Run(context.Background(), args)); code != 2 {
			t.Errorf("%v: expected exit 2, got %d", args, code)
		}
	}
}

func TestColorsAllIsConfirmationAlias(t *testing.T) {
	for _, spelling := range []string{"--all", "-a"} {
		options, err := parseFlags("colors", []string{spelling})
		if err != nil || !options.yes || len(options.values) != 0 {
			t.Fatalf("%s must authorize without changing worker defaults: %+v, %v", spelling, options, err)
		}
	}
	options, err := parseFlags("colors", []string{"--all=false"})
	if err != nil || options.yes {
		t.Fatalf("false must not authorize execution: %+v, %v", options, err)
	}
}

func TestRunAcceptsRegistryDefinedTask(t *testing.T) {
	options, err := parseRun(context.Background(), []string{"new-registry-task", "--input-json", `{"value":"hello"}`, "--yes"})
	if err != nil || options.id != "new-registry-task" || options.payload["value"] != "hello" {
		t.Fatalf("generic JSON execution must not require a hardcoded flag alias entry: %+v, %v", options, err)
	}
}

func TestPDFTemplateIsNotIgnored(t *testing.T) {
	o, err := parseFlags("fill-pdfs", []string{"-t", "template.pdf", "-c", "missing.json", "-y"})
	if err != nil || o.template != "template.pdf" {
		t.Fatalf("%+v %v", o, err)
	}
	err = checkPDFConfig(backend.Automation{}, map[string]any{"config_file": "missing.json"}, o.template)
	if err == nil || !strings.Contains(err.Error(), "r10n configure") {
		t.Fatal(err)
	}
	err = checkPDFConfig(backend.Automation{}, map[string]any{"config_file": "missing.json"}, "")
	if err == nil || !strings.Contains(err.Error(), "r10n configure") {
		t.Fatal(err)
	}
}

func TestMain(m *testing.M) {
	if os.Getenv("R10N_CLI_HELPER") == "1" {
		switch os.Args[1] {
		case "catalog":
			fmt.Println(`{"protocol":1,"automations":[{"id":"contacts","title":"Contacts","input_schema":{"properties":{"input_file":{"type":"string"},"output_file":{"type":"string"},"prefix":{"type":"string"}}},"field_order":["input_file","output_file","prefix"]}]}`)
		case "worker":
			var payload map[string]any
			if err := json.NewDecoder(os.Stdin).Decode(&payload); err != nil {
				os.Exit(2)
			}
			fmt.Println(`{"type":"hello","protocol":1}`)
			fmt.Println(`{"type":"started","protocol":1,"automation":"contacts"}`)
			_ = json.NewEncoder(os.Stdout).Encode(map[string]any{"type": "completed", "automation": "contacts", "success": true, "result": payload})
		default:
			os.Exit(2)
		}
		os.Exit(0)
	}
	os.Exit(m.Run())
}

func TestActualFlagPayloadForwarding(t *testing.T) {
	executable, _ := os.Executable()
	t.Setenv("R10N_BACKEND", executable)
	t.Setenv("R10N_CLI_HELPER", "1")
	old := stdout
	defer func() { stdout = old }()
	var output strings.Builder
	stdout = &output
	want := "file name; $(not a shell).txt"
	if err := Run(context.Background(), []string{"contacts", "-i", want, "-o", "out.vcf", "-p", "Team", "-y", "--json"}); err != nil {
		t.Fatal(err)
	}
	lines := strings.Split(strings.TrimSpace(output.String()), "\n")
	if len(lines) != 3 {
		t.Fatalf("JSON output contaminated: %s", output.String())
	}
	var final backend.Event
	if err := json.Unmarshal([]byte(lines[2]), &final); err != nil {
		t.Fatal(err)
	}
	if final.Result["input_file"] != want || final.Result["output_file"] != "out.vcf" || final.Result["prefix"] != "Team" {
		t.Fatalf("payload lost: %+v", final)
	}
}
