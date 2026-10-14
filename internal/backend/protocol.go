package backend

import (
	"bufio"
	"bytes"
	"context"
	"encoding/json"
	"errors"
	"fmt"
	"io"
	"os/exec"

	"github.com/pruthivithejan/r10n"
)

const ProtocolVersion = 1

// Catalog is exported by Python; all forms and task metadata derive from it.
type Catalog struct {
	Protocol    int             `json:"protocol"`
	Version     string          `json:"version"`
	Automations []Automation    `json:"automations"`
	Raw         json.RawMessage `json:"-"`
}

type Automation struct {
	ID           string   `json:"id"`
	Title        string   `json:"title"`
	Description  string   `json:"description"`
	Category     string   `json:"category"`
	Roles        []string `json:"roles"`
	Confirmation string   `json:"confirmation"`
	InputSchema  Schema   `json:"input_schema"`
	FieldOrder   []string `json:"field_order"`
}

type Schema struct {
	Properties map[string]Field `json:"properties"`
	Required   []string         `json:"required"`
}

// Field contains the scalar JSON Schema features used by current input models.
type Field struct {
	Type             string   `json:"type"`
	Title            string   `json:"title"`
	Description      string   `json:"description"`
	Default          any      `json:"default"`
	Enum             []string `json:"enum"`
	AnyOf            []Field  `json:"anyOf"`
	Minimum          *float64 `json:"minimum"`
	Maximum          *float64 `json:"maximum"`
	ExclusiveMinimum *float64 `json:"exclusiveMinimum"`
	MinLength        int      `json:"minLength"`
}

// Scalar resolves nullable fields without discarding the outer default/label.
func (f Field) Scalar() (Field, bool) {
	if len(f.AnyOf) == 0 {
		return f, false
	}
	for _, alternative := range f.AnyOf {
		if alternative.Type != "null" {
			alternative.Title = f.Title
			alternative.Description = f.Description
			alternative.Default = f.Default
			return alternative, true
		}
	}
	return f, true
}

// LoadCatalog fetches the registry without importing automation implementations.
func (b Backend) LoadCatalog(ctx context.Context) (Catalog, error) {
	cmd := b.Command(ctx, "catalog")
	var stderr limitedBuffer
	cmd.Stderr = &stderr
	raw, err := cmd.Output()
	if err != nil {
		if ctx.Err() != nil {
			return Catalog{}, ctx.Err()
		}
		return Catalog{}, fmt.Errorf("load automation catalog: %w: %s", err, stderr.String())
	}
	catalog, err := ParseCatalog(raw)
	if err == nil && catalog.Version != "" && catalog.Version != r10n.Version {
		return catalog, fmt.Errorf("backend version %s does not match native version %s; reinstall the complete bundle or sync the source environment", catalog.Version, r10n.Version)
	}
	return catalog, err
}

// ParseCatalog validates the same registry contract for direct and native probes.
func ParseCatalog(raw []byte) (Catalog, error) {
	var catalog Catalog
	if err := json.Unmarshal(raw, &catalog); err != nil {
		return catalog, fmt.Errorf("invalid backend catalog: %w", err)
	}
	catalog.Raw = append(json.RawMessage{}, raw...)
	if catalog.Protocol != ProtocolVersion {
		return catalog, fmt.Errorf("unsupported catalog protocol %d (expected %d)", catalog.Protocol, ProtocolVersion)
	}
	if len(catalog.Automations) == 0 {
		return catalog, errors.New("backend catalog contains no automations")
	}
	seen := map[string]bool{}
	for _, task := range catalog.Automations {
		if task.ID == "" || seen[task.ID] || len(task.FieldOrder) != len(task.InputSchema.Properties) {
			return catalog, fmt.Errorf("invalid catalog definition for %q", task.ID)
		}
		seen[task.ID] = true
		fieldNames := map[string]bool{}
		for _, name := range task.FieldOrder {
			if _, ok := task.InputSchema.Properties[name]; !ok || fieldNames[name] {
				return catalog, fmt.Errorf("unknown input %q in %s", name, task.ID)
			}
			fieldNames[name] = true
		}
	}
	return catalog, nil
}

// Event retains the original bytes for lossless --json forwarding.
type Event struct {
	Type       string          `json:"type"`
	Protocol   int             `json:"protocol"`
	Automation string          `json:"automation"`
	Message    string          `json:"message"`
	Error      string          `json:"error"`
	Path       string          `json:"path"`
	Current    float64         `json:"current"`
	Total      float64         `json:"total"`
	Success    *bool           `json:"success"`
	Result     map[string]any  `json:"result"`
	Raw        json.RawMessage `json:"-"`
}

