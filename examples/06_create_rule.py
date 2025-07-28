"""Create a new rule example."""

from uptimer.client import UptimerClient
from uptimer.models.rule import (
    CreateRuleRequest,
    RuleRequest,
    RuleResponse,
    RuleResponseBody,
)

client = UptimerClient(api_key="your-api-key-here")
workspace_id = "your-workspace-id-here"

# Create a new rule
rule = client.v1.rules.create(
    CreateRuleRequest(
        name="My Test Rule",
        interval=60,  # Check every 60 seconds
        workspace_id=workspace_id,
        request=RuleRequest(
            url="https://example.com",
            method="GET",
            content_type="application/json",
            data="",
            kind="rule_request",
        ),
        response=RuleResponse(
            statuses=[200, 201, 202],
            body=RuleResponseBody(content="expected response"),
            kind="rule_response",
        ),
    ),
)

print(f"Created rule: {rule.name} (ID: {rule.id})")
