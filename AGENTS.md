# AGENTS.md — uptimer-python-sdk

The public Python client for Uptimer. Fleet-wide rules apply (see the workspace
`AGENTS.md`): trunk-based on `main`, no agent attribution, Commitizen subjects.

## Documentation policy

**SDK docs describe only what this package implements.** That is all.

`README.md` (the PyPI long description), the docstrings under `src/`, and
`examples/` document capabilities present in **this package version**. No "not
wrapped yet", no checkout workarounds, no ticket numbers, no release
sequencing. A capability this package does not have is **omitted** — the
[REST documentation](https://uptimer.myuptime.info/latest/reference/rest-api/)
covers the HTTP API in full, and may be linked for that.

The same rule, in the form Cursor reads:
[`.cursor/rules/sdk-docs-implemented-only.mdc`](.cursor/rules/sdk-docs-implemented-only.mdc).

## Working here

```sh
task cq        # lint + type-check + tests (ruff, mypy, pytest)
task test      # pytest alone
task build     # sdist + wheel into dist/
```

- The package version tracks the Uptimer release it targets: 1.8.x speaks to
  Uptimer 1.8.0 and later. `uptimer.__version__` is where the compatibility
  minimum comes from, and `cz` bumps it with `pyproject.toml`.
- **Never publish a prerelease** (rc/a/b/dev) to TestPyPI or PyPI. This package
  ships final `X.Y.Z` only; publishing is an operator action.
