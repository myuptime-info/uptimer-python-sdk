from __future__ import annotations

from dataclasses import dataclass

# A maintenance window (uptimer 1.7.0).
#
# An operator is about to do something that will make a subject look broken — a
# deploy, a database move — and does not want to be paged about the breakage
# they are causing. The window holds back that subject's PROBLEM notifications
# until the time they chose.
#
# It changes nothing else. Monitoring runs, observations arrive, rules decide,
# incidents open and close and the timeline records all of it, so afterwards the
# outage reads exactly as it happened. And recoveries are never held back: "it
# is back" is the message you most want after maintenance, and silencing it
# would leave you believing something is still broken.


@dataclass
class MaintenanceWindow:
    """
    One maintenance window on one subject.

    `active` is the question a caller actually has — is this subject silenced
    right now? — answered by the server rather than left to a client comparing
    three timestamps against its own clock.

    The three states are told apart by the fields: `active` true is running,
    `cancelled_at` set is ended early, and neither is a window that simply ran
    out.
    """

    subject_id: str
    started_at: str  # RFC 3339
    ends_at: str  # RFC 3339
    cancelled_at: str | None
    active: bool
    # What the window holds back, in the server's own words — so a client is not
    # left inferring it. Recoveries are never in this list.
    muted: list[str]
    kind: str = "maintenance_window"
