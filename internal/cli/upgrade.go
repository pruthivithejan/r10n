package cli

import (
	"bytes"
	"context"
	"crypto/sha256"
	"encoding/hex"
	"encoding/json"
	"flag"
	"fmt"
	"io"
	"net/http"
	"net/url"
	"os"
	"path/filepath"
	"regexp"
	"runtime"
	"strconv"
	"strings"
	"time"

	"github.com/charmbracelet/huh"
	"github.com/pruthivithejan/r10n"
	"github.com/pruthivithejan/r10n/internal/backend"
	"github.com/pruthivithejan/r10n/internal/tui"
)

var releasesAPI = "https://api.github.com/repos/pruthivithejan/r10n/releases"
var upgradeHTTP = &http.Client{Timeout: 60 * time.Second}
var executablePath = os.Executable

type release struct {
	Tag    string `json:"tag_name"`
	Assets []struct {
		Name string `json:"name"`
		URL  string `json:"browser_download_url"`
	} `json:"assets"`
}

func platformAsset(goos, arch string) (string, error) {
	switch goos + "/" + arch {
	case "linux/amd64":
		return "r10n-linux-x86_64.tar.gz", nil
	case "darwin/arm64":
		return "r10n-macos-arm64.tar.gz", nil
	case "windows/amd64":
		return "r10n-windows-x86_64.exe", nil
	default:
		return "", fmt.Errorf("unsupported platform: %s/%s", goos, arch)
	}
}

var versionPattern = regexp.MustCompile(`^v?([0-9]+)\.([0-9]+)\.([0-9]+)$`)

func versionParts(value string) ([3]uint64, error) {
	var parts [3]uint64
	match := versionPattern.FindStringSubmatch(value)
	if match == nil {
		return parts, fmt.Errorf("invalid version %q; expected X.Y.Z or vX.Y.Z", value)
	}
	for i := range parts {
		n, err := strconv.ParseUint(match[i+1], 10, 64)
		if err != nil {
			return parts, fmt.Errorf("invalid version %q", value)
		}
		parts[i] = n
	}
	return parts, nil
}

func newerVersion(candidate, current string) (bool, error) {
	a, err := versionParts(candidate)
	if err != nil {
		return false, err
	}
	b, err := versionParts(current)
	if err != nil {
		return false, err
	}
	for i := range a {
		if a[i] != b[i] {
			return a[i] > b[i], nil
		}
	}
	return false, nil
}

func getRelease(ctx context.Context, target string) (release, error) {
	endpoint := releasesAPI + "/latest"
	if target != "" {
		endpoint = releasesAPI + "/tags/v" + strings.TrimPrefix(target, "v")
	}
	req, err := http.NewRequestWithContext(ctx, http.MethodGet, endpoint, nil)
	if err != nil {
		return release{}, err
	}
	req.Header.Set("Accept", "application/vnd.github+json")
	req.Header.Set("User-Agent", "r10n-upgrade")
	if token := os.Getenv("GITHUB_TOKEN"); token != "" {
		req.Header.Set("Authorization", "Bearer "+token)
	}
	response, err := upgradeHTTP.Do(req)
	if err != nil {
		return release{}, err
	}
	defer response.Body.Close()
	if response.StatusCode != http.StatusOK {
		return release{}, fmt.Errorf("release metadata HTTP %d (check release tag, connectivity or GitHub rate limits)", response.StatusCode)
	}
	var result release
	if err := json.NewDecoder(io.LimitReader(response.Body, 4*1024*1024)).Decode(&result); err != nil {
		return result, fmt.Errorf("invalid release metadata: %w", err)
	}
	if _, err := versionParts(result.Tag); err != nil {
		return result, err
	}
	return result, nil
}

func (r release) asset(name string) (string, error) {
	found := ""
	for _, asset := range r.Assets {
		if asset.Name == name {
			if found != "" {
				return "", fmt.Errorf("duplicate release asset: %s", name)
			}
			u, err := url.Parse(asset.URL)
			if err != nil || u.Host == "" || (u.Scheme != "https" && !(u.Scheme == "http" && strings.HasPrefix(releasesAPI, "http://"))) {
				return "", fmt.Errorf("invalid release asset URL")
			}
			found = asset.URL
		}
	}
	if found == "" {
		return "", fmt.Errorf("release asset not found: %s", name)
	}
	return found, nil
}

