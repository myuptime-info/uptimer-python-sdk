# Uptimer Python SDK

A Python SDK for hosted and self-hosted Uptimer.

* [Hosted Uptimer](https://myuptime.info)
* [Self-hosted documentation](https://uptimer.myuptime.info)
* [PyPI package](https://pypi.org/project/uptimer-python-sdk/)
* [Uptimer resources](https://myuptime.info/resources)
* [Product updates](https://myuptime.info/product-updates)

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
from uptimer.errors import (
    DefaultUptimerApiError,
    IncompatibleServerError,
    UptimerError,
    UptimerInvalidHttpCodeError,
)
from uptimer.models import (
    AGREEMENT_MAJORITY,
    CreateWebsiteMonitorRequest,
    UpdateWebsiteMonitorRequest,
    WebsiteMonitorRequest,
    WebsiteMonitorResponse,
    WebsiteMonitorResponseBody,
)

client = UptimerClient(
    api_key="your-api-key-here",
    base_url="http://127.0.0.1:2517/api",  # or your custom base URL
)

# Optional: fail fast with a message that names the fix, rather than a 404 on
# the first real call.
print("server:", client.check_compatibility())

workspace = client.workspaces.all()[0]
locations = [location.name for location in client.locations.all()]

monitor = client.monitoring.websites.create(
    CreateWebsiteMonitorRequest(
        name="Checkout API",
        interval=60,  # seconds between probes
        workspace_id=workspace.id,
        request=WebsiteMonitorRequest(
            url="https://checkout.example/health",
            method="GET",  # PATCH, POST, HEAD
            content_type="application/json",
            data="",
        ),
        response=WebsiteMonitorResponse(
            statuses=[200, 201],  # any of these means the site is up
            body=WebsiteMonitorResponseBody(content="ok"),  # expected substring
        ),
        locations=locations,
        # How many locations must report a problem before this monitor does:
        # "any", "majority" or "all". Omit to keep the server default.
        agreement=AGREEMENT_MAJORITY,
    ),
)

monitor = client.monitoring.websites.update(
    monitor.id,
    UpdateWebsiteMonitorRequest(
        name="Checkout API",
        interval=120,
        request=WebsiteMonitorRequest(url="https://checkout.example/health", method="GET"),
        response=WebsiteMonitorResponse(statuses=[200]),
        locations=locations,
        # Omitting agreement here keeps the stored one.
    ),
)

# What is wrong right now. Only open incidents come back.
for incident in client.incidents.all(workspace.id):
    print(incident.monitor_name, incident.status, incident.locations.failing)

try:
    client.monitoring.websites.delete(monitor.id)
except DefaultUptimerApiError as e:
    # error responses from the uptimer server
    print(
        e.message,  # user message
        e.code,  # error id
        e.error_type,  # class of error
        e.details,  # detailed message for a developer
    )
except IncompatibleServerError as e:
    # the server does not provide API v2 — see Migrating from 0.4.x below
    print(e)
except UptimerInvalidHttpCodeError as e:
    # the uptimer api always returns 200; anything else is a transport error.
    # a 404 really is "no such URL", not "no object with that id".
    print(e.url, e.status_code)
except UptimerError:  # base error, if you need one
    raise
```

### Incident status

`client.incidents.all()` returns only **open** incidents. `status` carries the
same words the Uptimer screens show, so a client and the UI cannot disagree:

| status | meaning |
|---|---|
| `problem` | confirmed, and notifications have gone out |
| `pending` | failing, but inside the confirm hold — **nobody has been notified yet** |
| `recovering` | reporting ok again while the incident is still open |
| `no_data` | nothing usable arrived; a silent location counts toward the agreement |
| `ok` | healthy |

`locations.failing` / `.unknown` / `.ok` is the evidence the verdict was taken
from. A location that has never reported stays in `unknown` — that is a real
state, not a missing one.

### Migrating from 0.4.x

**1.0.0 targets API v2 only.** Your existing 0.4.x code keeps working against
the server — API v1 is unchanged and supported — but it must stay on the 0.4.x
SDK. Pin `uptimer-python-sdk<1` if you are not ready to move.

What changed:

| 0.4.x (API v1) | 1.0.0 (API v2) |
|---|---|
| `client.v1.workspaces` | `client.workspaces` |
| `client.v1.regions` | `client.locations` |
| `client.v1.rules` | `client.monitoring.websites` |
| `Region` | `Location` |
| `Rule`, `CreateRuleRequest` | `WebsiteMonitor`, `CreateWebsiteMonitorRequest` |
| `regions=[...]` | `locations=[...]` |
| — | `agreement="any"｜"majority"｜"all"` |
| — | `client.incidents` |

Why `monitoring.websites` rather than `monitors`: website monitoring is a
built-in template, not the general model. Keeping the bare name free lets other
monitor types arrive later without renaming this one.

`client.version()` is unchanged — `/version` is a shared global endpoint, not a
versioned one, so it works against any server, including one too old for the
rest of this SDK.

Also, check out the [examples directory](https://github.com/myuptime-info/uptimer-python-sdk/tree/main/examples).

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
docker pull ghcr.io/myuptime-info/uptimer:1.3.0
docker run -p 2517:2517 ghcr.io/myuptime-info/uptimer:1.3.0
UPTIMER_URL=http://localhost:2517 uv run --integration
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
