from __future__ import annotations

from dataclasses import asdict
from typing import TYPE_CHECKING

from uptimer.endpoints.endpoint import BaseEndpoint
from uptimer.models.v2 import (
    DeleteDestinationResponse,
    DeleteTransformationResponse,
    TestDeliveryResponse,
    from_api_delivery_record,
    from_api_destination,
    from_api_transformation,
    from_api_transformation_preview,
    samples_from_api,
)

if TYPE_CHECKING:
    from uptimer.http import UptimerHttpLib
    from uptimer.models.v2 import (
        CreateDestinationRequest,
        CreateTransformationRequest,
        DeliveryRecord,
        Destination,
        Transformation,
        TransformationPreview,
        TransformationSample,
        UpdateDestinationRequest,
        UpdateTransformationRequest,
    )


def _params(workspace_id: str | None, **extra: str | int | None) -> dict | None:
    """
    Build the query for a notifications call.

    `workspace_id` is optional and settles an ambiguity rather than being
    required: these resources have no slug of their own, so the server searches
    your memberships when it is absent and says so if the answer is more than
    one.
    """
    params: dict[str, str | int] = {"workspace_id": workspace_id} if workspace_id else {}
    params.update({key: value for key, value in extra.items() if value is not None})
    return params or None


class DestinationsEndpoint(BaseEndpoint):
    """
    The workspace's alert destinations (uptimer 1.8.0).

    A destination is one place alerts can go: a Slack incoming webhook or any
    HTTP endpoint. Which SUBJECT sends to which of them is decided elsewhere —
    `client.v2.subjects(slug).delivery` — because that choice belongs to the
    subject, not to the workspace.

    Reading these needs the EDITOR role, not just membership: a destination
    holds a webhook URL, and a URL is enough for anyone holding it to post into
    your channel.
    """

    def __init__(
        self,
        http: UptimerHttpLib,
        parent_segments: str | list[str] | None = None,
    ):
        super().__init__(http, "destinations", parent_segments)

    def all(self, workspace_id: str | None = None) -> list[Destination]:
        """Every destination in the workspace, by name."""
        response = self.http.client.get(self.url, params=_params(workspace_id))
        result = self.http.parse_response(response=response)
        return [from_api_destination(item) for item in result]

    def get(self, destination_id: int, workspace_id: str | None = None) -> Destination:
        """One destination by id."""
        response = self.http.client.get(
            f"{self.url}/{destination_id}",
            params=_params(workspace_id),
        )
        result = self.http.parse_response(response=response)
        return from_api_destination(result)

    def create(
        self,
        destination: CreateDestinationRequest,
        workspace_id: str | None = None,
    ) -> Destination:
        """
        Create one, enabled.

        The FIRST destination in a workspace becomes its default whether or not
        it asks: a workspace whose only destination is not the default notifies
        nobody.

        Raises DefaultUptimerApiError on a name that is empty or already used, an
        address that is not http(s), a type that is neither slack nor webhook,
        and a transformation that is not in this workspace.
        """
        response = self.http.client.post(
            self.url,
            params=_params(workspace_id),
            json=asdict(destination),
        )
        result = self.http.parse_response(response=response)
        return from_api_destination(result)

    def update(
        self,
        destination_id: int,
        destination: UpdateDestinationRequest,
        workspace_id: str | None = None,
    ) -> Destination:
        """
        Replace name, channel, URL, default and transformation.

        The TYPE cannot be changed: a Slack hook and a plain webhook carry
        different payloads, and converting one silently is how a channel goes
        quiet. Delete and recreate instead.
        """
        response = self.http.client.post(
            f"{self.url}/{destination_id}",
            params=_params(workspace_id),
            json=asdict(destination),
        )
        result = self.http.parse_response(response=response)
        return from_api_destination(result)

    def set_enabled(
        self,
        destination_id: int,
        enabled: bool,  # noqa: FBT001
        workspace_id: str | None = None,
    ) -> Destination:
        """
        Switch one on or off.

        A disabled destination keeps its name, its address and every subject
        selection pointing at it, and sends nothing until it is switched back
        on.
        """
        response = self.http.client.post(
            f"{self.url}/{destination_id}/enabled",
            params=_params(workspace_id),
            json={"enabled": enabled},
        )
        result = self.http.parse_response(response=response)
        return from_api_destination(result)

    def make_default(
        self,
        destination_id: int,
        workspace_id: str | None = None,
    ) -> Destination:
        """
        Make this the workspace fallback.

        It is what a subject sends to when it has chosen nothing of its own.
        Moving the default clears it from whichever destination held it. A
        DISABLED destination is refused: a fallback that cannot receive anything
        is silence wearing a label.
        """
        response = self.http.client.post(
            f"{self.url}/{destination_id}/default",
            params=_params(workspace_id),
        )
        result = self.http.parse_response(response=response)
        return from_api_destination(result)

    def send_test(
        self,
        destination_id: int,
        workspace_id: str | None = None,
    ) -> TestDeliveryResponse:
        """
        Send one real test message.

        It is a REAL send: the same render, the same transport and the same
        delivery record an alert produces, so a template that works here works
        during an outage.

        A destination that refuses the message raises DefaultUptimerApiError
        carrying the far end's own words — the request was fine, the destination
        was not — and the attempt is recorded either way.
        """
        response = self.http.client.post(
            f"{self.url}/{destination_id}/test",
            params=_params(workspace_id),
        )
        result = self.http.parse_response(response=response)
        return TestDeliveryResponse(
            message=result["message"],
            destination_id=result["destination_id"],
            workspace_id=result["workspace_id"],
        )

    def delete(
        self,
        destination_id: int,
        workspace_id: str | None = None,
    ) -> DeleteDestinationResponse:
        """
        Delete one, and every subject selection naming it.

        The records it already wrote stay.

        Deleting the default PROMOTES NOBODY: a workspace is allowed to have
        none, and handing the role to whichever destination is next would start
        sending a channel alerts it never asked for. Check `was_default` on the
        answer. Delivery records stay — they record what was sent, and that
        remains true after the destination is gone.
        """
        response = self.http.client.delete(
            f"{self.url}/{destination_id}",
            params=_params(workspace_id),
        )
        result = self.http.parse_response(response=response)
        return DeleteDestinationResponse(
            message=result["message"],
            destination_id=result["destination_id"],
            workspace_id=result["workspace_id"],
            was_default=result.get("was_default", False),
        )


