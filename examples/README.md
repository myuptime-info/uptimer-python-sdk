# Uptimer Python SDK Examples

Minimal examples for the Uptimer Python SDK. Each one is a single operation, as
short as it can be.

API v2 resources are reached through `client.v2`, and its types are imported from
`uptimer.models.v2` — the SDK keeps the API version visible because the API is
versioned by path. `client.version()` and the compatibility helpers stay on the
client itself, since `/version` is shared and unversioned.

## The examples

1. `01_client_setup.py` — create a client and confirm the server speaks API v2
2. `02_list_workspaces.py` — `client.v2.workspaces.all()`
3. `03_list_locations.py` — `client.v2.locations.all()`
4. `04_create_website_monitor.py` — `client.v2.monitoring.websites.create(...)`
5. `05_open_incidents.py` — `client.v2.incidents.all(workspace_id)`

## Usage

Replace the placeholders before running:

- `your-api-key-here` — an API key from the dashboard (**User → API Keys**)
- the `base_url` — `https://myuptime.info/api` for the hosted product, or your
  own instance's URL plus `/api`

## Running

```bash
uv run python examples/01_client_setup.py
uv run python examples/02_list_workspaces.py
# ... and so on
```
