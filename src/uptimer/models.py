"""
Typed results.

Every identifier is the server's public id (a short string), never a database
row number. A Resource is also addressable by its `key`.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Generic, Iterator, TypeVar

T = TypeVar("T")


def _time(value: str | None) -> datetime | None:
    if not value:
        return None
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


def _required_time(value: str) -> datetime:
    parsed = _time(value)
    if parsed is None:
        msg = "missing timestamp"
        raise ValueError(msg)
    return parsed


@dataclass(frozen=True)
class Workspace:
    id: str
    name: str
    role: str

    @classmethod
    def from_api(cls, data: dict[str, Any]) -> Workspace:
        return cls(id=data["id"], name=data["name"], role=data["role"])


@dataclass(frozen=True)
class TemplateField:
    key: str
    label: str
    help: str
    type: str
    required: bool
    default: Any
    options: list[str]
    min: int | None
    max: int | None


@dataclass(frozen=True)
class Template:
    id: str
    version: int
    name: str
    summary: str
    fields: list[TemplateField]
    signals: list[dict[str, Any]]
    rules: list[dict[str, Any]]

    @classmethod
    def from_api(cls, data: dict[str, Any]) -> Template:
        return cls(
            id=data["id"],
            version=data["version"],
            name=data["name"],
            summary=data.get("summary", ""),
            fields=[
                TemplateField(
                    key=f["key"], label=f["label"], help=f.get("help", ""), type=f["type"],
                    required=f["required"], default=f.get("default"),
                    options=f.get("options") or [], min=f.get("min"), max=f.get("max"),
                )
                for f in data.get("fields") or []
            ],
            signals=data.get("signals") or [],
            rules=data.get("rules") or [],
        )

    def confirm_policy(self, signal: str) -> ConfirmPolicy | None:
        """Return the Confirmation policy of one of this Template's Signals, or None."""
        for one in self.signals:
            if one.get("key") == signal and one.get("confirm"):
                return ConfirmPolicy.from_api(one["confirm"])
        return None


def meta(field: str) -> dict[str, str]:
    """Return a Template value read from the Resource's own answer: ``{"meta": field}``."""
    return {"meta": field}


@dataclass(frozen=True)
class Confirmer:
    """
    One second opinion in a Signal's Confirmation policy.

    Exactly one of `probe` (a built-in probe: reachability, icmp, tcp, tls,
    http, dns) or `exec` (a command name a worker's own commands file defines).
    `with_` is its settings or parameters; a value may be ``meta("field")``.
    The server checks every bound and answers ValidationError otherwise.
    """

    probe: str | None = None
    exec: str | None = None
    with_: dict[str, Any] = field(default_factory=dict)

    def to_api(self) -> dict[str, Any]:
        out: dict[str, Any] = {"probe": self.probe} if self.probe else {"exec": self.exec}
        if self.with_:
            out["with"] = dict(self.with_)
        return out

    @classmethod
    def from_api(cls, data: dict[str, Any]) -> Confirmer:
        return cls(probe=data.get("probe"), exec=data.get("exec"), with_=data.get("with") or {})


@dataclass(frozen=True)
class ConfirmPolicy:
    """
    A Signal's Confirmation policy, checked again by `by` before Rules believe a problem.

    Only ``problem`` triggers one; a no_data reading is trusted as it is.
    `refuted_if` is ``any_ok`` or ``all_ok``; `timeout` is 5 to 600 seconds.
    Put ``policy.to_api()`` under a Template Signal's ``"confirm"`` key.
    """

    by: list[Confirmer]
    refuted_if: str
    timeout: int
    on: str = "problem"

    def to_api(self) -> dict[str, Any]:
        return {"on": self.on, "by": [one.to_api() for one in self.by],
                "refuted_if": self.refuted_if, "timeout": self.timeout}

    @classmethod
    def from_api(cls, data: dict[str, Any]) -> ConfirmPolicy:
        return cls(by=[Confirmer.from_api(one) for one in data.get("by") or []],
                   refuted_if=data["refuted_if"], timeout=data["timeout"], on=data.get("on") or "problem")