func download(ctx context.Context, address, destination string, limit int64) error {
	req, err := http.NewRequestWithContext(ctx, http.MethodGet, address, nil)
	if err != nil {
		return err
	}
	req.Header.Set("User-Agent", "r10n-upgrade")
	// Never send GITHUB_TOKEN to an asset host.
	res, err := upgradeHTTP.Do(req)
	if err != nil {
		return err
	}
	defer res.Body.Close()
	if res.StatusCode != http.StatusOK {
		return fmt.Errorf("asset download HTTP %d", res.StatusCode)
	}
	out, err := os.OpenFile(destination, os.O_CREATE|os.O_EXCL|os.O_WRONLY, 0600)
	if err != nil {
		return err
	}
	n, err := io.Copy(out, io.LimitReader(res.Body, limit+1))
	closeErr := out.Close()
	if err != nil {
		return err
	}
	if closeErr != nil {
		return closeErr
	}
	if n > limit {
		return fmt.Errorf("download exceeds size limit")
	}
	return nil
}

func verifyChecksum(archive, sums, name string) error {
	data, err := os.ReadFile(sums)
	if err != nil {
		return err
	}
	expected := ""
	for _, line := range strings.Split(string(data), "\n") {
		parts := strings.Fields(line)
		if len(parts) == 2 && strings.TrimPrefix(parts[1], "*") == name {
			if expected != "" {
				return fmt.Errorf("duplicate checksum for %s", name)
			}
			expected = strings.ToLower(parts[0])
		}
	}
	decoded, err := hex.DecodeString(expected)
	if err != nil || len(decoded) != sha256.Size {
		return fmt.Errorf("valid checksum for %s not found in SHA256SUMS", name)
	}
	file, err := os.Open(archive)
	if err != nil {
		return err
	}
	defer file.Close()
	hash := sha256.New()
	if _, err := io.Copy(hash, file); err != nil {
		return err
	}
	if hex.EncodeToString(hash.Sum(nil)) != expected {
		return fmt.Errorf("checksum verification failed for downloaded release")
	}
	return nil
}

func upgrade(ctx context.Context, args []string) error {
	fs := flag.NewFlagSet("upgrade", flag.ContinueOnError)
	fs.SetOutput(io.Discard)
	var target string
	var check, yes bool
	fs.StringVar(&target, "version", "", "")
	fs.BoolVar(&check, "check", false, "")
	fs.BoolVar(&yes, "yes", false, "")
	fs.BoolVar(&yes, "y", false, "")
	if err := fs.Parse(args); err != nil {
		if err == flag.ErrHelp {
			fmt.Fprintln(stdout, "Usage: r10n upgrade [--version VERSION] [--check] [--yes/-y]\nApplying an upgrade replaces the whole standalone bundle. --check is read-only.")
			return nil
		}
		return usage(err)
	}
	if fs.NArg() != 0 {
		return usage(fmt.Errorf("usage: r10n upgrade [--version VERSION] [--check] [--yes/-y]"))
	}
	if target != "" {
		if _, err := versionParts(target); err != nil {
			return usage(err)
		}
	}
	asset, err := platformAsset(runtime.GOOS, runtime.GOARCH)
	if err != nil {
		return err
	}
	native, err := executablePath()
	if err != nil {
		return err
	}
	native, err = filepath.EvalSymlinks(native)
	if err != nil {
		return err
	}
	sidecar := filepath.Join(filepath.Dir(native), "libexec", "r10n-python", "r10n-python")
	if runtime.GOOS == "windows" {
		sidecar += ".exe"
	}
	info, sidecarErr := os.Stat(sidecar)
	isRelease := backend.Bundled || (sidecarErr == nil && info.Mode().IsRegular())
	if os.Getenv("R10N_SOURCE") == "1" || !isRelease {
		return fmt.Errorf("upgrade is only for standalone binary installs; use git pull and uv sync for source installs")
	}
	if !check && os.Getenv("R10N_MANAGED") == "python" {
		return fmt.Errorf("this native binary is managed by the Python package; upgrade the uv/uvx package instead")
	}
	if !check && runtime.GOOS == "windows" {
		return fmt.Errorf("in-place upgrade is not supported on Windows; reinstall the release binary (upgrade --check is supported)")
	}
	r, err := getRelease(ctx, target)
	if err != nil {
		return err
	}
	if target != "" && strings.TrimPrefix(r.Tag, "v") != strings.TrimPrefix(target, "v") {
		return fmt.Errorf("release metadata version %s does not match requested version %s", r.Tag, target)
	}
	newer, err := newerVersion(r.Tag, r10n.Version)
	if err != nil {
		return err
	}
	fmt.Fprintf(stdout, "Current version: %s\nRelease: %s\nAsset: %s\n", r10n.Version, r.Tag, asset)
	if check {
		if newer {
			fmt.Fprintln(stdout, "Update available. Run r10n upgrade to install.")
		} else {
			fmt.Fprintln(stdout, "You are up to date.")
		}
		return nil
	}
	if !newer && target == "" {
		fmt.Fprintln(stdout, "Already on the latest version.")
		return nil
	}
	fmt.Fprintf(stdout, "Installation: %s\nThe complete app bundle will be replaced.\n", tui.SafeText(filepath.Dir(native)))
	if err := confirmUpgrade(ctx, yes); err != nil {
		return err
	}
	assetURL, err := r.asset(asset)
	if err != nil {
		return err
	}
	sumsURL, err := r.asset("SHA256SUMS")
	if err != nil {
		return err
	}
	tmp, err := os.MkdirTemp("", "r10n-upgrade-")
	if err != nil {
		return err
	}
	defer os.RemoveAll(tmp)
	archive, sums := filepath.Join(tmp, asset), filepath.Join(tmp, "SHA256SUMS")
	if err := download(ctx, assetURL, archive, 1024*1024*1024); err != nil {
		return err
	}
	if err := download(ctx, sumsURL, sums, 4*1024*1024); err != nil {
		return err
	}
	if err := verifyChecksum(archive, sums, asset); err != nil {
		return err
	}
	app, err := extractArchive(archive, filepath.Join(tmp, "extract"))
	if err != nil {
		return err
	}
	if err := ctx.Err(); err != nil {
		return err
	}
	if err := replaceBundle(ctx, native, app, r.Tag); err != nil {
		return err
	}
	fmt.Fprintf(stdout, "Updated to r10n %s.\n", r.Tag)
	return nil
}

