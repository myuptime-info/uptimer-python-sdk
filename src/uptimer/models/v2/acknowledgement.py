from __future__ import annotations

from dataclasses import dataclass

# Acknowledging an incident (uptimer 1.7.0).
#
# It says a PERSON has seen an open incident. It changes nothing the engine
# decided — the verdict, the evidence, the close hold and the alerting all carry
# on — and it is recorded once, with who and when.
#
# Two objects live here because the API answers two questions:
#
#   - SubjectIncident: which incidents are open on a Custom subject, and what
#     are their ids. It is the discovery half, and the id it carries is the one
#     acknowledgement takes.
#   - IncidentAcknowledgement: what the record says after a call.
#
# The acknowledgement object comes back from BOTH families — the v1 Website
# route and the v2 Custom one — because it is one operation with two doors. It
# is typed here, with the rest of the 1.7.0 payloads, rather than duplicated per
# version: the server sends the same object either way, and the only difference
# is which parent it names.


@dataclass
class SubjectIncident:
    """
    One OPEN incident of a Custom subject.

    This is not the website [Incident] model. That one describes a monitor's
    incident and carries `monitor_id`, `monitor_name` and the locations the
    probe ran from; a custom incident has none of those, so this names the RULE
    that opened it instead — `rule_id` is the rule's slug, `rule_name` the name
    an operator gave it. A subject can have several rules and therefore several
    incidents open at once, which is exactly why picking one is a choice a
    caller makes rather than something the API guesses.

    `id` is what `acknowledge()` takes.
    """

    id: str
    subject_id: str
    rule_id: str
    rule_name: str
    status: str
    trouble_since: str  # first non-ok tick, RFC 3339
    confirmed_at: str | None  # when the confirm hold elapsed; None while pending
    well_since: str | None  # first ok tick of a recovery run, else None
    acknowledged: bool = False
    acknowledged_at: str | None = None
    # The display name, or the username where there is none. Empty while nobody
    # has acknowledged it.
    acknowledged_by: str = ""
    kind: str = "subject_incident"


@dataclass
class IncidentAcknowledgement:
    """
    What the record says after acknowledging an incident.

    It reports the PERSISTED state, not what your call did. The two differ on a
    repeat: acknowledging again records nothing and still answers the FIRST
    person's name and time, because that is what the record says. `recorded` is
    how the two are told apart — `True` means this call wrote it.

    Exactly one parent is named: `monitor_id` for a Website incident,
    `subject_id` with `rule_id` for a Custom one. The other family's fields are
    absent from the payload and read as None here.

    `status` is the incident's condition, unchanged by acknowledging it: an
    acknowledged problem is still a problem. A closed incident has no current
    condition and reads "ok" — `closed_at` is what tells you it closed.
    """

    incident_id: str
    status: str
    acknowledged: bool
    acknowledged_at: str | None
    acknowledged_by: str
    recorded: bool
    trouble_since: str
    confirmed_at: str | None = None
    well_since: str | None = None
    closed_at: str | None = None
    monitor_id: str | None = None
    subject_id: str | None = None
    rule_id: str | None = None
    kind: str = "incident_acknowledgement"

    @property
    def is_website(self) -> bool:
        """Whether this acknowledgement was made through the Website family."""
        return self.monitor_id is not None

    @property
    def is_custom(self) -> bool:
        """Whether this acknowledgement was made through the Custom family."""
        return self.subject_id is not None
