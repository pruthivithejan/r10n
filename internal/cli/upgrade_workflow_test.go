package cli

import (
	"context"
	"crypto/sha256"
	"encoding/json"
	"fmt"
	"io"
	"net/http"
	"net/http/httptest"
	"os"
	"os/exec"
	"path/filepath"
	"runtime"
	"strings"
	"testing"

	"github.com/pruthivithejan/r10n"
)

// Unlike the shell-native fixtures, this exercises the real native argument
// parser, backend discovery, JSON forwarding, and strict worker handshake.
func TestUpgradeRealNativeFrontend(t *testing.T) {
	if runtime.GOOS == "windows" {
		t.Skip("Unix bundle upgrade")
	}
	native := filepath.Join(t.TempDir(), "r10n")
	cmd := exec.CommandContext(t.Context(), "go", "build", "-o", native, "./cmd/r10n")
	cmd.Dir = filepath.Join("..", "..")
	if output, err := cmd.CombinedOutput(); err != nil {
		t.Fatalf("build native frontend: %v\n%s", err, output)
	}
	data, err := os.ReadFile(native)
	if err != nil {
		t.Fatal(err)
	}
	entries := releaseFixtureEntries()
	entries[0].body = string(data)
	entries[1].body = strings.ReplaceAll(entries[1].body, "99.0.0", r10n.Version)
	runNativeUpgradeWorkflow(t, archiveBytes(t, entries), r10n.Version)
}

// Run against a downloaded checksum-verified host-native release archive to
// cover the actual frozen runtime, including older native JSON contracts:
// R10N_TEST_RELEASE_ARCHIVE=/path/release.tar.gz R10N_TEST_BUNDLE_VERSION=0.12.2
func TestUpgradeFrozenReleaseWorkflow(t *testing.T) {
	archive := os.Getenv("R10N_TEST_RELEASE_ARCHIVE")
	if archive == "" {
		t.Skip("set R10N_TEST_RELEASE_ARCHIVE to a host-native release archive")
	}
	if runtime.GOOS == "windows" {
		t.Skip("Unix bundle upgrade")
	}
	version := os.Getenv("R10N_TEST_BUNDLE_VERSION")
	if version == "" {
		version = r10n.Version
	}
	data, err := os.ReadFile(archive)
	if err != nil {
		t.Fatal(err)
	}
	runNativeUpgradeWorkflow(t, data, version)
}

func runNativeUpgradeWorkflow(t *testing.T, archive []byte, version string) {
	t.Helper()
	asset, err := platformAsset(runtime.GOOS, runtime.GOARCH)
	if err != nil {
		t.Fatal(err)
	}
	root, native := installedFixture(t)
	command := filepath.Join(root, "r10n")
	if err := os.Symlink(".r10n/r10n", command); err != nil {
		t.Fatal(err)
	}
	oldExecutable, oldAPI, oldClient, oldDownloadClient, oldOutput := executablePath, releasesAPI, upgradeHTTP, upgradeDownloadHTTP, stdout
	t.Cleanup(func() {
		executablePath, releasesAPI, upgradeHTTP, upgradeDownloadHTTP, stdout = oldExecutable, oldAPI, oldClient, oldDownloadClient, oldOutput
	})
	executablePath = func() (string, error) { return command, nil }
	stdout = io.Discard
	t.Setenv("R10N_SOURCE", "")
	t.Setenv("R10N_MANAGED", "")
	t.Setenv("R10N_CONFIG_DIR", filepath.Join(root, "settings"))
	sum := sha256.Sum256(archive)
	var server *httptest.Server
	server = httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		switch r.URL.Path {
		case "/tags/v" + version:
			_ = json.NewEncoder(w).Encode(map[string]any{
				"tag_name": "v" + version,
				"assets": []map[string]any{
					{"name": asset, "browser_download_url": server.URL + "/asset", "size": len(archive)},
					{"name": "SHA256SUMS", "browser_download_url": server.URL + "/sums"},
				},
			})
		case "/asset":
			_, _ = w.Write(archive)
		case "/sums":
			fmt.Fprintf(w, "%x  %s\n", sum, asset)
		default:
			http.NotFound(w, r)
		}
	}))
	defer server.Close()
	releasesAPI, upgradeHTTP, upgradeDownloadHTTP = server.URL, server.Client(), server.Client()
	for range 2 {
		if err := upgrade(context.Background(), []string{"--version", version, "--yes"}); err != nil {
			t.Fatal(err)
		}
		if target, err := os.Readlink(command); err != nil || target != ".r10n/r10n" {
			t.Fatalf("launcher changed: %q, %v", target, err)
		}
		if err := validateReleaseBundle(t.Context(), filepath.Dir(native), version); err != nil {
			t.Fatal(err)
		}
	}
}