class TransformationsEndpoint(BaseEndpoint):
    """
    The workspace's outbound payload templates (uptimer 1.8.0).

    A transformation is a named template for what a destination receives — a
    PagerDuty event, your own JSON, a line of text. A destination with none gets
    Uptimer's built-in Slack-shaped message.
    """

    def __init__(
        self,
        http: UptimerHttpLib,
        parent_segments: str | list[str] | None = None,
    ):
        super().__init__(http, "transformations", parent_segments)

    def all(self, workspace_id: str | None = None) -> list[Transformation]:
        """Every transformation in the workspace, by name."""
        response = self.http.client.get(self.url, params=_params(workspace_id))
        result = self.http.parse_response(response=response)
        return [from_api_transformation(item) for item in result]

    def samples(self) -> list[TransformationSample]:
        """
        Return the three messages every template is judged against.

        Each carries every field it may read. No workspace: the samples are the product's, not a tenant's. They are
        the same fixtures the editor shows and the same ones a save is judged
        against, so you can render locally and get the answer this API would
        give.
        """
        response = self.http.client.get(f"{self.url}/samples")
        result = self.http.parse_response(response=response)
        return samples_from_api(result)

    def preview(
        self,
        template: str,
        workspace_id: str | None = None,
    ) -> TransformationPreview:
        """
        Render a template against every sample, storing nothing.

        `passed` is exactly the condition a create or an update enforces, so
        this answers "will a write be accepted" before attempting one — and
        says, per sample, what is wrong when it will not.
        """
        response = self.http.client.post(
            f"{self.url}/preview",
            params=_params(workspace_id),
            json={"template": template},
        )
        result = self.http.parse_response(response=response)
        return from_api_transformation_preview(result)

    def get(
        self,
        transformation_id: int,
        workspace_id: str | None = None,
    ) -> Transformation:
        """One transformation by id."""
        response = self.http.client.get(
            f"{self.url}/{transformation_id}",
            params=_params(workspace_id),
        )
        result = self.http.parse_response(response=response)
        return from_api_transformation(result)

    def create(
        self,
        transformation: CreateTransformationRequest,
        workspace_id: str | None = None,
    ) -> Transformation:
        """
        Store one, if it renders every sample.

        There is no force flag. A template that breaks one message raises
        DefaultUptimerApiError naming the sample that broke, because a template
        that cannot render a recovery would fail at the moment it mattered.
        """
        response = self.http.client.post(
            self.url,
            params=_params(workspace_id),
            json=asdict(transformation),
        )
        result = self.http.parse_response(response=response)
        return from_api_transformation(result)

    def update(
        self,
        transformation_id: int,
        transformation: UpdateTransformationRequest,
        workspace_id: str | None = None,
    ) -> Transformation:
        """
        Replace its name and template, judged by the same rule.

        A refused edit leaves the STORED template exactly as it was.
        """
        response = self.http.client.post(
            f"{self.url}/{transformation_id}",
            params=_params(workspace_id),
            json=asdict(transformation),
        )
        result = self.http.parse_response(response=response)
        return from_api_transformation(result)

    def delete(
        self,
        transformation_id: int,
        workspace_id: str | None = None,
    ) -> DeleteTransformationResponse:
        """Delete one. Destinations using it fall back to the built-in message."""
        response = self.http.client.delete(
            f"{self.url}/{transformation_id}",
            params=_params(workspace_id),
        )
        result = self.http.parse_response(response=response)
        return DeleteTransformationResponse(
            message=result["message"],
            transformation_id=result["transformation_id"],
            workspace_id=result["workspace_id"],
        )


