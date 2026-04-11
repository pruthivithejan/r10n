# r10n MCP Server Design

## Overview

Add an MCP (Model Context Protocol) server to r10n that exposes all 8 automations as tools and config templates as resources. This allows AI assistants (Claude Desktop, etc.) to invoke r10n automations programmatically via stdio transport.

## Architecture

```
src/
├── mcp/
│   ├── __init__.py           # Package init
│   ├── server.py             # MCPServer instance, registers all tools & resources
│   ├── tools/
│   │   ├── __init__.py
│   │   ├── contacts.py       # generate_contacts tool
│   │   ├── fill_pdfs.py      # fill_pdfs tool
│   │   ├── images.py         # optimize_images tool
│   │   ├── email.py          # send_email tool
│   │   ├── colors.py         # convert_colors tool
│   │   ├── rename.py         # rename_files tool
│   │   ├── validate.py       # validate_csv tool
│   │   └── markdown_to_pdf.py # md2pdf tool
│   └── resources/
│       ├── __init__.py
│       └── configs.py        # Expose config templates as MCP resources
```

Each tool file imports the underlying automation function from `src/automations/`, registers one MCP tool with typed parameters (no Rich/Click prompts), and returns structured results.

`server.py` creates the `MCPServer` instance, imports all tool modules to trigger registration, and provides the `run()` entry point.

## Tool Definitions

| Tool Name | Wraps | Required Params | Optional Params |
|-----------|-------|-----------------|-----------------|
| `generate_contacts` | `generate_vcf_from_file()` | `input_file` | `output_name`, `prefix` |
| `fill_pdfs` | `fill_certificates_from_file()` | `recipients_file`, `config_file` | `base_dir` |
| `optimize_images` | `optimize_images()` | `input_dir` | `output_dir`, `prefix`, `max_size_mb`, `quality`, `max_width`, `max_height`, `preserve_filename` |
| `send_email` | `send_personalized_emails_with_certificates()` | `email_list_file`, `subject`, `body_template`, `config_file` | `certificates_dir` |
| `convert_colors` | `convert_colors()` | `path` | `file`, `dry_run`, `no_backup`, `excludes` |
| `rename_files` | `rename_files()` | `input_directory` | `pattern`, `prefix`, `suffix`, `replace_from`, `replace_to`, `add_date`, `add_sequence`, `lowercase`, `uppercase`, `recursive`, `dry_run`, `file_pattern` |
| `validate_csv` | `validate_csv()` | `input_file` | `schema_file`, `output_file`, `strict_mode` |
| `convert_markdown_to_pdf` | `convert_markdown_to_pdf()` | `input_path` | `output_path`, `css_file`, `page_size`, `margin_top`, `margin_bottom`, `include_toc` |

Each tool returns the automation's result dict as JSON. Errors are caught and returned as error responses.

## Resources

| Resource URI | Description |
|-------------|-------------|
| `r10n://configs/fill-pdfs` | Default fill-pdfs config template |
| `r10n://configs/email` | Default email config template |
| `r10n://configs/images` | Default images config template |
| `r10n://configs/blog` | Default blog config template |
| `r10n://automations` | List of all available automations with descriptions |

Resources are read-only. Config resources read from `configs/*.default.json` and return JSON content so AI assistants can understand expected config formats before invoking a tool.

## Entry Points

1. **CLI command**: `r10n mcp` starts the MCP server via stdio (new Click command in `cli.py`)
2. **Direct entry point**: `r10n-mcp` in `pyproject.toml` `[project.scripts]` for `uvx` usage

### Claude Desktop Configuration

```json
{
  "mcpServers": {
    "r10n": {
      "command": "uvx",
      "args": ["--from", "git+https://github.com/pruthivithejan/r10n.git", "r10n-mcp"]
    }
  }
}
```

## Transport

stdio only. Simplest option, works with Claude Desktop and most MCP clients out of the box.

## Dependencies

New dependency: `mcp` (official MCP Python SDK)

## Error Handling

- Each tool wraps its automation call in try/except
- Automation errors return structured error messages (not stack traces)
- File-not-found and validation errors caught early with clear messages
- Email tool warns if SMTP credentials missing in config

## Testing

- One test file per tool in `tests/test_mcp_*.py`
- Tests verify tool registration, parameter schemas, and basic invocation
- Uses existing test patterns (pytest, tempfile isolation)
