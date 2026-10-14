package cli

import (
	"flag"
	"fmt"
	"os"
	"sort"
	"strconv"
	"strings"

	"github.com/pruthivithejan/r10n/internal/backend"
	"github.com/pruthivithejan/r10n/internal/tui"
)

// These are CLI spellings, not schemas: types, defaults, bounds and choices
// always come from the Python catalog.
var aliases = map[string]string{
	"contacts":       "input,i=input_file output,o=output_file prefix,p=prefix",
	"fill-pdfs":      "config,c=config_file recipients,r=recipients_file template,t=@template",
	"images":         "input,i=input_directory output,o=output_directory quality,q=quality max-size,s=max_size_mb prefix,p=prefix preserve-names=preserve_filenames",
	"website-images": "url,u=url output,o=output_directory format,f=output_format quality,q=quality timeout=timeout max-pages=max_pages",
	"logos":          "names,n=names output,o=output_directory timeout=timeout max-candidates=max_candidates overwrite=overwrite no-manifest=!write_manifest",
	"email":          "config,c=config_file recipients,r=recipients_file body,b=body_file attachments-dir,d=attachments_directory",
	"colors":         "path,p=path file,f=file no-backup=!create_backups all,a=@all dry-run=dry_run no-dry-run=!dry_run",
	"rename":         "input,i=input_directory pattern,p=pattern prefix=prefix suffix=suffix replace-from=replace_from replace-to=replace_to lowercase=lowercase uppercase=uppercase add-date=add_date add-sequence=add_sequence recursive,r=recursive dry-run,n=dry_run no-dry-run=!dry_run file-pattern=file_pattern",
	"validate":       "input,i=input_file schema,s=schema_file output,o=report_file strict=strict clean=clean_invalid format,f=report_format",
	"md2pdf":         "input,i=input_path output,o=output_path css,c=css_file page-size=page_size toc=include_toc syntax-highlight=syntax_highlighting recursive,r=recursive",
}

var booleanFields = map[string]bool{
	"preserve_filenames": true, "overwrite": true, "write_manifest": true,
	"create_backups": true, "dry_run": true, "lowercase": true, "uppercase": true,
	"add_date": true, "add_sequence": true, "recursive": true, "strict": true,
	"clean_invalid": true, "include_toc": true, "syntax_highlighting": true, "@all": true,
}

func flagMap(id string) map[string]string {
	result := map[string]string{}
	for _, group := range strings.Fields(aliases[id]) {
		parts := strings.SplitN(group, "=", 2)
		for _, name := range strings.Split(parts[0], ",") {
			result[name] = parts[1]
		}
	}
	return result
}

func printTaskHelp(id string) {
	fmt.Fprintf(stdout, "Usage: r10n %s [flags]\nBare command opens the native form.\n", id)
	flags := flagMap(id)
	names := make([]string, 0, len(flags))
	for name := range flags {
		names = append(names, name)
	}
	sort.Strings(names)
	for _, name := range names {
		prefix := "--"
		if len(name) == 1 {
			prefix = "-"
		}
		arg := " VALUE"
		field := strings.TrimPrefix(flags[name], "!")
		if booleanFields[field] {
			arg = "[=true|false]"
		}
		fmt.Fprintf(stdout, "  %s%s%s\n", prefix, name, arg)
	}
	fmt.Fprintln(stdout, "  --yes, -y       Skip confirmation\n  --json          Stream worker JSON Lines")
}

type flagOptions struct {
	values    map[string]string
	yes, json bool
	template  string
}

func parseFlags(id string, args []string) (flagOptions, error) {
	o := flagOptions{values: map[string]string{}}
	flags := flagMap(id)
	for i := 0; i < len(args); i++ {
		arg := args[i]
		if arg == "--help" || arg == "-h" {
			return o, flag.ErrHelp
		}
		if !strings.HasPrefix(arg, "-") || arg == "-" || arg == "--" {
			return o, fmt.Errorf("unexpected argument: %s", arg)
		}
		name, value, hasValue := strings.Cut(strings.TrimLeft(arg, "-"), "=")
		if strings.HasPrefix(arg, "---") {
			return o, fmt.Errorf("unknown option: %s", arg)
		}
		if name == "yes" || name == "y" || name == "json" {
			if !hasValue {
				value = "true"
			}
			b, err := strconv.ParseBool(value)
			if err != nil {
				return o, fmt.Errorf("%s requires true or false", arg)
			}
			if name == "json" {
				o.json = b
			} else {
				o.yes = b
			}
			continue
		}
		mapped, ok := flags[name]
		if !ok {
			return o, fmt.Errorf("unknown option: %s", arg)
		}
		field := strings.TrimPrefix(mapped, "!")
		if booleanFields[field] {
			if !hasValue {
				value = "true"
			}
			b, err := strconv.ParseBool(value)
			if err != nil {
				return o, fmt.Errorf("%s requires true or false", arg)
			}
			if strings.HasPrefix(mapped, "!") {
				b = !b
			}
			value = strconv.FormatBool(b)
		} else if !hasValue {
			i++
			if i >= len(args) || strings.HasPrefix(args[i], "--") {
				return o, fmt.Errorf("%s requires a value", arg)
			}
			value = args[i]
		}
		if field == "@template" {
			o.template = value
			continue
		}
		if field == "@all" {
			if value == "true" {
				o.yes = true
			}
			continue
		} // Compatibility confirmation alias, never a worker parameter.
		if old, exists := o.values[field]; exists && old != value {
			return o, fmt.Errorf("conflicting options for %s", field)
		}
		o.values[field] = value
	}
	return o, nil
}

func (o flagOptions) payload(task backend.Automation) (map[string]any, error) {
	result := map[string]any{}
	for name, text := range o.values {
		field, ok := task.InputSchema.Properties[name]
		if !ok {
			return nil, fmt.Errorf("backend does not support input %s", name)
		}
		scalar, _ := field.Scalar()
		if task.ID == "website-images" && name == "output_format" && text == "jpeg" {
			text = "jpg"
		}
		if scalar.Type == "boolean" {
			value, err := strconv.ParseBool(text)
			if err != nil {
				return nil, fmt.Errorf("%s: expected boolean", name)
			}
			result[name] = value
		} else {
			value, err := tui.ParseField(field, text, false)
			if err != nil {
				return nil, fmt.Errorf("%s: %w", name, err)
			}
			result[name] = value
		}
	}
	for _, name := range task.InputSchema.Required {
		if _, ok := result[name]; !ok {
			return nil, fmt.Errorf("missing required input %s; run the bare command for a guided form", name)
		}
	}
	return result, nil
}

func checkPDFConfig(task backend.Automation, payload map[string]any, template string) error {
	config, _ := payload["config_file"].(string)
	if config == "" {
		config, _ = task.InputSchema.Properties["config_file"].Default.(string)
	}
	if template != "" {
		return fmt.Errorf("--template is a configuration helper, not a task input; first run: r10n configure --template %q --output %q; then run fill-pdfs --config %q", template, config, config)
	}
	if config != "" {
		if _, err := os.Stat(config); err != nil {
			return fmt.Errorf("PDF config not found: %s; create it with r10n configure --template template.pdf --output %q", config, config)
		}
	}
	return nil
}
