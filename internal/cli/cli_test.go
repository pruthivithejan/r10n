package cli

import (
	"bytes"
	"context"
	"errors"
	"fmt"
	"os"
	"path/filepath"
	"strings"
	"testing"
	"time"
)

func TestParseRun(t *testing.T) {
	file := filepath.Join(t.TempDir(), "inputs.json")
	if err := os.WriteFile(file, []byte(`{"quality":85,"prefix":null}`), 0600); err != nil {
		t.Fatal(err)
	}
	for _, test := range []struct {
		name  string
		args  []string
		valid bool
	}{
		{"defaults", []string{"contacts", "--yes"}, true},
		{"inline", []string{"images", "--input-json", `{"quality":85}`, "--json", "--yes"}, true},
		{"file", []string{"images", "--input-file", file, "--yes"}, true},
		{"array", []string{"images", "--input-json", `[]`}, false},
		{"null", []string{"images", "--input-json", `null`}, false},
		{"malformed", []string{"images", "--input-json", `bad`}, false},
		{"trailing-json", []string{"images", "--input-json", `{} {}`}, false},
		{"empty-explicit", []string{"images", "--input-json", ""}, false},
		{"both-sources", []string{"images", "--input-json", `{}`, "--input-file", file}, false},
		{"missing-file", []string{"images", "--input-file", file + ".missing"}, false},
		{"unexpected-argument", []string{"images", "extra"}, false},
		{"no-task", nil, false},
	} {
		t.Run(test.name, func(t *testing.T) {
			_, err := parseRun(context.Background(), test.args)
			if (err == nil) != test.valid {
				t.Fatalf("valid=%v, err=%v", test.valid, err)
			}
		})
	}
	options, err := parseRun(context.Background(), []string{"images", "--input-json", `{"quality":9007199254740993}`})
	if err != nil || fmt.Sprint(options.payload["quality"]) != "9007199254740993" {
		t.Fatal("input numbers must not be rounded before Python validation")
	}
}

func TestStdinInputCanBeCancelled(t *testing.T) {
	reader, writer, err := os.Pipe()
	if err != nil {
		t.Fatal(err)
	}
	defer reader.Close()
	defer writer.Close()
	original := stdin
	stdin = reader
	defer func() { stdin = original }()
	ctx, cancel := context.WithTimeout(context.Background(), 50*time.Millisecond)
	defer cancel()
	_, err = parseRun(ctx, []string{"contacts", "--input-file", "-"})
	if !errors.Is(err, context.DeadlineExceeded) {
		t.Fatalf("blocked stdin ignored cancellation: %v", err)
	}
}

func TestVersionAndHelpDoNotNeedBackend(t *testing.T) {
	t.Setenv("R10N_BACKEND", "/nonexistent/backend")
	original := stdout
	defer func() { stdout = original }()
	var output bytes.Buffer
	stdout = &output
	cases := [][]string{{"--version"}, {"--help"}, {"run", "--help"}, {"list", "--help"}, {"tui", "--help"}, {"configure", "--help"}, {"status", "--help"}, {"upgrade", "--help"}}
	for id := range aliases {
		cases = append(cases, []string{id, "--help"})
	}
	for _, args := range cases {
		if err := Run(context.Background(), args); err != nil {
			t.Fatal(err)
		}
	}
	if !strings.Contains(output.String(), "r10n, version") || !strings.Contains(output.String(), "--input-json") {
		t.Fatal(output.String())
	}
}
