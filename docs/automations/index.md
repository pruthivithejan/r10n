---
icon: lucide/wand-sparkles
---

# Automations

All r10n automations are listed below. Click any card to view the full guide with copy-paste examples.

---

<div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(215px, 1fr)); gap: 1.7rem 1rem;">

<a href="contacts/" style="text-decoration:none; border:1px solid var(--md-default-fg-color--lightest); border-radius:1rem; padding:1.15rem 1rem; display:flex; flex-direction:column; align-items:center; background:var(--md-accent-fg-color--lightest)">
  <span class="twemoji" style="font-size:2rem;">:lucide-book-user:</span>
  <span style="font-weight:600; margin-top:.5em;">Contacts</span>
  <span style="font-size:.9em; margin-top:4px; color:var(--md-default-fg-color--light); text-align:center;">Generate VCF contact cards from phone numbers</span>
</a>

<a href="certificates/" style="text-decoration:none; border:1px solid var(--md-default-fg-color--lightest); border-radius:1rem; padding:1.15rem 1rem; display:flex; flex-direction:column; align-items:center; background:var(--md-primary-fg-color--lightest)">
  <span class="twemoji" style="font-size:2rem;">:lucide-file-text:</span>
  <span style="font-weight:600; margin-top:.5em;">Certificates</span>
  <span style="font-size:.9em; margin-top:4px; color:var(--md-default-fg-color--light); text-align:center;">Create personalized PDF certificates from templates</span>
</a>

<a href="images/" style="text-decoration:none; border:1px solid var(--md-default-fg-color--lightest); border-radius:1rem; padding:1.15rem 1rem; display:flex; flex-direction:column; align-items:center; background:var(--md-accent-fg-color--lightest)">
  <span class="twemoji" style="font-size:2rem;">:lucide-image:</span>
  <span style="font-weight:600; margin-top:.5em;">Images</span>
  <span style="font-size:.9em; margin-top:4px; color:var(--md-default-fg-color--light); text-align:center;">Optimize and convert images to WebP format</span>
</a>

<a href="email/" style="text-decoration:none; border:1px solid var(--md-default-fg-color--lightest); border-radius:1rem; padding:1.15rem 1rem; display:flex; flex-direction:column; align-items:center; background:var(--md-primary-fg-color--lightest)">
  <span class="twemoji" style="font-size:2rem;">:lucide-mail:</span>
  <span style="font-weight:600; margin-top:.5em;">Email</span>
  <span style="font-size:.9em; margin-top:4px; color:var(--md-default-fg-color--light); text-align:center;">Send bulk personalized emails with attachments</span>
</a>

<a href="colors/" style="text-decoration:none; border:1px solid var(--md-default-fg-color--lightest); border-radius:1rem; padding:1.15rem 1rem; display:flex; flex-direction:column; align-items:center; background:var(--md-accent-fg-color--lightest)">
  <span class="twemoji" style="font-size:2rem;">:lucide-palette:</span>
  <span style="font-weight:600; margin-top:.5em;">Colors</span>
  <span style="font-size:.9em; margin-top:4px; color:var(--md-default-fg-color--light); text-align:center;">Convert CSS color codes to oklch() format</span>
</a>

</div>

---

## Quick Reference

| Automation | Command | Description |
|------------|---------|-------------|
| [Contacts](contacts/) | `r10n contacts` | Generate VCF from phone numbers |
| [Certificates](certificates/) | `r10n certificates` | Create PDF certificates |
| [Images](images/) | `r10n images` | Optimize images to WebP |
| [Email](email/) | `r10n email` | Send bulk emails |
| [Colors](colors/) | `r10n colors` | Convert CSS to oklch() |

---

## Run Any Automation Instantly

No installation required:

```bash
uvx --from git+https://github.com/pruthivithejan/r10n.git r10n <command>
```

**Examples:**

```bash
# Generate contacts
uvx --from git+https://github.com/pruthivithejan/r10n.git r10n contacts

# Optimize images
uvx --from git+https://github.com/pruthivithejan/r10n.git r10n images

# See all commands
uvx --from git+https://github.com/pruthivithejan/r10n.git r10n --help
```

---

## Want More Automations?

[Open an issue](https://github.com/pruthivithejan/r10n/issues) or [contribute on GitHub](https://github.com/pruthivithejan/r10n)!
