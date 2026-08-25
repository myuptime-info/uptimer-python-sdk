"""List the workspaces an API key can reach."""

from uptimer.client import UptimerClient

client = UptimerClient(
    api_key="your-api-key-here", base_url="https://myuptime.info/api"
)

for workspace in client.v2.workspaces.all():
    print(f"{workspace.id}  {workspace.name}  ({workspace.role})")
