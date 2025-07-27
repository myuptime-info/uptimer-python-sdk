from __future__ import annotations

from typing import TYPE_CHECKING

from models.rule import Rule, RuleRequest, RuleResponse, RuleResponseBody
from uptimer.endpoints.endpoint import BaseEndpoint

if TYPE_CHECKING:
    from uptimer.http import UptimerHttpLib


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

        rules = []
        for rule_data in result:
            # Deserialize nested objects based on their kind
            if isinstance(rule_data.get("request"), dict):
                rule_data["request"] = RuleRequest(**rule_data["request"])

            if isinstance(rule_data.get("response"), dict):
                response_data = rule_data["response"]
                if isinstance(response_data.get("body"), dict):
                    response_data["body"] = RuleResponseBody(
                        **response_data["body"],
                    )
                rule_data["response"] = RuleResponse(**response_data)

            rules.append(Rule(**rule_data))

        return rules

    def get(self, rule_id: str) -> Rule:
        """Get a single rule by ID."""
        response = self.http.client.get(f"{self.url}/{rule_id}")
        result = self.http.parse_response(response=response)

        # Deserialize nested objects based on their kind
        if isinstance(result.get("request"), dict):
            result["request"] = RuleRequest(**result["request"])

        if isinstance(result.get("response"), dict):
            response_data = result["response"]
            if isinstance(response_data.get("body"), dict):
                response_data["body"] = RuleResponseBody(
                    **response_data["body"],
                )
            result["response"] = RuleResponse(**response_data)

        return Rule(**result)
