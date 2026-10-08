# Uptimer Python SDK

A Python client for the Uptimer 2.0 API (v3): Resources, Templates,
Observations, Incidents, maintenance and acknowledgement.

* [Self-hosted documentation](https://uptimer.myuptime.info)

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

For third-party license information, see the [NOTICE](NOTICE) file.

## Installation

```shell
pip install uptimer-python-sdk
```

**This package speaks API v3 and targets Uptimer 2.0.0 and later.** Its
major.minor tracks the server release it speaks to.
`client.check_compatibility()` fails with `IncompatibleServerError` against a
server that does not serve API v3.

## Usage

```python
from uptimer import UptimerClient

client = UptimerClient(
    api_key="your-api-key",                 # User → API keys
    base_url="http://127.0.0.1:8080/api",   # your server, plus /api
)
client.check_compatibility()
```

The key is a person's key: it reads and writes what that person may in each
Workspace. A viewer reads; changing a Workspace is an editor's or an owner's;
any member may acknowledge an Incident.

### Workspaces, Templates, Locations

```python
client.workspaces()   # [Workspace(id, name, role)]
client.create_workspace("Field iteration 2")  # Workspace(id, name, role="owner"); a full key only
client.templates()    # the Templates this server publishes, with their fields
client.locations()    # [Location(id, name)]
ws = client.workspace("<workspace id>")
```

### Resources

A Resource is addressed by its `id` or by its `key`.

```python
resource = ws.resources.create(
    template="website-check",
    key="checkout-api",
    name="Checkout API",
    meta={"url": "https://checkout.example.com/health", "locations": [location_id],
          "interval_value": 5, "interval_unit": "MINUTE",
          "failure_mode": "at_least_one", "confirm_after": 0, "recover_after": 0},
)
ws.resources.list()
ws.resources.get("checkout-api")      # with signals, rules and each rule's latest result
ws.resources.update("checkout-api", name="Checkout", meta={"confirm_after": 60})
# A pushed-data Resource can move to another published pushed-data Template revision,
# keeping its id and key; its old Rules' open Incidents close as rule_removed.
ws.resources.rebind("srv-0042", "service-triage@4", meta={"provider": "alpha"})
```

`resource.rules[i]` carries `status`, `explanation`, `since` and
`open_incident` once the Rule has decided. `routes` is where its Template
sends each Incident transition (a list of `Route(destination, on)`; `[]`
sends nothing), or `None` for a Rule that follows `destination`, then the
Resource's and the Workspace default. Routes are set in the Template manifest
you pass to `ws.templates.publish(manifest)`.

### Observations

```python
ws.resources.observe("checkout-api", signal=resource.signals[0].key,
                     state="problem", labels={"status": "503"},
                     reason="upstream answered 503")   # kept with the evidence and alert; cut at 200
ws.resources.observations("checkout-api", limit=20)   # newest first
```

`state` is `ok` or `problem`. The same `observation_id` sent twice is stored
once. The observation log is investigation context, not a record of what a
decision read.

### Incidents

```python
page = ws.incidents.list(lifecycle="open", limit=50)        # newest first
page.next_cursor                                            # None on the last page
ws.incidents.list(resource="checkout-api", rule="availability",
                  lifecycle="closed", confirmation="unconfirmed")
ws.incidents.list(lifecycle="open", acknowledged=False, rule="availability")  # what still needs action
for incident in ws.incidents.iterate(lifecycle="open"):     # every page
    ...
incident = ws.incidents.get(incident_id)                    # with ordered history
ws.incidents.acknowledge(incident_id)
ws.resources.incidents("checkout-api")                      # one Resource's Incidents
```

An `Incident` has `lifecycle` (open, closed), `confirmation` (confirmed,
unconfirmed), `condition` (ok, problem, no_data), the `rule` it was recorded
with, `explanation`, `opened_at`, `confirmed_at`, `closed_at`, `effective_at`,
`closed_reason` (recovered, rule_removed) and `acknowledgement`. Its `history`
is oldest first, and stays after its Rule is edited or removed.

### Maintenance

```python
ws.resources.set_maintenance("checkout-api", minutes=60)   # holds notifications
ws.resources.end_maintenance("checkout-api")
```

### Errors

Every refusal raises a subclass of `UptimerApiError` with `code`,
`error_type`, `message`, `details` and the HTTP `status`:

| Exception | Code | When |
|---|---|---|
| `BadRequestError` | 1400 | the request could not be read |
| `AuthenticationError` | 1401 | no API key, or one the server does not accept |
| `ForbiddenError` | 1403 | your role does not allow this write |
| `NotFoundError` | 1404 | no such thing in this Workspace, or no such Workspace for you |
| `ConflictError` | 1409 | e.g. acknowledging a closed or already acknowledged Incident |
| `ValidationError` | 1422 | a field was refused; `.field` names it |
| `ServerError` | 1500 | the server failed |

### Server 2.0.0-rc5

`resource.rules[i].routes` reads a Rule's notification routes (`Route(destination, on)`).
Routes themselves are set in the Template manifest passed to
`ws.templates.publish(manifest)`; no new client method is needed. Known
predicates (rc4) and the `opened` webhook opt-in (UI) need none either.

## Examples

See [`examples/`](examples/): from a key to an Incident, and a fleet from one
Template.
