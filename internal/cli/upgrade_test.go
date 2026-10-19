package cli

import (
	"archive/tar"
	"bytes"
	"compress/gzip"
	"context"
	"crypto/sha256"
	"encoding/json"
	"errors"
	"fmt"
	"io"
	"net/http"
	"net/http/httptest"
	"os"
	"path/filepath"
	"runtime"
	"strings"
	"testing"
)

type archiveEntry struct {
	name, target, body string
	kind               byte
}

func archiveBytes(t *testing.T, entries []archiveEntry) []byte {
	t.Helper()
	var buffer bytes.Buffer
	gz := gzip.NewWriter(&buffer)
	tw := tar.NewWriter(gz)
	for _, entry := range entries {
		kind := entry.kind
		if kind == 0 {
			kind = tar.TypeReg
		}
		header := &tar.Header{Name: entry.name, Linkname: entry.target, Typeflag: kind, Mode: 0755}
		if kind == tar.TypeReg {
			header.Size = int64(len(entry.body))
		}
		if err := tw.WriteHeader(header); err != nil {
			t.Fatal(err)
		}
		if kind == tar.TypeReg {
			if _, err := io.WriteString(tw, entry.body); err != nil {
				t.Fatal(err)
			}
		}
	}
	if err := tw.Close(); err != nil {
		t.Fatal(err)
	}
	if err := gz.Close(); err != nil {
		t.Fatal(err)
	}
	return buffer.Bytes()
}

func extractFixture(t *testing.T, entries []archiveEntry) (string, error) {
	t.Helper()
	dir := t.TempDir()
	archive := filepath.Join(dir, "release.tar.gz")
	if err := os.WriteFile(archive, archiveBytes(t, entries), 0600); err != nil {
		t.Fatal(err)
	}
	return extractArchive(archive, filepath.Join(dir, "extract"))
}

func TestArchiveTraversalAndSymlinks(t *testing.T) {
	for _, entry := range []archiveEntry{
		{name: "../escape"}, {name: "/absolute"}, {name: "r10n/../../escape"}, {name: "r10n/../r10n/alias"},
		{name: `r10n\evil`}, {name: "C:/evil"},
		{name: "r10n/link", target: "../../escape", kind: tar.TypeSymlink},
		{name: "r10n/link", target: "/absolute", kind: tar.TypeSymlink},
		{name: "r10n/link", target: "r10n", kind: tar.TypeLink},
		{name: "r10n/device", kind: tar.TypeChar},
	} {
		t.Run(entry.name+entry.target, func(t *testing.T) {
			if _, err := extractFixture(t, []archiveEntry{{name: "r10n/r10n", body: "native"}, entry}); err == nil {
				t.Fatal("unsafe archive accepted")
			}
		})
	}
	if runtime.GOOS == "windows" {
		t.Skip("symlinks require Windows privileges")
	}
	app, err := extractFixture(t, append(releaseFixtureEntries(), []archiveEntry{
		{name: "r10n/libexec/runtime/lib/library.so", body: "library"},
		{name: "r10n/libexec/runtime/library.so", target: "lib/library.so", kind: tar.TypeSymlink},
	}...))
	if err != nil {
		t.Fatal(err)
	}
	link := filepath.Join(app, "libexec/runtime/library.so")
	if target, err := os.Readlink(link); err != nil || target != "lib/library.so" {
		t.Fatalf("link not preserved: %q %v", target, err)
	}
	for _, entries := range [][]archiveEntry{
		{{name: "r10n/r10n", body: "native"}, {name: "r10n/link", target: "sub", kind: tar.TypeSymlink}, {name: "r10n/link/child", body: "bad"}},
		{{name: "r10n/r10n", body: "native"}, {name: "r10n/a", target: "b", kind: tar.TypeSymlink}, {name: "r10n/b", target: "a", kind: tar.TypeSymlink}},
		{{name: "r10n/r10n", body: "native"}, {name: "r10n/r10n", body: "duplicate"}},
		{{name: "r10n/r10n", target: "payload", kind: tar.TypeSymlink}, {name: "r10n/payload", body: "native"}},
	} {
		if _, err := extractFixture(t, entries); err == nil {
			t.Fatal("malformed archive accepted")
		}
	}
}

