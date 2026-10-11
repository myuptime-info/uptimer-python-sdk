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
ws.resources.update("checkout-api", labels={"env": "prod", "team": None})  # set env, remove team
ws.resources.list(labels={"env": "prod"})   # also ws.incidents.list(labels=…)
ws.resources.list(missing="stale")          # a Signal with no usable reading: never_reported, stale, reported_no_data
ws.resources.list(missing=["never_reported", "stale"])
# A pushed-data Resource can move to another published pushed-data Template revision,
# keeping its id and key; its old Rules' open Incidents close as rule_removed.
# A Signal that keeps its key and kind keeps its history (baselines carry on);
# reset_history starts named Signals fresh when their meaning changed.
ws.resources.rebind("srv-0042", "service-triage@4", meta={"provider": "alpha"})
ws.resources.rebind("srv-0042", "service-triage@5", reset_history=["load"])
```

`resource.rules[i]` carries `status`, `explanation`, `since` and
`open_incident` once the Rule has decided. `routes` is where its Template
sends each Incident transition (a list of `Route(destination, on)`; `[]`
sends nothing), or `None` for a Rule that follows `destination`, then the
Resource's and the Workspace default. Routes are set in the Template manifest
you pass to `ws.templates.publish(manifest)`.

`resource.signals[i].applicability` is `"applicable"`, or `"not_applicable"`
where the Template's `applies_if` is false for this Resource (`.applicable`
is the same as a bool). A Signal that does not apply is not missing data and
not healthy evidence: no Rule reads it. `resource.signals[i].missing` is why a
Signal has no usable reading now — `"never_reported"`, `"stale"` (a heartbeat
silent for more than three of its periods) or `"reported_no_data"` — or `None`
where it has a current `ok` or `problem` reading, or does not apply.
`resource.signals[i].on_demand` is a Signal checked only when asked, and
`not_checked` is one nobody has asked for yet: it is not missing data and not
`no_data`, so its `missing` is `None`. A Signal applies only where its
manifest condition holds:

```python
{"key": "replication", "kind": "heartbeat", "every_seconds": 300,
 "applies_if": {"field": "role", "operator": "eq", "value": "replica"}}
```

### Confirmations

A Template Signal can ask for a second opinion before its `problem` is
believed. `ConfirmPolicy` writes that `"confirm"` policy, `Confirmer` one
confirmer (a built-in probe or a command name the worker defines), and `meta`
a value read from the Resource's own field. `Comparison` writes one
comparison of a composite Rule; `if_unknown=False` makes it false, rather than
unknown, when its Signal has no usable data (never reported, silent,
`no_data`, or an on-demand Signal not checked yet).

```python
from uptimer import Comparison, Confirmer, ConfirmPolicy, meta

policy = ConfirmPolicy(
    by=[Confirmer(probe="tcp", with_={"host": meta("host"), "port": 5432}),
        Confirmer(exec="check-replica", with_={"host": meta("host")})],
    refuted_if="any_ok",   # any ok refutes; "all_ok" needs every confirmer ok
    timeout=30,            # seconds, 5 to 600
)
manifest = {"key": "replica", "version": 1, "name": "Replica", "summary": "A replica.",
            "fields": [{"key": "host", "label": "Host", "type": "string"}],
            "signals": [{"key": "port", "kind": "event", "confirm": policy.to_api()},
                        {"key": "deep", "kind": "event", "on_demand": True}],
            "rules": [{"key": "down", "action": "Look at the replica.",
                       "wait": {"confirm_after": 0, "recover_after": 0},
                       "decision": {"any": [Comparison("port", "status", "eq", "problem").to_api(),
                                            Comparison("deep", "status", "eq", "problem",
                                                       if_unknown=False).to_api()]}}]}
template = ws.templates.publish(manifest)
template.confirm_policy("port")          # the same ConfirmPolicy, read back
```

Only a `problem` reading is confirmed; a `no_data` one is trusted as it is.
While a reading is being confirmed, Rules on that Signal hold. What was
decided reads back in three places. `status` is `pending`, `confirmed`,
`unconfirmed` or `not_run`. `reason` is `refuted`, `problem_confirmed`,
`timeout`, `confirmer_no_data`, `limited` or `source_no_data`. A refuted
problem reads `ok`; every other outcome keeps the original.

```python
signal = ws.resources.get("db-1").signals[0]
signal.confirmation        # SignalConfirmation(status, reason, effective, original), or None

row = ws.resources.observations("db-1", signal="port")[0]
row.state                  # the original reading, always
row.confirmation           # ObservationConfirmation: status, reason, effective, refuted_if,
                           # deadline, decided_at, and confirmers (probe or exec, state, value, reason, at)

incident = ws.incidents.get(incident_id)
for one in incident.history[0].inputs:   # the evidence a transition recorded, typed
    one.status, one.confirmation         # what the Rule read; EvidenceConfirmation(status, reason, original)
```

An Incident's own `confirmation` (`confirmed` once its Rule's `confirm_after`
has passed) is a different thing from a Signal's Confirmation.

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

A fleet sends many at once: up to 500 Observations, for any Resources, per
request. Each item is what `observe` sends plus `resource`; give each an `id`
so a retry stores nothing twice.

```python
items = [{"resource": key, "signal": "origin", "state": "ok", "id": f"round-118-{key}"}
         for key in fleet_keys]
for start in range(0, len(items), 500):
    result = ws.resources.observe_batch(items[start:start + 500])
    for item in result.results:
        if not item.accepted:
            print(items[start + item.index]["resource"], item.error["message"])
```

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

### Destinations

A full API key manages where alerts go. A destination's URL is written, never
read back.

```python
oncall = ws.destinations.create("oncall", type="slack", url="https://hooks.slack.com/services/…")
ws.destinations.create("ops", type="webhook", url="https://ops.example/hook", send_on_open=True)
ws.destinations.test(oncall.id)          # DestinationTest(status="delivered", reason=None)
ws.destinations.update(oncall.id, enabled=False)
page = ws.destinations.deliveries(oncall.id)   # event, status, reason code, incident
```

A Template Rule's routes may name a destination instead of its id; publishing
resolves it in that Workspace, so one manifest works in several:

```python
"routes": [{"destination": {"name": "oncall"}, "on": ["opened", "problem", "recovery"]}]
```

`ws.destinations.delete(id)` raises `ValidationError` (`details["used_by"]`)
while a live route still sends there.

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

## Examples

See [`examples/`](examples/): from a key to an Incident, a fleet from one
Template, a counted comparison, and Confirmations with on-demand and
`applies_if` Signals and missing-Signal causes.
