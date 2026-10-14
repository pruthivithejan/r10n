package cli

import (
	"archive/tar"
	"compress/gzip"
	"context"
	"fmt"
	"io"
	"os"
	"path"
	"path/filepath"
	"strings"
)

// safeArchivePath uses POSIX paths even when cross-compiled for Windows.
// Require one app root; reject absolute, traversal and platform-specific paths.
func safeArchivePath(name string) (string, error) {
	if name == "" || strings.ContainsAny(name, "\\:\x00") || strings.HasPrefix(name, "/") {
		return "", fmt.Errorf("unsafe archive path: %q", name)
	}
	for _, part := range strings.Split(name, "/") {
		if part == ".." {
			return "", fmt.Errorf("unsafe archive path: %q", name)
		}
	}
	clean := path.Clean(name)
	if clean != "r10n" && !strings.HasPrefix(clean, "r10n/") {
		return "", fmt.Errorf("unsafe archive path: %q", name)
	}
	return clean, nil
}

func safeLink(name, target string) error {
	if target == "" || strings.HasPrefix(target, "/") || strings.ContainsAny(target, "\\:\x00") {
		return fmt.Errorf("unsafe archive symlink: %s -> %s", name, target)
	}
	resolved := path.Clean(path.Join(path.Dir(name), target))
	if resolved != "r10n" && !strings.HasPrefix(resolved, "r10n/") {
		return fmt.Errorf("unsafe archive symlink: %s -> %s", name, target)
	}
	return nil
}

func extractArchive(archive, destination string) (string, error) {
	// Only extract into a newly created private directory.
	if err := os.Mkdir(destination, 0700); err != nil {
		return "", err
	}
	destination, err := filepath.EvalSymlinks(destination)
	if err != nil {
		return "", err
	}
	file, err := os.Open(archive)
	if err != nil {
		return "", err
	}
	defer file.Close()
	gz, err := gzip.NewReader(file)
	if err != nil {
		return "", err
	}
	defer gz.Close()
	reader := tar.NewReader(gz)
	type link struct{ name, target string }
	var links []link
	seen := map[string]byte{}
	var total int64
	for {
		h, err := reader.Next()
		if err == io.EOF {
			break
		}
		if err != nil {
			return "", err
		}
		name, err := safeArchivePath(h.Name)
		if err != nil {
			return "", err
		}
		if old, ok := seen[name]; ok {
			if old == tar.TypeDir && h.Typeflag == tar.TypeDir {
				continue
			}
			return "", fmt.Errorf("duplicate archive path: %s", name)
		}
		if len(seen) >= 100000 {
			return "", fmt.Errorf("too many archive entries")
		}
		seen[name] = h.Typeflag
		target := filepath.Join(destination, filepath.FromSlash(name))
		switch h.Typeflag {
		case tar.TypeDir:
			if err := os.MkdirAll(target, 0755); err != nil {
				return "", err
			}
		case tar.TypeReg, tar.TypeRegA:
			if h.Size < 0 || h.Size > 2*1024*1024*1024 || total+h.Size > 4*1024*1024*1024 {
				return "", fmt.Errorf("archive exceeds size limit")
			}
			total += h.Size
			if err := os.MkdirAll(filepath.Dir(target), 0755); err != nil {
				return "", err
			}
			out, err := os.OpenFile(target, os.O_CREATE|os.O_EXCL|os.O_WRONLY, os.FileMode(h.Mode)&0777)
			if err != nil {
				return "", err
			}
			_, writeErr := io.CopyN(out, reader, h.Size)
			closeErr := out.Close()
			if writeErr != nil {
				return "", writeErr
			}
			if closeErr != nil {
				return "", closeErr
			}
		case tar.TypeSymlink:
			if err := safeLink(name, h.Linkname); err != nil {
				return "", err
			}
			links = append(links, link{name, h.Linkname})
		default:
			return "", fmt.Errorf("unsupported archive entry: %s (type %d)", name, h.Typeflag)
		}
	}
	// Install symlinks last: no file or directory is ever written through one.
	for _, l := range links {
		target := filepath.Join(destination, filepath.FromSlash(l.name))
		if err := os.MkdirAll(filepath.Dir(target), 0755); err != nil {
			return "", err
		}
		if err := os.Symlink(l.target, target); err != nil {
			return "", err
		}
	}
	app := filepath.Join(destination, "r10n")
	// Check resolved chains too: loops and dangling links are malformed bundles.
	if err := filepath.WalkDir(app, func(p string, entry os.DirEntry, err error) error {
		if err != nil {
			return err
		}
		if entry.Type()&os.ModeSymlink != 0 {
			resolved, err := filepath.EvalSymlinks(p)
			if err != nil {
				return err
			}
			rel, err := filepath.Rel(app, resolved)
			if err != nil || rel == ".." || strings.HasPrefix(rel, ".."+string(filepath.Separator)) {
				return fmt.Errorf("unsafe archive symlink: %s", p)
			}
		}
		return nil
	}); err != nil {
		return "", err
	}
	if err := validateBundleLayout(app); err != nil {
		return "", err
	}
	return app, nil
}

