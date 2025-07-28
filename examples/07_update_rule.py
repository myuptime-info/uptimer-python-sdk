"""Update an existing rule example."""

from uptimer.client import UptimerClient
from uptimer.models.rule import (
    CreateRuleRequest,
    RuleRequest,
    RuleResponse,
    RuleResponseBody,
)

client = UptimerClient(api_key="your-api-key-here")
rule_id = "your-rule-id-here"
workspace_id = "your-workspace-id-here"

# Update a rule
updated_rule = client.v1.rules.update(
    rule_id,
    CreateRuleRequest(
        name="Updated Rule Name",
        interval=120,  # Change to 2 minutes
        workspace_id=workspace_id,
        request=RuleRequest(
            url="https://updated-example.com",
            method="POST",
            content_type="application/json",
            data='{"key": "value"}',
            kind="rule_request",
        ),
        response=RuleResponse(
            statuses=[200, 201],
            body=RuleResponseBody(content="updated expected response"),
            kind="rule_response",
        ),
    ),
)

print(f"Updated rule: {updated_rule.name}")
