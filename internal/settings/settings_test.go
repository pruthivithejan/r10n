package settings

import (
	"os"
	"os/exec"
	"path/filepath"
	"strings"
	"testing"
)

func TestLoadMissingSettingsDoesNotCreateDirectory(t *testing.T) {
	root := filepath.Join(t.TempDir(), "user", "config")
	t.Setenv("R10N_CONFIG_DIR", root)
	document, err := Load()
	if err != nil {
		t.Fatal(err)
	}
	if document.Version != Version || document.Theme != "dark" {
		t.Fatalf("unexpected defaults: %#v", document)
	}
	if _, err := os.Stat(root); !os.IsNotExist(err) {
		t.Fatalf("reading default settings created %q", root)
	}
}

func TestDirectoryExpandsUserHomeOverride(t *testing.T) {
	home, err := os.UserHomeDir()
	if err != nil {
		t.Fatal(err)
	}
	t.Setenv("R10N_CONFIG_DIR", filepath.Join("~", "r10n-settings-test"))
	directory, err := Directory()
	if err != nil {
		t.Fatal(err)
	}
	if directory != filepath.Join(home, "r10n-settings-test") {
		t.Fatalf("expanded config directory = %q, want %q", directory, filepath.Join(home, "r10n-settings-test"))
	}
}

func TestDirectoryExpandsEnvironmentVariables(t *testing.T) {
	t.Setenv("R10N_CONFIG_DIR", filepath.Join(t.TempDir(), "$R10N_CONFIG_SEGMENT"))
	t.Setenv("R10N_CONFIG_SEGMENT", "expanded")
	directory, err := Directory()
	if err != nil {
		t.Fatal(err)
	}
	if filepath.Base(directory) != "expanded" {
		t.Fatalf("config directory did not expand: %q", directory)
	}
}

func TestPythonPDFSettingsRoundTrip(t *testing.T) {
	root := t.TempDir()
	t.Setenv("R10N_CONFIG_DIR", root)
	content := `{"version":1,"theme":"dark","active_pdf_profile":"certificate","pdf_profiles":{"certificate":{"template_pdf":"template.pdf","output_directory":"output","font_family":"Helvetica","fields":{"name":{"x":100.0,"y":200.0,"font_size":24.0,"font_weight":400,"alignment":"center","color":[0.5,0.25,1.0],"max_width":null,"font_path":null}}}}}`
	if err := os.WriteFile(filepath.Join(root, "config.json"), []byte(content), 0600); err != nil {
		t.Fatal(err)
	}
	document, err := Load()
	if err != nil {
		t.Fatal(err)
	}
	if _, err := Save(document); err != nil {
		t.Fatal(err)
	}
	reloaded, err := Load()
	if err != nil {
		t.Fatal(err)
	}
	color := reloaded.PDFProfiles["certificate"].Fields["name"].Color
	if len(color) != 3 || color[0] != 0.5 || color[1] != 0.25 || color[2] != 1 {
		t.Fatalf("fractional color did not round-trip: %v", color)
	}
}

func TestPythonAndGoSettingsRoundTrip(t *testing.T) {
	python := os.Getenv("R10N_TEST_PYTHON")
	if python == "" {
		t.Skip("set R10N_TEST_PYTHON to a Python interpreter with r10n installed")
	}
	t.Setenv("R10N_TEST_ROOT", t.TempDir())
	t.Setenv("R10N_CONFIG_DIR", filepath.Join("$R10N_TEST_ROOT", "settings"))
	write := `from r10n_backend.settings import Settings, PDFProfile, save_settings
save_settings(Settings(active_pdf_profile="certificate", pdf_profiles={"certificate": PDFProfile(template_pdf="input.pdf", output_directory="output", fields={"name": {"x": 1, "y": 2, "font_size": 12, "color": [0.5, 0.25, 1]}})}))`
	if output, err := exec.Command(python, "-c", write).CombinedOutput(); err != nil {
		t.Fatalf("Python settings write failed: %v\n%s", err, output)
	}
	document, err := Load()
	if err != nil {
		t.Fatal(err)
	}
	if _, err := Save(document); err != nil {
		t.Fatal(err)
	}
	read := `from r10n_backend.settings import load_settings
assert load_settings().pdf_profiles["certificate"].fields["name"].color == (0.5, 0.25, 1.0)`
	if output, err := exec.Command(python, "-c", read).CombinedOutput(); err != nil {
		t.Fatalf("Python settings read failed: %v\n%s", err, output)
	}
}