func installedFixture(t *testing.T) (string, string) {
	t.Helper()
	root := t.TempDir()
	app := filepath.Join(root, ".r10n")
	sidecar := filepath.Join(app, "libexec/r10n-python")
	if err := os.MkdirAll(sidecar, 0755); err != nil {
		t.Fatal(err)
	}
	native := filepath.Join(app, "r10n")
	if err := os.WriteFile(native, []byte("old-native"), 0755); err != nil {
		t.Fatal(err)
	}
	name := "r10n-python"
	if runtime.GOOS == "windows" {
		name += ".exe"
	}
	if err := os.WriteFile(filepath.Join(sidecar, name), []byte("old-backend"), 0755); err != nil {
		t.Fatal(err)
	}
	return root, native
}

func TestBundleAtomicSwapRollbackAndLauncher(t *testing.T) {
	if runtime.GOOS == "windows" {
		t.Skip("Unix bundle layout")
	}
	root, native := installedFixture(t)
	command := filepath.Join(root, "r10n")
	if err := os.Symlink(".r10n/r10n", command); err != nil {
		t.Fatal(err)
	}
	app, err := extractFixture(t, append(releaseFixtureEntries(), archiveEntry{name: "r10n/libexec/r10n-python/alias", target: "r10n-python", kind: tar.TypeSymlink}))
	if err != nil {
		t.Fatal(err)
	}
	original := renamePath
	defer func() { renamePath = original }()
	calls := 0
	renamePath = func(old, new string) error {
		calls++
		if calls == 2 {
			return errors.New("injected install failure")
		}
		return os.Rename(old, new)
	}
	if err := replaceBundle(context.Background(), native, app, "99.0.0"); err == nil || !strings.Contains(err.Error(), "restored") {
		t.Fatalf("missing rollback: %v", err)
	}
	data, _ := os.ReadFile(command)
	if string(data) != "old-native" {
		t.Fatal("rollback lost original executable")
	}
	renamePath = original
	if err := replaceBundle(context.Background(), native, app, "99.0.0"); err != nil {
		t.Fatal(err)
	}
	if target, _ := os.Readlink(command); target != ".r10n/r10n" {
		t.Fatalf("launcher replaced: %s", target)
	}
	data, _ = os.ReadFile(command)
	if string(data) != releaseFixtureEntries()[0].body {
		t.Fatal("new bundle not installed")
	}
	data, _ = os.ReadFile(filepath.Join(root, ".r10n/libexec/r10n-python/alias"))
	if string(data) != releaseFixtureEntries()[1].body {
		t.Fatal("backend/link not installed")
	}
}

func TestRollbackFailureRetainsRecoveryBundle(t *testing.T) {
	if runtime.GOOS == "windows" {
		t.Skip("Unix release helpers")
	}
	_, native := installedFixture(t)
	app, err := extractFixture(t, releaseFixtureEntries())
	if err != nil {
		t.Fatal(err)
	}
	original := renamePath
	defer func() { renamePath = original }()
	calls := 0
	renamePath = func(old, new string) error {
		calls++
		if calls > 1 {
			return errors.New("injected rollback failure")
		}
		return os.Rename(old, new)
	}
	if err := replaceBundle(context.Background(), native, app, "99.0.0"); err == nil || !strings.Contains(err.Error(), "recover bundle from") {
		t.Fatal(err)
	}
	matches, _ := filepath.Glob(filepath.Join(filepath.Dir(filepath.Dir(native)), ".r10n-stage-*", "old", "r10n"))
	if len(matches) != 1 {
		t.Fatal("recovery bundle was removed", matches)
	}
	data, _ := os.ReadFile(matches[0])
	if string(data) != "old-native" {
		t.Fatal("recovery data corrupted")
	}
}

