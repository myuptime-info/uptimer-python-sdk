"""Get a specific rule by ID example."""

from uptimer.client import UptimerClient

client = UptimerClient(api_key="your-api-key-here")
rule_id = "your-rule-id-here"

# Get a specific rule
rule = client.v1.rules.get(rule_id)

print(f"Rule: {rule.name}")
print(f"URL: {rule.request.url}")
print(f"Interval: {rule.interval} seconds")
