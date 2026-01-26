# Code of Conduct

## Our Pledge

We as contributors and maintainers pledge to make participation in r10n a harassment-free experience for everyone, regardless of age, body size, disability, ethnicity, gender identity and expression, level of experience, nationality, personal appearance, race, religion, or sexual identity and orientation.

## Our Standards

### Positive Behavior

- Using welcoming and inclusive language
- Being respectful of differing viewpoints and experiences
- Gracefully accepting constructive criticism
- Focusing on what is best for the community
- Showing empathy towards other community members

### Unacceptable Behavior

- Trolling, insulting/derogatory comments, and personal or political attacks
- Public or private harassment
- Publishing others' private information without explicit permission
- Other conduct which could reasonably be considered inappropriate

## Development Standards

### Code Quality

1. **Type Hints Required**: All functions must have type hints
   ```python
   def process(data: list[str], config: dict[str, Any]) -> dict[str, int]:
   ```

2. **Docstrings Required**: All public functions must have Google-style docstrings
   ```python
   def function(arg: str) -> bool:
       """Short description.

       Args:
           arg: Description of argument

       Returns:
           Description of return value
       """
   ```

3. **Error Handling**: Use specific exceptions with helpful messages
   ```python
   if not path.exists():
       raise FileNotFoundError(f"Input file not found: {path}")
   ```

### Testing Requirements

- All automations must have tests in `tests/`
- Aim for >80% code coverage
- Run tests before committing: `uv run pytest`

### Commit Messages

Use conventional commits format:

```
<type>(<scope>): <description>
```

Types:
- `feat`: New feature
- `fix`: Bug fix
- `docs`: Documentation
- `refactor`: Code refactoring
- `test`: Adding tests
- `chore`: Maintenance

Examples:
```
feat(automations): add PDF merger automation
fix(contacts): handle international phone formats
docs(automations): add colors automation documentation
```

### Pull Request Process

1. Update documentation for any new features
2. Add tests for new functionality
3. Ensure all tests pass: `uv run pytest`
4. Ensure code passes linting: `uv run ruff check src tests`
5. Update CHANGELOG.md if applicable

## Enforcement

Project maintainers are responsible for clarifying standards and are expected to take appropriate action in response to any unacceptable behavior.

Maintainers have the right to remove, edit, or reject comments, commits, code, wiki edits, issues, and other contributions that do not align with this Code of Conduct.

## Attribution

This Code of Conduct is adapted from the [Contributor Covenant](https://www.contributor-covenant.org/), version 2.0.

## Contact

For questions about this Code of Conduct, open an issue at [GitHub Issues](https://github.com/pruthivithejan/r10n/issues).
