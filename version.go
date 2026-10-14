// Package r10n exposes the shared release version to the native shell.
package r10n

import (
	_ "embed"
	"regexp"
)

//go:embed pyproject.toml
var projectMetadata string

// Version comes from Python package metadata, not a second Go version constant.
var Version = regexp.MustCompile(`(?m)^version = "([^"]+)"`).FindStringSubmatch(projectMetadata)[1]
