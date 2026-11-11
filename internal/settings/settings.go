// Package settings owns r10n's per-user, non-secret preferences and profiles.
package settings

import (
	"bytes"
	"encoding/json"
	"errors"
	"fmt"
	"os"
	"path/filepath"
	"runtime"
	"strconv"
	"strings"
)

const Version = 1

// Document contains preferences and reusable configuration. Credentials are
// deliberately excluded and belong in the operating system credential store.
type Document struct {
	Version           int                    `json:"version"`
	Theme             string                 `json:"theme"`
	Accessible        bool                   `json:"accessible"`
	ReducedMotion     bool                   `json:"reduced_motion"`
	OutputDirectory   string                 `json:"output_directory,omitempty"`
	ActiveSMTPProfile string                 `json:"active_smtp_profile,omitempty"`
	SMTPProfiles      map[string]SMTPProfile `json:"smtp_profiles,omitempty"`
	ActivePDFProfile  string                 `json:"active_pdf_profile,omitempty"`
	PDFProfiles       map[string]PDFProfile  `json:"pdf_profiles,omitempty"`
}

type SMTPProfile struct {
	Server  string `json:"smtp_server"`
	Port    int    `json:"smtp_port"`
	Email   string `json:"email"`
	Subject string `json:"subject"`
	UseTLS  bool   `json:"use_tls"`
}

type PDFProfile struct {
	TemplatePDF     string              `json:"template_pdf"`
	OutputDirectory string              `json:"output_directory"`
	FontFamily      string              `json:"font_family"`
	Fields          map[string]PDFField `json:"fields"`
}

type PDFField struct {
	X          float64   `json:"x"`
	Y          float64   `json:"y"`
	FontSize   float64   `json:"font_size"`
	FontWeight any       `json:"font_weight,omitempty"`
	Alignment  string    `json:"alignment"`
	Color      []float64 `json:"color,omitempty"`
	MaxWidth   float64   `json:"max_width,omitempty"`
	FontPath   string    `json:"font_path,omitempty"`
}

func defaults() Document {
	return Document{
		Version:      Version,
		Theme:        "dark",
		SMTPProfiles: map[string]SMTPProfile{},
		PDFProfiles:  map[string]PDFProfile{},
	}
}

// Directory returns the OS user config directory for r10n without creating it.
func Directory() (string, error) {
	if configured := os.Getenv("R10N_CONFIG_DIR"); configured != "" {
		configured = filepath.Clean(os.ExpandEnv(configured))
		if configured == "~" || strings.HasPrefix(configured, "~"+string(os.PathSeparator)) {
			home, err := os.UserHomeDir()
			if err != nil {
				return "", fmt.Errorf("resolve user home directory: %w", err)
			}
			if configured == "~" {
				configured = home
			} else {
				configured = filepath.Join(home, strings.TrimPrefix(configured, "~"+string(os.PathSeparator)))
			}
		}
		return filepath.Abs(configured)
	}
	if runtime.GOOS == "windows" {
		if local := os.Getenv("LOCALAPPDATA"); local != "" {
			return filepath.Join(local, "r10n"), nil
		}
	}
	base, err := os.UserConfigDir()
	if err != nil {
		return "", fmt.Errorf("resolve user configuration directory: %w", err)
	}
	return filepath.Join(base, "r10n"), nil
}

// Path returns the settings file path without creating it.
func Path() (string, error) {
	dir, err := Directory()
	if err != nil {
		return "", err
	}
	return filepath.Join(dir, "config.json"), nil
}

// Load reads and validates the single user settings document. A missing file
// returns built-in defaults and creates no filesystem state.
func Load() (Document, error) {
	path, err := Path()
	if err != nil {
		return Document{}, err
	}
	data, err := os.ReadFile(path)
	if errors.Is(err, os.ErrNotExist) {
		return defaults(), nil
	}
	if err != nil {
		return Document{}, fmt.Errorf("read r10n settings: %w", err)
	}
	document, err := Decode(data)
	if err != nil {
		return Document{}, fmt.Errorf("decode r10n settings: %w", err)
	}
	return document, nil
}

// Decode reads a portable or imported settings JSON object without touching disk.
func Decode(data []byte) (Document, error) {
	var document Document
	decoder := json.NewDecoder(bytes.NewReader(data))
	decoder.DisallowUnknownFields()
	if err := decoder.Decode(&document); err != nil {
		return Document{}, err
	}
	return normalize(document)
}

// normalize applies version checks and defaults without rejecting legacy data.
func normalize(document Document) (Document, error) {
	if document.Version > Version {
		return Document{}, fmt.Errorf(
			"settings version %d is newer than supported version %d",
			document.Version, Version,
		)
	}
	if document.Version == 0 {
		document.Version = Version
	}
	if document.Theme == "" {
		document.Theme = "dark"
	}
	if document.SMTPProfiles == nil {
		document.SMTPProfiles = map[string]SMTPProfile{}
	}
	if document.PDFProfiles == nil {
		document.PDFProfiles = map[string]PDFProfile{}
	}
	return document, nil
}

