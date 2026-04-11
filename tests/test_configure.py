"""Tests for the visual certificate field picker."""

import json
import tempfile
from io import BytesIO
from pathlib import Path

import pytest
from reportlab.pdfgen import canvas

from src.configure.server import (
    create_app,
    pixel_to_pdf_coords,
    render_pdf_page,
)


def _create_test_pdf(path, width=612, height=792):
    """Create a minimal PDF for testing (US Letter size by default)."""
    c = canvas.Canvas(str(path), pagesize=(width, height))
    c.drawString(100, 700, "Test Certificate Template")
    c.save()


@pytest.fixture()
def test_pdf(tmp_path):
    """Create a temporary test PDF."""
    pdf_path = tmp_path / "template.pdf"
    _create_test_pdf(pdf_path)
    return str(pdf_path)


@pytest.fixture()
def test_csv(tmp_path):
    """Create a temporary test CSV."""
    csv_path = tmp_path / "recipients.csv"
    csv_path.write_text("name,position,email\nAlice,Lead,a@b.com\n")
    return str(csv_path)


@pytest.fixture()
def app_client(test_pdf, test_csv, tmp_path):
    """Create a Flask test client."""
    output_config = str(tmp_path / "config.json")
    app = create_app(
        template_pdf=test_pdf,
        recipients_file=test_csv,
        output_config=output_config,
    )
    app.config["TESTING"] = True
    with app.test_client() as client:
        yield client, output_config


class TestPixelToPdfCoords:
    """Test coordinate conversion."""

    def test_top_left_corner(self):
        """Top-left pixel maps to top-left PDF (0, page_height)."""
        x, y = pixel_to_pdf_coords(0, 0, 1224, 1584, 612, 792)
        assert x == 0.0
        assert y == 792.0

    def test_bottom_right_corner(self):
        """Bottom-right pixel maps to bottom-right PDF (page_width, 0)."""
        x, y = pixel_to_pdf_coords(1224, 1584, 1224, 1584, 612, 792)
        assert x == 612.0
        assert y == 0.0

    def test_center(self):
        """Center pixel maps to center PDF point."""
        x, y = pixel_to_pdf_coords(612, 792, 1224, 1584, 612, 792)
        assert x == 306.0
        assert y == 396.0

    def test_landscape_page(self):
        """Works with landscape dimensions."""
        x, y = pixel_to_pdf_coords(500, 300, 1000, 600, 842, 595)
        assert x == 421.0
        assert y == 297.5

    def test_rounding(self):
        """Values are rounded to 1 decimal place."""
        x, y = pixel_to_pdf_coords(100, 200, 1224, 1584, 612, 792)
        assert isinstance(x, float)
        assert isinstance(y, float)
        # Check that result has at most 1 decimal place
        assert x == round(x, 1)
        assert y == round(y, 1)


class TestRenderPdfPage:
    """Test PDF to PNG rendering."""

    def test_renders_png(self, test_pdf):
        """Should return valid PNG bytes."""
        png_bytes, w, h, pdf_w, pdf_h = render_pdf_page(test_pdf)
        assert len(png_bytes) > 0
        # PNG magic bytes
        assert png_bytes[:4] == b"\x89PNG"

    def test_dimensions(self, test_pdf):
        """Rendered dimensions should be scale * PDF dimensions."""
        _, w, h, pdf_w, pdf_h = render_pdf_page(test_pdf, scale=2.0)
        assert pdf_w == pytest.approx(612, abs=1)
        assert pdf_h == pytest.approx(792, abs=1)
        assert w == pytest.approx(612 * 2, abs=2)
        assert h == pytest.approx(792 * 2, abs=2)

    def test_custom_scale(self, test_pdf):
        """Different scale factor produces different pixel dimensions."""
        _, w1, h1, _, _ = render_pdf_page(test_pdf, scale=1.0)
        _, w2, h2, _, _ = render_pdf_page(test_pdf, scale=3.0)
        assert w2 > w1
        assert h2 > h1


