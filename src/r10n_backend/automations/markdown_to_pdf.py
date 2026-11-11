"""
Markdown document to PDF converter automation.

Converts markdown files to styled PDF documents with support for
custom CSS styling, syntax highlighting, and batch processing.
"""

import html as html_lib
import json
import re
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from typing import Any, cast

import markdown
from pygments import highlight
from pygments.formatters.html import HtmlFormatter
from pygments.lexers import get_lexer_by_name
from pygments.lexers.special import TextLexer
from pygments.util import ClassNotFound
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4, LEGAL, LETTER
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import (
    Paragraph,
    Preformatted,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
    XPreformatted,
)
from reportlab.platypus.tableofcontents import TableOfContents

PAGE_SIZES = {
    "A4": A4,
    "Letter": LETTER,
    "LETTER": LETTER,
    "Legal": LEGAL,
}


class _Heading(Paragraph):
    """A heading with a destination for the contents list."""

    def __init__(self, content: str, style: ParagraphStyle, level: int, key: str) -> None:
        super().__init__(content, style)
        self.toc_level = level
        self.toc_key = key

    def drawOn(self, canvas, x, y, _sW=0):  # noqa: N802, N803 - ReportLab callback signature
        """Place the link destination at the actual top of this heading."""
        canvas.bookmarkHorizontalAbsolute(self.toc_key, y + self.height, left=x)
        return super().drawOn(canvas, x, y, _sW)


class _DocumentWithContents(SimpleDocTemplate):
    """Collect heading locations during ReportLab's multi-pass build."""

    def afterFlowable(self, flowable):  # noqa: N802 - ReportLab callback name
        """Register a heading's page and link destination."""
        if isinstance(flowable, _Heading):
            key = flowable.toc_key
            self.notify("TOCEntry", (flowable.toc_level, flowable.getPlainText(), self.page, key))


@dataclass
class MarkdownToPdfConfig:
    """Configuration for markdown to PDF conversion."""

    input_path: str
    output_path: str
    css_file: str | None = None
    page_size: str = "A4"
    margin_top: int = 20
    margin_bottom: int = 20
    margin_left: int = 20
    margin_right: int = 20
    include_toc: bool = False
    syntax_highlighting: bool = True


def parse_markdown(content: str) -> str:
    """
    Parse markdown content to HTML.

    Args:
        content: Markdown content as string

    Returns:
        HTML string
    """
    extensions = [
        "markdown.extensions.tables",
        "markdown.extensions.fenced_code",
        "markdown.extensions.codehilite",
        "markdown.extensions.toc",
        "markdown.extensions.nl2br",
    ]

    md = markdown.Markdown(extensions=extensions)
    html = md.convert(content)

    return html


def apply_css_styling(
    html: str,
    css_file: str | None = None,
    syntax_highlighting: bool = True,
) -> str:
    """
    Apply CSS styling to HTML content.

    Args:
        html: HTML content
        css_file: Path to custom CSS file (optional)
        syntax_highlighting: Include syntax highlighting styles

    Returns:
        HTML with embedded styles
    """
    default_css = """
    body { font-family: Helvetica, Arial, sans-serif; }
    h1 { font-size: 24pt; color: #333; margin-top: 20pt; }
    h2 { font-size: 18pt; color: #444; margin-top: 16pt; }
    h3 { font-size: 14pt; color: #555; margin-top: 12pt; }
    p { font-size: 11pt; line-height: 1.5; }
    code { font-family: Courier, monospace; background: #f5f5f5; padding: 2pt; }
    pre { background: #f5f5f5; padding: 10pt; font-family: Courier, monospace; }
    blockquote { border-left: 3pt solid #ccc; padding-left: 10pt; color: #666; }
    """

    highlight_css = """
    .codehilite { background: #f8f8f8; padding: 10pt; }
    .codehilite .k { color: #008000; font-weight: bold; }
    .codehilite .s { color: #BA2121; }
    .codehilite .c { color: #408080; font-style: italic; }
    .codehilite .n { color: #000000; }
    """

    css = default_css
    if syntax_highlighting:
        css += highlight_css

    if css_file:
        css_path = Path(css_file)
        if not css_path.exists():
            raise FileNotFoundError(f"CSS file not found: {css_file}")
        css += css_path.read_text()

    styled_html = f"""
    <html>
    <head>
        <style>
        {css}
        </style>
    </head>
    <body>
    {html}
    </body>
    </html>
    """

    return styled_html


