"""
A fleet from one Template: create a website Resource per host, then read every
open Incident across the Workspace, page by page.

    UPTIMER_URL=http://127.0.0.1:8080/api UPTIMER_API_KEY=... python 02_large_fleet.py
"""

import os
import sys

from uptimer import UptimerClient, ValidationError

def chosen_workspace(client):
    """The Workspace UPTIMER_WORKSPACE names (its id or name), or the only one this key reaches."""
    want = os.environ.get("UPTIMER_WORKSPACE", "")
    reachable = client.workspaces()
    matching = [w for w in reachable if want in (w.id, w.name)] if want else reachable
    if len(matching) != 1:
        choices = ", ".join(f"{w.id} ({w.name})" for w in reachable)
        problem = f"no single Workspace is called {want!r}" if want else f"this key reaches {len(reachable)} Workspaces"
        sys.exit(f"{problem}; set UPTIMER_WORKSPACE to one of: {choices}")
    return client.workspace(matching[0].id)


client = UptimerClient(
    api_key=os.environ["UPTIMER_API_KEY"],
    base_url=os.environ.get("UPTIMER_URL", "http://127.0.0.1:8080/api"),
)
ws = chosen_workspace(client)
locations = [location.id for location in client.locations()]

hosts = [f"shop-{n:03d}.example.com" for n in range(1, 51)]
existing = {resource.key for resource in ws.resources.list()}

for host in hosts:
    key = host.split(".")[0]
    if key in existing:
        continue
    try:
        ws.resources.create(
            template="website-check",
            key=key,
            name=host,
            meta={"url": f"https://{host}/health", "locations": locations,
                  "interval_value": 1, "interval_unit": "MINUTE",
                  "failure_mode": "majority", "confirm_after": 120, "recover_after": 120},
        )
    except ValidationError as refused:
        print(f"{host}: {refused.field}: {refused.message}")

print(len(ws.resources.list()), "resources")

open_incidents = list(ws.incidents.iterate(lifecycle="open", limit=100))
print(len(open_incidents), "open incidents")
for incident in open_incidents:
    print(f"  {incident.resource.key}: {incident.condition} since {incident.opened_at:%H:%M} - {incident.explanation}")
