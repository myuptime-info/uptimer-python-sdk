from __future__ import annotations

from dataclasses import dataclass, field

# Status carries the same words the screens show, so a client and the UI cannot
# disagree about whether something is wrong.
STATUS_OK = "ok"
# Failing, but inside the confirm hold — nobody has been notified yet.
STATUS_PENDING = "pending"
STATUS_PROBLEM = "problem"
# A real incident, not an absence: a location that never reported stays unknown
# and still counts toward the agreement.
STATUS_NO_DATA = "no_data"
# Reporting ok again while the incident is still open.
STATUS_RECOVERING = "recovering"


@dataclass
class IncidentLocations:
    """What each location reported for the tick the verdict was taken from."""

    failing: list[str] = field(default_factory=list)
    unknown: list[str] = field(default_factory=list)
    ok: list[str] = field(default_factory=list)


@dataclass
class Incident:
    """An open incident on a monitor."""

    id: str
    monitor_id: str
    monitor_name: str
    status: str
    trouble_since: str  # first non-ok tick, RFC 3339
    confirmed_at: str | None  # when the confirm hold elapsed; None while pending
    well_since: str | None  # first ok tick of a recovery run, else None
    locations: IncidentLocations
    kind: str = "incident"
