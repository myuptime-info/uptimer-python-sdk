"""List all regions example."""

from uptimer.client import UptimerClient

client = UptimerClient(api_key="your-api-key-here")

# Get all regions
regions = client.v1.regions.all()

print("Regions:")
for region in regions:
    print(region)
