"""
Synthetic service triage with a counted load gate: one low reading cannot decide access loss.

Publishes a workerless Template whose `access_loss` and `probe_issue` Rules judge the latest
three distinct traffic readings within fifteen minutes, creates one server by its own key,
pushes one round (no verdict), then two more (access_loss opens). The Rules' confirmation
and recovery waits apply after the count, as always.

    UPTIMER_URL=http://localhost:8080/api UPTIMER_API_KEY=<full key> python 03_field_triage_counted.py
"""

from __future__ import annotations

import os
import time
import uuid

from uptimer import ConflictError, UptimerClient

KEY = "service-triage-counted"


def status(signal: str, state: str) -> dict:
    return {"signal": signal, "field": "status", "operator": "eq", "operand": state}


def traffic(operator: str) -> dict:
    # The latest three readings within 900 seconds decide: all low or all high.
    # Mixed, fewer, or no_data stays unknown, so access_loss and probe_issue never both hold.
    return {"signal": "load_ratio", "field": "value", "operator": operator,
            "operand": {"meta": "load_threshold"}, "min_count": 3, "within_seconds": 900}


MANIFEST = {
    "key": KEY, "version": 1, "name": "Synthetic service triage (counted traffic)",
    "summary": "Access loss, service failure, or probe fault from pushed checks; traffic needs three readings.",
    "fields": [{"key": "load_threshold", "label": "Traffic ratio threshold", "type": "number",
                "default": 0.5, "min": 0}],
    "signals": [{"key": key, "kind": "heartbeat", "every_seconds": 300}
                for key in ("probe_a", "probe_b", "origin", "service_health", "load_ratio")],
    "rules": [
        {"key": "access_loss", "action": "Investigate the access path.",
         "wait": {"confirm_after": 600, "recover_after": 600},
         "decision": {"all": [status("probe_a", "problem"), status("probe_b", "problem"),
                              status("origin", "ok"), status("service_health", "ok"), traffic("lt")]}},
        {"key": "service_down", "action": "Investigate the service.",
         "wait": {"confirm_after": 0, "recover_after": 300},
         "decision": {"any": [status("origin", "problem"), status("service_health", "problem")]}},
        {"key": "probe_issue", "action": "Inspect the probe.",
         "wait": {"confirm_after": 0, "recover_after": 0},
         "decision": {"all": [{"any": [status("probe_a", "problem"), status("probe_b", "problem")]},
                              status("origin", "ok"), status("service_health", "ok"), traffic("gte")]}},
    ],
}


def push(ws, server: str, ratio: float) -> None:
    """One round of what the organization's database knows: probes down, host fine, traffic low."""
    for signal, state in (("probe_a", "problem"), ("probe_b", "problem"), ("origin", "ok"), ("service_health", "ok")):
        ws.resources.observe(server, signal=signal, state=state)
    ws.resources.observe(server, signal="load_ratio", state="ok", value=ratio)


def access_loss(ws, server: str):
    rule = next(r for r in ws.resources.get(server).rules if r.key == "access_loss")
    open_ = [i for i in ws.resources.incidents(server).items if i.rule == "access_loss"]
    return rule, open_


client = UptimerClient(api_key=os.environ["UPTIMER_API_KEY"], base_url=os.environ["UPTIMER_URL"])
client.check_compatibility()
ws = client.workspace(client.workspaces()[0].id)

try:
    ws.templates.publish(MANIFEST)
    print(f"published {KEY}@1")
except ConflictError:
    print(f"{KEY}@1 is already published")

server = f"srv-{uuid.uuid4().hex[:6]}"
ws.resources.create(template=KEY, key=server, name=server, meta={})

push(ws, server, 0.1)
time.sleep(35)  # Uptimer judges a burst of pushes within about half a minute.
rule, incidents = access_loss(ws, server)
print(f"after one reading:    access_loss {rule.status} — {rule.explanation}; incidents: {len(incidents)}")

for _ in range(2):
    push(ws, server, 0.1)
    time.sleep(2)
time.sleep(35)
rule, incidents = access_loss(ws, server)
print(f"after three readings: access_loss {rule.status} — {rule.explanation}")
for incident in incidents:
    print(f"  incident {incident.id}: {incident.lifecycle}, {incident.confirmation} — {incident.action}")
