"""List rules for a workspace example."""

from uptimer.client import UptimerClient

client = UptimerClient(api_key="your-api-key-here")
workspace_id = "your-workspace-id-here"

# Get all rules for a workspace
rules = client.v1.rules.all(workspace_id)

print("Rules:")
for rule in rules:
    print(rule)
