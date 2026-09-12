from __future__ import annotations

from dataclasses import asdict
from typing import TYPE_CHECKING
from urllib.parse import quote

from uptimer.endpoints.endpoint import BaseEndpoint
from uptimer.models.v2 import (
    from_api_acknowledgement,
    from_api_observation,
    from_api_subject,
    from_api_subject_incident,
)

if TYPE_CHECKING:
    from uptimer.http import UptimerHttpLib
    from uptimer.models.v2 import (
        CreateObservationRequest,
        CreateSubjectRequest,
        IncidentAcknowledgement,
        Observation,
        Subject,
        SubjectIncident,
    )


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
    The signals of one custom subject.

    Call it with a slug to reach one:
    `client.v2.subjects("nightly-export").signals("worker-pulse")`.

    There is no listing or authoring here. Uptimer 1.6.0 serves those routes —
    the Signals screen has an API half — but this SDK does not wrap them yet:
    add a signal in the Uptimer UI, and use this to report data to one that
    already exists.
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


class SubjectIncidentEndpoint(BaseEndpoint):
    """One incident of a custom subject, addressed by its opaque id."""

    def __init__(
        self,
        http: UptimerHttpLib,
        incident_id: str,
        parent_segments: str | list[str] | None = None,
        workspace_id: str | None = None,
    ):
        super().__init__(http, _slug(incident_id, "incident"), parent_segments)
        self._workspace_id = workspace_id

    def acknowledge(self) -> IncidentAcknowledgement:
        """
        Record that you have seen THIS incident. Requires uptimer 1.7.0+.

        It says a person looked; it changes nothing the engine decided. The
        verdict, the evidence and the close hold carry on, and alerting is
        untouched — acknowledging does not silence anything.

        There is no body and no actor argument: the person recorded is the owner
        of the API key, and the time is the time of the call. The server refuses
        a body rather than letting one client file an acknowledgement under
        another person's name.

        Repeating it is safe. A second call records nothing, adds no second
        history entry, and returns the FIRST person's name and time with
        `recorded=False`.

        Raises DefaultUptimerApiError when the incident is not this subject's —
        another subject's, another workspace's, or a website monitor's — and
        when it has closed. Nothing is retried through the other family: a
        website incident is acknowledged through `client.v1.rules(...)`, and
        this method will not do it for you.
        """
        params = {"workspace_id": self._workspace_id} if self._workspace_id else None
        response = self.http.client.post(f"{self.url}/acknowledge", params=params)
        result = self.http.parse_response(response=response)
        return from_api_acknowledgement(result)


class SubjectIncidentsEndpoint(BaseEndpoint):
    """
    The OPEN incidents of one custom subject. Requires uptimer 1.7.0+.

    This is where an acknowledgement target comes from. The acknowledge call
    takes one exact incident id and refuses to guess — a subject can have
    several incidents open at once — so the flow is: list these, choose the one
    you mean, acknowledge it by id.

    `client.v2.incidents` is the WEBSITE list and does not serve custom
    subjects; this is its custom counterpart, scoped to one subject.
    """

    def __init__(
        self,
        http: UptimerHttpLib,
        parent_segments: str | list[str] | None = None,
        workspace_id: str | None = None,
    ):
        super().__init__(http, "incidents", parent_segments)
        self._workspace_id = workspace_id

    def __call__(self, incident_id: str) -> SubjectIncidentEndpoint:
        return SubjectIncidentEndpoint(
            self.http,
            incident_id,
            [*self._parent_segments, self.segment],
            self._workspace_id,
        )

    def all(self) -> list[SubjectIncident]:
        """
        Every open incident of this subject, newest trouble first.

        Open ones only, and all of them: pending, recovering and no-data
        included, and already-acknowledged ones too — that somebody is on one is
        half of what this answers. A subject with nothing wrong returns [].

        Closed history is not here; it lives on the subject timeline in the
        dashboard.
        """
        params = {"workspace_id": self._workspace_id} if self._workspace_id else None
        response = self.http.client.get(self.url, params=params)
        result = self.http.parse_response(response=response)
        return [from_api_subject_incident(item) for item in result]