class MarkdownConverter:
    """Class for converting markdown to PDF."""

    def __init__(self, config: MarkdownToPdfConfig):
        """
        Initialize the MarkdownConverter.

        Args:
            config: Conversion configuration
        """
        self.config = config
        self.styles = getSampleStyleSheet()
        self._setup_styles()

    def _setup_styles(self):
        """Set up custom paragraph styles."""
        self.styles.add(
            ParagraphStyle(
                name="Heading1Custom",
                parent=self.styles["Heading1"],
                fontSize=24,
                spaceAfter=12,
                textColor=colors.HexColor("#333333"),
            )
        )
        self.styles.add(
            ParagraphStyle(
                name="Heading2Custom",
                parent=self.styles["Heading2"],
                fontSize=18,
                spaceAfter=10,
                textColor=colors.HexColor("#444444"),
            )
        )
        self.styles.add(
            ParagraphStyle(
                name="Heading3Custom",
                parent=self.styles["Heading3"],
                fontSize=14,
                spaceAfter=8,
                textColor=colors.HexColor("#555555"),
            )
        )
        for level in range(4, 7):
            self.styles.add(
                ParagraphStyle(name=f"Heading{level}Custom", parent=self.styles["Heading3Custom"])
            )
        self.styles.add(
            ParagraphStyle(
                name="CodeBlock",
                parent=self.styles["Code"],
                fontName="Courier",
                fontSize=9,
                backColor=colors.HexColor("#f5f5f5"),
                borderColor=colors.HexColor("#dddddd"),
                borderWidth=1,
                borderPadding=5,
            )
        )
        self.styles.add(
            ParagraphStyle(
                name="BlockQuote",
                parent=self.styles["Normal"],
                leftIndent=20,
                textColor=colors.HexColor("#666666"),
                borderColor=colors.HexColor("#cccccc"),
                borderWidth=0,
                borderPadding=0,
            )
        )

    def _apply_custom_styles(self) -> None:
        """Apply the supported basic element and typography CSS declarations."""
        if not self.config.css_file:
            return
        css = Path(self.config.css_file).read_text(encoding="utf-8")
        css = re.sub(r"/\*.*?\*/", "", css, flags=re.DOTALL)
        selectors = {
            "h1": ("Heading1Custom",),
            "h2": ("Heading2Custom",),
            "h3": ("Heading3Custom",),
            "h4": ("Heading4Custom",),
            "h5": ("Heading5Custom",),
            "h6": ("Heading6Custom",),
            "p": ("Normal",),
            "pre": ("CodeBlock",),
            "code": ("CodeBlock",),
            "blockquote": ("BlockQuote",),
        }
        for selector_text, declarations in re.findall(r"([^{}]+)\{([^{}]*)\}", css):
            for selector in selector_text.split(","):
                for style_name in selectors.get(selector.strip().lower(), ()):
                    style = self.styles[style_name]
                    for declaration in declarations.split(";"):
                        name, separator, value = declaration.partition(":")
                        if not separator:
                            continue
                        name, value = name.strip().lower(), value.strip()
                        if name in {"color", "background-color"}:
                            try:
                                if re.fullmatch(r"#[0-9a-fA-F]{3}", value):
                                    value = "#" + "".join(character * 2 for character in value[1:])
                                parse_color = cast(Callable[[str], Any], colors.toColor)
                                color = parse_color(value)
                            except (ValueError, TypeError):
                                continue
                            setattr(style, "textColor" if name == "color" else "backColor", color)
                        elif name == "font-size" and re.fullmatch(r"\d+(?:\.\d+)?pt", value):
                            style.fontSize = float(value[:-2])
                            style.leading = style.fontSize * 1.2

    def _code_flowable(self, content: str, language: str) -> Preformatted | XPreformatted:
        """Render fenced code with optional Pygments token colors."""
        code = html_lib.unescape(re.sub(r"<[^>]*>", "", content))
        if not self.config.syntax_highlighting:
            return Preformatted(code, self.styles["CodeBlock"])
        try:
            lexer = get_lexer_by_name(language) if language else TextLexer()
        except ClassNotFound:
            lexer = TextLexer()
        highlighted = highlight(code, lexer, HtmlFormatter(nowrap=True, noclasses=True))

        def render_token(match: re.Match[str]) -> str:
            color = re.search(r"color:\s*(#[0-9A-Fa-f]{3,6})", match.group(1))
            if not color:
                return match.group(2)
            value = color.group(1)
            if len(value) == 4:
                value = "#" + "".join(character * 2 for character in value[1:])
            return f'<font color="{value}">{match.group(2)}</font>'

        highlighted = re.sub(
            r'<span\s+style="([^"]*)">(.*?)</span>', render_token, highlighted, flags=re.DOTALL
        )
        return XPreformatted(highlighted.rstrip("\n"), self.styles["CodeBlock"])

    def _parse_html_to_elements(self, html: str) -> list:
        """
        Parse HTML to reportlab flowable elements.

        Args:
            html: HTML content

        Returns:
            List of flowable elements
        """
        elements = []

        def heading(content: str, style: str, level: int) -> _Heading:
            key = f"heading-{sum(isinstance(item, _Heading) for item in elements)}"
            return _Heading(content, self.styles[style], level, key)

        html = re.sub(
            r"<html[^>]*>|</html>|<head[^>]*>.*?</head>|<body[^>]*>|</body>",
            "",
            html,
            flags=re.DOTALL | re.IGNORECASE,
        )
        html = re.sub(r"<style[^>]*>.*?</style>", "", html, flags=re.DOTALL | re.IGNORECASE)

        escaped_marker = "\x00r10n-content-marker\x00"
        while escaped_marker in html:
            escaped_marker += "\x00"
        html = html.replace("|||", escaped_marker)

        html = re.sub(
            r"<h1[^>]*>(.*?)</h1>", r"|||H1|||\1|||/H1|||", html, flags=re.DOTALL | re.IGNORECASE
        )
        html = re.sub(
            r"<h2[^>]*>(.*?)</h2>", r"|||H2|||\1|||/H2|||", html, flags=re.DOTALL | re.IGNORECASE
        )
        html = re.sub(
            r"<h3[^>]*>(.*?)</h3>", r"|||H3|||\1|||/H3|||", html, flags=re.DOTALL | re.IGNORECASE
        )
        html = re.sub(
            r"<h4[^>]*>(.*?)</h4>", r"|||H4|||\1|||/H4|||", html, flags=re.DOTALL | re.IGNORECASE
        )
        html = re.sub(
            r"<h5[^>]*>(.*?)</h5>", r"|||H5|||\1|||/H5|||", html, flags=re.DOTALL | re.IGNORECASE
        )
        html = re.sub(
            r"<h6[^>]*>(.*?)</h6>", r"|||H6|||\1|||/H6|||", html, flags=re.DOTALL | re.IGNORECASE
        )

        html = re.sub(
            r"<p[^>]*>(.*?)</p>", r"|||P|||\1|||/P|||", html, flags=re.DOTALL | re.IGNORECASE
        )

        def code_marker(match: re.Match[str]) -> str:
            language = re.search(r"language-([^\s\"'<>]+)", match.group(1))
            return f"|||CODE:{language.group(1) if language else ''}|||{match.group(2)}|||/CODE|||"

        html = re.sub(
            r"<pre[^>]*><code([^>]*)>(.*?)</code></pre>",
            code_marker,
            html,
            flags=re.DOTALL | re.IGNORECASE,
        )
        html = re.sub(
            r"<pre[^>]*>(.*?)</pre>",
            r"|||CODE|||\1|||/CODE|||",
            html,
            flags=re.DOTALL | re.IGNORECASE,
        )

        html = re.sub(
            r"<blockquote[^>]*>(.*?)</blockquote>",
            r"|||QUOTE|||\1|||/QUOTE|||",
            html,
            flags=re.DOTALL | re.IGNORECASE,
        )

        html = re.sub(
            r"<li[^>]*>(.*?)</li>", r"|||LI|||\1|||/LI|||", html, flags=re.DOTALL | re.IGNORECASE
        )

        html = re.sub(
            r"<table[^>]*>(.*?)</table>",
            r"|||TABLE|||\1|||/TABLE|||",
            html,
            flags=re.DOTALL | re.IGNORECASE,
        )

        html = re.sub(r"<br\s*/?>", "\n", html, flags=re.IGNORECASE)
        html = re.sub(r"<hr\s*/?>", "|||HR|||", html, flags=re.IGNORECASE)

        html = re.sub(
            r"<strong[^>]*>(.*?)</strong>", r"<b>\1</b>", html, flags=re.DOTALL | re.IGNORECASE
        )
        html = re.sub(r"<em[^>]*>(.*?)</em>", r"<i>\1</i>", html, flags=re.DOTALL | re.IGNORECASE)
        html = re.sub(
            r"<code[^>]*>(.*?)</code>",
            r"<font face='Courier'>\1</font>",
            html,
            flags=re.DOTALL | re.IGNORECASE,
        )
        html = re.sub(
            r"<a[^>]*href=['\"]([^'\"]*)['\"][^>]*>(.*?)</a>",
            r"<link href='\1'>\2</link>",
            html,
            flags=re.DOTALL | re.IGNORECASE,
        )

        parts = [part.replace(escaped_marker, "|||") for part in html.split("|||")]

        i = 0
        while i < len(parts):
            part = parts[i].strip()

            if part.startswith("H1"):
                content = parts[i + 1] if i + 1 < len(parts) else ""
                content = self._clean_html(content)
                if content:
                    elements.append(heading(content, "Heading1Custom", 0))
                    elements.append(Spacer(1, 6 * mm))
                i += 3

            elif part.startswith("H2"):
                content = parts[i + 1] if i + 1 < len(parts) else ""
                content = self._clean_html(content)
                if content:
                    elements.append(heading(content, "Heading2Custom", 1))
                    elements.append(Spacer(1, 4 * mm))
                i += 3

            elif part.startswith("H3"):
                content = parts[i + 1] if i + 1 < len(parts) else ""
                content = self._clean_html(content)
                if content:
                    elements.append(heading(content, "Heading3Custom", 2))
                    elements.append(Spacer(1, 3 * mm))
                i += 3

            elif part.startswith("H") and len(part) == 2 and part[1].isdigit():
                content = parts[i + 1] if i + 1 < len(parts) else ""
                content = self._clean_html(content)
                if content:
                    elements.append(heading(content, f"Heading{part[1]}Custom", int(part[1]) - 1))
                    elements.append(Spacer(1, 3 * mm))
                i += 3

            elif part == "P":
                content = parts[i + 1] if i + 1 < len(parts) else ""
                content = self._clean_html(content)
                if content:
                    elements.append(Paragraph(content, self.styles["Normal"]))
                    elements.append(Spacer(1, 3 * mm))
                i += 3

            elif part == "CODE" or part.startswith("CODE:"):
                content = parts[i + 1] if i + 1 < len(parts) else ""
                if content:
                    elements.append(
                        self._code_flowable(content, part[5:] if part.startswith("CODE:") else "")
                    )
                    elements.append(Spacer(1, 4 * mm))
                i += 3

            elif part == "QUOTE":
                content = parts[i + 1] if i + 1 < len(parts) else ""
                content = self._clean_html(content)
                if content:
                    elements.append(Paragraph(content, self.styles["BlockQuote"]))
                    elements.append(Spacer(1, 3 * mm))
                i += 3

            elif part == "LI":
                content = parts[i + 1] if i + 1 < len(parts) else ""
                content = self._clean_html(content)
                if content:
                    bullet_text = f"• {content}"
                    elements.append(Paragraph(bullet_text, self.styles["Normal"]))
                i += 3

            elif part == "HR":
                elements.append(Spacer(1, 5 * mm))
                i += 1

            elif part == "TABLE":
                table_html = parts[i + 1] if i + 1 < len(parts) else ""
                table_elements = self._parse_table(table_html)
                if table_elements:
                    elements.extend(table_elements)
                i += 3

            else:
                if (
                    part
                    and not part.startswith("/")
                    and part not in ("TABLE", "HR", "LI", "CODE", "QUOTE", "P")
                ):
                    cleaned = self._clean_html(part)
                    if cleaned and len(cleaned) > 2:
                        elements.append(Paragraph(cleaned, self.styles["Normal"]))
                        elements.append(Spacer(1, 2 * mm))
                i += 1

        return elements

    def _clean_html(self, text: str) -> str:
        """Clean HTML text for reportlab."""
        text = re.sub(r"<(?!b|/b|i|/i|u|/u|font|/font|link|/link)[^>]+>", "", text)
        text = self._unescape_html(text)
        return text.strip()

    def _unescape_html(self, text: str) -> str:
        """Unescape HTML entities."""
        text = text.replace("&lt;", "<")
        text = text.replace("&gt;", ">")
        text = text.replace("&amp;", "&")
        text = text.replace("&quot;", '"')
        text = text.replace("&#39;", "'")
        text = text.replace("&nbsp;", " ")
        return text

    def _parse_table(self, table_html: str) -> list:
        """Parse HTML table to reportlab Table."""
        elements = []

        rows = re.findall(r"<tr[^>]*>(.*?)</tr>", table_html, flags=re.DOTALL | re.IGNORECASE)
        if not rows:
            return elements

        table_data = []
        for row in rows:
            cells = re.findall(r"<t[hd][^>]*>(.*?)</t[hd]>", row, flags=re.DOTALL | re.IGNORECASE)
            if cells:
                cleaned_cells = [self._clean_html(cell) for cell in cells]
                table_data.append(cleaned_cells)

        if table_data:
            table = Table(table_data)
            table.setStyle(
                TableStyle(
                    [
                        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#f0f0f0")),
                        ("TEXTCOLOR", (0, 0), (-1, 0), colors.HexColor("#333333")),
                        ("ALIGN", (0, 0), (-1, -1), "LEFT"),
                        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                        ("FONTSIZE", (0, 0), (-1, -1), 10),
                        ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
                        ("TOPPADDING", (0, 0), (-1, -1), 6),
                        ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#cccccc")),
                    ]
                )
            )
            elements.append(table)
            elements.append(Spacer(1, 4 * mm))

        return elements

    def convert(self) -> dict[str, Any]:
        """
        Convert markdown file to PDF.

        Returns:
            Dictionary with conversion result

        Raises:
            FileNotFoundError: If input file doesn't exist
        """
        input_path = Path(self.config.input_path)
        if not input_path.exists():
            raise FileNotFoundError(f"Input file not found: {self.config.input_path}")

        output_path = Path(self.config.output_path)

        output_path.parent.mkdir(parents=True, exist_ok=True)

        content = input_path.read_text(encoding="utf-8")

        html = markdown.Markdown(extensions=["tables", "fenced_code", "toc", "nl2br"]).convert(
            content
        )

        styled_html = apply_css_styling(
            html,
            css_file=self.config.css_file,
            syntax_highlighting=self.config.syntax_highlighting,
        )

        self._apply_custom_styles()
        elements = self._parse_html_to_elements(styled_html)
        if not elements:
            elements.append(Spacer(1, 0))

        include_toc = self.config.include_toc and any(
            isinstance(item, _Heading) for item in elements
        )
        if include_toc:
            contents = TableOfContents()
            contents.levelStyles = [
                ParagraphStyle(
                    f"ContentsLevel{level}",
                    parent=self.styles["Normal"],
                    leftIndent=level * 12,
                    firstLineIndent=-6,
                    leading=14,
                )
                for level in range(6)
            ]
            elements = [
                Paragraph("Table of Contents", self.styles["Heading1Custom"]),
                contents,
                Spacer(1, 8 * mm),
                *elements,
            ]

        page_size = PAGE_SIZES.get(self.config.page_size, A4)

        doc = _DocumentWithContents(
            str(output_path),
            pagesize=page_size,
            topMargin=self.config.margin_top * mm,
            bottomMargin=self.config.margin_bottom * mm,
            leftMargin=self.config.margin_left * mm,
            rightMargin=self.config.margin_right * mm,
        )

        if include_toc:
            doc.multiBuild(elements)
        else:
            doc.build(elements)

        return {
            "success": True,
            "input_path": str(input_path),
            "output_path": str(output_path),
            "pages": doc.page,
        }


