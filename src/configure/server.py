"""Flask server for the visual PDF field picker."""

import csv
import io
import json
import socket
import threading
import webbrowser
from pathlib import Path

import pypdfium2 as pdfium
from flask import Flask, jsonify, render_template, request, send_file

from src.automations.fill_pdfs import (
    create_text_overlay,
    fill_certificate,
    font_mappings_keys,
)

# Render scale: how many pixels per PDF point
RENDER_SCALE = 2.0


def pixel_to_pdf_coords(click_x, click_y, render_w, render_h, pdf_w_pt, pdf_h_pt):
    """Convert pixel coordinates (top-left origin) to PDF coordinates (bottom-left origin)."""
    pdf_x = click_x * (pdf_w_pt / render_w)
    pdf_y = pdf_h_pt - (click_y * (pdf_h_pt / render_h))
    return round(pdf_x, 1), round(pdf_y, 1)


def render_pdf_page(pdf_path, scale=RENDER_SCALE):
    """Render the first page of a PDF to a PNG image.

    Returns:
        tuple: (png_bytes, render_width_px, render_height_px, pdf_width_pt, pdf_height_pt)
    """
    pdf = pdfium.PdfDocument(pdf_path)
    page = pdf[0]
    bitmap = page.render(scale=scale)
    pil_image = bitmap.to_pil()
    buf = io.BytesIO()
    pil_image.save(buf, format="PNG")
    png_bytes = buf.getvalue()
    pdf_w_pt = page.get_width()
    pdf_h_pt = page.get_height()
    return png_bytes, pil_image.width, pil_image.height, pdf_w_pt, pdf_h_pt


def _find_free_port():
    """Find an available port on localhost."""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


# Column names that should not appear as placeable certificate fields
_IGNORED_HEADERS = {"email", "e-mail", "email_address", "email address", "mail"}


def _read_csv_headers(csv_path):
    """Read column headers from a CSV file, excluding email columns."""
    with open(csv_path, encoding="utf-8-sig", newline="") as f:
        reader = csv.reader(f)
        headers = next(reader, [])
    return [h.strip() for h in headers if h.strip() and h.strip().lower() not in _IGNORED_HEADERS]


def create_app(template_pdf, recipients_file=None, output_config=None, done_event=None):
    """Create and configure the Flask application."""
    app = Flask(__name__, template_folder=str(Path(__file__).parent / "templates"))

    # Pre-render template image and cache info
    png_bytes, render_w, render_h, pdf_w_pt, pdf_h_pt = render_pdf_page(template_pdf)

    csv_headers = []
    if recipients_file and Path(recipients_file).exists():
        csv_headers = _read_csv_headers(recipients_file)

    @app.route("/")
    def index():
        return render_template("picker.html")

    @app.route("/api/template-image")
    def template_image():
        return send_file(io.BytesIO(png_bytes), mimetype="image/png")

    @app.route("/api/template-info")
    def template_info():
        return jsonify({
            "width_pt": pdf_w_pt,
            "height_pt": pdf_h_pt,
            "render_width_px": render_w,
            "render_height_px": render_h,
        })

    @app.route("/api/csv-headers")
    def get_csv_headers():
        return jsonify(csv_headers)

    @app.route("/api/font-families")
    def get_font_families():
        return jsonify(font_mappings_keys())

    @app.route("/api/preview", methods=["POST"])
    def preview():
        data = request.get_json()
        if not data:
            return jsonify({"error": "No data provided"}), 400

        config = {
            "font_family": data.get("font_family", "Helvetica"),
            "fields": data.get("fields", {}),
        }

        # Build sample recipient data from field names
        sample_data = {}
        for field_name in config["fields"]:
            sample_data[field_name] = data.get("sample_data", {}).get(field_name, field_name.title())

        import tempfile

        with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as tmp:
            tmp_path = tmp.name

        try:
            fill_certificate(template_pdf, config, sample_data, tmp_path)
            preview_png, _, _, _, _ = render_pdf_page(tmp_path)
            return send_file(io.BytesIO(preview_png), mimetype="image/png")
        finally:
            Path(tmp_path).unlink(missing_ok=True)

    @app.route("/api/save", methods=["POST"])
    def save_config():
        data = request.get_json()
        if not data:
            return jsonify({"error": "No data provided"}), 400

        config = {
            "template_pdf": str(template_pdf),
            "output_directory": data.get("output_directory", "local/outputs/fill-pdfs"),
            "font_family": data.get("font_family", "Helvetica"),
            "fields": data.get("fields", {}),
        }

        save_path = Path(output_config or "local/configs/fill-pdfs.json")
        save_path.parent.mkdir(parents=True, exist_ok=True)
        save_path.write_text(json.dumps(config, indent=2))

        if done_event:
            done_event.set()

        return jsonify({"saved": str(save_path)})

    return app


def launch_picker(template_pdf, recipients_file=None, output_config=None):
    """Launch the visual field picker in a browser.

    Args:
        template_pdf: Path to the PDF template file.
        recipients_file: Optional path to a CSV file (for column header extraction).
        output_config: Optional path for the output config JSON.

    Returns:
        str: The path to the saved configuration file.
    """
    template_pdf = str(Path(template_pdf).resolve())
    if not Path(template_pdf).exists():
        raise FileNotFoundError(f"Template PDF not found: {template_pdf}")

    done_event = threading.Event()
    port = _find_free_port()
    config_path = output_config or "local/configs/fill-pdfs.json"

    app = create_app(
        template_pdf=template_pdf,
        recipients_file=recipients_file,
        output_config=config_path,
        done_event=done_event,
    )

    def run_server():
        app.run(host="127.0.0.1", port=port, debug=False, use_reloader=False)

    server_thread = threading.Thread(target=run_server, daemon=True)
    server_thread.start()

    url = f"http://127.0.0.1:{port}"
    print(f"Opening visual picker at {url}")
    webbrowser.open(url)

    # Block until save is called
    done_event.wait()
    print(f"Configuration saved to {config_path}")
    return config_path