class SubjectEndpoint(BaseEndpoint):
    """One monitored subject, addressed by its slug."""

    signals: SignalsEndpoint
    incidents: SubjectIncidentsEndpoint

    def __init__(
        self,
        http: UptimerHttpLib,
        subject_slug: str,
        parent_segments: str | list[str] | None = None,
        workspace_id: str | None = None,
    ):
        super().__init__(http, _slug(subject_slug, "subject"), parent_segments)
        self.signals = SignalsEndpoint(http, [*self._parent_segments, self.segment])
        self.incidents = SubjectIncidentsEndpoint(
            http,
            [*self._parent_segments, self.segment],
            workspace_id,
        )


class SubjectsEndpoint(BaseEndpoint):
    """
    The workspace's CUSTOM monitored subjects.

    Uptimer splits its API by subject kind: website monitoring is
    `client.v2.monitoring.websites`, and this is the custom half. Neither one
    serves the other's subjects — a website subject's slug is refused here.

    Two ways in, because there are two things to do with a subject:

    - call it with a slug to reach what is under one —
      `client.v2.subjects("nightly-export").signals("worker-pulse").observations`;
    - call the methods here to list, fetch, or create one.

    There is no update or delete. Deleting a subject takes its whole history
    with it, which is not something to do by accident from a script.
    """

    def __init__(
        self,
        http: UptimerHttpLib,
        parent_segments: str | list[str] | None = None,
    ):
        super().__init__(http, "subjects", parent_segments)

    def __call__(self, subject_slug: str, workspace_id: str | None = None) -> SubjectEndpoint:
        """
        Reach one subject by slug.

        `workspace_id` settles an ambiguity rather than being required: a slug
        is unique within a workspace, not across them. Pass it when the same
        slug exists in two workspaces you belong to, and the incident routes
        under this subject will carry it.
        """
        return SubjectEndpoint(
            self.http,
            subject_slug,
            [*self._parent_segments, self.segment],
            workspace_id,
        )

    def all(self, workspace_id: str) -> list[Subject]:
        """
        Every CUSTOM subject in a workspace.

        Website monitoring is not here — it is `client.v2.monitoring.websites`.
        Against a 1.6.0 server every item reads `subject_kind == "custom"`;
        `subject_kind` is still on the model, because an older server answered
        this route with both kinds.
        """
        response = self.http.client.get(self.url, params={"workspace_id": workspace_id})
        result = self.http.parse_response(response=response)
        return [from_api_subject(item) for item in result]

    def get(self, subject_slug: str, workspace_id: str | None = None) -> Subject:
        """
        One custom subject by its slug.

        `workspace_id` is optional and settles an ambiguity rather than being
        required: a slug is unique within a workspace, not across them, so pass
        it when the same slug exists in two workspaces you belong to. Without
        it the server searches your memberships and says so if the answer is
        more than one.

        A website subject's slug raises a DefaultUptimerApiError saying it is
        managed elsewhere.
        """
        params = {"workspace_id": workspace_id} if workspace_id else None
        response = self.http.client.get(
            f"{self.url}/{_slug(subject_slug, 'subject')}",
            params=params,
        )
        result = self.http.parse_response(response=response)
        return from_api_subject(result)

    def create(self, subject: CreateSubjectRequest) -> Subject:
        """
        Create one empty Custom subject.

        It arrives with nothing under it: no signal, no rule, no HTTP probe.
        Add a signal to it in the Uptimer UI, then report to that signal through
        `client.v2.subjects(...).signals(...).observations`.

        Website monitoring is created by `client.v2.monitoring.websites.create`
        instead — it needs a URL, an interval and locations, and asking for one
        here is refused with a DefaultUptimerApiError saying so.
        """
        response = self.http.client.post(self.url, json=asdict(subject))
        result = self.http.parse_response(response=response)
        return from_api_subject(result)
