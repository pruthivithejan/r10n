// Package r10n exposes shared release metadata to the native command interface.
package r10n

import (
	_ "embed"
	"regexp"
)

//go:embed pyproject.toml
var projectMetadata string

// Version comes from Python package metadata, not a second Go version constant.
var Version = regexp.MustCompile(`(?m)^version = "([^"]+)"`).FindStringSubmatch(projectMetadata)[1]
