"""
Field triage with a counted traffic gate: one low traffic reading cannot ban a server.

Publishes a workerless Template whose `banned` and `checker_issue` Rules judge the latest
three distinct traffic readings within fifteen minutes, creates one server by its own key,
pushes one round (no verdict), then two more (banned opens). The Rules' confirmation
and recovery waits apply after the count, as always.

    UPTIMER_URL=http://localhost:8080/api UPTIMER_API_KEY=<full key> python 03_field_triage_counted.py
"""

from __future__ import annotations

import os
import time
import uuid

from uptimer import ConflictError, UptimerClient

KEY = "fleet-triage-counted"


def status(signal: str, state: str) -> dict:
    return {"signal": signal, "field": "status", "operator": "eq", "operand": state}


def traffic(operator: str) -> dict:
    # The latest three readings within 900 seconds decide: all low or all high.
    # Mixed, fewer, or no_data stays unknown, so banned and checker_issue never both hold.
    return {"signal": "traffic_ratio", "field": "value", "operator": operator,
            "operand": {"meta": "ratio_threshold"}, "min_count": 3, "within_seconds": 900}


MANIFEST = {
    "key": KEY, "version": 1, "name": "Fleet server triage (counted traffic)",
    "summary": "Banned, dead or checker issue from pushed checks; traffic needs three readings.",
    "fields": [{"key": "ratio_threshold", "label": "Traffic ratio threshold", "type": "number",
                "default": 0.5, "min": 0}],
    "signals": [{"key": key, "kind": "heartbeat", "every_seconds": 300}
                for key in ("region_a", "region_b", "control", "host_health", "traffic_ratio")],
    "rules": [
        {"key": "banned", "action": "Replace the server.",
         "wait": {"confirm_after": 600, "recover_after": 600},
         "decision": {"all": [status("region_a", "problem"), status("region_b", "problem"),
                              status("control", "ok"), status("host_health", "ok"), traffic("lt")]}},
        {"key": "dead", "action": "Open a provider ticket.",
         "wait": {"confirm_after": 0, "recover_after": 300},
         "decision": {"any": [status("control", "problem"), status("host_health", "problem")]}},
        {"key": "checker_issue", "action": "Inspect the checker; do not replace the server.",
         "wait": {"confirm_after": 0, "recover_after": 0},
         "decision": {"all": [{"any": [status("region_a", "problem"), status("region_b", "problem")]},
                              status("control", "ok"), status("host_health", "ok"), traffic("gte")]}},
    ],
}


def push(ws, server: str, ratio: float) -> None:
    """One round of what the organization's database knows: regions down, host fine, traffic low."""
    for signal, state in (("region_a", "problem"), ("region_b", "problem"), ("control", "ok"), ("host_health", "ok")):
        ws.resources.observe(server, signal=signal, state=state)
    ws.resources.observe(server, signal="traffic_ratio", state="ok", value=ratio)


def banned(ws, server: str):
    rule = next(r for r in ws.resources.get(server).rules if r.key == "banned")
    open_ = [i for i in ws.resources.incidents(server).items if i.rule == "banned"]
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
rule, incidents = banned(ws, server)
print(f"after one reading:    banned {rule.status} — {rule.explanation}; incidents: {len(incidents)}")

for _ in range(2):
    push(ws, server, 0.1)
    time.sleep(2)
time.sleep(35)
rule, incidents = banned(ws, server)
print(f"after three readings: banned {rule.status} — {rule.explanation}")
for incident in incidents:
    print(f"  incident {incident.id}: {incident.lifecycle}, {incident.confirmation} — {incident.action}")
