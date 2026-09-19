from __future__ import annotations

from dataclasses import asdict
from typing import TYPE_CHECKING
from urllib.parse import quote

from uptimer.endpoints.delivery import AlertDeliveryEndpoint
from uptimer.endpoints.endpoint import BaseEndpoint
from uptimer.models.v2 import (
    DeleteRuleResponse,
    DeleteSignalResponse,
    from_api_acknowledgement,
    from_api_maintenance,
    from_api_observation,
    from_api_signal,
    from_api_subject,
    from_api_subject_incident,
    from_api_subject_rule,
    rule_document_to_api,
)

if TYPE_CHECKING:
    from uptimer.http import UptimerHttpLib
    from uptimer.models.v2 import (
        CreateObservationRequest,
        CreateRuleRequest,
        CreateSignalRequest,
        CreateSubjectRequest,
        IncidentAcknowledgement,
        MaintenanceWindow,
        Observation,
        Signal,
        Subject,
        SubjectIncident,
        SubjectRule,
        UpdateRuleRequest,
        UpdateSignalRequest,
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


def _scope(workspace_id: str | None) -> dict | None:
    """
    Build the workspace query these routes take, or nothing.

    A subject slug is unique within a workspace, not across them, and the server
    resolves the subject BEFORE it does anything else — so a caller who named a
    workspace must have it carried into every nested route, or the same slug in
    two of their workspaces answers `Ambiguous subject`.
    """
    return {"workspace_id": workspace_id} if workspace_id else None


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
        workspace_id: str | None = None,
    ):
        super().__init__(http, "observations", parent_segments)
        self._workspace_id = workspace_id

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
        response = self.http.client.post(
            self.url,
            params=_scope(self._workspace_id),
            json=_payload(observation),
        )
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
        workspace_id: str | None = None,
    ):
        super().__init__(http, _slug(signal_slug, "signal"), parent_segments)
        self.observations = ObservationsEndpoint(
            http,
            [*self._parent_segments, self.segment],
            workspace_id,
        )


class SignalsEndpoint(BaseEndpoint):
    """
    The signals of one custom subject.

    Two ways in, as with subjects themselves: call it with a slug to reach what
    is under one —
    `client.v2.subjects("nightly-export").signals("worker-pulse").observations` —
    or call the methods here to list, read, author, rename or delete.

    Every route refuses a website subject: the signal a website monitor keeps is
    the check form's, and this is the custom half of the API.
    """

    def __init__(
        self,
        http: UptimerHttpLib,
        parent_segments: str | list[str] | None = None,
        workspace_id: str | None = None,
    ):
        super().__init__(http, "signals", parent_segments)
        self._workspace_id = workspace_id

    def __call__(self, signal_slug: str) -> SignalEndpoint:
        return SignalEndpoint(
            self.http,
            signal_slug,
            self._parent_segments_with_self(),
            self._workspace_id,
        )

    def _parent_segments_with_self(self) -> list[str]:
        return [*self._parent_segments, self.segment]

    def all(self) -> list[Signal]:
        """Every signal of this subject. A subject you just created has none."""
        response = self.http.client.get(self.url, params=_scope(self._workspace_id))
        result = self.http.parse_response(response=response)
        return [from_api_signal(item) for item in result]

    def get(self, signal_slug: str) -> Signal:
        """One signal by its slug."""
        response = self.http.client.get(
            f"{self.url}/{_slug(signal_slug, 'signal')}",
            params=_scope(self._workspace_id),
        )
        result = self.http.parse_response(response=response)
        return from_api_signal(result)

    def create(self, signal: CreateSignalRequest) -> Signal:
        """
        Add one custom signal, and return it as the server stored it.

        The name produces the SLUG a sender will post to, and the kind is fixed
        once created: choosing between heartbeat and event is choosing what this
        signal's silence means, and changing that under a sender is not a
        rename.

        Raises DefaultUptimerApiError on a name with no letter or digit, a name
        already used on this subject, a kind that is not custom heartbeat or
        event, and a `meta` that is not an object.
        """
        response = self.http.client.post(
            self.url,
            params=_scope(self._workspace_id),
            json=asdict(signal),
        )
        result = self.http.parse_response(response=response)
        return from_api_signal(result)

    def update(self, signal_slug: str, signal: UpdateSignalRequest) -> Signal:
        """
        Rename one and REPLACE its meta.

        The kind and the slug are immutable — senders are already posting to
        that address — so a rename never moves it. The signal a website monitor
        maintains refuses this: its configuration is the check form's.
        """
        response = self.http.client.post(
            f"{self.url}/{_slug(signal_slug, 'signal')}",
            params=_scope(self._workspace_id),
            json=asdict(signal),
        )
        result = self.http.parse_response(response=response)
        return from_api_signal(result)

    def delete(self, signal_slug: str) -> DeleteSignalResponse:
        """
        Delete one signal AND its observations.

        A signal a rule reads is refused: retarget or remove those rules first.
        Uptimer never unlinks a rule on its own, because that would quietly
        change what the rule watches in order to complete an unrelated delete.
        """
        response = self.http.client.delete(
            f"{self.url}/{_slug(signal_slug, 'signal')}",
            params=_scope(self._workspace_id),
        )
        result = self.http.parse_response(response=response)
        return DeleteSignalResponse(
            message=result["message"],
            signal_id=result["signal_id"],
            subject_id=result["subject_id"],
        )