func confirmUpgrade(ctx context.Context, yes bool) error {
	if err := ctx.Err(); err != nil {
		return err
	}
	if yes {
		return nil
	}
	if !tui.Interactive() {
		return usage(fmt.Errorf("noninteractive upgrade requires --yes after reviewing the target and installation"))
	}
	var approved bool
	form := huh.NewForm(huh.NewGroup(huh.NewConfirm().
		Title("Replace the installed r10n bundle?").
		Affirmative("Upgrade").Negative("Cancel").Value(&approved))).
		WithInput(stdin).WithOutput(stderr).WithAccessible(os.Getenv("R10N_ACCESSIBLE") == "1")
	if err := form.RunWithContext(ctx); err != nil {
		return err
	}
	if !approved {
		return context.Canceled
	}
	return ctx.Err()
}

// Validation must not fall back to a checkout, a Python installation, or a
// caller's backend override. Probe outside the checkout to avoid local/.env.
func releaseValidationEnv() []string {
	var env []string
	for _, item := range os.Environ() {
		key, _, _ := strings.Cut(item, "=")
		key = strings.ToUpper(key)
		if strings.HasPrefix(key, "R10N_") || strings.HasPrefix(key, "PYTHON") ||
			strings.HasPrefix(key, "UV_") || key == "VIRTUAL_ENV" ||
			key == "LD_PRELOAD" || key == "LD_LIBRARY_PATH" || strings.HasPrefix(key, "DYLD_") {
			continue
		}
		env = append(env, item)
	}
	return append(env, "R10N_DISABLE_UPDATE_CHECK=1")
}

type validationOutput struct {
	bytes.Buffer
}

func (b *validationOutput) Write(p []byte) (int, error) {
	if b.Len()+len(p) > 8*1024*1024 {
		return 0, fmt.Errorf("release validation output exceeds 8 MiB")
	}
	return b.Buffer.Write(p)
}

func runReleaseProbe(ctx context.Context, native, dir string, env []string, args ...string) ([]byte, error) {
	ctx, cancel := context.WithTimeout(ctx, 30*time.Second)
	defer cancel()
	cmd := (backend.Backend{Executable: native, Env: env}).Command(ctx, args...)
	cmd.Dir, cmd.Env = dir, env
	// Bound inherited-pipe waits too, including a faulty backend that outlives
	// its native parent. The native process owns its backend's cancellation.
	cmd.WaitDelay = time.Second
	var out, diagnostics validationOutput
	cmd.Stdout, cmd.Stderr = &out, &diagnostics
	if err := cmd.Run(); err != nil {
		if ctx.Err() != nil {
			return nil, ctx.Err()
		}
		return nil, fmt.Errorf("%s: %w: %s", strings.Join(args, " "), err, diagnostics.String())
	}
	if err := ctx.Err(); err != nil {
		return nil, err
	}
	return out.Bytes(), nil
}