@dataclass(frozen=True)
class Comparison:
    """
    One comparison in a composite Rule's decision.

    ``if_unknown=False`` makes it false, rather than unknown, when its Signal
    has no usable data (never reported, silent, no_data, not checked yet);
    only ``False`` is accepted, and not on ``known``, a group, or under ``not``.
    """

    signal: str
    field: str
    operator: str | None = None
    operand: Any = None
    if_unknown: bool | None = None

    def to_api(self) -> dict[str, Any]:
        out: dict[str, Any] = {"signal": self.signal, "field": self.field}
        if self.operator is not None:
            out["operator"] = self.operator
        if self.operand is not None:
            out["operand"] = self.operand
        if self.if_unknown is not None:
            out["if_unknown"] = self.if_unknown
        return out


@dataclass(frozen=True)
class Location:
    id: str
    name: str

    @classmethod
    def from_api(cls, data: dict[str, Any]) -> Location:
        return cls(id=data["id"], name=data["name"])


@dataclass(frozen=True)
class SignalConfirmation:
    """
    What a Signal's Confirmation policy made of its newest reading.

    `status` is pending, confirmed, unconfirmed or not_run; `reason` is
    refuted, problem_confirmed, timeout, confirmer_no_data, limited or
    source_no_data (None while pending); `effective` is the state Rules
    evaluate (ok where confirmers refuted the problem, else the original), and
    `original` what the Signal first said. While pending, Rules hold.
    """

    status: str
    reason: str | None
    effective: str
    original: str

    @classmethod
    def from_api(cls, data: dict[str, Any] | None) -> SignalConfirmation | None:
        if not data:
            return None
        return cls(status=data["status"], reason=data.get("reason"), effective=data["effective"],
                   original=data["original"])


@dataclass(frozen=True)
class Signal:
    id: str
    key: str
    kind: str
    states: list[str]
    # "applicable", or "not_applicable" where the Template's `applies_if` is
    # false for this Resource: no Rule reads it, and it is not missing data.
    applicability: str = "applicable"
    # Why it has no usable reading now: "never_reported", "stale" or
    # "reported_no_data"; None where it has one, or does not apply.
    missing: str | None = None
    # An on-demand Signal is checked only when asked; `not_checked` is one
    # nobody has asked for yet: not missing data, and not no_data.
    on_demand: bool = False
    not_checked: bool = False
    # What its Confirmation policy made of its newest reading; None without a
    # policy, or before a reading that needed one.
    confirmation: SignalConfirmation | None = None

    @property
    def applicable(self) -> bool:
        return self.applicability != "not_applicable"


@dataclass(frozen=True)
class Route:
    """One destination a Rule routes to, and the transitions it receives."""

    destination: str
    on: list[str]


@dataclass(frozen=True)
class Rule:
    """A Rule and its latest result; `status` is None until it has decided."""

    key: str
    signals: list[str]
    status: str | None
    explanation: str | None
    since: datetime | None
    open_incident: str | None
    # What this Rule's Incident tells a person to do, where its Template says.
    action: str | None = None
    # The destination id this Rule's Incidents are announced to, where its
    # Template names one; None follows the Resource's and the Workspace default.
    destination: str | None = None
    # Where each transition goes, where its Template routes: [] sends nothing;
    # None follows `destination`, then the Resource's and the Workspace default.
    routes: list[Route] | None = None


@dataclass(frozen=True)
class Maintenance:
    starts: datetime
    until: datetime
    by: str


@dataclass(frozen=True)
class OpenIncident:
    id: str
    standing: str
    explanation: str


