"""Homepage automation cards stay in sync with the shared registry."""

from r10n_backend.registry import list_automations
from scripts import render_home_automations


def test_generated_cards_are_current() -> None:
    """The committed fragment matches the registry renderer."""
    assert (
        render_home_automations.FRAGMENT.read_text(encoding="utf-8")
        == render_home_automations.render_cards()
    )


def test_every_automation_has_a_docs_slug() -> None:
    """No registered automation is silently dropped from the homepage."""
    missing = {automation.id for automation in list_automations()} - set(
        render_home_automations.DOC_SLUGS
    )
    assert not missing
