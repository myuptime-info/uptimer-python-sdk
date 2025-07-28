"""List all workspaces example."""

from uptimer.client import UptimerClient

client = UptimerClient(api_key="your-api-key-here")

# Get all workspaces
workspaces = client.v1.workspaces.all()

print("Workspaces:")
for workspace in workspaces:
    print(workspace)
