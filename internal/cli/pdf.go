package cli

import (
	"bytes"
	"context"
	"encoding/json"
	"flag"
	"fmt"
	"io"
	"math"
	"os"
	"path/filepath"
	"strconv"
	"strings"

	"github.com/charmbracelet/huh"
	"github.com/pruthivithejan/r10n/internal/backend"
	"github.com/pruthivithejan/r10n/internal/brand"
	"github.com/pruthivithejan/r10n/internal/settings"
	"github.com/pruthivithejan/r10n/internal/tui"
)

type pdfInspection struct {
	TemplatePDF string            `json:"template_pdf"`
	PageWidth   float64           `json:"page_width"`
	PageHeight  float64           `json:"page_height"`
	Fields      []string          `json:"fields"`
	Sample      map[string]string `json:"sample"`
}

func configurePDF(ctx context.Context, args []string) error {
	fs := flag.NewFlagSet("configure", flag.ContinueOnError)
	fs.SetOutput(io.Discard)
	var template, recipients, name, outputDirectory string
	fs.StringVar(&template, "template", "", "PDF template path")
	fs.StringVar(&template, "t", "", "PDF template path")
	fs.StringVar(&recipients, "recipients", "", "CSV, XLSX, or TXT recipient path")
	fs.StringVar(&recipients, "r", "", "CSV, XLSX, or TXT recipient path")
	fs.StringVar(&name, "name", "default", "Saved system profile name")
	fs.StringVar(&outputDirectory, "output-directory", "", "PDF output destination")
	fs.StringVar(&outputDirectory, "output-dir", "", "PDF output destination")
	if err := fs.Parse(args); err != nil {
		return usage(err)
	}
	if fs.NArg() != 0 {
		return usage(fmt.Errorf("unexpected arguments: %s", strings.Join(fs.Args(), " ")))
	}
	if name == "" {
		return usage(fmt.Errorf("PDF profile name cannot be empty"))
	}
	if !tui.Interactive() {
		return usage(fmt.Errorf("PDF configuration requires a terminal"))
	}
	if err := tui.ApplySettings(); err != nil {
		return err
	}
	if template == "" {
		template = ""
		form := huh.NewForm(huh.NewGroup(
			huh.NewInput().Title("PDF template path").Value(&template),
			huh.NewInput().Title("Recipient CSV/XLSX/TXT path (optional)").Value(&recipients),
			huh.NewInput().Title("Profile name").Value(&name),
		).Title("Configure a PDF template"))
		if err := tui.RunForm(ctx, form); err != nil {
			return err
		}
	}
	template, err := filepath.Abs(template)
	if err != nil {
		return err
	}
	if info, err := os.Stat(template); err != nil || info.IsDir() {
		return usage(fmt.Errorf("PDF template file not found: %s", template))
	}
	if recipients != "" {
		recipients, err = filepath.Abs(recipients)
		if err != nil {
			return err
		}
		if info, err := os.Stat(recipients); err != nil || info.IsDir() {
			return usage(fmt.Errorf("recipient file not found: %s", recipients))
		}
	}
	inspectionJSON, err := runBackendJSON(ctx, []string{"pdf-inspect", "--template", template}, nil)
	if err != nil {
		return err
	}
	var inspection pdfInspection
	if err := json.Unmarshal(inspectionJSON, &inspection); err != nil {
		return fmt.Errorf("invalid PDF inspection response: %w", err)
	}
	if inspection.PageWidth <= 0 || inspection.PageHeight <= 0 {
		return fmt.Errorf("PDF template has invalid page dimensions")
	}
	fields := inspection.Fields
	if recipients != "" {
		inspectionJSON, err = runBackendJSON(
			ctx,
			[]string{"pdf-inspect", "--template", template, "--recipients", recipients},
			nil,
		)
		if err != nil {
			return err
		}
		if err := json.Unmarshal(inspectionJSON, &inspection); err != nil {
			return fmt.Errorf("invalid recipient inspection response: %w", err)
		}
		fields = inspection.Fields
	}
	if len(fields) == 0 {
		var fieldList string
		form := huh.NewForm(huh.NewGroup(
			huh.NewInput().Title("Data fields (comma-separated)").Value(&fieldList).
				Validate(func(value string) error {
					if strings.TrimSpace(value) == "" {
						return fmt.Errorf("enter at least one data field")
					}
					return nil
				}),
		).Title("Choose PDF merge fields"))
		if err := tui.RunForm(ctx, form); err != nil {
			return err
		}
		for _, value := range strings.Split(fieldList, ",") {
			if field := strings.TrimSpace(value); field != "" {
				fields = append(fields, field)
			}
		}
	}
	if len(fields) == 0 {
		return fmt.Errorf("no data fields were selected")
	}

	fmt.Fprintf(stderr, "%s\nPDF page: %.1f x %.1f points\n",
		brand.Banner(os.Getenv("R10N_ACCESSIBLE") == "1"),
		inspection.PageWidth,
		inspection.PageHeight,
	)
	fmt.Fprintln(stderr, "Coordinates are measured from the page's left and bottom edges.")
	fontFamily := "Helvetica"
	formFont := huh.NewForm(huh.NewGroup(huh.NewSelect[string]().Title("Font family").
		Options(huh.NewOptions("Helvetica", "Times", "Courier", "Futura")...).
		Value(&fontFamily),
	).Title("Profile typography"))
	if err := tui.RunForm(ctx, formFont); err != nil {
		return err
	}

	type draft struct {
		X, Y, FontSize, MaxWidth string
		FontWeight, Alignment    string
	}
	drafts := make([]draft, len(fields))
	groups := make([]*huh.Group, 0, len(fields))
	for index, field := range fields {
		value := &drafts[index]
		value.X = strconv.FormatFloat(inspection.PageWidth/2, 'f', 1, 64)
		value.Y = strconv.FormatFloat(inspection.PageHeight/2, 'f', 1, 64)
		value.FontSize = "24"
		value.FontWeight = "normal"
		value.Alignment = "center"
		x := huh.NewInput().Title("x from left (PDF points)").Value(&value.X).
			Validate(validatePDFCoordinate(inspection.PageWidth))
		y := huh.NewInput().Title("y from bottom (PDF points)").Value(&value.Y).
			Validate(validatePDFCoordinate(inspection.PageHeight))
		size := huh.NewInput().Title("Font size (PDF points)").Value(&value.FontSize).
			Validate(validatePositivePDFNumber)
		weight := huh.NewSelect[string]().Title("Font weight").
			Options(huh.NewOptions("normal", "bold", "400", "700")...).
			Value(&value.FontWeight)
		alignment := huh.NewSelect[string]().Title("Text alignment").
			Options(huh.NewOptions("left", "center", "right")...).
			Value(&value.Alignment)
		maxWidth := huh.NewInput().Title("Maximum width (optional PDF points)").Value(&value.MaxWidth).
			Validate(func(text string) error {
				if strings.TrimSpace(text) == "" {
					return nil
				}
				return validatePositivePDFNumber(text)
			})
		groups = append(groups, huh.NewGroup(x, y, size, weight, alignment, maxWidth).
			Title(fmt.Sprintf("%s — field %d/%d: %s", name, index+1, len(fields), tui.SafeText(field))))
	}
	form := huh.NewForm(groups...)
	if err := tui.RunForm(ctx, form); err != nil {
		return err
	}
	fieldSettings := make(map[string]settings.PDFField, len(fields))
	for index, name := range fields {
		value := drafts[index]
		x, _ := strconv.ParseFloat(value.X, 64)
		y, _ := strconv.ParseFloat(value.Y, 64)
		fontSize, _ := strconv.ParseFloat(value.FontSize, 64)
		field := settings.PDFField{
			X: x, Y: y, FontSize: fontSize, FontWeight: value.FontWeight,
			Alignment: value.Alignment, Color: []int{0, 0, 0},
		}
		if strings.TrimSpace(value.MaxWidth) != "" {
			field.MaxWidth, _ = strconv.ParseFloat(value.MaxWidth, 64)
		}
		fieldSettings[name] = field
	}
	document, err := settings.Load()
	if err != nil {
		return err
	}
	if _, exists := document.PDFProfiles[name]; exists {
		replace := false
		form := huh.NewForm(huh.NewGroup(huh.NewConfirm().Title("Replace this saved PDF profile?").
			Affirmative("Replace").Negative("Keep existing").Value(&replace)))
		if err := tui.RunForm(ctx, form); err != nil {
			return err
		}
		if !replace {
			fmt.Fprintln(stdout, "The existing PDF profile was not changed.")
			return nil
		}
	}
	if outputDirectory == "" {
		outputDirectory = document.OutputDirectory
		if outputDirectory == "" {
			cwd, err := os.Getwd()
			if err != nil {
				return err
			}
			outputDirectory = filepath.Join(cwd, "r10n-output")
		}
		outputDirectory = filepath.Join(outputDirectory, "fill-pdfs")
	}
	outputDirectory, err = filepath.Abs(outputDirectory)
	if err != nil {
		return err
	}
	document.PDFProfiles[name] = settings.PDFProfile{
		TemplatePDF: template, OutputDirectory: outputDirectory,
		FontFamily: fontFamily, Fields: fieldSettings,
	}
	document.ActivePDFProfile = name

	if err := showPDFPreview(ctx, inspection, document.PDFProfiles[name]); err != nil {
		fmt.Fprintf(stderr, "Sample preview unavailable: %s\n", tui.SafeText(err.Error()))
	}
	confirmed := false
	formSave := huh.NewForm(huh.NewGroup(huh.NewConfirm().
		Title("Save this PDF profile in r10n's system settings?").
		Affirmative("Save profile").Negative("Cancel").Value(&confirmed)))
	if err := tui.RunForm(ctx, formSave); err != nil {
		return err
	}
	if !confirmed {
		return nil
	}
	path, err := settings.Save(document)
	if err != nil {
		return err
	}
	fmt.Fprintf(stdout, "Saved PDF profile %q to %s\n", tui.SafeText(name), tui.SafeText(path))
	fmt.Fprintf(stdout, "Generated PDFs will use %s\n", tui.SafeText(outputDirectory))
	return nil
}

