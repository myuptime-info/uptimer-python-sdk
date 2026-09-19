from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

# What a signal's silence means (uptimer 1.6.0).
#
# A HEARTBEAT is expected to keep reporting: silence is itself a symptom, and a
# rule reading one can say "no data after 5m". An EVENT reports only when there
# is something to say, so silence means nothing at all and a no-data window on
# it is meaningless.
#
# The kind is fixed when the signal is created: senders are already posting to
# it, and changing what their silence means underneath them is not a rename.
SIGNAL_KIND_HEARTBEAT = "custom_heartbeat"
SIGNAL_KIND_EVENT = "custom_event"

# The one a website monitor maintains for itself. It is returned by the read
# routes and refused by the write ones — its policy belongs to the check form.
SIGNAL_KIND_HTTP = "platform_http"


@dataclass
class CreateSignalRequest:
    """
    One custom signal to add to a Custom subject.

    `name` produces the slug the sender posts to, so pick it the way you would
    pick a hostname. `meta` is any JSON object: Uptimer stores and returns it
    untouched and never reads a key out of it.
    """

    name: str
    kind: str = SIGNAL_KIND_HEARTBEAT
    meta: dict[str, Any] = field(default_factory=dict)


@dataclass
class UpdateSignalRequest:
    """
    A rename, and a replacement `meta`.

    The kind and the slug are immutable — senders are already posting to that
    address — so this carries neither.
    """

    name: str
    meta: dict[str, Any] = field(default_factory=dict)


@dataclass
class Signal:
    """
    One signal of a subject.

    `id` is the signal's SLUG: the second half of the observation address, and
    what a rule input cites. A rename never moves it.
    """

    id: str
    name: str
    signal_kind: str
    subject_id: str
    workspace_id: str
    meta: dict[str, Any] = field(default_factory=dict)
    kind: str = "signal"

    @property
    def is_heartbeat(self) -> bool:
        """Whether silence on this signal is itself a symptom."""
        return self.signal_kind == SIGNAL_KIND_HEARTBEAT

    @property
    def is_managed(self) -> bool:
        """
        Whether Website monitoring owns this signal.

        A managed signal is readable and refuses every write: its configuration
        is the check form's.
        """
        return self.signal_kind == SIGNAL_KIND_HTTP


@dataclass
class DeleteSignalResponse:
    """What the server says after deleting a signal and its observations."""

    message: str
    signal_id: str
    subject_id: str
