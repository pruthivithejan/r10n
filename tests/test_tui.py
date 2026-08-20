"""Headless interaction tests for the Textual r10n workspace."""

import asyncio

from textual.widgets import Static

from src.tui.app import R10nApp


class TestR10nTui:
    """Verify catalog discovery and generated forms."""

    def test_catalog_loads_schema_generated_form(self):
        """The first automation renders its registered input fields."""

        async def exercise() -> None:
            app = R10nApp("test")
            async with app.run_test(size=(120, 40)) as pilot:
                await pilot.pause()
                title = app.query_one("#automation-title", Static)

                assert app.current_automation_id == "contacts"
                assert str(title.content) == "Generate contacts"
                assert set(app._field_widgets) == {"input_file", "output_file", "prefix"}

        asyncio.run(exercise())

    def test_search_finds_automations_by_role(self):
        """Catalog search includes role metadata, not just titles."""

        async def exercise() -> None:
            app = R10nApp("test")
            async with app.run_test(size=(120, 40)) as pilot:
                await pilot.click("#search")
                await pilot.press(*"marketing")
                await pilot.pause()

                assert app.filtered_ids == [
                    "images",
                    "website-images",
                    "logos",
                    "rename",
                    "md2pdf",
                ]

        asyncio.run(exercise())