func validateReleaseBundle(ctx context.Context, app, version string) error {
	if err := ctx.Err(); err != nil {
		return err
	}
	if err := validateBundleLayout(app); err != nil {
		return err
	}
	probeDir, err := os.MkdirTemp("", "r10n-upgrade-probe-")
	if err != nil {
		return err
	}
	defer os.RemoveAll(probeDir)
	// macOS temp paths may pass through /var -> /private/var.
	probeDir, err = filepath.EvalSymlinks(probeDir)
	if err != nil {
		return err
	}
	env := releaseValidationEnv()
	native := filepath.Join(app, "r10n")
	reported, err := runReleaseProbe(ctx, native, probeDir, env, "--version")
	if err != nil {
		return err
	}
	version = strings.TrimPrefix(version, "v")
	if strings.TrimSpace(string(reported)) != "r10n, version "+version {
		return fmt.Errorf("staged native version does not match requested version %s", version)
	}
	raw, err := runReleaseProbe(ctx, native, probeDir, env, "list", "--json")
	if err != nil {
		return err
	}
	catalog, err := backend.ParseCatalog(raw)
	if err != nil {
		return err
	}
	if catalog.Version != version {
		return fmt.Errorf("frozen catalog metadata does not match release %s", version)
	}
	hasContacts := false
	for _, task := range catalog.Automations {
		hasContacts = hasContacts || task.ID == "contacts"
	}
	if !hasContacts {
		return fmt.Errorf("frozen catalog is missing the contacts automation")
	}
	input, output := filepath.Join(probeDir, "numbers.txt"), filepath.Join(probeDir, "contacts.vcf")
	if err := os.WriteFile(input, []byte("+94771234567\n"), 0600); err != nil {
		return err
	}
	payload := map[string]any{"input_file": input, "output_file": output, "prefix": "Upgrade"}
	payloadJSON, err := json.Marshal(payload)
	if err != nil {
		return err
	}
	events, err := runReleaseProbe(ctx, native, probeDir, env, "run", "contacts", "--input-json", string(payloadJSON), "--json", "--yes")
	if err != nil {
		return fmt.Errorf("native contacts execution: %w", err)
	}
	if err := validateProbeEvents(events, output); err != nil {
		return err
	}
	if err := verifyProbeContacts(output); err != nil {
		return err
	}
	return ctx.Err()
}

// The native command enforces the worker protocol; also require a successful
// exchange and the expected artifact before replacing a working installation.
func validateProbeEvents(raw []byte, output string) error {
	hello, started, completed, artifact := false, false, false, false
	for _, line := range bytes.Split(bytes.TrimSpace(raw), []byte("\n")) {
		var event backend.Event
		if err := json.Unmarshal(line, &event); err != nil {
			return fmt.Errorf("invalid contacts probe event: %w", err)
		}
		if completed || (!hello && event.Type != "hello") {
			return fmt.Errorf("invalid contacts probe event order")
		}
		switch event.Type {
		case "hello":
			if hello || event.Protocol != backend.ProtocolVersion {
				return fmt.Errorf("invalid contacts probe handshake")
			}
			hello = true
		case "started":
			if started || event.Protocol != backend.ProtocolVersion || event.Automation != "contacts" {
				return fmt.Errorf("invalid contacts probe started event")
			}
			started = true
		case "artifact", "log", "progress":
			if !started {
				return fmt.Errorf("contacts probe event before started")
			}
			if event.Type == "artifact" && event.Path == output {
				artifact = true
			}
		case "completed":
			if !started || event.Automation != "contacts" || event.Success == nil || !*event.Success || event.Result == nil {
				return fmt.Errorf("contacts probe did not succeed")
			}
			completed = true
		default:
			return fmt.Errorf("contacts probe failed: %s", event.Type)
		}
	}
	if !completed || !artifact {
		return fmt.Errorf("contacts probe did not complete with its expected artifact")
	}
	return nil
}

func verifyProbeContacts(output string) error {
	data, err := os.ReadFile(output)
	if err != nil {
		return fmt.Errorf("release contacts artifact: %w", err)
	}
	if strings.Count(string(data), "BEGIN:VCARD") != 1 || !bytes.Contains(data, []byte("+94771234567")) {
		return fmt.Errorf("release contacts worker produced an invalid VCF")
	}
	return nil
}
