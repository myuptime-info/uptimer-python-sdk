from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

# Where a workspace's alerts can go (uptimer 1.8.0).
#
# Before 1.8.0 a workspace had one webhook URL and every alert in it went there.
# Now it has as many DESTINATIONS as it needs, each subject chooses which of
# them it tells, a TRANSFORMATION changes the shape one receives, and every
# attempt is recorded for 30 days.

# What a destination speaks. Fixed at creation: a Slack hook and a plain webhook
# carry different payloads, and converting one silently is how a channel goes
# quiet.
DESTINATION_TYPE_SLACK = "slack"
DESTINATION_TYPE_WEBHOOK = "webhook"

# The three things a subject can send. A reminder rides with `problem` — it is a
# message about time passing rather than a fourth kind of event — which is why
# there is no fourth value.
ALERT_KIND_PROBLEM = "problem"
ALERT_KIND_NO_DATA = "no_data"
ALERT_KIND_RECOVERY = "recovery"

ALERT_KINDS = (ALERT_KIND_PROBLEM, ALERT_KIND_NO_DATA, ALERT_KIND_RECOVERY)

# What an empty delivery table means right now. The server answers it rather
# than leaving a client to model the fallback itself.
FALLBACK_WORKSPACE_DEFAULT = "workspace_default"
FALLBACK_SILENCE = "silence"

# Whether an attempt arrived.
DELIVERY_STATUS_DELIVERED = "delivered"
DELIVERY_STATUS_FAILED = "failed"


@dataclass
class CreateDestinationRequest:
    """
    One destination to add.

    `default` is a request, not a promise: the FIRST destination in a workspace
    becomes the default whether or not it asks, because a workspace whose only
    destination is not the default notifies nobody.

    `channel` is Slack-only and optional — "#alerts" and "alerts" are the same
    channel, and the leading '#' is dropped before it is stored. A modern Slack
    webhook is already bound to one, so leaving it empty is normal.

    `transformation_id` is None for Uptimer's own message. None IS the default,
    not "unset".
    """

    name: str
    url: str
    destination_type: str = DESTINATION_TYPE_SLACK
    channel: str = ""
    default: bool = False
    transformation_id: int | None = None


@dataclass
class UpdateDestinationRequest:
    """
    What may be changed about a destination.

    The TYPE is not here, and that is deliberate: delete and recreate instead.
    """

    name: str
    url: str
    channel: str = ""
    default: bool = False
    transformation_id: int | None = None


@dataclass
class Destination:
    """
    One place a workspace's alerts can go.

    `url` comes back IN FULL — you set it and need it back for a
    read-modify-write — which also means a log of these objects is a log of
    webhook URLs. Treat it as the credential it is.

    `channel` is returned WITHOUT its '#', as stored. `default` marks the
    workspace fallback: at most one destination has it, and a workspace is
    allowed to have none.
    """

    id: int
    name: str
    destination_type: str
    channel: str
    url: str
    enabled: bool
    default: bool
    workspace_id: str
    transformation_id: int | None = None
    created_at: str = ""
    updated_at: str = ""
    kind: str = "notification_destination"

    @property
    def is_slack(self) -> bool:
        """Whether this destination carries a Slack channel."""
        return self.destination_type == DESTINATION_TYPE_SLACK

    @property
    def is_transformed(self) -> bool:
        """Whether a template shapes this destination's payload."""
        return self.transformation_id is not None


@dataclass
class DeleteDestinationResponse:
    """
    What the server says after deleting a destination.

    `was_default` is worth reading: deleting the default promotes nobody, so a
    workspace that had one now has none, and subjects that had chosen nothing
    now send nothing.
    """

    message: str
    destination_id: int
    workspace_id: str
    was_default: bool = False


@dataclass
class TestDeliveryResponse:
    """
    What the server says after a test send.

    The send is real: the same render, the same transport and the same delivery
    record an alert produces. A destination that refuses the message raises
    instead — the request was fine, the destination was not — and the attempt is
    recorded either way.
    """

    message: str
    destination_id: int
    workspace_id: str


