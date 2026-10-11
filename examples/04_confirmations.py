"""
Synthetic replica with a confirmed port, an on-demand deep check and an applies_if Signal.

Publishes a workerless Template whose `port` problem is confirmed by a tcp
probe before Rules believe it, whose `deep` check runs only when asked (and is
read with `if_unknown: false`), and whose `replication` heartbeat applies only
to replicas. Creates a primary and a replica, pushes a port problem to the
replica, then reads what each Signal says: applicability, missing cause,
not_checked, and the confirmation.

    UPTIMER_URL=http://localhost:8080/api UPTIMER_API_KEY=<full key> python 04_confirmations.py

A worker must run the tcp probe; without one the confirmation stays pending,
then reads unconfirmed / timeout after 30 seconds and the original problem stands.
"""

from __future__ import annotations

import os
import sys
import time
import uuid

from uptimer import Comparison, Confirmer, ConfirmPolicy, ConflictError, UptimerClient, meta

KEY = "replica-confirmed"

POLICY = ConfirmPolicy(by=[Confirmer(probe="tcp", with_={"host": meta("host"), "port": 5432})],
                       refuted_if="any_ok", timeout=30)

MANIFEST = {
    "key": KEY, "version": 1, "name": "Synthetic replica (confirmed port)",
    "summary": "A port confirmed before it pages, a deep check on demand, replication only on replicas.",
    "fields": [{"key": "host", "label": "Host", "type": "string", "required": True},
               {"key": "role", "label": "Role", "type": "enum", "options": ["primary", "replica"], "default": "primary"}],
    "signals": [
        {"key": "port", "kind": "event", "confirm": POLICY.to_api()},
        {"key": "deep", "kind": "event", "on_demand": True},
        {"key": "replication", "kind": "heartbeat", "every_seconds": 300,
         "applies_if": {"field": "role", "operator": "eq", "value": "replica"}},
    ],
    "rules": [{"key": "down", "action": "Look at the database host.", "wait": {"confirm_after": 0, "recover_after": 0},
               "decision": {"any": [Comparison("port", "status", "eq", "problem").to_api(),
                                    Comparison("deep", "status", "eq", "problem", if_unknown=False).to_api()]}}],
}


def main() -> int:
    url, api_key = os.environ.get("UPTIMER_URL"), os.environ.get("UPTIMER_API_KEY")
    if not url or not api_key:
        print("set UPTIMER_URL (your server plus /api) and UPTIMER_API_KEY", file=sys.stderr)
        return 2
    with UptimerClient(api_key=api_key, base_url=url) as client:
        client.ensure_compatible()
        workspaces = client.workspaces()
        wanted = os.environ.get("UPTIMER_WORKSPACE")
        chosen = [w for w in workspaces if wanted in (w.id, w.name)] if wanted else workspaces
        if len(chosen) != 1:
            print("choose a Workspace with UPTIMER_WORKSPACE:", [(w.id, w.name) for w in workspaces], file=sys.stderr)
            return 2
        ws = client.workspace(chosen[0].id)

        try:
            template = ws.templates.publish(MANIFEST)
        except ConflictError:
            template = next(t for t in ws.templates.list() if t.id == f"{KEY}@1")
        print("policy", template.confirm_policy("port"))

        run = uuid.uuid4().hex[:6]
        for role in ("primary", "replica"):
            ws.resources.create(key=f"{KEY}-{role}-{run}", template=KEY, name=f"db {role} {run}",
                                meta={"host": f"{role}.db.example.test", "role": role})
        replica = f"{KEY}-replica-{run}"
        ws.resources.observe(replica, signal="port", state="problem", reason="connection refused")
        time.sleep(2)

        for key in (f"{KEY}-primary-{run}", replica):
            for signal in ws.resources.get(key).signals:
                print(key, signal.key, signal.applicability, "missing:", signal.missing,
                      "not_checked:", signal.not_checked, "confirmation:", signal.confirmation)
        row = ws.resources.observations(replica, signal="port", limit=1)[0]
        print("history", row.state, row.confirmation)
    return 0


if __name__ == "__main__":
    sys.exit(main())
