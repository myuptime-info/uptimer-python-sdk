from __future__ import annotations

from dataclasses import dataclass


@dataclass
class RuleRequest:
    url: str  # request URL
    method: str  # HTTP method (GET, POST, etc.)
    content_type: str  # content type for the request
    data: str  # request data/payload
    kind: str = "rule_request"


@dataclass
class RuleResponseBody:
    content: str  # expected response body content
    kind: str = "rule_response_body"


@dataclass
class RuleResponse:
    statuses: list[int]  # list of acceptable HTTP status codes
    body: RuleResponseBody  # expected response body
    kind: str = "rule_response"


@dataclass
class BaseRule:
    """Base class containing common rule fields."""

    name: str  # rule name
    interval: int  # check interval in seconds
    workspace_id: str  # workspace id
    request: RuleRequest  # request configuration
    response: RuleResponse  # response validation
    kind: str = "rule"


@dataclass
class Rule(BaseRule):
    """Complete rule with ID for API responses."""

    id: str = ""  # rule id, uuids used for api ids


@dataclass
class CreateRuleRequest(BaseRule):
    """Rule data for creation requests (no ID needed)."""


@dataclass
class DeleteRuleResponse:
    """Response object for successful rule deletion."""

    message: str  # success message
    rule_id: str  # ID of the deleted rule
