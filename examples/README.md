# Uptimer Python SDK examples

Each example is a complete script. Set two variables and run it:

```bash
export UPTIMER_URL=http://127.0.0.1:8080/api   # your server, plus /api
export UPTIMER_API_KEY=...                       # User → API keys
python examples/01_quickstart.py
```

1. `01_quickstart.py` — from an API key to an Incident: create a Resource from
   the website Template, send it an Observation, read the Rule's result and
   the Incident with its history.
2. `02_large_fleet.py` — one website Resource per host from the same Template,
   then every open Incident in the Workspace, page by page.

The website Template needs at least one Location on the server
(Server → Locations).
