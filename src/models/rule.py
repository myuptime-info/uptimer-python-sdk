from __future__ import annotations

from dataclasses import dataclass


@dataclass
class RuleRequest:
    url: str  # request URL
    method: str  # HTTP method (GET, POST, etc.)
    content_type: str  # content type for the request
    data: str  # request data/payload
    kind: str  # always "rule_request"


@dataclass
class RuleResponseBody:
    content: str  # expected response body content


@dataclass
class RuleResponse:
    statuses: list[int]  # list of acceptable HTTP status codes
    body: RuleResponseBody  # expected response body
    kind: str  # always "rule_response"


@dataclass
class Rule:
    id: str  # rule id, uuids used for api ids
    name: str  # rule name
    interval: int  # check interval in seconds
    request: RuleRequest  # request configuration
    response: RuleResponse  # response validation
    kind: str  # always "rule"