func TestDownloadProgressShowsDecimalMegabytesAndUnknownTotals(t *testing.T) {
	known := formatDownloadProgress("release.tar.gz", 12_000_000, 24_000_000)
	if known != "release.tar.gz [############------------] 12.0 MB / 24.0 MB · 50%" {
		t.Fatalf("known-size progress = %q", known)
	}
	unknown := formatDownloadProgress("release.tar.gz", 12_400_000, 0)
	if !strings.Contains(unknown, "12.4 MB downloaded") ||
		!strings.Contains(unknown, "total unknown") ||
		strings.Contains(unknown, "%") {
		t.Fatalf("unknown-size progress fabricated a total: %q", unknown)
	}
}

func TestReleaseAssetCarriesItsAdvertisedByteSize(t *testing.T) {
	r := release{Assets: []struct {
		Name string `json:"name"`
		URL  string `json:"browser_download_url"`
		Size int64  `json:"size"`
	}{{Name: "bundle.tar.gz", URL: "https://example.test/bundle", Size: 12_400_000}}}

	address, size, err := r.asset("bundle.tar.gz")
	if err != nil || address != "https://example.test/bundle" || size != 12_400_000 {
		t.Fatalf("asset() = %q, %d, %v", address, size, err)
	}
}

func TestPlatformVersionChecksum(t *testing.T) {
	for _, test := range []struct{ os, arch, want string }{
		{"linux", "amd64", "r10n-linux-x86_64.tar.gz"}, {"darwin", "arm64", "r10n-macos-arm64.tar.gz"}, {"windows", "amd64", "r10n-windows-x86_64.exe"},
	} {
		got, err := platformAsset(test.os, test.arch)
		if err != nil || got != test.want {
			t.Fatalf("%s %v", got, err)
		}
	}
	if _, err := platformAsset("darwin", "amd64"); err == nil {
		t.Fatal("unsupported platform accepted")
	}
	for _, version := range []string{"v2.10.3", "2.0.0"} {
		if _, err := versionParts(version); err != nil {
			t.Fatal(err)
		}
	}
	for _, version := range []string{"v1.2", "v1.2.x", "v1.2.3/../bad", "1.2.3-rc1", "999999999999999999999.1.1"} {
		if _, err := versionParts(version); err == nil {
			t.Fatal(version)
		}
	}
	if newer, err := newerVersion("v2.10.3", "2.9.99"); err != nil || !newer {
		t.Fatal(newer, err)
	}
	dir := t.TempDir()
	archive, sums := filepath.Join(dir, "asset"), filepath.Join(dir, "sums")
	data := []byte("release")
	os.WriteFile(archive, data, 0600)
	sum := sha256.Sum256(data)
	valid := fmt.Sprintf("%x *asset\n", sum)
	for _, content := range []string{valid, "", "bad  asset\n", valid + valid, fmt.Sprintf("%064x  asset\n", 0)} {
		os.WriteFile(sums, []byte(content), 0600)
		err := verifyChecksum(archive, sums, "asset")
		if (err == nil) != (content == valid) {
			t.Fatalf("content=%q error=%v", content, err)
		}
	}
}

