"""
From an API key to an Incident: create a Resource, send it an Observation,
read the Rule's result and the Incident it opened.

    UPTIMER_URL=http://127.0.0.1:8080/api UPTIMER_API_KEY=... python 01_quickstart.py

A key that reaches more than one Workspace needs UPTIMER_WORKSPACE (its id or name).

The server needs one Location (Server → Locations) for the website Template.
"""

import os
import sys
import time

from uptimer import NotFoundError, UptimerClient

def chosen_workspace(client):
    """The Workspace UPTIMER_WORKSPACE names (its id or name), or the only one this key reaches."""
    want = os.environ.get("UPTIMER_WORKSPACE", "")
    reachable = client.workspaces()
    matching = [w for w in reachable if want in (w.id, w.name)] if want else reachable
    if len(matching) != 1:
        choices = ", ".join(f"{w.id} ({w.name})" for w in reachable)
        problem = f"no single Workspace is called {want!r}" if want else f"this key reaches {len(reachable)} Workspaces"
        sys.exit(f"{problem}; set UPTIMER_WORKSPACE to one of: {choices}")
    return matching[0]


client = UptimerClient(
    api_key=os.environ["UPTIMER_API_KEY"],
    base_url=os.environ.get("UPTIMER_URL", "http://127.0.0.1:8080/api"),
)
print("server", client.check_compatibility())

workspace = chosen_workspace(client)
ws = client.workspace(workspace.id)
location = client.locations()[0]
print(f"workspace {workspace.name} ({workspace.id}), location {location.name}")

# A Resource from the website Template. Its key is the handle you use from now on.
try:
    resource = ws.resources.get("checkout-api")
except NotFoundError:
    resource = ws.resources.create(
        template="website-check",
        key="checkout-api",
        name="Checkout API",
        meta={
            "url": "https://checkout.example.com/health",
            "locations": [location.id],
            "interval_value": 5,
            "interval_unit": "MINUTE",
            "failure_mode": "at_least_one",
            "confirm_after": 0,
            "recover_after": 0,
        },
    )
signal = resource.signals[0]
rule = resource.rules[0]
print(f"resource {resource.key} ({resource.id}): signal {signal.key}, rule {rule.key}")

# One Observation: the check failed.
observed = ws.resources.observe(resource.key, signal=signal.key, state="problem", labels={"status": "503"})
print("observation", observed.observation)

# The server judges it within a moment.
for _ in range(20):
    rule = ws.resources.get(resource.key).rules[0]
    if rule.open_incident:
        break
    time.sleep(0.5)
print(f"rule {rule.key}: {rule.status} - {rule.explanation}")

incident = ws.incidents.get(rule.open_incident)
print(f"incident {incident.id}: {incident.lifecycle}, {incident.confirmation}, {incident.condition}")
for step in incident.history:
    print(f"  {step.at:%H:%M:%S} {step.kind:<16} {step.explanation}")
