package backend

import (
	"os"
	"path/filepath"
	"strings"
	"testing"
)

func TestResolveExplicitBackend(t *testing.T) {
	executable, _ := os.Executable()
	t.Setenv("R10N_BACKEND", executable)
	engine, err := Resolve()
	if err != nil {
		t.Fatal(err)
	}
	if engine.Executable != executable || len(engine.Prefix) != 0 ||
		!strings.Contains(strings.Join(engine.Env, "\n"), "R10N_EXECUTABLE=") {
		t.Fatalf("backend override or native executable identity lost: %+v", engine)
	}
}

func TestSourceRootAndInterpreter(t *testing.T) {
	root := t.TempDir()
	if err := os.Mkdir(filepath.Join(root, "src"), 0700); err != nil {
		t.Fatal(err)
	}
	if err := os.WriteFile(filepath.Join(root, "src", "backend.py"), nil, 0600); err != nil {
		t.Fatal(err)
	}
	if err := os.WriteFile(filepath.Join(root, "pyproject.toml"), []byte("[project]\nname = \"r10n\"\n"), 0600); err != nil {
		t.Fatal(err)
	}
	executable, _ := os.Executable()
	t.Setenv("R10N_BACKEND", "")
	t.Setenv("R10N_PROJECT", root)
	t.Setenv("R10N_PYTHON", executable)
	t.Setenv("PYTHONPATH", "existing-path")
	engine, err := Resolve()
	if err != nil {
		t.Fatal(err)
	}
	expected := "PYTHONPATH=" + root + string(os.PathListSeparator) + "existing-path"
	if strings.Join(engine.Prefix, " ") != "-u "+filepath.Join(root, "src", "backend.py") ||
		!strings.Contains(strings.Join(engine.Env, "\n"), expected) {
		t.Fatalf("wrong source launcher: %+v", engine)
	}
	t.Setenv("R10N_PROJECT", filepath.Join(root, "missing"))
	if _, err := Resolve(); err == nil {
		t.Fatal("invalid explicit project must fail with guidance")
	}
}

func TestSetEnvReplacesDuplicateKeys(t *testing.T) {
	env := setEnv([]string{"A=old", "B=retained", "A=duplicate"}, "A", "new")
	if strings.Join(env, ";") != "B=retained;A=new" {
		t.Fatal(env)
	}
}