def convert_markdown_to_pdf(
    input_path: str,
    output_path: str | None = None,
    css_file: str | None = None,
    page_size: str = "A4",
    margin_top: int = 20,
    margin_bottom: int = 20,
    margin_left: int = 20,
    margin_right: int = 20,
    include_toc: bool = False,
    syntax_highlighting: bool = True,
) -> dict[str, Any]:
    """
    Convert a markdown file to PDF.

    Args:
        input_path: Path to markdown file
        output_path: Path for output PDF (auto-generated if not provided)
        css_file: Path to custom CSS file
        page_size: Page size ("A4" or "Letter")
        margin_top: Top margin in mm
        margin_bottom: Bottom margin in mm
        margin_left: Left margin in mm
        margin_right: Right margin in mm
        include_toc: Include table of contents
        syntax_highlighting: Enable syntax highlighting for code

    Returns:
        Dictionary with conversion result
    """
    if output_path is None:
        input_file = Path(input_path)
        output_path = str(input_file.with_suffix(".pdf"))

    config = MarkdownToPdfConfig(
        input_path=input_path,
        output_path=output_path,
        css_file=css_file,
        page_size=page_size,
        margin_top=margin_top,
        margin_bottom=margin_bottom,
        margin_left=margin_left,
        margin_right=margin_right,
        include_toc=include_toc,
        syntax_highlighting=syntax_highlighting,
    )

    converter = MarkdownConverter(config)
    return converter.convert()