class RulesEndpoint(BaseEndpoint):
    """
    The incident rules of one custom subject.

    A rule reads the subject's signals — or another of its rules — and decides
    whether there is a problem. The policy is a document: what it reads, what
    they have to agree on, and how long a state must hold.

    Authoring one needs the signals to exist first: every input cites a signal
    or a rule OF THIS SUBJECT, because a subject is the boundary.
    """

    def __init__(
        self,
        http: UptimerHttpLib,
        parent_segments: str | list[str] | None = None,
        workspace_id: str | None = None,
    ):
        super().__init__(http, "rules", parent_segments)
        self._workspace_id = workspace_id

    def all(self) -> list[SubjectRule]:
        """Every rule of this subject, each with its policy document."""
        response = self.http.client.get(self.url, params=_scope(self._workspace_id))
        result = self.http.parse_response(response=response)
        return [from_api_subject_rule(item) for item in result]

    def get(self, rule_slug: str) -> SubjectRule:
        """One rule by its slug."""
        response = self.http.client.get(
            f"{self.url}/{_slug(rule_slug, 'rule')}",
            params=_scope(self._workspace_id),
        )
        result = self.http.parse_response(response=response)
        return from_api_subject_rule(result)

    def create(self, rule: CreateRuleRequest) -> SubjectRule:
        """
        Add one rule, returned at `policy_version` 1.

        Every input must cite a signal or a rule of this subject.

        Raises DefaultUptimerApiError when the name has no letter or digit or is
        already used on this subject, when an input cites a signal or rule this
        subject does not have, when an input sets neither or both of `mode`
        readings, and when the document is otherwise not a valid policy.
        """
        body = {"name": rule.name, "document": rule_document_to_api(rule.document)}
        response = self.http.client.post(
            self.url,
            params=_scope(self._workspace_id),
            json=body,
        )
        result = self.http.parse_response(response=response)
        return from_api_subject_rule(result)

    def update(self, rule_slug: str, rule: UpdateRuleRequest) -> SubjectRule:
        """
        Replace a rule's name and its whole policy.

        The document is a REPLACEMENT, not a patch: send the policy you want.
        A CHANGED policy increments `policy_version`; sending the same document
        back leaves it where it was, because the timeline records which version
        produced an entry and a no-op must not churn it. Either way the rule
        keeps its identity and its slug, so the incidents and the timeline
        already pointing at it stay attached.

        A rule website monitoring created refuses this: its policy is the check
        form's, and a save here would be rewritten on the next check save.
        """
        body = {"name": rule.name, "document": rule_document_to_api(rule.document)}
        response = self.http.client.post(
            f"{self.url}/{_slug(rule_slug, 'rule')}",
            params=_scope(self._workspace_id),
            json=body,
        )
        result = self.http.parse_response(response=response)
        return from_api_subject_rule(result)

    def delete(self, rule_slug: str) -> DeleteRuleResponse:
        """
        Delete one rule.

        A rule another rule reads with `from` is refused, for the same reason a
        signal in use is: the delete would quietly change what the other rule
        watches.
        """
        response = self.http.client.delete(
            f"{self.url}/{_slug(rule_slug, 'rule')}",
            params=_scope(self._workspace_id),
        )
        result = self.http.parse_response(response=response)
        return DeleteRuleResponse(
            message=result["message"],
            rule_id=result["rule_id"],
            subject_id=result["subject_id"],
        )


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
        verdict, the evidence and the close hold carry on. Its one effect on
        alerting is that the four-hour reminders for this incident stop
        (uptimer 1.7.0); nothing else is silenced, and the recovery still
        arrives.

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


