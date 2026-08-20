"""Create website monitoring for a URL.

Saving it creates the monitoring subject, its built-in HTTP signal and its
Reachability rule — you do not create those separately.
"""

from uptimer.client import UptimerClient
from uptimer.models import (
    AGREEMENT_MAJORITY,
    CreateWebsiteMonitorRequest,
    WebsiteMonitorRequest,
    WebsiteMonitorResponse,
    WebsiteMonitorResponseBody,
)

client = UptimerClient(
    api_key="your-api-key-here", base_url="https://myuptime.info/api"
)

workspace = client.workspaces.all()[0]
locations = [location.name for location in client.locations.all()]

monitor = client.monitoring.websites.create(
    CreateWebsiteMonitorRequest(
        name="Checkout API",
        interval=60,
        workspace_id=workspace.id,
        request=WebsiteMonitorRequest(
            url="https://checkout.example/health",
            method="GET",
        ),
        response=WebsiteMonitorResponse(
            statuses=[200, 201],
            body=WebsiteMonitorResponseBody(content="ok"),
        ),
        locations=locations,
        # How many locations must report a problem before this one does:
        # "any", "majority" or "all". Omit to leave it at the server default.
        agreement=AGREEMENT_MAJORITY,
    ),
)

print(f"created {monitor.id}: {monitor.name} from {monitor.locations}")
