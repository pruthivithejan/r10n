//go:build !bundled

package backend

func embeddedBackend() (string, error) {
	return "", nil
}
