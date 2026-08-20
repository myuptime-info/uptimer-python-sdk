"""Read what is currently wrong.

Only open incidents come back. Two statuses decide whether to act:

  pending    - failing, but inside the confirm hold; nobody has been notified
  recovering - reporting ok again while the incident is still open
"""

from uptimer.client import UptimerClient
from uptimer.models import STATUS_PENDING

client = UptimerClient(
    api_key="your-api-key-here", base_url="https://myuptime.info/api"
)

workspace = client.workspaces.all()[0]

for incident in client.incidents.all(workspace.id):
    note = " (not yet notified)" if incident.status == STATUS_PENDING else ""
    print(f"{incident.monitor_name}: {incident.status}{note}")
    print(f"  since {incident.trouble_since}")
    print(f"  failing: {incident.locations.failing or '-'}")
    print(f"  unknown: {incident.locations.unknown or '-'}")

# Narrow it to one monitor:
# client.incidents.all(workspace.id, monitor_id="…")