@dataclass
class CreateTransformationRequest:
    """
    One named payload template to store.

    It is stored ONLY if it renders all three sample messages. There is no force
    flag: ask `preview()` first if you want the answer before writing.
    """

    name: str
    template: str


@dataclass
class UpdateTransformationRequest:
    """
    A transformation's name and template.

    Judged by the same rule as a create, and a refused edit leaves the STORED
    template exactly as it was — a template that works today cannot be replaced
    by one that fails during an outage.
    """

    name: str
    template: str


@dataclass
class Transformation:
    """
    One named outbound template.

    `content_type` is what a body of this shape is sent as, so a client can see
    whether its template reads as JSON without guessing: a template starting
    with '{' or '[' is treated as JSON, its values escaped as they are
    substituted, and the result has to parse.
    """

    id: int
    name: str
    template: str
    content_type: str
    workspace_id: str
    created_at: str = ""
    updated_at: str = ""
    kind: str = "notification_transformation"


@dataclass
class DeleteTransformationResponse:
    """
    What the server says after deleting a transformation.

    Destinations using it fall back to Uptimer's built-in message.
    """

    message: str
    transformation_id: int
    workspace_id: str


@dataclass
class TransformationSample:
    """
    One of the three messages a template is judged against.

    `fields` is the whole published vocabulary with a real value for each, so a
    client can render locally and get the answer this API would give.
    """

    alert_kind: str
    label: str
    fields: dict[str, str] = field(default_factory=dict)


@dataclass
class PreviewResult:
    """What one sample rendered to, or why it did not."""

    alert_kind: str
    label: str
    ok: bool
    output: str = ""
    error: str = ""


@dataclass
class TransformationPreview:
    """
    A template rendered against every sample.

    `passed` is exactly the condition a create or an update enforces, so this
    answers "will a write be accepted" without attempting one. Nothing is
    stored.
    """

    passed: bool
    results: list[PreviewResult] = field(default_factory=list)
    kind: str = "notification_transformation_preview"


@dataclass
class DeliverySelection:
    """
    One destination on a subject, and what it hears.

    `alert_kinds` is any of problem, no_data, recovery — at least one. A row
    that receives nothing is a row that means nothing, and the server refuses
    it.
    """

    destination_id: int
    alert_kinds: list[str] = field(default_factory=list)
    destination_name: str = ""


@dataclass
class SubjectAlertDelivery:
    """
    One subject's whole alert delivery table.

    `fallback` is filled ONLY when `selections` is empty, and says which of the
    two things that means: "workspace_default" or "silence". A subject with rows
    of its own does not also send to the default — the table replaces the
    fallback rather than adding to it.
    """

    subject_id: str
    workspace_id: str
    selections: list[DeliverySelection] = field(default_factory=list)
    default_destination_id: int | None = None
    fallback: str = ""
    kind: str = "subject_alert_delivery"

    @property
    def uses_workspace_default(self) -> bool:
        """Whether this subject currently falls back to the workspace default."""
        return self.fallback == FALLBACK_WORKSPACE_DEFAULT

    @property
    def is_silent(self) -> bool:
        """Whether nothing at all is sent for this subject right now."""
        return self.fallback == FALLBACK_SILENCE


@dataclass
class DeliveryRecord:
    """
    One recorded attempt.

    `destination_name` and `destination_type` are the destination AS IT WAS at
    the attempt: the log outlives the destination it describes, so a rename or a
    delete later leaves the record still saying where the message went. The
    webhook URL is never recorded.

    Records are kept 30 days.
    """

    id: int
    destination_id: int
    destination_name: str
    destination_type: str
    alert_kind: str
    status: str
    payload: str
    at: str
    error: str = ""
    kind: str = "notification_delivery"

    @property
    def delivered(self) -> bool:
        """Whether the far end accepted this message."""
        return self.status == DELIVERY_STATUS_DELIVERED


def samples_from_api(data: list[dict[str, Any]]) -> list[TransformationSample]:
    """Read the sample vocabulary. These carry no `kind` of their own."""
    return [
        TransformationSample(
            alert_kind=item.get("alert_kind", ""),
            label=item.get("label", ""),
            fields=item.get("fields") or {},
        )
        for item in data
    ]