func validatePDFCoordinate(maximum float64) func(string) error {
	return func(text string) error {
		value, err := strconv.ParseFloat(text, 64)
		if err != nil || math.IsNaN(value) || math.IsInf(value, 0) {
			return fmt.Errorf("enter a valid coordinate in PDF points")
		}
		if value < 0 || value > maximum {
			return fmt.Errorf("coordinate must be between 0 and %.1f points", maximum)
		}
		return nil
	}
}

func validatePositivePDFNumber(text string) error {
	value, err := strconv.ParseFloat(text, 64)
	if err != nil || math.IsNaN(value) || math.IsInf(value, 0) || value <= 0 {
		return fmt.Errorf("enter a positive number of PDF points")
	}
	return nil
}

func showPDFPreview(ctx context.Context, inspection pdfInspection, profile settings.PDFProfile) error {
	if os.Getenv("R10N_ACCESSIBLE") == "1" {
		fmt.Fprintf(stderr, "Screen-reader preview: %d fields on a %.1f x %.1f point page\n",
			len(profile.Fields), inspection.PageWidth, inspection.PageHeight)
		for name, field := range profile.Fields {
			fmt.Fprintf(stderr, "%s: x %.1f, y %.1f points, %s aligned\n",
				tui.SafeText(name), field.X, field.Y, field.Alignment)
		}
		return nil
	}
	engine, err := backend.Resolve()
	if err != nil {
		return err
	}
	payload, err := json.Marshal(map[string]any{
		"template_pdf": profile.TemplatePDF,
		"profile":      profile,
		"sample":       inspection.Sample,
	})
	if err != nil {
		return err
	}
	command := engine.Command(ctx, "pdf-preview")
	command.Stdin = bytes.NewReader(payload)
	var output, diagnostic bytes.Buffer
	command.Stdout, command.Stderr = &output, &diagnostic
	if err := command.Run(); err != nil {
		return fmt.Errorf("%s: %w", tui.SafeText(diagnostic.String()), err)
	}
	var preview struct {
		ASCII string `json:"ascii_preview"`
	}
	if err := json.Unmarshal(output.Bytes(), &preview); err != nil {
		return err
	}
	fmt.Fprintln(stderr, "Sample PDF terminal preview:")
	fmt.Fprintln(stderr, tui.SafeText(preview.ASCII))
	return nil
}

func runBackendJSON(ctx context.Context, args []string, input []byte) ([]byte, error) {
	engine, err := backend.Resolve()
	if err != nil {
		return nil, err
	}
	command := engine.Command(ctx, args...)
	if input != nil {
		command.Stdin = bytes.NewReader(input)
	}
	var diagnostic bytes.Buffer
	command.Stderr = &diagnostic
	result, err := command.Output()
	if err != nil {
		if message := strings.TrimSpace(diagnostic.String()); message != "" {
			return nil, fmt.Errorf("%s: %w", tui.SafeText(message), err)
		}
		return nil, err
	}
	return result, nil
}
