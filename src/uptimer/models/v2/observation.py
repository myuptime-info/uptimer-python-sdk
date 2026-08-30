from __future__ import annotations

from dataclasses import dataclass, field

# The two words a custom sender may report. There is no "unknown" to send: an
# observation exists to say whether the sender is ok or in trouble, and an unset
# status is never read as health.
STATUS_OK = "ok"
STATUS_PROBLEM = "problem"

# Why a stored observation will not be evaluated. `accepted` is the only one that
# means the engine may use the row; the rest are kept and shown so an operator
# can see that data arrived and was set aside, rather than wondering whether it
# was ever received.
REJECT_ACCEPTED = "accepted"
REJECT_LATE = "late"
REJECT_OUT_OF_ORDER = "out_of_order"
# Stamped too far ahead of the server's clock.
REJECT_CLOCK_SKEW = "clock_skew"
REJECT_OUT_OF_RETENTION = "out_of_retention"


@dataclass
class CreateObservationRequest:
    """
    One observation to report for a custom heartbeat or event signal.

    Only `status` is required. `observed_at` defaults to the moment the server
    receives the report, which is what a heartbeat usually wants; send it
    explicitly when reporting something that happened earlier.

    `labels` is your own vocabulary — Uptimer stores it and matches rules
    against it, and never requires a particular key.
    """

    status: str
    # RFC 3339, for example "2026-08-30T12:00:00Z". None means "now".
    observed_at: str | None = None
    # The optional numeric reading a rule can compare against a threshold.
    value: float | None = None
    # The sender's own error text, for a problem worth explaining.
    error: str | None = None
    labels: dict[str, str] | None = None


@dataclass
class Observation:
    """
    One observation as the server stored it.

    `accepted` reports ACCEPTANCE, not health: it says the engine may use this
    row, not that the subject is fine. Whether anything is wrong is decided by a
    rule, and no rule need select this signal at all. Read `status` for what was
    reported.

    A refused observation is returned rather than raised as an error — it was
    stored, it is visible in the Unaccepted log, and `reject_reason` names why
    it will not be evaluated.
    """

    subject_id: str  # the subject slug the observation was posted to
    signal_id: str  # the signal slug within that subject
    observed_at: str  # when the SENDER observed it
    received_at: str  # when the server stored it
    status: str
    value: float | None
    error: str
    labels: dict[str, str] = field(default_factory=dict)
    accepted: bool = False
    reject_reason: str = REJECT_ACCEPTED
    kind: str = "observation"
