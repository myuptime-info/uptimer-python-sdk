# Uptimer Python SDK

A Python SDK for uptimer services.

## Installation

This project uses [uv](https://github.com/astral-sh/uv) for dependency management.

### Prerequisites

- Python 3.8 or higher
- uv (install with `pip install uv`)

### Development Setup

1. Clone the repository:
```bash
git clone <repository-url>
cd uptimer-python-sdk
```

2. Install dependencies:
```bash
uv sync --dev
```

3. Run tests:
```bash
uv run pytest
```

4. Run linting:
```bash
uv run ruff check .
```

5. Format code:
```bash
uv run ruff format .
```

6. Run pre-commit hooks:
```bash
uv run pre-commit run --all-files
```

## Project Structure

```
uptimer-python-sdk/
├── src/
│   └── uptimer_python_sdk/
│       ├── __init__.py
│       └── example.py
├── tests/
│   ├── __init__.py
│   └── test_example.py
├── pyproject.toml
└── README.md
```

## Development

- **Testing**: Uses pytest with coverage reporting
- **Linting**: Uses ruff with all rules enabled
- **Formatting**: Uses ruff formatter
- **Pre-commit hooks**: Automatically runs ruff check and format on commits
- **Build System**: Uses hatchling for package building

## License

[Add your license here] 