@dataclass(frozen=True)
class Resource:
    id: str
    key: str
    name: str
    template: str | None
    meta: dict[str, Any]
    created_at: datetime
    open_incident: OpenIncident | None
    signals: list[Signal] = field(default_factory=list)
    rules: list[Rule] = field(default_factory=list)
    maintenance: Maintenance | None = None
    # When it left the inventory, or None while it is active.
    archived_at: datetime | None = None
    # The Resource's own labels; not Template fields, and no Rule reads them.
    labels: dict[str, str] = field(default_factory=dict)

    @classmethod
    def from_api(cls, data: dict[str, Any]) -> Resource:
        incident = data.get("open_incident")
        window = data.get("maintenance")
        return cls(
            id=data["id"],
            key=data["key"],
            name=data["name"],
            template=data.get("template"),
            meta=data.get("meta") or {},
            labels=data.get("labels") or {},
            created_at=_required_time(data["created_at"]),
            open_incident=OpenIncident(**incident) if incident else None,
            signals=[
                Signal(
                    id=s["id"], key=s["key"], kind=s["kind"], states=s.get("states") or [],
                    applicability=s.get("applicability") or "applicable",
                    missing=s.get("missing"),
                    on_demand=bool(s.get("on_demand")),
                    not_checked=bool(s.get("not_checked")),
                    confirmation=SignalConfirmation.from_api(s.get("confirmation")),
                )
                for s in data.get("signals") or []
            ],
            rules=[
                Rule(
                    key=r["key"], signals=r.get("signals") or [], status=r.get("status"),
                    explanation=r.get("explanation"), since=_time(r.get("since")),
                    open_incident=r.get("open_incident"), action=r.get("action"),
                    destination=r.get("destination"),
                    routes=None if r.get("routes") is None else [
                        Route(destination=route["destination"], on=route.get("on") or [])
                        for route in r["routes"]
                    ],
                )
                for r in data.get("rules") or []
            ],
            maintenance=Maintenance(
                starts=_required_time(window["from"]), until=_required_time(window["until"]), by=window["by"],
            ) if window else None,
            archived_at=_time(data.get("archived_at")),
        )


@dataclass(frozen=True)
class Observed:
    """What sending an Observation did."""

    resource: str
    signal: str
    observation: str
    created_signal: bool

    @classmethod
    def from_api(cls, data: dict[str, Any]) -> Observed:
        return cls(
            resource=data["resource"], signal=data["signal"],
            observation=data["observation"], created_signal=data["created_signal"],
        )


@dataclass(frozen=True)
class ConfirmerReading:
    """
    One confirmer's part of a confirmation: a probe or a named command, and its reading.

    `state` is None until it answers. No worker is named.
    """

    probe: str | None
    exec: str | None
    state: str | None
    value: float | None
    reason: str
    at: datetime | None

    @classmethod
    def from_api(cls, data: dict[str, Any]) -> ConfirmerReading:
        return cls(probe=data.get("probe"), exec=data.get("exec"), state=data.get("state"),
                   value=data.get("value"), reason=data.get("reason") or "", at=_time(data.get("at")))


@dataclass(frozen=True)
class ObservationConfirmation:
    """
    What an Observation's Confirmation policy made of it, kept beside the original reading.

    The outcome, the state Rules evaluate, and each confirmer's reading.
    """

    status: str
    reason: str | None
    effective: str
    refuted_if: str
    deadline: datetime
    decided_at: datetime | None
    confirmers: list[ConfirmerReading]

    @classmethod
    def from_api(cls, data: dict[str, Any] | None) -> ObservationConfirmation | None:
        if not data:
            return None
        return cls(status=data["status"], reason=data.get("reason"), effective=data["effective"],
                   refuted_if=data.get("refuted_if", ""), deadline=_required_time(data["deadline"]),
                   decided_at=_time(data.get("decided_at")),
                   confirmers=[ConfirmerReading.from_api(one) for one in data.get("confirmers") or []])


