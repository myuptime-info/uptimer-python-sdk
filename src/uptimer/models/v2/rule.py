from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

# How many inputs must agree before the rule says there is a problem.
NEED_ANY = "any"
NEED_MAJORITY = "majority"
NEED_ALL = "all"
NEED_AT_LEAST = "at_least"

# What an input reads. `status` is the latest selected observation reporting a
# problem; `latest_value` compares its number against a threshold.
INPUT_MODE_STATUS = "status"
INPUT_MODE_LATEST_VALUE = "latest_value"

# The state a rule decides. `down` is the only one this release authors.
RULE_STATE_DOWN = "down"


@dataclass
class RuleInput:
    """
    One thing a rule reads.

    Exactly one of `signal` and `from_rule` is set: a signal of this subject, or
    another rule of it whose verdict becomes the input. Cross-subject inputs do
    not exist — a subject is the boundary.

    `from_rule` is spelled that way because `from` is a Python keyword; it is
    sent and received as `from`.

    On a signal input, `mode` is required. `compare` and `threshold` belong to
    `latest_value` alone, `match` selects which observations count (`"*"` means
    the label must be present with any value), and `no_data_after` is how long
    this input may stay silent before it counts as unknown — a duration string
    like "5m", not a number of seconds.
    """

    signal: str | None = None
    from_rule: str | None = None
    mode: str | None = None
    compare: str | None = None
    threshold: float | None = None
    match: dict[str, str] = field(default_factory=dict)
    no_data_after: str | None = None


@dataclass
class RuleDecision:
    """
    What the inputs have to agree on.

    `need` is "any", "majority", "all", or "at_least" with `at_least` set.
    """

    state: str = RULE_STATE_DOWN
    need: str = NEED_ANY
    at_least: int | None = None


@dataclass
class RuleWait:
    """
    The two holds, as duration strings.

    `confirm_after` is how long a problem must last before the incident is
    confirmed and anyone is alerted — the incident opens on the first bad tick
    regardless. `close_after` is how much continuous recovery closes it.
    """

    confirm_after: str = "2m"
    close_after: str = "2m"


@dataclass
class RuleDocument:
    """The policy itself: what is read, what it must agree on, and how long."""

    inputs: list[RuleInput] = field(default_factory=list)
    decision: RuleDecision = field(default_factory=RuleDecision)
    wait: RuleWait = field(default_factory=RuleWait)


@dataclass
class CreateRuleRequest:
    """
    One rule to author on a Custom subject.

    Every input must cite a signal or a rule of this subject, so add the signals
    first.
    """

    name: str
    document: RuleDocument = field(default_factory=RuleDocument)


@dataclass
class UpdateRuleRequest:
    """
    A rule's name and its whole policy.

    The document is a **replacement**, not a patch: send the policy you want,
    not the part you are changing. A successful save increments
    `policy_version`, and the rule keeps its identity and its slug, so the
    incidents and the timeline already pointing at it stay attached.
    """

    name: str
    document: RuleDocument = field(default_factory=RuleDocument)


@dataclass
class SubjectRule:
    """
    One operator-authored incident rule.

    `id` is the rule's SLUG — what another rule cites with `from`, and what the
    nested routes address. `policy_version` counts saved policies: the document
    of each is kept, so a past verdict can be read against the policy that
    produced it.

    This is not the v1 rule object, which describes a website probe.
    """

    id: str
    name: str
    subject_id: str
    workspace_id: str
    policy_version: int = 1
    document: RuleDocument = field(default_factory=RuleDocument)
    kind: str = "subject_rule"


@dataclass
class DeleteRuleResponse:
    """What the server says after deleting a rule."""

    message: str
    rule_id: str
    subject_id: str


def rule_document_to_api(document: RuleDocument) -> dict[str, Any]:
    """
    Serialize a policy the way the server reads it.

    Two translations happen here and nowhere else: `from_rule` is sent as
    `from`, and anything unset is left out rather than sent as null — an absent
    `no_data_after` means "derive it from the interval", where a null would be a
    malformed duration.
    """
    inputs: list[dict[str, Any]] = []
    for item in document.inputs:
        raw: dict[str, Any] = {}
        if item.signal is not None:
            raw["signal"] = item.signal
        if item.from_rule is not None:
            raw["from"] = item.from_rule
        if item.mode is not None:
            raw["mode"] = item.mode
        if item.compare is not None:
            raw["compare"] = item.compare
        if item.threshold is not None:
            raw["threshold"] = item.threshold
        if item.match:
            raw["match"] = dict(item.match)
        if item.no_data_after is not None:
            raw["no_data_after"] = item.no_data_after
        inputs.append(raw)

    decision: dict[str, Any] = {
        "state": document.decision.state,
        "need": document.decision.need,
    }
    if document.decision.at_least is not None:
        decision["at_least"] = document.decision.at_least

    return {
        "inputs": inputs,
        "decision": decision,
        "wait": {
            "confirm_after": document.wait.confirm_after,
            "close_after": document.wait.close_after,
        },
    }


def rule_document_from_api(data: dict[str, Any] | None) -> RuleDocument:
    """Read a stored policy back, undoing the `from` spelling."""
    if not data:
        return RuleDocument()

    inputs = [
        RuleInput(
            signal=raw.get("signal"),
            from_rule=raw.get("from"),
            mode=raw.get("mode"),
            compare=raw.get("compare"),
            threshold=raw.get("threshold"),
            match=raw.get("match") or {},
            no_data_after=raw.get("no_data_after"),
        )
        for raw in data.get("inputs") or []
    ]

    decision_raw = data.get("decision") or {}
    wait_raw = data.get("wait") or {}
    return RuleDocument(
        inputs=inputs,
        decision=RuleDecision(
            state=decision_raw.get("state", RULE_STATE_DOWN),
            need=decision_raw.get("need", NEED_ANY),
            at_least=decision_raw.get("at_least"),
        ),
        wait=RuleWait(
            confirm_after=wait_raw.get("confirm_after", "2m"),
            close_after=wait_raw.get("close_after", "2m"),
        ),
    )
