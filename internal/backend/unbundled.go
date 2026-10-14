//go:build !bundled

package backend

// Bundled identifies a release with its Python runtime embedded.
const Bundled = false

func embeddedBackend() (string, error) {
	return "", nil
}
