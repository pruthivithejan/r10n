package r10n

import "embed"

// WorkspaceTemplates contains canonical examples, shared with source installs.
//
//go:embed configs/*.default.json
var WorkspaceTemplates embed.FS