// validate checks settings before writing them.
func validate(document Document) (Document, error) {
	document, err := normalize(document)
	if err != nil {
		return Document{}, err
	}
	if document.Theme != "dark" && document.Theme != "light" && document.Theme != "system" {
		return Document{}, fmt.Errorf("unsupported theme %q", document.Theme)
	}
	document.Version = Version
	if document.ActiveSMTPProfile != "" {
		if _, ok := document.SMTPProfiles[document.ActiveSMTPProfile]; !ok {
			return Document{}, fmt.Errorf("active SMTP profile %q does not exist", document.ActiveSMTPProfile)
		}
	}
	if document.ActivePDFProfile != "" {
		if _, ok := document.PDFProfiles[document.ActivePDFProfile]; !ok {
			return Document{}, fmt.Errorf("active PDF profile %q does not exist", document.ActivePDFProfile)
		}
	}
	for name, profile := range document.SMTPProfiles {
		if name == "" || profile.Server == "" || profile.Port < 1 || profile.Port > 65535 || profile.Email == "" {
			return Document{}, fmt.Errorf("SMTP profile %q needs a server, valid port, and sender address", name)
		}
	}
	for name, profile := range document.PDFProfiles {
		if name == "" || profile.TemplatePDF == "" || profile.OutputDirectory == "" || len(profile.Fields) == 0 {
			return Document{}, fmt.Errorf("PDF profile %q needs a template, output directory, and at least one field", name)
		}
		for fieldName, field := range profile.Fields {
			if fieldName == "" || field.X < 0 || field.Y < 0 || field.FontSize <= 0 {
				return Document{}, fmt.Errorf("PDF profile %q contains invalid settings for field %q", name, fieldName)
			}
			if field.Alignment == "" {
				field.Alignment = "left"
				profile.Fields[fieldName] = field
			}
			if field.Alignment != "left" && field.Alignment != "center" && field.Alignment != "right" {
				return Document{}, fmt.Errorf("PDF profile %q has unsupported alignment for field %q", name, fieldName)
			}
			if len(field.Color) != 0 && len(field.Color) != 3 {
				return Document{}, fmt.Errorf("PDF profile %q needs three color components for field %q", name, fieldName)
			}
			if field.MaxWidth < 0 {
				return Document{}, fmt.Errorf("PDF profile %q has invalid maximum width for field %q", name, fieldName)
			}
			switch weight := field.FontWeight.(type) {
			case nil, int:
			case bool:
				field.FontWeight = 0
				if weight {
					field.FontWeight = 1
				}
				profile.Fields[fieldName] = field
			case float64:
				if weight != float64(int64(weight)) {
					return Document{}, fmt.Errorf("PDF profile %q has invalid font weight for field %q", name, fieldName)
				}
			case string:
				if weight != "bold" && weight != "normal" {
					integer := strings.TrimSpace(weight)
					if whole, fraction, found := strings.Cut(integer, "."); found && fraction != "" && strings.Trim(fraction, "0") == "" {
						integer = whole
					}
					numeric, err := strconv.Atoi(integer)
					if err != nil {
						return Document{}, fmt.Errorf("PDF profile %q has invalid font weight for field %q", name, fieldName)
					}
					field.FontWeight = numeric
					profile.Fields[fieldName] = field
				}
			default:
				return Document{}, fmt.Errorf("PDF profile %q has invalid font weight for field %q", name, fieldName)
			}
		}
	}
	return document, nil
}

// Save validates and atomically writes settings with private file permissions.
func Save(document Document) (string, error) {
	document, err := validate(document)
	if err != nil {
		return "", err
	}
	path, err := Path()
	if err != nil {
		return "", err
	}
	dir := filepath.Dir(path)
	if info, err := os.Lstat(dir); err == nil && info.Mode()&os.ModeSymlink != 0 {
		return "", fmt.Errorf("refusing symlinked r10n settings directory: %s", dir)
	}
	if err := os.MkdirAll(dir, 0700); err != nil {
		return "", fmt.Errorf("create r10n settings directory: %w", err)
	}
	if os.PathSeparator != '\\' {
		if err := os.Chmod(dir, 0700); err != nil {
			return "", err
		}
	}
	data, err := json.MarshalIndent(document, "", "  ")
	if err != nil {
		return "", fmt.Errorf("encode r10n settings: %w", err)
	}
	data = append(data, '\n')
	temporary, err := os.CreateTemp(dir, ".r10n-config-*.tmp")
	if err != nil {
		return "", err
	}
	temporaryPath := temporary.Name()
	defer os.Remove(temporaryPath)
	if os.PathSeparator != '\\' {
		if err := temporary.Chmod(0600); err != nil {
			_ = temporary.Close()
			return "", err
		}
	}
	if _, err := temporary.Write(data); err != nil {
		_ = temporary.Close()
		return "", err
	}
	if err := temporary.Sync(); err != nil {
		_ = temporary.Close()
		return "", err
	}
	if err := temporary.Close(); err != nil {
		return "", err
	}
	if err := os.Rename(temporaryPath, path); err != nil {
		return "", fmt.Errorf("replace r10n settings: %w", err)
	}
	if os.PathSeparator != '\\' {
		if err := os.Chmod(path, 0600); err != nil {
			return "", err
		}
	}
	return path, nil
}
