"""Tests for the declarative automation registry."""

import pytest
from pydantic import ValidationError

from src.automation_registry import get_automation, list_automations


class TestAutomationRegistry:
    """Verify registry metadata and validation contracts."""

    def test_ids_are_unique_and_role_aware(self):
        """Every automation has one stable id and at least one role."""
        automations = list_automations()
        ids = [automation.id for automation in automations]

        assert len(automations) == 10
        assert len(ids) == len(set(ids))
        assert all(automation.roles for automation in automations)

    def test_models_generate_form_ready_json_schema(self):
        """Every input model exports titled, described JSON Schema fields."""
        for automation in list_automations():
            schema = automation.input_model.model_json_schema()
            assert schema["properties"]
            for field_schema in schema["properties"].values():
                assert field_schema.get("title")
                assert field_schema.get("description")

    def test_constraints_are_enforced(self):
        """Registry validation rejects invalid interactive values."""
        images = get_automation("images")
        with pytest.raises(ValidationError):
            images.validate(
                {
                    "input_directory": "images",
                    "output_directory": "output",
                    "quality": 101,
                    "max_size_mb": 1,
                    "prefix": "img",
                    "preserve_filenames": True,
                }
            )

    def test_unknown_automation_has_helpful_error(self):
        """Unknown registry identifiers fail explicitly."""
        with pytest.raises(KeyError, match="Unknown automation"):
            get_automation("not-real")
