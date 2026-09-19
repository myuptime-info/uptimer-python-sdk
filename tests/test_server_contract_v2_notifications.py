"""
The 1.8.0 payloads, copied verbatim from the server's own contract document.

Every other test in this suite asserts what the SDK SENDS. These assert what it
can READ, against payloads lifted character for character from
`app/api/README_notifications.md` in the Uptimer repository — the document the
API handlers are written against and QA verified for `v1.8.0-rc14`.

That is the failure this file exists for: a model that deserializes a payload
the SDK author imagined is worth nothing. If a field is renamed on the server,
these break.
"""

from __future__ import annotations

from uptimer.models.v2 import (
    ALERT_KIND_PROBLEM,
    DELIVERY_STATUS_FAILED,
    DESTINATION_TYPE_SLACK,
    FALLBACK_WORKSPACE_DEFAULT,
    from_api_delivery_record,
    from_api_destination,
    from_api_subject_delivery,
    from_api_transformation_preview,
    samples_from_api,
)

# --- A destination, as the server answers a create -----------------------------
SERVER_DESTINATION = {
    "kind": "notification_destination",
    "id": 1,
    "name": "Acme Slack · #incidents",
    "destination_type": "slack",
    "channel": "incidents",
    "url": "https://hooks.slack.com/services/T00/B00/xxxx",
    "enabled": True,
    "default": True,
    "transformation_id": None,
    "workspace_id": "8a1f…",
    "created_at": "2026-09-18T09:12:44Z",
    "updated_at": "2026-09-18T09:12:44Z",
}

# --- A subject's delivery table, empty, with a workspace default ---------------
SERVER_DELIVERY_TABLE = {
    "kind": "subject_alert_delivery",
    "subject_id": "payments-worker",
    "selections": [],
    "default_destination_id": 1,
    "fallback": "workspace_default",
    "workspace_id": "8a1f…",
}

# --- One recorded attempt that was refused -------------------------------------
SERVER_DELIVERY_RECORD = {
    "kind": "notification_delivery",
    "id": 87,
    "destination_id": 2,
    "destination_name": "Pager relay",
    "destination_type": "webhook",
    "alert_kind": "problem",
    "status": "failed",
    "payload": '{"event":"problem","summary":"Checkout API is down …"}',
    "error": "the address answered 403 Forbidden: invalid_token",
    "at": "2026-09-18T09:41:02Z",
}

# --- A preview where every sample rendered --------------------------------------
SERVER_PREVIEW = {
    "kind": "notification_transformation_preview",
    "passed": True,
    "results": [
        {"alert_kind": "problem", "label": "Problems and reminders",
         "ok": True, "output": '{"event":"problem"}'},
        {"alert_kind": "no_data", "label": "No data", "ok": True, "output": "…"},
        {"alert_kind": "recovery", "label": "Recoveries", "ok": True, "output": "…"},
    ],
}

# --- The published field vocabulary of one sample --------------------------------
SERVER_SAMPLES = [
    {
        "alert_kind": "problem",
        "label": "Problems and reminders",
        "fields": {
            "kind": "problem", "status": "down", "subject": "Checkout API",
            "url": "https://checkout.example/health",
            "summary": "Checkout API is down — failing from 2 of 3 locations",
            "error": 'Get "https://checkout.example/health": i/o timeout',
            "locations": "de, fr", "lasted": "2m",
            "link": "https://uptimer.example/ui/workspace/…/monitoring/subject/…",
            "workspace": "Acme ops", "at": "2026-09-16T14:04:00Z",
        },
    },
]


def test_a_destination_reads_back_whole():
    destination = from_api_destination(SERVER_DESTINATION)

    assert destination.id == 1
    assert destination.name == "Acme Slack · #incidents"
    assert destination.destination_type == DESTINATION_TYPE_SLACK
    # Stored without the '#', and returned that way.
    assert destination.channel == "incidents"
    assert destination.url.endswith("/xxxx")
    assert destination.default is True
    # null transformation IS the built-in message, and must not become 0 or "".
    assert destination.transformation_id is None
    assert destination.is_transformed is False


def test_an_empty_table_carries_its_fallback():
    table = from_api_subject_delivery(SERVER_DELIVERY_TABLE)

    assert table.selections == []
    assert table.default_destination_id == 1
    assert table.fallback == FALLBACK_WORKSPACE_DEFAULT
    assert table.uses_workspace_default


def test_a_refused_attempt_keeps_the_reason_and_the_snapshot():
    record = from_api_delivery_record(SERVER_DELIVERY_RECORD)

    assert record.status == DELIVERY_STATUS_FAILED
    assert record.delivered is False
    assert record.error.startswith("the address answered 403")
    # The destination as it was AT THE ATTEMPT, not a join.
    assert record.destination_name == "Pager relay"
    assert record.alert_kind == ALERT_KIND_PROBLEM


def test_a_preview_reads_every_sample():
    preview = from_api_transformation_preview(SERVER_PREVIEW)

    assert preview.passed is True
    assert [r.alert_kind for r in preview.results] == ["problem", "no_data", "recovery"]
    assert all(r.ok for r in preview.results)


def test_the_samples_carry_the_published_vocabulary():
    samples = samples_from_api(SERVER_SAMPLES)

    assert samples[0].label == "Problems and reminders"
    # The eleven fields a template may read. A template written against a name
    # this SDK dropped would render empty at the moment it mattered.
    assert set(samples[0].fields) == {
        "kind", "status", "subject", "url", "summary", "error",
        "locations", "lasted", "link", "workspace", "at",
    }
