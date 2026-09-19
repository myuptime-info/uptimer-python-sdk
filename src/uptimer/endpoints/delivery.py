from __future__ import annotations

from typing import TYPE_CHECKING

from uptimer.endpoints.endpoint import BaseEndpoint
from uptimer.models.v2 import from_api_subject_delivery

if TYPE_CHECKING:
    from uptimer.http import UptimerHttpLib
    from uptimer.models.v2 import DeliverySelection, SubjectAlertDelivery


class AlertDeliveryEndpoint(BaseEndpoint):
    """
    Which destinations ONE subject tells, and about what (uptimer 1.8.0).

    The choice lives on the subject rather than on the workspace, and that is
    the whole point of it: the marketing site telling nobody must not stop the
    payments API paging the on-call.

    Three operations: read the table, replace it, clear it. There is no "add one
    row" — the resource IS the table, so a save says what the subject will have.
    A merge would make a removed row reappear, which is the bug an operator
    reports as "it keeps notifying the channel I deleted".
    """

    def __init__(
        self,
        http: UptimerHttpLib,
        parent_segments: str | list[str] | None = None,
        workspace_id: str | None = None,
    ):
        super().__init__(http, "delivery", parent_segments)
        self._workspace_id = workspace_id

    def _params(self) -> dict | None:
        return {"workspace_id": self._workspace_id} if self._workspace_id else None

    def get(self) -> SubjectAlertDelivery:
        """
        Return the whole table, and what an empty one means right now.

        `fallback` reads "workspace_default" or "silence", so a caller knows
        what happens next without modelling the fallback itself.
        """
        response = self.http.client.get(self.url, params=self._params())
        result = self.http.parse_response(response=response)
        return from_api_subject_delivery(result)

    def replace(self, selections: list[DeliverySelection]) -> SubjectAlertDelivery:
        """
        Replace the table with these rows.

        Each row needs at least one alert kind — problem, no_data, recovery — a
        destination of this workspace, and no duplicate destination. An empty
        list is a real instruction ("use the workspace default, or send nothing
        if there is none") and does the same as `clear()`.

        Saving changes delivery ONLY: signals, rules, incidents, acknowledgement
        and maintenance are untouched, and nothing is sent by saving.
        """
        body = {
            "selections": [
                {
                    "destination_id": row.destination_id,
                    "alert_kinds": list(row.alert_kinds),
                }
                for row in selections
            ],
        }
        response = self.http.client.post(self.url, params=self._params(), json=body)
        result = self.http.parse_response(response=response)
        return from_api_subject_delivery(result)

    def clear(self) -> SubjectAlertDelivery:
        """
        Empty the table.

        The workspace default then speaks for this subject — or, with no
        default, nothing does.
        """
        response = self.http.client.delete(self.url, params=self._params())
        result = self.http.parse_response(response=response)
        return from_api_subject_delivery(result)
