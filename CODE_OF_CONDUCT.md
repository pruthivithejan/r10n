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

### untangle-codebase

Use this guideline when undertaking a codebase-wide refactor, optionally focused
on a particular area. Preserve observable behavior except for bugs fixed by the
structural changes. Work in small, independently verified units.

1. **Agree on scope.** In addition to untangling, ask whether to remove comments
   that only restate the code and whether to remove tests that cannot catch a
   real bug or repair tests that fail without one. Only perform the selected
   optional work.
2. **Audit before editing.** Record hidden dependencies, duplicated rules,
   implicit ordering and related code scattered across modules; unnecessary
   dependencies on internals or volatile details; and unused wrappers,
   extension points and dead code. Record special cases, including single-value
   branches, caller-specific parameters, swallowed exceptions, retries, sleeps
   and disabled tests. Check whether each serves a real requirement before
   changing it.
3. **Redesign around change.** Put rules that change together together, separate
   those that change independently, and depend on stable contracts. Document
   each proposed fix above the problems it addresses in a decision log. Use
   import graphs and Git history as evidence where useful. In Python, consider
   imports, module globals, protocols, and file paths; in Go, consider package
   dependencies, interfaces, exported APIs, and error handling.
4. **Implement and verify.** Apply the decisions in focused steps, retaining
   compatibility cases that remain necessary. Check behavior at each step and
   keep a regression safety net. If comment cleanup was selected, retain
   explanations of external constraints and remove comments made redundant by
   the code. If test cleanup was selected, do it last: retain tests that detect
   observable regressions and rewrite tests coupled to implementation details.
5. **Review again.** Re-examine the dependency graph and remaining special
   cases, involve independent reviewers or agents when available, and repeat
   for issues worth fixing. Run the relevant tests and verify the actual output
   before declaring the work complete.

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
