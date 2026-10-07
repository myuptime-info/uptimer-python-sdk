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


@dataclass(frozen=True)
class Location:
    id: str
    name: str

    @classmethod
    def from_api(cls, data: dict[str, Any]) -> Location:
        return cls(id=data["id"], name=data["name"])


@dataclass(frozen=True)
class Signal:
    id: str
    key: str
    kind: str
    states: list[str]


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
            created_at=_required_time(data["created_at"]),
            open_incident=OpenIncident(**incident) if incident else None,
            signals=[
                Signal(id=s["id"], key=s["key"], kind=s["kind"], states=s.get("states") or [])
                for s in data.get("signals") or []
            ],
            rules=[
                Rule(
                    key=r["key"], signals=r.get("signals") or [], status=r.get("status"),
                    explanation=r.get("explanation"), since=_time(r.get("since")),
                    open_incident=r.get("open_incident"), action=r.get("action"),
                    destination=r.get("destination"),
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

    @classmethod
    def from_api(cls, data: dict[str, Any]) -> Observation:
        return cls(
            id=data["id"], signal=data["signal"], location=data.get("location", ""),
            state=data["state"], value=data.get("value"), labels=data.get("labels") or {},
            at=_required_time(data["at"]), received_at=_required_time(data["received_at"]),
            source=data.get("source", ""), reason=data.get("reason") or "",
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
