package backend

import (
	"context"
	"encoding/json"
	"fmt"
	"os"
	"strings"
	"testing"
	"time"
)

// TestBackendHelperProcess uses the test executable, not Python or the network.
func TestBackendHelperProcess(t *testing.T) {
	if os.Getenv("R10N_TEST_HELPER") != "1" {
		return
	}
	switch os.Getenv("R10N_TEST_SCENARIO") {
	case "catalog":
		fmt.Print(`{"protocol":2,"automations":[{"id":"contacts","title":"Contacts","input_schema":{"properties":{"path":{"type":"string","default":"a","ui:widget":"file"}}},"field_order":["path"]}]}`)
	case "bad-catalog":
		fmt.Print(`{"protocol":2,"automations":[]}`)
	case "mismatched-catalog-version":
		fmt.Print(`{"protocol":2,"version":"99.0.0","automations":[{"id":"contacts","input_schema":{"properties":{}},"field_order":[]}]}`)
	case "duplicate-field":
		fmt.Print(`{"protocol":2,"automations":[{"id":"x","input_schema":{"properties":{"a":{},"b":{}}},"field_order":["a","a"]}]}`)
	case "invalid":
		fmt.Println("not json")
	case "wrong-protocol":
		fmt.Println(`{"type":"hello","protocol":1}`)
	case "truncated":
		fmt.Println(`{"type":"hello","protocol":2}`)
	case "extra":
		fmt.Println("{\"type\":\"hello\",\"protocol\":2}\n{\"type\":\"started\",\"protocol\":2,\"automation\":\"contacts\"}\n{\"type\":\"completed\",\"automation\":\"contacts\",\"success\":true,\"result\":{}}\n{\"type\":\"log\",\"message\":\"late\"}")
	case "input-error":
		fmt.Println("{\"type\":\"hello\",\"protocol\":2}\n{\"type\":\"error\",\"kind\":\"input\",\"error\":\"invalid inputs\"}")
		os.Exit(2)
	case "failed":
		fmt.Println("{\"type\":\"hello\",\"protocol\":2}\n{\"type\":\"started\",\"protocol\":2,\"automation\":\"contacts\"}\n{\"type\":\"completed\",\"automation\":\"contacts\",\"success\":false,\"result\":{}}")
	case "incomplete-completed":
		fmt.Println("{\"type\":\"hello\",\"protocol\":2}\n{\"type\":\"started\",\"protocol\":2,\"automation\":\"contacts\"}\n{\"type\":\"completed\",\"automation\":\"contacts\"}")
	case "mismatched-automation":
		fmt.Println("{\"type\":\"hello\",\"protocol\":2}\n{\"type\":\"started\",\"protocol\":2,\"automation\":\"images\"}")
	case "missing-started":
		fmt.Println("{\"type\":\"hello\",\"protocol\":2}\n{\"type\":\"completed\",\"automation\":\"contacts\",\"success\":true,\"result\":{}}")
	case "cancelled":
		fmt.Println("{\"type\":\"hello\",\"protocol\":2}\n{\"type\":\"cancelled\"}")
	case "blocking":
		fmt.Println(`{"type":"hello","protocol":2}`)
		time.Sleep(30 * time.Second)
	case "success", "live":
		var payload map[string]any
		if err := json.NewDecoder(os.Stdin).Decode(&payload); err != nil {
			os.Exit(2)
		}
		fmt.Println("{\"type\":\"hello\",\"protocol\":2}\n{\"type\":\"started\",\"protocol\":2,\"automation\":\"contacts\"}\n{\"type\":\"progress\",\"current\":1,\"total\":2}")
		if os.Getenv("R10N_TEST_SCENARIO") == "live" {
			time.Sleep(300 * time.Millisecond)
		}
		_ = json.NewEncoder(os.Stdout).Encode(map[string]any{"type": "completed", "automation": "contacts", "success": true, "result": payload})
	default:
		os.Exit(3)
	}
	os.Exit(0)
}

func helperBackend(t *testing.T, scenario string) Backend {
	t.Helper()
	executable, err := os.Executable()
	if err != nil {
		t.Fatal(err)
	}
	env := setEnv(os.Environ(), "R10N_TEST_HELPER", "1")
	env = setEnv(env, "R10N_TEST_SCENARIO", scenario)
	return Backend{executable, []string{"-test.run=^TestBackendHelperProcess$", "--"}, env}
}

func TestLoadCatalog(t *testing.T) {
	catalog, err := helperBackend(t, "catalog").LoadCatalog(context.Background())
	if err != nil {
		t.Fatal(err)
	}
	if len(catalog.Automations) != 1 || catalog.Automations[0].FieldOrder[0] != "path" ||
		!strings.Contains(string(catalog.Raw), `"ui:widget":"file"`) {
		t.Fatalf("unexpected or lossy catalog: %+v", catalog)
	}
	for _, scenario := range []string{"bad-catalog", "duplicate-field", "mismatched-catalog-version"} {
		if _, err := helperBackend(t, scenario).LoadCatalog(context.Background()); err == nil {
			t.Errorf("%s accepted an invalid catalog", scenario)
		}
	}
}