@dataclass(frozen=True)
class Observation:
    """One logged Observation: investigation context, not a decision record."""

    id: str
    signal: str
    location: str
    state: str
    value: float | None
    labels: dict[str, str]
    at: datetime
    received_at: datetime
    source: str
    # The sender's short reason; "" when it gave none, or from an older server.
    reason: str = ""
    # What its Signal's Confirmation policy made of it; None without a policy.
    # `state` above stays the original reading.
    confirmation: ObservationConfirmation | None = None

    @classmethod
    def from_api(cls, data: dict[str, Any]) -> Observation:
        return cls(
            id=data["id"], signal=data["signal"], location=data.get("location", ""),
            state=data["state"], value=data.get("value"), labels=data.get("labels") or {},
            at=_required_time(data["at"]), received_at=_required_time(data["received_at"]),
            source=data.get("source", ""), reason=data.get("reason") or "",
            confirmation=ObservationConfirmation.from_api(data.get("confirmation")),
        )


@dataclass(frozen=True)
class ResourceRef:
    id: str
    key: str
    name: str


@dataclass(frozen=True)
class Acknowledgement:
    by: str
    at: datetime
    via: str


@dataclass(frozen=True)
class EvidenceConfirmation:
    """A recorded reading's confirmation: status, reason code and the original state."""

    status: str
    reason: str | None
    original: str


@dataclass(frozen=True)
class EvidenceInput:
    """
    One input of a Transition's recorded evidence, as the Rule read it.

    `status` is the state the Rule evaluated; where a Confirmation decided the
    reading, `confirmation.original` is what the Signal first said.
    """

    signal: str
    where: str
    status: str | None
    value: float | None
    at: datetime | None
    reason: str
    unresolved: str
    confirmation: EvidenceConfirmation | None

    @classmethod
    def from_api(cls, data: dict[str, Any]) -> EvidenceInput:
        said = data.get("confirmation")
        return cls(signal=data["signal"], where=data.get("where", ""), status=data.get("status"),
                   value=data.get("value"), at=_time(data.get("at")), reason=data.get("reason") or "",
                   unresolved=data.get("unresolved") or "",
                   confirmation=EvidenceConfirmation(status=said["status"], reason=said.get("reason"),
                                                     original=said["original"]) if said else None)


@dataclass(frozen=True)
class Transition:
    at: datetime
    kind: str
    condition: str
    verdict: str
    explanation: str
    # The bounded input evidence this transition recorded: {"inputs": [...],
    # "omitted": n, "truncated": bool}. An input may carry "counted" (a
    # min_count set), "baseline" ({days, required, samples, median}: the
    # own-history median it compared with) or "reason" (what the sender said
    # about that reading). None where it recorded none (an
    # administrative closure, or a server before 2.0 evidence).
    evidence: dict[str, Any] | None = None

    @property
    def inputs(self) -> list[EvidenceInput]:
        """The recorded evidence's inputs, typed; [] where none was recorded."""
        if not self.evidence:
            return []
        return [EvidenceInput.from_api(one) for one in self.evidence.get("inputs") or []]


