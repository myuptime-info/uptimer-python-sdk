"""
A fleet from one Template: create a website Resource per host, then read every
open Incident across the Workspace, page by page.

    UPTIMER_URL=http://127.0.0.1:8080/api UPTIMER_API_KEY=... python 02_large_fleet.py
"""

import os

from uptimer import UptimerClient, ValidationError

client = UptimerClient(
    api_key=os.environ["UPTIMER_API_KEY"],
    base_url=os.environ.get("UPTIMER_URL", "http://127.0.0.1:8080/api"),
)
ws = client.workspace(client.workspaces()[0].id)
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