class MaintenanceEndpoint(BaseEndpoint):
    """
    The maintenance window of one custom subject. Requires uptimer 1.7.0+.

    A window holds back this subject's PROBLEM notifications until the time you
    choose. Nothing else changes: monitoring runs, incidents open and close, the
    timeline records all of it — so afterwards the outage reads exactly as it
    happened. Recoveries are never held back.

    Four operations: read it, start one, move its end, end it early. Moving the
    end is a real update — the window keeps its identity and its start, and
    nothing that reads it sees the subject briefly leave maintenance.
    """

    def __init__(
        self,
        http: UptimerHttpLib,
        parent_segments: str | list[str] | None = None,
        workspace_id: str | None = None,
    ):
        super().__init__(http, "maintenance", parent_segments)
        self._workspace_id = workspace_id

    def _params(self) -> dict | None:
        return {"workspace_id": self._workspace_id} if self._workspace_id else None

    def get(self) -> MaintenanceWindow | None:
        """
        Return the window running on this subject, or None.

        None is an ANSWER, not an error: a script checking whether it is safe to
        deploy should not have to catch an exception for the ordinary case.
        """
        response = self.http.client.get(self.url, params=self._params())
        result = self.http.parse_response(response=response)
        if result is None:
            return None
        return from_api_maintenance(result)

    def start(self, ends_at: str) -> MaintenanceWindow:
        """
        Start a window now, ending at `ends_at`.

        `ends_at` is an RFC 3339 timestamp and carries its own zone, so there is
        nothing to guess — pass "2026-09-13T18:00:00Z" or your own offset.

        Raises DefaultUptimerApiError when the time has already passed, when a
        window is already running on this subject (cancel it first), when the
        subject is a website check — those are managed from the dashboard — or
        when the caller is not an editor of that workspace.
        """
        response = self.http.client.post(
            self.url,
            params=self._params(),
            json={"ends_at": ends_at},
        )
        result = self.http.parse_response(response=response)
        return from_api_maintenance(result)

    def update_end(self, ends_at: str) -> MaintenanceWindow:
        """
        Move the end of the window that is already running.

        It is an UPDATE, not a cancel and a new window: the window keeps its
        identity and its start, so "since when have we been silencing this?"
        keeps one answer, and nothing that reads it sees the subject briefly
        leave maintenance. Nothing is notified — moving an end time is a
        correction to a plan, not an event.

        `ends_at` is RFC 3339, as it is for `start`. A time that has already
        passed raises rather than ending the window: to stop it now, call
        `cancel()`. So does a subject with nothing running — there is no end to
        move — and a caller who is not an editor.
        """
        response = self.http.client.post(
            f"{self.url}/ends_at",
            params=self._params(),
            json={"ends_at": ends_at},
        )
        result = self.http.parse_response(response=response)
        return from_api_maintenance(result)

    def cancel(self) -> MaintenanceWindow:
        """
        End the running window now, and return it as it was recorded.

        Notifications are back to normal immediately. Raises
        DefaultUptimerApiError when there is nothing to cancel: "it was already
        over" is worth knowing rather than reporting as success.
        """
        response = self.http.client.delete(self.url, params=self._params())
        result = self.http.parse_response(response=response)
        return from_api_maintenance(result)


class SubjectEndpoint(BaseEndpoint):
    """One monitored subject, addressed by its slug."""

    signals: SignalsEndpoint
    rules: RulesEndpoint
    incidents: SubjectIncidentsEndpoint
    maintenance: MaintenanceEndpoint
    delivery: AlertDeliveryEndpoint

    def __init__(
        self,
        http: UptimerHttpLib,
        subject_slug: str,
        parent_segments: str | list[str] | None = None,
        workspace_id: str | None = None,
    ):
        super().__init__(http, _slug(subject_slug, "subject"), parent_segments)
        mine = [*self._parent_segments, self.segment]
        self.signals = SignalsEndpoint(http, mine, workspace_id)
        self.rules = RulesEndpoint(http, mine, workspace_id)
        self.incidents = SubjectIncidentsEndpoint(http, mine, workspace_id)
        self.maintenance = MaintenanceEndpoint(http, mine, workspace_id)
        self.delivery = AlertDeliveryEndpoint(http, mine, workspace_id)


class SubjectsEndpoint(BaseEndpoint):
    """
    The workspace's CUSTOM monitored subjects.

    Uptimer splits its API by subject kind: website monitoring is
    `client.v2.monitoring.websites`, and this is the custom half. Neither one
    serves the other's subjects — a website subject's slug is refused here.

    Two ways in, because there are two things to do with a subject:

    - call it with a slug to reach what is under one — its signals, its rules,
      its incidents, its maintenance and its alert delivery;
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