func TestUpgradeMetadataCheckAndInstall(t *testing.T) {
	if runtime.GOOS == "windows" {
		t.Skip("in-place update intentionally unsupported")
	}
	asset, err := platformAsset(runtime.GOOS, runtime.GOARCH)
	if err != nil {
		t.Skip(err)
	}
	_, native := installedFixture(t)
	oldExecutable, oldAPI, oldClient, oldOutput := executablePath, releasesAPI, upgradeHTTP, stdout
	defer func() { executablePath, releasesAPI, upgradeHTTP, stdout = oldExecutable, oldAPI, oldClient, oldOutput }()
	executablePath = func() (string, error) { return native, nil }
	stdout = io.Discard
	t.Setenv("R10N_SOURCE", "")
	t.Setenv("R10N_MANAGED", "")
	t.Setenv("GITHUB_TOKEN", "test-token")
	data := archiveBytes(t, releaseFixtureEntries())
	hash := sha256.Sum256(data)
	downloads := 0
	var server *httptest.Server
	server = httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		switch r.URL.Path {
		case "/releases/latest", "/releases/tags/v99.0.0":
			if r.Header.Get("Authorization") != "Bearer test-token" {
				t.Error("metadata token missing")
			}
			json.NewEncoder(w).Encode(map[string]any{"tag_name": "v99.0.0", "assets": []map[string]string{{"name": asset, "browser_download_url": server.URL + "/asset"}, {"name": "SHA256SUMS", "browser_download_url": server.URL + "/sums"}}})
		case "/asset":
			downloads++
			if r.Header.Get("Authorization") != "" {
				t.Error("token leaked to asset host")
			}
			w.Write(data)
		case "/sums":
			downloads++
			fmt.Fprintf(w, "%x  %s\n", hash, asset)
		default:
			http.NotFound(w, r)
		}
	}))
	defer server.Close()
	releasesAPI = server.URL + "/releases"
	upgradeHTTP = server.Client()
	if err := upgrade(context.Background(), []string{"--check", "--version", "99.0.0"}); err != nil {
		t.Fatal(err)
	}
	if downloads != 0 {
		t.Fatal("check downloaded assets")
	}
	t.Setenv("R10N_MANAGED", "python")
	if err := upgrade(context.Background(), nil); err == nil || !strings.Contains(err.Error(), "managed") {
		t.Fatal(err)
	}
	t.Setenv("R10N_MANAGED", "")
	oldInput := stdin
	input, err := os.Open(os.DevNull)
	if err != nil {
		t.Fatal(err)
	}
	defer input.Close()
	stdin = input
	defer func() { stdin = oldInput }()
	if err := upgrade(context.Background(), nil); err == nil || !strings.Contains(err.Error(), "--yes") {
		t.Fatalf("headless upgrade allowed: %v", err)
	}
	if downloads != 0 {
		t.Fatal("unconfirmed upgrade downloaded assets")
	}
	if err := upgrade(context.Background(), []string{"-y"}); err != nil {
		t.Fatal(err)
	}
	result, _ := os.ReadFile(native)
	if string(result) != releaseFixtureEntries()[0].body || downloads != 2 {
		t.Fatal("full upgrade failed")
	}
}

func TestUpgradeSourceAndCancellationGuards(t *testing.T) {
	oldExecutable, oldAPI, oldClient := executablePath, releasesAPI, upgradeHTTP
	defer func() { executablePath, releasesAPI, upgradeHTTP = oldExecutable, oldAPI, oldClient }()
	_, native := installedFixture(t)
	executablePath = func() (string, error) { return native, nil }
	requests := 0
	server := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) { requests++; http.Error(w, "unexpected", 500) }))
	defer server.Close()
	releasesAPI = server.URL
	upgradeHTTP = server.Client()
	t.Setenv("R10N_SOURCE", "1")
	if err := upgrade(context.Background(), nil); err == nil || !strings.Contains(err.Error(), "source") {
		t.Fatal(err)
	}
	if requests != 0 {
		t.Fatal("source install contacted release API")
	}
	t.Setenv("R10N_SOURCE", "")
	ctx, cancel := context.WithCancel(context.Background())
	cancel()
	if _, err := getRelease(ctx, ""); !errors.Is(err, context.Canceled) {
		t.Fatal(err)
	}
	if requests != 0 {
		t.Fatal("cancelled metadata request sent")
	}
}
