# Uptimer Python SDK examples

Each example is a complete script. Set two variables and run it:

```bash
export UPTIMER_URL=http://127.0.0.1:8080/api   # your server, plus /api
export UPTIMER_API_KEY=...                       # User → API keys
# export UPTIMER_WORKSPACE=...                   # its id or name; only when the key reaches several
python examples/01_quickstart.py
```

With more than one reachable Workspace and no `UPTIMER_WORKSPACE`, an example stops before it
writes anything and lists the Workspaces to choose from.

1. `01_quickstart.py` — from an API key to an Incident: create a Resource from
   the website Template, send it an Observation, read the Rule's result and
   the Incident with its history.
2. `02_large_fleet.py` — one website Resource per host from the same Template,
   then every open Incident in the Workspace, page by page.
3. `03_field_triage_counted.py` — publish a workerless Template whose traffic
   comparison needs three distinct readings within fifteen minutes, push one
   round (no verdict) and then two more (`access_loss` opens, with its action). Needs
   a full key of a Workspace editor; no Location.
4. `04_confirmations.py` — publish a synthetic replica Template with a
   confirmed port Signal, an on-demand check read with `if_unknown: false`, and
   a Signal that `applies_if` the role is replica; create a primary and a
   replica, push a problem, and read each Signal's applicability, missing
   cause, `not_checked` and confirmation. Running the probe needs an Uptimer
   worker; without one the confirmation stays `pending`, and `unconfirmed` /
   `timeout` after 30 seconds. Needs a full key of a Workspace editor.

The website Template needs at least one Location on the server
(Server → Locations).