// RunError preserves meaningful worker exit codes across the native boundary.
type RunError struct {
	Code    int
	Message string
}

func (e *RunError) Error() string { return e.Message }

// ExitCode maps protocol/input failures, execution failures, and cancellation.
func ExitCode(err error) int {
	if err == nil {
		return 0
	}
	var runError *RunError
	if errors.As(err, &runError) {
		return runError.Code
	}
	var exitError *exec.ExitError
	if errors.As(err, &exitError) && exitError.ExitCode() > 0 {
		return exitError.ExitCode()
	}
	if errors.Is(err, context.Canceled) {
		return 130
	}
	return 1
}

// Stream runs exactly one worker and enforces the versioned JSON Lines contract.
// The callback is synchronous, providing bounded backpressure for large jobs.
func (b Backend) Stream(ctx context.Context, id string, payload map[string]any, receive func(Event) error) error {
	raw, err := json.Marshal(payload)
	if err != nil {
		return err
	}
	ctx, cancel := context.WithCancel(ctx)
	defer cancel()
	cmd := b.Command(ctx, "worker", id)
	cmd.Stdin = bytes.NewReader(raw)
	var stderr limitedBuffer
	cmd.Stderr = &stderr
	stdout, err := cmd.StdoutPipe()
	if err != nil {
		return err
	}
	if err := cmd.Start(); err != nil {
		return fmt.Errorf("start Python worker: %w", err)
	}
	hello, started, terminal := false, false, false
	var terminalError string
	terminalCode := 1
	scanner := bufio.NewScanner(stdout)
	scanner.Buffer(make([]byte, 64*1024), 8*1024*1024)
	for scanner.Scan() {
		var event Event
		if err = json.Unmarshal(scanner.Bytes(), &event); err != nil {
			err = fmt.Errorf("invalid worker JSON Lines event: %w", err)
			break
		}
		if !hello {
			if event.Type != "hello" || event.Protocol != ProtocolVersion {
				err = fmt.Errorf("unsupported worker handshake (expected protocol %d)", ProtocolVersion)
				break
			}
			hello = true
		} else if event.Type == "hello" || terminal {
			err = errors.New("unexpected event after worker handshake or terminal event")
			break
		}
		switch event.Type {
		case "hello":
		case "started":
			if started || event.Protocol != ProtocolVersion || event.Automation != id {
				err = errors.New("invalid worker started event")
				break
			}
			started = true
		case "progress", "log", "artifact":
			if !started {
				err = errors.New("worker emitted execution events before started")
			}
		case "completed":
			if !started || event.Success == nil || event.Result == nil || event.Automation != id {
				err = errors.New("incomplete or mismatched worker completed event")
				break
			}
			terminal = true
			if event.Success != nil && !*event.Success {
				terminalError = "automation reported an unsuccessful result"
			}
		case "error":
			terminal, terminalError = true, event.Error
			if terminalError == "" {
				terminalError = "worker reported an error"
			}
		case "cancelled":
			terminal, terminalError = true, "automation cancelled"
			terminalCode = 130
		default:
			err = fmt.Errorf("unknown worker event type %q", event.Type)
		}
		if err != nil {
			break
		}
		event.Raw = append(json.RawMessage{}, scanner.Bytes()...)
		if err = receive(event); err != nil {
			break
		}
	}
	if err == nil {
		err = scanner.Err()
	}
	if err != nil {
		cancel()
	}
	waitErr := cmd.Wait()
	if ctx.Err() != nil && err == nil {
		return ctx.Err()
	}
	if err != nil {
		return err
	}
	if waitErr != nil {
		message := terminalError
		if message == "" {
			message = fmt.Sprintf("Python worker failed: %v: %s", waitErr, stderr.String())
		}
		return &RunError{ExitCode(waitErr), message}
	}
	if !hello || !terminal {
		return errors.New("Python worker exited without a complete protocol exchange")
	}
	if terminalError != "" {
		return &RunError{terminalCode, terminalError}
	}
	return nil
}

// limitedBuffer bounds stderr diagnostics while still draining the subprocess.
type limitedBuffer struct{ bytes.Buffer }

func (b *limitedBuffer) Write(data []byte) (int, error) {
	n := len(data)
	remaining := 64*1024 - b.Len()
	if remaining > 0 {
		_, _ = b.Buffer.Write(data[:min(remaining, n)])
	}
	return n, nil
}

var _ io.Writer = (*limitedBuffer)(nil)
