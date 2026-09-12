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
from uptimer.models.v2 import (
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

workspace = client.v2.workspaces.all()[0]
locations = [location.name for location in client.v2.locations.all()]

monitor = client.v2.monitoring.websites.create(
    CreateWebsiteMonitorRequest(
        name="Checkout API",
        interval=60,  # seconds between probes
        workspace_id=workspace.id,
        request=WebsiteMonitorRequest(
            url="https://checkout.example/health",
            method="GET",  # one of GET, POST, PATCH, OPTIONS
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

monitor = client.v2.monitoring.websites.update(
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
for incident in client.v2.incidents.all(workspace.id):
    print(incident.monitor_name, incident.status, incident.locations.failing)

try:
    client.v2.monitoring.websites.delete(monitor.id)
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

### Subjects: your custom monitoring

A **subject** is one monitored thing. Every subject is one of two kinds, and the
kind says how it is configured:

- **website** — Uptimer's own probe watches a URL, and the website check form
  owns its signal and its rule;
- **custom** — yours, reporting through the signals you add to it.

Uptimer 1.6.0 splits its API along that line, and so does this SDK: website
monitoring is `client.v2.monitoring.websites`, and `client.v2.subjects` is the
**custom** half. Neither serves the other's subjects — passing a website
subject's slug to a `subjects` call is refused.

Requires Uptimer 1.6.0 or later.

```python
from uptimer.client import UptimerClient
from uptimer.models.v2 import SUBJECT_KIND_CUSTOM, CreateSubjectRequest

client = UptimerClient(
    api_key="your-api-key-here",
    base_url="http://127.0.0.1:2517/api",
)

# The workspace's custom subjects. Website checks are not here.
for subject in client.v2.subjects.all("your-workspace-id"):
    print(subject.id, subject.subject_kind, subject.signal_count)

# Create an empty custom subject. It arrives with nothing under it: no signal,
# no rule, no HTTP probe — add a signal to it in the Uptimer UI, then report to
# that signal with the observations API below.
created = client.v2.subjects.create(
    CreateSubjectRequest(name="Nightly export", workspace_id="your-workspace-id"),
)
assert created.subject_kind == SUBJECT_KIND_CUSTOM
assert created.signal_count == 0

# `id` is the subject's slug — the same name the observation route addresses it
# by, and it never moves when the subject is renamed.
fetched = client.v2.subjects.get(created.id, workspace_id="your-workspace-id")
```

`kind` and `subject_kind` are different fields on purpose. `kind` is `"subject"`
on every one of these objects — it says what you are holding, the way every v2
object does. `subject_kind` says how the subject is configured, and against a
1.6.0 server everything these calls return reads `"custom"`; `is_custom` is the
typed way to read it. `SUBJECT_KIND_WEBSITE` and `is_website` stay in the model
for a payload from an older server.

**Website monitoring is not created here.** It needs a URL, an interval and
locations, so it has its own call — `client.v2.monitoring.websites.create` —
and asking for `subject_kind="website"` on this route is refused with a message
saying so.

**Signals and rules are added in the Uptimer UI.** Uptimer 1.6.0 also serves
them over the API, under `/v2/subjects/{subject}/signals` and
`/v2/subjects/{subject}/rules`; this SDK does not wrap those routes yet.

### Reporting your own observations

Uptimer probes websites itself. For anything else — a cron job, a queue worker,
a nightly export — you add a **custom signal** to a subject in the Uptimer UI
and report to it yourself.

Requires Uptimer 1.6.0 or later, and a **custom heartbeat or event** signal. The
platform HTTP signal of a website monitor is written by Uptimer's own probe and
refuses posted observations.

```python
from uptimer.client import UptimerClient
from uptimer.models.v2 import (
    OBSERVATION_STATUS_OK,
    OBSERVATION_STATUS_PROBLEM,
    CreateObservationRequest,
)

client = UptimerClient(
    api_key="your-api-key-here",
    base_url="http://127.0.0.1:2517/api",
)

# The two slugs are the address: the subject, and the signal within it. Both
# are shown on the signal's page in the Uptimer UI.
observations = client.v2.subjects("checkout-api").signals("worker-pulse").observations

# A heartbeat: "I ran, and I am fine."
stored = observations.create(CreateObservationRequest(status=OBSERVATION_STATUS_OK))

# Everything except status is optional.
stored = observations.create(
    CreateObservationRequest(
        status=OBSERVATION_STATUS_PROBLEM,
        observed_at="2026-08-30T12:00:00Z",  # RFC 3339; omit to mean "now"
        value=0.0,                            # optional numeric reading
        error="queue backlog over threshold",
        labels={"instance": "worker-3", "env": "prod"},
    ),
)

print(stored.accepted, stored.reject_reason)
```

`accepted` reports **acceptance, not health**: it says Uptimer stored the
observation and may evaluate it, not that anything is wrong or fine. Whether an
observation raises an incident is decided by a *rule* that selects the signal.

An observation Uptimer keeps but will not evaluate — one stamped too far in the
future, say — comes back with `accepted=False` and a `reject_reason` such as
`clock_skew`. It is **returned, not raised**: it was received. An exception
means nothing was stored.

Retries are safe. An observation is identified by its signal, its `observed_at`
and its labels, so re-sending the same one replaces it rather than counting
twice.

### Acknowledging an incident

**New in 1.7.0.** Acknowledging says a **person has seen** an open incident. It
changes nothing the engine decided — the verdict, the evidence, the close hold
and the alerting all carry on — and it is recorded once, with who and when.

Each kind of monitoring acknowledges through **its own family**, the same split
subjects follow: a website incident under its monitor on v1, a custom incident
under its subject on v2. Neither method falls back to the other, and there is no
kind-agnostic one: acknowledging is a claim about a specific incident, and an
SDK that guessed which family it belonged to could claim the wrong one.

**Availability.** These methods are part of the SDK's **1.7.0** release: they are
not in the published 1.6.0 package, so until 1.7.0 is on PyPI use them from a
checkout of this repository. They need a matching **Uptimer 1.7.0+** server —
the routes do not exist before that — and on
[myuptime.info](https://myuptime.info) they arrive when the hosted service picks
up the 1.7.0 API.

**Custom monitoring** — list the subject's open incidents, pick one, acknowledge
it by id:

```python
from uptimer.client import UptimerClient

client = UptimerClient(
    api_key="your-api-key-here",
    base_url="http://127.0.0.1:2517/api",
)

subject = client.v2.subjects("payments-worker", "your-workspace-id")

# Open incidents of this subject: all of them, newest trouble first. A subject
# can have one open per rule, so each names the rule that opened it.
open_incidents = subject.incidents.all()
for incident in open_incidents:
    print(incident.id, incident.rule_name, incident.status, incident.acknowledged)

# Nothing open is an ordinary answer, not an error.
if open_incidents:
    # Acknowledge the one you mean, by the id the listing gave you. No body and
    # no actor argument: the person recorded is the owner of the API key, at the
    # time of the call.
    target = open_incidents[0]
    record = subject.incidents(target.id).acknowledge()
    print(record.acknowledged_by, record.acknowledged_at, record.recorded)
```

**Website monitoring** — the ids come from the workspace incident list this SDK
has had since 1.5.0, which already names each incident's monitor:

```python
# An empty list means nothing is wrong: the loop simply does not run.
for incident in client.v2.incidents.all("your-workspace-id"):
    record = client.v1.rules(incident.monitor_id).incidents(incident.id).acknowledge()
    print(record.incident_id, record.acknowledged_by, record.recorded)
```

`client.v1` exists for this one route. This is still a v2 client — website
monitors are read and written through `client.v2.monitoring.websites` — but
Uptimer serves website acknowledgement under `/v1/rules/...`, because website
monitoring is v1's resource and custom monitoring is v2's.

What the answer says:

| field | meaning |
|---|---|
| `recorded` | whether **this call** wrote it. `False` means it was already acknowledged and nothing changed |
| `acknowledged_by` / `acknowledged_at` | the record — on a repeat, the **first** person's name and time, not yours |
| `status` | the incident's condition, unchanged by acknowledging it |
| `monitor_id` | set for a website incident; `None` for a custom one |
| `subject_id` / `rule_id` | set for a custom incident; `None` for a website one |
| `closed_at` | set if the incident had already closed |

**Repeating it is safe.** A second call adds no second history entry and returns
the original name and time with `recorded=False` — so a retry after a timeout is
not a second claim.

**Refusals are raised, never worked around.** A `DefaultUptimerApiError` means
the incident is not this parent's — another monitor's, another subject's,
another workspace's, or the other kind of monitoring. Nothing is retried through
the other family.

**Closing cuts both ways, and the two are different.** A **first**
acknowledgement of an incident that has already closed is refused
(`Incident is closed`): there is nothing left to be on, and anything open now is
a different incident. But an incident acknowledged **while it was open** keeps
that record after it closes, so asking again is not an error — it answers the
original name and time with `recorded=False` and `closed_at` set. The look did
happen.

### Incident status

`client.v2.incidents.all()` returns only **open** incidents. `status` carries the
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

**1.5.0 targets API v2 only.** Your existing 0.4.x code keeps working against
the server — API v1 is unchanged and supported — but it must stay on the 0.4.x
SDK. Pin `uptimer-python-sdk<1` if you are not ready to move.

What changed:

| 0.4.x (API v1) | 1.5.0 (API v2) |
|---|---|
| `client.v1.workspaces` | `client.v2.workspaces` |
| `client.v1.regions` | `client.v2.locations` |
| `client.v1.rules` | `client.v2.monitoring.websites` |
| `Region` | `Location` |
| `Rule`, `CreateRuleRequest` | `WebsiteMonitor`, `CreateWebsiteMonitorRequest` |
| `regions=[...]` | `locations=[...]` |
| — | `agreement="any"｜"majority"｜"all"` |
| — | `client.v2.incidents` |
| `from uptimer.models import …` | `from uptimer.models.v2 import …` |

**The version namespace stays, and now covers the types too.** As in 0.4.x,
resources sit under the API version that serves them — `client.v1.*` becomes
`client.v2.*`, not a bare `client.*` — and the models follow: import them from
`uptimer.models.v2`, not from `uptimer.models`. The HTTP API is versioned by
path, so the SDK shows the same thing rather than hiding it. There are no
root-level aliases for either surface, so a stale flat import fails loudly
instead of silently binding to the wrong thing.

The deserialization exceptions (`ModelError`, `TypeMismatchError`, …) stay on
`uptimer.models`: the same error is raised whichever API version produced the
payload, so versioning them would say something untrue.

Why `monitoring.websites` rather than `monitors`: website monitoring is a
built-in template, not the general model. Keeping the bare name free lets other
monitor types arrive later without renaming this one.

`client.version()`, `client.check_compatibility()` and
`client.ensure_compatible()` are unchanged and stay on the client itself —
`/version` is a shared global endpoint, not a versioned one, so it works against
any server, including one too old for the rest of this SDK.

**Why 1.5.0 and not 1.0.0:** the SDK's major.minor tracks the uptimer release it
targets, so the version is the compatibility statement — 1.5.x speaks to uptimer
1.5.0 and later. Patch numbers are independent, so an SDK fix can ship without a
server release.

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
