# Agents documentation and automated doc workflow

This document captures how agents (automations) should be documented, updated,
and how the documentation site should be updated when a new automation is
added. The intent is that agents (automated processes or developer assistants)
can read and re-use this guidance to keep docs accurate.

Principles
- Every automation must have a dedicated doc under `docs/automations/`.
- The automations index `docs/automations/index.md` must include a card for the
  automation outlining its short description, icon, and link to the doc.
- `zensical.toml` navigation must list the new automation file under the
  `Automations` section so it appears in the site sidebar.

Required files when adding an automation
1. Script under `scripts/` (e.g. `scripts/convert_css_colors_to_oklch.py`).
2. Doc under `docs/automations/` named after the automation (e.g. `colors.md`).
3. Update `docs/automations/index.md` to include a card with icon and short blurb.
4. Add the doc to `zensical.toml` navigation under the `Automations` section.

Docs conventions
- Page front matter should include an `icon:` key (Material icon name) where
  possible.
- Provide a one-line summary, usage examples, and limitations section.
- Include the path to the script and any CLI flags.

Automated doc workflow (for agents)
1. When a new automation is created, create the doc file and add it to
   `docs/automations/` using the doc template.
2. Insert an entry into `docs/automations/index.md` with an icon card.
3. Update `zensical.toml` navigation so the automation appears in the sidebar.
4. Commit changes with a concise message like `docs(automations): add <name> automation`.
5. Optionally open a PR to allow human review.

How agents can re-run this process
- Agents should search the repo for `scripts/` files with CLI-like headers
  (e.g. `if __name__ == '__main__'`) and propose doc stubs.
- Agents must not overwrite existing documentation without a human confirm step.

Reading this file
- Agents should read `AGENTS.md` to understand how to update docs and site
  configuration when automations are added.