func TestSaveRejectsPDFSettingsRejectedByBackend(t *testing.T) {
	t.Setenv("R10N_CONFIG_DIR", t.TempDir())
	for _, field := range []PDFField{
		{FontSize: 12, Color: []float64{0.5, 0.5}},
		{FontSize: 12, MaxWidth: -1},
		{FontSize: 12, FontWeight: "heavy"},
		{FontSize: 12, FontWeight: 2.5},
	} {
		document := defaults()
		document.PDFProfiles["certificate"] = PDFProfile{
			TemplatePDF: "template.pdf", OutputDirectory: "output",
			Fields: map[string]PDFField{"name": field},
		}
		if _, err := Save(document); err == nil {
			t.Fatalf("accepted incompatible PDF field: %#v", field)
		}
	}
}

func TestSaveSettingsIsPrivateAndRoundTrips(t *testing.T) {
	root := filepath.Join(t.TempDir(), "user", "config")
	t.Setenv("R10N_CONFIG_DIR", root)
	document := defaults()
	document.Accessible = true
	document.OutputDirectory = filepath.Join(t.TempDir(), "results")
	document.SMTPProfiles["work"] = SMTPProfile{
		Server: "smtp.example.test", Port: 587, Email: "sender@example.test",
	}
	document.ActiveSMTPProfile = "work"

	path, err := Save(document)
	if err != nil {
		t.Fatal(err)
	}
	loaded, err := Load()
	if err != nil {
		t.Fatal(err)
	}
	if !loaded.Accessible || loaded.ActiveSMTPProfile != "work" {
		t.Fatalf("settings did not round-trip: %#v", loaded)
	}
	data, err := os.ReadFile(path)
	if err != nil {
		t.Fatal(err)
	}
	if strings.Contains(string(data), "password") {
		t.Fatal("settings file must never contain a credential")
	}
	if runtimeOS := os.PathSeparator; runtimeOS != '\\' {
		info, err := os.Stat(path)
		if err != nil {
			t.Fatal(err)
		}
		if info.Mode().Perm() != 0600 {
			t.Fatalf("settings permissions = %o, want 600", info.Mode().Perm())
		}
	}
}

func TestSaveRejectsDanglingProfileAndInvalidTheme(t *testing.T) {
	if _, err := Save(Document{
		Theme: "solarized", ActiveSMTPProfile: "missing",
	}); err == nil {
		t.Fatal("invalid theme should not be saved")
	}
	document := defaults()
	document.ActiveSMTPProfile = "missing"
	if _, err := Save(document); err == nil {
		t.Fatal("dangling active profile should not be saved")
	}
}

func TestLoadRejectsUnknownAndFutureSettings(t *testing.T) {
	root := t.TempDir()
	t.Setenv("R10N_CONFIG_DIR", root)
	path := filepath.Join(root, "config.json")
	if err := os.MkdirAll(root, 0700); err != nil {
		t.Fatal(err)
	}
	for _, contents := range []string{
		`{"version":999,"theme":"dark"}`,
		`{"version":1,"password":"must-not-be-persisted"}`,
	} {
		if err := os.WriteFile(path, []byte(contents), 0600); err != nil {
			t.Fatal(err)
		}
		if _, err := Load(); err == nil {
			t.Fatalf("expected invalid settings to be rejected: %s", contents)
		}
	}
}