// Unix releases require the complete frozen onedir runtime, not only Go.
func validateBundleLayout(app string) error {
	for _, name := range []string{"r10n", "libexec/r10n-python/r10n-python"} {
		info, err := os.Lstat(filepath.Join(app, filepath.FromSlash(name)))
		if err != nil || !info.Mode().IsRegular() || info.Mode().Perm()&0111 == 0 {
			return fmt.Errorf("release requires a regular executable %s", name)
		}
	}
	runtime := filepath.Join(app, "libexec", "r10n-python", "_internal")
	info, err := os.Lstat(runtime)
	if err != nil || !info.IsDir() {
		return fmt.Errorf("release requires frozen runtime directory libexec/r10n-python/_internal")
	}
	entries, err := os.ReadDir(runtime)
	if err != nil || len(entries) == 0 {
		return fmt.Errorf("release contains an empty or unreadable frozen runtime")
	}
	return nil
}

var renamePath = os.Rename

// replaceBundle stages on the same filesystem and swaps the entire app directory,
// leaving the original command symlink untouched. On failure restore the old app.
func replaceBundle(ctx context.Context, native, newApp, version string) error {
	app := filepath.Dir(native)
	if filepath.Base(native) != "r10n" {
		return fmt.Errorf("cannot identify native installation; reinstall the release bundle")
	}
	// A binary installed directly in a shared bin directory must not cause that
	// directory to be replaced. Supported archives install an isolated app dir.
	if filepath.Base(app) != ".r10n" && filepath.Base(app) != "r10n" {
		return fmt.Errorf("upgrade requires an isolated r10n app bundle; reinstall with install.sh")
	}
	parent := filepath.Dir(app)
	stage, err := os.MkdirTemp(parent, ".r10n-stage-")
	if err != nil {
		return err
	}
	retainRecovery := false
	defer func() {
		if !retainRecovery {
			_ = os.RemoveAll(stage)
		}
	}()
	staged := filepath.Join(stage, "app")
	if err := copyBundle(newApp, staged); err != nil {
		return err
	}
	if err := validateReleaseBundle(ctx, staged, version); err != nil {
		return fmt.Errorf("validate staged release: %w", err)
	}
	if err := ctx.Err(); err != nil {
		return err
	}
	backup := filepath.Join(stage, "old")
	if err := renamePath(app, backup); err != nil {
		return fmt.Errorf("backup installed bundle: %w", err)
	}
	restore := func(failure error, installed bool) error {
		// Preserve both trees if either rollback rename fails.
		if installed {
			if err := renamePath(app, staged); err != nil {
				retainRecovery = true
				return fmt.Errorf("upgrade failed: %v; rollback failed: %v; recover bundle from %s", failure, err, backup)
			}
		}
		if rollbackErr := renamePath(backup, app); rollbackErr != nil {
			retainRecovery = true
			return fmt.Errorf("upgrade failed: %v; rollback failed: %v; recover bundle from %s", failure, rollbackErr, backup)
		}
		return fmt.Errorf("upgrade failed; original bundle restored: %w", failure)
	}
	if err := ctx.Err(); err != nil {
		return restore(err, false)
	}
	if err := renamePath(staged, app); err != nil {
		return restore(err, false)
	}
	if err := validateReleaseBundle(ctx, app, version); err != nil {
		return restore(err, true)
	}
	if err := ctx.Err(); err != nil {
		return restore(err, true)
	}
	return nil
}

func copyBundle(source, destination string) error {
	return filepath.WalkDir(source, func(p string, entry os.DirEntry, err error) error {
		if err != nil {
			return err
		}
		rel, err := filepath.Rel(source, p)
		if err != nil {
			return err
		}
		out := filepath.Join(destination, rel)
		info, err := entry.Info()
		if err != nil {
			return err
		}
		if entry.IsDir() {
			return os.Mkdir(out, info.Mode().Perm()|0700)
		}
		if entry.Type()&os.ModeSymlink != 0 {
			target, err := os.Readlink(p)
			if err != nil {
				return err
			}
			if err := safeLink("r10n/"+filepath.ToSlash(rel), target); err != nil {
				return err
			}
			return os.Symlink(target, out)
		}
		if !info.Mode().IsRegular() {
			return fmt.Errorf("unsupported bundle entry: %s", p)
		}
		in, err := os.Open(p)
		if err != nil {
			return err
		}
		defer in.Close()
		file, err := os.OpenFile(out, os.O_WRONLY|os.O_CREATE|os.O_EXCL, info.Mode().Perm())
		if err != nil {
			return err
		}
		_, writeErr := io.Copy(file, in)
		closeErr := file.Close()
		if writeErr != nil {
			return writeErr
		}
		return closeErr
	})
}
