//go:build bundled

package backend

import (
	"bytes"
	"crypto/sha256"
	_ "embed"
	"fmt"
	"os"
	"path/filepath"
	"runtime"
)

// The release builder supplies a frozen, self-contained Python backend.
//
//go:embed payload/backend.bin
var payload []byte

// embeddedBackend extracts into a private, content-addressed cache. Existing
// files are verified rather than blindly executed. No runtime downloads occur.
func embeddedBackend() (string, error) {
	cache, err := os.UserCacheDir()
	if err != nil {
		return "", err
	}
	digest := sha256.Sum256(payload)
	dir := filepath.Join(cache, "r10n", fmt.Sprintf("%x", digest))
	if err := os.MkdirAll(dir, 0700); err != nil {
		return "", fmt.Errorf("create backend cache: %w", err)
	}
	name := "r10n-python"
	if runtime.GOOS == "windows" {
		name += ".exe"
	}
	path := filepath.Join(dir, name)
	existing, err := os.ReadFile(path)
	if err == nil {
		if bytes.Equal(existing, payload) {
			return path, nil
		}
		return "", fmt.Errorf("backend cache verification failed: remove %s and retry", dir)
	}
	if !os.IsNotExist(err) {
		return "", err
	}
	temp, err := os.CreateTemp(dir, "backend-")
	if err != nil {
		return "", err
	}
	defer os.Remove(temp.Name())
	if _, err := temp.Write(payload); err != nil {
		temp.Close()
		return "", err
	}
	if err := temp.Chmod(0700); err != nil {
		temp.Close()
		return "", err
	}
	if err := temp.Close(); err != nil {
		return "", err
	}
	if err := os.Rename(temp.Name(), path); err != nil {
		// Another launcher can win the extraction race (notably on Windows).
		existing, readErr := os.ReadFile(path)
		if readErr != nil || !bytes.Equal(existing, payload) {
			return "", err
		}
	}
	return path, nil
}