def convert_directory(
    input_dir: str,
    output_dir: str | None = None,
    recursive: bool = False,
    preserve_structure: bool = True,
    css_file: str | None = None,
    page_size: str = "A4",
    include_toc: bool = False,
    syntax_highlighting: bool = True,
) -> dict[str, Any]:
    """
    Convert all markdown files in a directory to PDF.

    Args:
        input_dir: Directory containing markdown files
        output_dir: Directory for output PDFs
        recursive: Process subdirectories
        preserve_structure: Maintain directory structure in output
        css_file: Path to custom CSS file for all conversions
        page_size: Page size for all PDFs
        include_toc: Include a table of contents in each PDF
        syntax_highlighting: Highlight fenced code in each PDF

    Returns:
        Dictionary with conversion summary
    """
    input_path = Path(input_dir)

    if not input_path.exists():
        raise FileNotFoundError(f"Input directory not found: {input_dir}")

    if output_dir is None:
        output_dir = str(input_path / "pdf_output")

    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)

    if recursive:
        md_files = list(input_path.rglob("*.md"))
    else:
        md_files = list(input_path.glob("*.md"))

    results = {
        "total": len(md_files),
        "converted": 0,
        "failed": 0,
        "files": [],
    }

    for md_file in md_files:
        try:
            if preserve_structure and recursive:
                relative = md_file.relative_to(input_path)
                pdf_output = output_path / relative.with_suffix(".pdf")
                pdf_output.parent.mkdir(parents=True, exist_ok=True)
            else:
                pdf_output = output_path / md_file.with_suffix(".pdf").name

            convert_markdown_to_pdf(
                input_path=str(md_file),
                output_path=str(pdf_output),
                css_file=css_file,
                page_size=page_size,
                include_toc=include_toc,
                syntax_highlighting=syntax_highlighting,
            )

            results["converted"] += 1
            results["files"].append(
                {
                    "input": str(md_file.name),
                    "output": str(pdf_output),
                    "success": True,
                }
            )

        except Exception as e:
            results["failed"] += 1
            results["files"].append(
                {
                    "input": str(md_file.name),
                    "error": str(e),
                    "success": False,
                }
            )

    return results


def load_config(config_path: str) -> MarkdownToPdfConfig:
    """
    Load configuration from a JSON file.

    Args:
        config_path: Path to configuration JSON file

    Returns:
        MarkdownToPdfConfig object

    Raises:
        FileNotFoundError: If config file doesn't exist
    """
    path = Path(config_path)
    if not path.exists():
        raise FileNotFoundError(f"Config file not found: {config_path}")

    with open(path, encoding="utf-8") as f:
        data = json.load(f)

    return MarkdownToPdfConfig(
        input_path=data.get("input_path", ""),
        output_path=data.get("output_path", ""),
        css_file=data.get("css_file"),
        page_size=data.get("page_size", "A4"),
        margin_top=data.get("margin_top", 20),
        margin_bottom=data.get("margin_bottom", 20),
        margin_left=data.get("margin_left", 20),
        margin_right=data.get("margin_right", 20),
        include_toc=data.get("include_toc", False),
        syntax_highlighting=data.get("syntax_highlighting", True),
    )


if __name__ == "__main__":
    print("Markdown to PDF Converter automation")
    print("Use the main CLI: uv run r10n md2pdf")