func TestParseCatalogSharedContract(t *testing.T) {
	raw := []byte(`{"protocol":2,"version":"0.13.0","automations":[{"id":"new-task","input_schema":{"properties":{"path":{"type":"string"}}},"field_order":["path"]}]}`)
	catalog, err := ParseCatalog(raw)
	if err != nil || catalog.Version != "0.13.0" || catalog.Automations[0].ID != "new-task" {
		t.Fatalf("valid registry metadata rejected: %+v, %v", catalog, err)
	}
	raw[0] = ' '
	if !strings.HasPrefix(string(catalog.Raw), "{") {
		t.Fatal("catalog retained a mutable caller buffer")
	}
	for _, invalid := range []string{
		`not json`,
		`{"protocol":1,"automations":[]}`,
		`{"protocol":2,"automations":[]}`,
		`{"protocol":2,"automations":[{"id":"x","input_schema":{"properties":{"a":{}}},"field_order":[]}]}`,
	} {
		if _, err := ParseCatalog([]byte(invalid)); err == nil {
			t.Errorf("invalid catalog accepted: %s", invalid)
		}
	}
}

func TestExplicitCatalogProtocolDoesNotRelaxBackendContract(t *testing.T) {
	raw := []byte(`{"protocol":1,"version":"0.12.2","automations":[{"id":"contacts","input_schema":{"properties":{}},"field_order":[]}]}`)
	if _, err := ParseCatalog(raw); err == nil {
		t.Fatal("live backend accepted a legacy worker contract")
	}
	if _, err := ParseCatalogForProtocol(raw, 2); err == nil {
		t.Fatal("catalog did not enforce selected contract")
	}
	if _, err := ParseCatalogForProtocol(raw, 1); err != nil {
		t.Fatal(err)
	}
	for _, invalid := range []string{
		`{"protocol":1,"automations":[]}`,
		`{"protocol":1,"automations":[{"id":"x","input_schema":{"properties":{"a":{}}},"field_order":[]}]}`,
	} {
		if _, err := ParseCatalogForProtocol([]byte(invalid), 1); err == nil {
			t.Fatal("legacy release bypassed schema validation")
		}
	}
}

func TestStreamSuccessAndLiveDelivery(t *testing.T) {
	for _, scenario := range []string{"success", "live"} {
		t.Run(scenario, func(t *testing.T) {
			var progressAt, completedAt time.Time
			var events []Event
			err := helperBackend(t, scenario).Stream(context.Background(), "contacts",
				map[string]any{"path": "a file; not a shell command"}, func(event Event) error {
					if event.Type == "progress" {
						progressAt = time.Now()
					}
					if event.Type == "completed" {
						completedAt = time.Now()
					}
					if !json.Valid(event.Raw) {
						t.Error("lost original JSON event")
					}
					events = append(events, event)
					return nil
				})
			if err != nil {
				t.Fatal(err)
			}
			if len(events) != 4 || events[3].Result["path"] != "a file; not a shell command" {
				t.Fatalf("unexpected events: %+v", events)
			}
			if scenario == "live" && completedAt.Sub(progressAt) < 200*time.Millisecond {
				t.Error("progress was buffered until worker completion")
			}
		})
	}
}

func TestStreamFailures(t *testing.T) {
	for _, test := range []struct {
		scenario string
		code     int
	}{
		{"invalid", 1}, {"wrong-protocol", 1}, {"truncated", 1}, {"extra", 1},
		{"input-error", 2}, {"failed", 1}, {"cancelled", 130},
		{"incomplete-completed", 1}, {"mismatched-automation", 1}, {"missing-started", 1},
	} {
		t.Run(test.scenario, func(t *testing.T) {
			err := helperBackend(t, test.scenario).Stream(context.Background(), "contacts", map[string]any{}, func(Event) error { return nil })
			if err == nil || ExitCode(err) != test.code {
				t.Fatalf("got %v (code %d), expected code %d", err, ExitCode(err), test.code)
			}
		})
	}
}

func TestStreamCancellation(t *testing.T) {
	ctx, cancel := context.WithCancel(context.Background())
	start := time.Now()
	err := helperBackend(t, "blocking").Stream(ctx, "contacts", map[string]any{}, func(Event) error {
		cancel()
		return nil
	})
	if ExitCode(err) != 130 || time.Since(start) > 3*time.Second {
		t.Fatalf("cancellation did not promptly reap worker: %v", err)
	}
}

func TestStreamCallbackFailure(t *testing.T) {
	expected := fmt.Errorf("output writer closed")
	err := helperBackend(t, "blocking").Stream(context.Background(), "contacts", map[string]any{}, func(Event) error {
		return expected
	})
	if err != expected {
		t.Fatalf("got %v, expected callback error", err)
	}
}

func TestBoundedDiagnostics(t *testing.T) {
	var buffer limitedBuffer
	data := make([]byte, 128*1024)
	if n, err := buffer.Write(data); n != len(data) || err != nil || buffer.Len() != 64*1024 {
		t.Fatal("stderr should be drained with bounded diagnostic retention")
	}
}
