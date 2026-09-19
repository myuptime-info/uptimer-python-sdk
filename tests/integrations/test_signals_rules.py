"""
Custom signal and rule authoring against a running Uptimer.

Needs an EDITOR key and a workspace. It creates its own Custom subject, authors
a signal and a rule on it, reads the policy back, updates it and deletes both —
so it needs nothing to exist beforehand. Set

    UPTIMER_API_KEY, UPTIMER_WORKSPACE_ID

and optionally UPTIMER_URL.

The subject is left behind: the SDK has no delete for one, by design. What is
left is an empty subject with a timestamped name.
"""

import os
from datetime import datetime, timezone

import pytest

from tests.conftest import integration_test
from uptimer.errors import DefaultUptimerApiError
from uptimer.models.v2 import (
    INPUT_MODE_STATUS,
    NEED_ANY,
    SIGNAL_KIND_HEARTBEAT,
    CreateRuleRequest,
    CreateSignalRequest,
    CreateSubjectRequest,
    RuleDecision,
    RuleDocument,
    RuleInput,
    RuleWait,
    UpdateRuleRequest,
    UpdateSignalRequest,
)

from .conftest import get_client

API_KEY = os.environ.get("UPTIMER_API_KEY", "")
WORKSPACE_ID = os.environ.get("UPTIMER_WORKSPACE_ID", "")

needs_workspace = pytest.mark.skipif(
    not (API_KEY and WORKSPACE_ID),
    reason="set UPTIMER_API_KEY and UPTIMER_WORKSPACE_ID",
)


def _unique(prefix: str) -> str:
    stamp = datetime.now(timezone.utc).strftime("%Y%m%d%H%M%S")
    return f"{prefix} {stamp}"


@integration_test
@needs_workspace
def test_authoring_a_signal_and_a_rule(uptimer_url: str):
    client = get_client(API_KEY, uptimer_url)

    subject = client.v2.subjects.create(
        CreateSubjectRequest(name=_unique("SDK signals"), workspace_id=WORKSPACE_ID),
    )
    signals = client.v2.subjects(subject.id, WORKSPACE_ID).signals
    rules = client.v2.subjects(subject.id, WORKSPACE_ID).rules

    assert signals.all() == []
    assert rules.all() == []

    signal = signals.create(
        CreateSignalRequest(
            name="Worker pulse",
            kind=SIGNAL_KIND_HEARTBEAT,
            meta={"team": "payments"},
        ),
    )
    assert signal.is_heartbeat
    assert signal.meta == {"team": "payments"}

    renamed = signals.update(
        signal.id,
        UpdateSignalRequest(name="Worker heartbeat", meta={}),
    )
    # The slug is the address a sender posts to: a rename never moves it.
    assert renamed.id == signal.id
    assert renamed.name == "Worker heartbeat"
    assert renamed.meta == {}

    rule = rules.create(
        CreateRuleRequest(
            name="Pulse health",
            document=RuleDocument(
                inputs=[
                    RuleInput(
                        signal=signal.id,
                        mode=INPUT_MODE_STATUS,
                        no_data_after="5m",
                    ),
                ],
                decision=RuleDecision(need=NEED_ANY),
                wait=RuleWait(confirm_after="2m", close_after="2m"),
            ),
        ),
    )
    assert rule.policy_version == 1
    assert rule.document.inputs[0].signal == signal.id

    # A policy read back and sent straight on is the same policy, and saving it
    # counts as a new version.
    updated = rules.update(
        rule.id,
        UpdateRuleRequest(name=rule.name, document=rule.document),
    )
    assert updated.policy_version == rule.policy_version + 1
    assert updated.document.inputs[0].mode == INPUT_MODE_STATUS

    # A signal a rule reads cannot be deleted: Uptimer never silently unlinks a
    # rule to complete an unrelated delete.
    with pytest.raises(DefaultUptimerApiError):
        signals.delete(signal.id)

    assert rules.delete(rule.id).rule_id == rule.id
    assert signals.delete(signal.id).signal_id == signal.id
    assert signals.all() == []
