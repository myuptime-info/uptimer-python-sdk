# Uptimer Python SDK

![Uptimer](https://static.myuptime.info/61uvxp/icon.png)

A Python SDK for uptimer - a monitoring and uptime checking service.
* [uptimer self-hosted](https://uptimer.myuptime.info)
* [myuptime.info](https://myuptime.info)

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

For third-party license information, see the [NOTICE](NOTICE) file.

## Installation 

```shell
pip install uptimer-python-sdk
```

or 
```shell
uv add uptimer-python-sdk
```

## Usage

### Create client

#### self-hosted

```python
from uptimer.client import UptimerClient
client = UptimerClient(
    api_key="your-api-key-here",
    base_url="http://127.0.0.1:2517/api",  # or your custom base URL
)
```

#### cloud  
```python
from uptimer.client import UptimerCloudClient
client = UptimerCloudClient(
    api_key="your-api-key-here",
)
```

### Basic example
```python
from uptimer.client import UptimerClient
from uptimer.models.rule import CreateRuleRequest, RuleRequest, RuleResponse, RuleResponseBody
from uptimer.errors import DefaultUptimerApiError, UptimerInvalidHttpCodeError, UptimerError
# Initialize the client
client = UptimerClient(
    api_key="your-api-key-here",
    base_url="http://127.0.0.1:2517/api",  # or your custom base URL
)
regions = client.v1.regions.all()
workspaces = client.v1.workspaces.all()
workspace_id = workspaces[0].id
rules =client.v1.rules.all(workspace_id)

new_rule = client.v1.rules.create(
    CreateRuleRequest(
        name="My Test Rule",
        interval=60,  # Check every 60 seconds
        workspace_id=workspace_id,
        request=RuleRequest(
            url="https://example.com",
            method="GET",  # PATCH, POST, HEAD
            content_type="application/json",  # expected content type
            data="",  # data (substring) that should be contained in resonse
        ),
        response=RuleResponse(
            statuses=[200, 201, 202],  # any of this status means site is up
            body=RuleResponseBody(content="expected response"),
        ),
    ),
)

new_rule_updated = client.v1.rules.update(
    new_rule.id,
    CreateRuleRequest(
        name="Updated Rule Name",
        interval=120,  # Change to 2 minutes
        workspace_id=workspace_id,
        request=RuleRequest(
            url="https://updated-example.com",
            method="POST",
            content_type="application/json",
            data='{"key": "value"}',
        ),
        response=RuleResponse(
            statuses=[200, 201],
            body=RuleResponseBody(content="updated expected response"),
        ),
    ),
)

# caching errors on delete example
try:
  client.v1.rules.delete(new_rule_updated.id)
except DefaultUptimerApiError as e:
  # error responses from uptimer server
  print(
    e.message,  # user message
    e.code,  # error id
    e.error_type,  # class of error,
    e.details,  # detailed message for a developer
  )
except UptimerInvalidHttpCodeError as e:
  # uptimer api always return 200, if not -> http transport error
  # for an example 404 status is really page (url) not found, it doesn't mean that an object with id not found.
  print(
    e.url,
    e.status_code,
  )
except UptimerError as e: # base error, if you need one
  raise
```

Also, check out [examples directory](https://github.com/myuptime-info/uptimer-python-sdk/examples)

### Development Setup

1. Clone the repository:

```bash
git clone <repository-url>
cd uptimer-python-sdk
```

2. Install dependencies:

```bash
uv sync --dev
# for integration tests
uv run playwright install chromium
```

3. Run tests:

```bash
uv run pytest
# integration
docker pull myuptime/uptimer
docker run -p 2517:2517 myuptime/uptimer
UPTIMER_URL=http://localhost:2517  uv run --integration
```

4. Run linting:

```bash
uv run ruff check .
uv run mypy src
```

5. Format code:

```bash
uv run ruff format .
```

6. Run pre-commit hooks:

```bash
uv run pre-commit run --all-files
```

## Third-Party Licenses

This project uses the following third-party libraries:

### Production Dependencies

- **httpx** (BSD 3-Clause License) - HTTP client for Python

### Development Dependencies

- **mypy** (Apache 2.0 License) - Static type checker
- **playwright** (Apache 2.0 License) - Browser automation
- **pre-commit** (MIT License) - Git hooks framework
- **pytest** (MIT License) - Testing framework
- **pytest-cov** (MIT License) - Coverage plugin for pytest
- **pytest-httpx** (MIT License) - HTTPX plugin for pytest
- **pytest-playwright** (MIT License) - Playwright plugin for pytest
- **responses** (Apache 2.0 License) - Mock library for requests
- **ruff** (MIT License) - Fast Python linter and formatter

All third-party licenses are compatible with the MIT License used by this project. Note that the BSD 3-Clause License (used by httpx) includes an additional restriction prohibiting the use of the copyright holder's name for endorsement without permission.