class TestTemplateInfoRoute:
    """Test /api/template-info endpoint."""

    def test_returns_dimensions(self, app_client):
        client, _ = app_client
        resp = client.get("/api/template-info")
        assert resp.status_code == 200
        data = resp.get_json()
        assert "width_pt" in data
        assert "height_pt" in data
        assert "render_width_px" in data
        assert "render_height_px" in data
        assert data["width_pt"] == pytest.approx(612, abs=1)
        assert data["height_pt"] == pytest.approx(792, abs=1)


class TestCsvHeadersRoute:
    """Test /api/csv-headers endpoint."""

    def test_returns_headers_without_email(self, app_client):
        client, _ = app_client
        resp = client.get("/api/csv-headers")
        assert resp.status_code == 200
        headers = resp.get_json()
        assert headers == ["name", "position"]
        assert "email" not in headers

    def test_no_csv_returns_empty(self, test_pdf, tmp_path):
        """When no CSV is provided, returns empty list."""
        app = create_app(template_pdf=test_pdf)
        app.config["TESTING"] = True
        with app.test_client() as client:
            resp = client.get("/api/csv-headers")
            assert resp.status_code == 200
            assert resp.get_json() == []


class TestTemplateImageRoute:
    """Test /api/template-image endpoint."""

    def test_returns_png(self, app_client):
        client, _ = app_client
        resp = client.get("/api/template-image")
        assert resp.status_code == 200
        assert resp.content_type == "image/png"
        assert resp.data[:4] == b"\x89PNG"


class TestFontFamiliesRoute:
    """Test /api/font-families endpoint."""

    def test_returns_list(self, app_client):
        client, _ = app_client
        resp = client.get("/api/font-families")
        assert resp.status_code == 200
        fonts = resp.get_json()
        assert isinstance(fonts, list)
        assert "Helvetica" in fonts


class TestSaveRoute:
    """Test /api/save endpoint."""

    def test_saves_config(self, app_client):
        client, output_config = app_client
        fields = {
            "name": {
                "x": 300,
                "y": 400,
                "font_size": 36,
                "font_weight": "bold",
                "alignment": "center",
                "color": [0, 0, 0],
            }
        }
        resp = client.post(
            "/api/save",
            json={
                "font_family": "Helvetica",
                "output_directory": "local/outputs/fill-pdfs",
                "fields": fields,
            },
        )
        assert resp.status_code == 200
        data = resp.get_json()
        assert "saved" in data

        # Verify file was written
        saved = json.loads(Path(output_config).read_text())
        assert saved["font_family"] == "Helvetica"
        assert "name" in saved["fields"]
        assert saved["fields"]["name"]["x"] == 300
        assert saved["fields"]["name"]["y"] == 400

    def test_save_no_data(self, app_client):
        client, _ = app_client
        resp = client.post("/api/save", content_type="application/json")
        assert resp.status_code == 400


class TestPreviewRoute:
    """Test /api/preview endpoint."""

    def test_returns_png(self, app_client):
        client, _ = app_client
        fields = {
            "name": {
                "x": 300,
                "y": 400,
                "font_size": 36,
                "font_weight": "bold",
                "alignment": "center",
                "color": [0, 0, 0],
            }
        }
        resp = client.post(
            "/api/preview",
            json={
                "font_family": "Helvetica",
                "fields": fields,
                "sample_data": {"name": "John Doe"},
            },
        )
        assert resp.status_code == 200
        assert resp.content_type == "image/png"
        assert resp.data[:4] == b"\x89PNG"

    def test_preview_no_data(self, app_client):
        client, _ = app_client
        resp = client.post("/api/preview", content_type="application/json")
        assert resp.status_code == 400


class TestIndexRoute:
    """Test the main page route."""

    def test_serves_html(self, app_client):
        client, _ = app_client
        resp = client.get("/")
        assert resp.status_code == 200
        assert b"Certificate Field Picker" in resp.data
