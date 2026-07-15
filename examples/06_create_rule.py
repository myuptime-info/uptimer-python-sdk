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

# Regions are matched by name. List them to see what's available on your instance;
# a rule with no regions is never checked and stays at "No Data", so assign at least one.
region_names = [region.name for region in client.v1.regions.all()]

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
        regions=region_names[:1],  # assign the first available region
    ),
)

print(f"Created rule: {rule.name} (ID: {rule.id})")
print(f"Assigned regions: {rule.regions}")
