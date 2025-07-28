"""Delete a rule example."""

from uptimer.client import UptimerClient

client = UptimerClient(api_key="your-api-key-here")
rule_id = "your-rule-id-here"

# Delete a rule
delete_response = client.v1.rules.delete(rule_id)

print(
    f"Rule deleted: {delete_response.message} (ID: {delete_response.rule_id})",
)
