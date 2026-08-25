"""List the locations checks can run from.

API v1 called these regions; v2 uses the product's word.
"""

from uptimer.client import UptimerClient

client = UptimerClient(
    api_key="your-api-key-here", base_url="https://myuptime.info/api"
)

for location in client.v2.locations.all():
    print(f"{location.name}: {location.active_workers_count} active worker(s)")