@dataclass(frozen=True)
class Incident:
    """
    One period of suspected trouble from one Rule.

    `lifecycle` is open or closed, `confirmation` confirmed or unconfirmed,
    `condition` ok, problem or no_data. A closed Incident says why in
    `closed_reason`: recovered or rule_removed. `history` is filled by
    `incidents.get()`, oldest first.
    """

    id: str
    resource: ResourceRef
    rule: str
    lifecycle: str
    confirmation: str
    condition: str
    verdict: str
    explanation: str
    closed_reason: str | None
    opened_at: datetime
    confirmed_at: datetime | None
    closed_at: datetime | None
    effective_at: datetime
    acknowledgement: Acknowledgement | None
    history: list[Transition] = field(default_factory=list)
    # What its Rule told a person to do when it opened, or None.
    action: str | None = None

    @classmethod
    def from_api(cls, data: dict[str, Any]) -> Incident:
        ack = data.get("acknowledgement")
        return cls(
            id=data["id"],
            resource=ResourceRef(**data["resource"]),
            rule=data["rule"],
            lifecycle=data["lifecycle"],
            confirmation=data["confirmation"],
            condition=data["condition"],
            verdict=data["verdict"],
            explanation=data.get("explanation", ""),
            closed_reason=data.get("closed_reason"),
            opened_at=_required_time(data["opened_at"]),
            confirmed_at=_time(data.get("confirmed_at")),
            closed_at=_time(data.get("closed_at")),
            effective_at=_required_time(data["effective_at"]),
            acknowledgement=Acknowledgement(by=ack["by"], at=_required_time(ack["at"]), via=ack["via"])
            if ack else None,
            history=[
                Transition(
                    at=_required_time(h["at"]), kind=h["kind"], condition=h["condition"],
                    verdict=h["verdict"], explanation=h.get("explanation", ""),
                    evidence=h.get("evidence"),
                )
                for h in data.get("history") or []
            ],
            action=data.get("action"),
        )


@dataclass(frozen=True)
class Destination:
    """A place a Workspace's alerts go. Its URL is never read back."""

    id: str
    name: str
    type: str
    channel: str | None
    enabled: bool
    send_on_open: bool
    default: bool

    @classmethod
    def from_api(cls, data: dict[str, Any]) -> Destination:
        return cls(
            id=data["id"], name=data["name"], type=data["type"], channel=data.get("channel"),
            enabled=data["enabled"], send_on_open=data.get("send_on_open", False), default=data.get("default", False),
        )


@dataclass(frozen=True)
class DestinationTest:
    """How a test message ended: `status` delivered or failed, and a reason code."""

    status: str
    reason: str | None

    @property
    def delivered(self) -> bool:
        return self.status == "delivered"


@dataclass(frozen=True)
class DestinationDelivery:
    """One thing sent to a destination: event, status and a reason code, never the payload."""

    at: datetime
    event: str
    status: str
    reason: str | None
    # The Incident it was about; None for a test message.
    incident: str | None

    @classmethod
    def from_api(cls, data: dict[str, Any]) -> DestinationDelivery:
        return cls(
            at=_required_time(data["at"]), event=data["event"], status=data["status"],
            reason=data.get("reason"), incident=data.get("incident"),
        )


@dataclass(frozen=True)
class BatchItem:
    """One item of a batch: accepted with its identity, or rejected with the error a single send would raise."""

    index: int
    status: str
    resource: str | None
    signal: str | None
    observation: str | None
    created_signal: bool
    # The API error as it came: {code, error_type, message, details}; None when accepted.
    error: dict[str, Any] | None

    @property
    def accepted(self) -> bool:
        return self.status == "accepted"


@dataclass(frozen=True)
class BatchResult:
    """What one batch of Observations did, item by item, in the order sent."""

    accepted: int
    rejected: int
    results: list[BatchItem]

    @classmethod
    def from_api(cls, data: dict[str, Any]) -> BatchResult:
        return cls(
            accepted=data["accepted"], rejected=data["rejected"],
            results=[
                BatchItem(
                    index=one["index"], status=one["status"], resource=one.get("resource"),
                    signal=one.get("signal"), observation=one.get("observation"),
                    created_signal=one.get("created_signal", False), error=one.get("error"),
                )
                for one in data["results"]
            ],
        )


@dataclass(frozen=True)
class Page(Generic[T]):
    """One page of a list, and the cursor for the next one (None at the end)."""

    items: list[T]
    next_cursor: str | None

    def __iter__(self) -> Iterator[T]:
        """Iterate over this page's items."""
        return iter(self.items)

    def __len__(self) -> int:
        """Return how many items this page holds."""
        return len(self.items)
