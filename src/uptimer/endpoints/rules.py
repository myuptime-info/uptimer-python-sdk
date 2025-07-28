from __future__ import annotations

from dataclasses import asdict
from typing import TYPE_CHECKING

from uptimer.endpoints.endpoint import BaseEndpoint
from uptimer.models import from_api_rule
from uptimer.models.rule import DeleteRuleResponse

if TYPE_CHECKING:
    from uptimer.http import UptimerHttpLib
    from uptimer.models.rule import (
        BaseRule,
        CreateRuleRequest,
        Rule,
    )


class RulesEndpoint(BaseEndpoint):
    def __init__(
        self,
        http: UptimerHttpLib,
        parent_segments: str | list[str] | None = None,
    ):
        super().__init__(http, "rules", parent_segments)

    def all(self, workspace_id: str) -> list[Rule]:
        """Get all rules for a specific workspace."""
        params = {"workspace_id": workspace_id}
        response = self.http.client.get(self.url, params=params)
        result = self.http.parse_response(response=response)

        return [from_api_rule(rule_data) for rule_data in result]

    def get(self, rule_id: str) -> Rule:
        """Get a single rule by ID."""
        response = self.http.client.get(f"{self.url}/{rule_id}")
        result = self.http.parse_response(response=response)

        return from_api_rule(result)

    def create(self, rule_data: CreateRuleRequest) -> Rule:
        """Create a new rule."""
        # Use serialization to convert dataclass to dict
        payload = asdict(rule_data)

        response = self.http.client.post(self.url, json=payload)
        result = self.http.parse_response(response=response)

        return from_api_rule(result)

    def update(self, rule_id: str, rule_data: BaseRule) -> Rule:
        """Update an existing rule."""
        # Use serialization to convert dataclass to dict
        payload = asdict(rule_data)

        # Remove id field if present (it's already in the URL)
        payload.pop("id", None)

        response = self.http.client.post(f"{self.url}/{rule_id}", json=payload)
        result = self.http.parse_response(response=response)

        return from_api_rule(result)

    def delete(self, rule_id: str) -> DeleteRuleResponse:
        """Delete a rule by ID."""
        response = self.http.client.delete(f"{self.url}/{rule_id}")

        # parse_response already returns the result field
        result_data = self.http.parse_response(response=response)

        return DeleteRuleResponse(
            message=result_data["message"],
            rule_id=result_data["rule_id"],
        )
