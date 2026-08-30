from __future__ import annotations

from dataclasses import asdict
from typing import TYPE_CHECKING
from urllib.parse import quote

from uptimer.endpoints.endpoint import BaseEndpoint
from uptimer.models.v2 import from_api_observation

if TYPE_CHECKING:
    from uptimer.http import UptimerHttpLib
    from uptimer.models.v2 import CreateObservationRequest, Observation


def _slug(value: str, what: str) -> str:
    """
    Escape one slug for a URL path segment.

    A slug is the API name of a subject or signal, and it lands in the path. It
    is quoted rather than trusted so a value containing a slash addresses a
    signal named that, instead of silently reaching a different resource.
    """
    if not value or not value.strip():
        message = f"{what} slug is required"
        raise ValueError(message)
    return quote(value, safe="")


def _payload(observation: CreateObservationRequest) -> dict:
    """
    Serialize an observation, omitting what was not set.

    The server rejects unknown fields and distinguishes an absent optional from
    a null one — an absent `observed_at` means "stamp it now", where a null
    would be a malformed timestamp. So unset fields are left out rather than
    sent as None.
    """
    body = asdict(observation)
    return {key: value for key, value in body.items() if value is not None}


class ObservationsEndpoint(BaseEndpoint):
    """
    The observations of one signal.

    Reached through the signal that owns them —
    `client.v2.subjects(subject).signals(signal).observations` — because a
    signal slug is unique within its subject, not across the workspace. The pair
    is the address.
    """

    def __init__(
        self,
        http: UptimerHttpLib,
        parent_segments: str | list[str] | None = None,
    ):
        super().__init__(http, "observations", parent_segments)

    def create(self, observation: CreateObservationRequest) -> Observation:
        """
        Report one observation, and return it as the server stored it.

        Only custom heartbeat and event signals accept this. A platform HTTP
        signal is written by Uptimer's own probe and refuses posted
        observations, which arrives as a DefaultUptimerApiError.

        A stored observation the engine will not evaluate is RETURNED, not
        raised: check `accepted` and `reject_reason` on the result. An error is
        raised only when nothing was stored — a bad status, an unparsable
        timestamp, a signal that does not exist, or no permission.
        """
        response = self.http.client.post(self.url, json=_payload(observation))
        result = self.http.parse_response(response=response)
        return from_api_observation(result)


class SignalEndpoint(BaseEndpoint):
    """One signal of a subject, addressed by its slug."""

    observations: ObservationsEndpoint

    def __init__(
        self,
        http: UptimerHttpLib,
        signal_slug: str,
        parent_segments: str | list[str] | None = None,
    ):
        super().__init__(http, _slug(signal_slug, "signal"), parent_segments)
        self.observations = ObservationsEndpoint(
            http,
            [*self._parent_segments, self.segment],
        )


class SignalsEndpoint(BaseEndpoint):
    """
    The signals of one subject.

    Call it with a slug to reach one:
    `client.v2.subjects("checkout").signals("worker-pulse")`.

    There is no listing or authoring here. Signals are created and managed in
    the Uptimer UI; the SDK exists to report data to one that already exists.
    """

    def __init__(
        self,
        http: UptimerHttpLib,
        parent_segments: str | list[str] | None = None,
    ):
        super().__init__(http, "signals", parent_segments)

    def __call__(self, signal_slug: str) -> SignalEndpoint:
        return SignalEndpoint(self.http, signal_slug, self._parent_segments_with_self())

    def _parent_segments_with_self(self) -> list[str]:
        return [*self._parent_segments, self.segment]


class SubjectEndpoint(BaseEndpoint):
    """One monitored subject, addressed by its slug."""

    signals: SignalsEndpoint

    def __init__(
        self,
        http: UptimerHttpLib,
        subject_slug: str,
        parent_segments: str | list[str] | None = None,
    ):
        super().__init__(http, _slug(subject_slug, "subject"), parent_segments)
        self.signals = SignalsEndpoint(http, [*self._parent_segments, self.segment])


class SubjectsEndpoint(BaseEndpoint):
    """
    The monitored subjects.

    Call it with a slug to reach one: `client.v2.subjects("checkout")`.

    Deliberately narrow: there is no subject CRUD here. The one thing this
    namespace exists for is reporting observations to a custom signal, and the
    path to that is the subject that owns it.
    """

    def __init__(
        self,
        http: UptimerHttpLib,
        parent_segments: str | list[str] | None = None,
    ):
        super().__init__(http, "subjects", parent_segments)

    def __call__(self, subject_slug: str) -> SubjectEndpoint:
        return SubjectEndpoint(self.http, subject_slug, [*self._parent_segments, self.segment])