class DeliveriesEndpoint(BaseEndpoint):
    """
    The delivery log (uptimer 1.8.0).

    What was actually sent, and what the far end said. It is a READ. Nothing here sends, resends or changes a destination — Uptimer
    sends once, in the background, and this is the record. Attempts are kept 30
    days.
    """

    def __init__(
        self,
        http: UptimerHttpLib,
        parent_segments: str | list[str] | None = None,
    ):
        super().__init__(http, "deliveries", parent_segments)

    def all(
        self,
        workspace_id: str | None = None,
        destination_id: int | None = None,
        undelivered: bool = False,  # noqa: FBT001, FBT002
    ) -> list[DeliveryRecord]:
        """
        Return recorded attempts, newest first.

        `destination_id` narrows the log to one destination, and `undelivered`
        to the attempts that were not accepted — the two filters the Delivery
        page has.
        """
        params = _params(
            workspace_id,
            destination_id=destination_id,
            undelivered="true" if undelivered else None,
        )
        response = self.http.client.get(self.url, params=params)
        result = self.http.parse_response(response=response)
        return [from_api_delivery_record(item) for item in result]


class NotificationsEndpoint(BaseEndpoint):
    """
    Where a workspace's alerts can go, and what they look like (uptimer 1.8.0).

    Three collections, and one thing that is NOT here: which destinations a
    subject tells. That belongs to the subject —
    `client.v2.subjects(slug).delivery` and
    `client.v2.monitoring.websites(id).delivery` — because a workspace-wide
    route says one thing for everything a team watches, and the point of this
    release is that it no longer has to.
    """

    destinations: DestinationsEndpoint
    transformations: TransformationsEndpoint
    deliveries: DeliveriesEndpoint

    def __init__(
        self,
        http: UptimerHttpLib,
        parent_segments: str | list[str] | None = None,
    ):
        super().__init__(http, "notifications", parent_segments)
        mine = [*self._parent_segments, self.segment]
        self.destinations = DestinationsEndpoint(http, mine)
        self.transformations = TransformationsEndpoint(http, mine)
        self.deliveries = DeliveriesEndpoint(http, mine)
