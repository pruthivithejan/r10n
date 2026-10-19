// Package backend locates and communicates with the Python automation worker.
package backend

import (
	"context"
	"fmt"
	"os"
	"os/exec"
	"path/filepath"
	"runtime"
	"strings"

	"github.com/pruthivithejan/r10n/internal/settings"
)

// Backend describes a command without interpreting any values through a shell.
type Backend struct {
	Executable string
	Prefix     []string
	Env        []string
}

// Resolve prefers the release backend, then a source installation. It never
// changes the user's working directory, so input/output paths retain meaning.
func Resolve() (Backend, error) {
	executable, err := os.Executable()
	if err != nil {
		return Backend{}, err
	}
	executable, err = filepath.EvalSymlinks(executable)
	if err != nil {
		return Backend{}, err
	}
	env := setEnv(os.Environ(), "R10N_EXECUTABLE", executable)
	env = setEnv(env, "R10N_SOURCE", "")
	configDir, err := settings.Directory()
	if err != nil {
		return Backend{}, err
	}
	env = setEnv(env, "R10N_CONFIG_DIR", configDir)
	commandPath := os.Args[0]
	if found, err := exec.LookPath(commandPath); err == nil {
		commandPath, _ = filepath.Abs(found)
	}
	env = setEnv(env, "R10N_COMMAND_PATH", commandPath)
	if override := os.Getenv("R10N_BACKEND"); override != "" {
		path, err := exec.LookPath(override)
		if err != nil {
			return Backend{}, fmt.Errorf("R10N_BACKEND: %w", err)
		}
		return Backend{Executable: path, Env: env}, nil
	}
	name := "r10n-python"
	if runtime.GOOS == "windows" {
		name += ".exe"
	}
	sidecar := filepath.Join(filepath.Dir(executable), "libexec", "r10n-python", name)
	if info, err := os.Stat(sidecar); err == nil && !info.IsDir() {
		return Backend{Executable: sidecar, Env: env}, nil
	}
	if embedded, err := embeddedBackend(); err != nil {
		return Backend{}, err
	} else if embedded != "" {
		return Backend{Executable: embedded, Env: env}, nil
	}

	root, err := sourceRoot(executable)
	if err != nil {
		return Backend{}, err
	}
	env = setEnv(env, "R10N_SOURCE", "1")
	pythonPath := filepath.Join(root, "src")
	if existing := os.Getenv("PYTHONPATH"); existing != "" {
		pythonPath += string(os.PathListSeparator) + existing
	}
	env = setEnv(env, "PYTHONPATH", pythonPath)
	env = setEnv(env, "PYTHONUNBUFFERED", "1")
	entry := filepath.Join(root, "src", "r10n_backend", "__main__.py")
	if python := os.Getenv("R10N_PYTHON"); python != "" {
		path, err := exec.LookPath(python)
		if err != nil {
			return Backend{}, fmt.Errorf("R10N_PYTHON: %w", err)
		}
		return Backend{path, []string{"-u", "-X", "utf8", entry}, env}, nil
	}
	if uv, err := exec.LookPath("uv"); err == nil {
		return Backend{uv, []string{"run", "--locked", "--project", root, "python", "-u", "-X", "utf8", entry}, env}, nil
	}
	python, err := exec.LookPath("python3")
	if err != nil {
		return Backend{}, fmt.Errorf("source installs require uv or Python 3.10+: %w", err)
	}
	return Backend{python, []string{"-u", "-X", "utf8", entry}, env}, nil
}

func sourceRoot(executable string) (string, error) {
	if root := os.Getenv("R10N_PROJECT"); root != "" {
		root, err := filepath.Abs(root)
		if err != nil {
			return "", err
		}
		if !isSourceRoot(root) {
			return "", fmt.Errorf("R10N_PROJECT must point to an r10n source checkout")
		}
		return root, nil
	}
	cwd, err := os.Getwd()
	if err != nil {
		return "", err
	}
	for _, start := range []string{cwd, filepath.Dir(executable)} {
		for dir := start; ; dir = filepath.Dir(dir) {
			if isSourceRoot(dir) {
				return dir, nil
			}
			if filepath.Dir(dir) == dir {
				break
			}
		}
	}
	return "", fmt.Errorf("Python backend not found; reinstall the complete release bundle, or set R10N_PROJECT to a source checkout and run uv sync")
}

func isSourceRoot(path string) bool {
	info, err := os.Stat(filepath.Join(path, "src", "r10n_backend"))
	metadata, metadataErr := os.ReadFile(filepath.Join(path, "pyproject.toml"))
	return err == nil && info.IsDir() && metadataErr == nil && strings.Contains(string(metadata), `name = "r10n"`)
}

func setEnv(env []string, key, value string) []string {
	result := make([]string, 0, len(env)+1)
	for _, item := range env {
		if !strings.HasPrefix(item, key+"=") {
			result = append(result, item)
		}
	}
	return append(result, key+"="+value)
}

// Command creates a backend subprocess in the caller's working directory.
func (b Backend) Command(ctx context.Context, args ...string) *exec.Cmd {
	command := exec.CommandContext(ctx, b.Executable, append(append([]string{}, b.Prefix...), args...)...)
	command.Env = b.Env
	configureProcess(command)
	return command
}
