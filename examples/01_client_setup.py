"""Basic client setup example."""

from uptimer.client import UptimerClient

# Initialize the client
client = UptimerClient(
    api_key="your-api-key-here",
    base_url="https://api.uptimer.com",  # or your custom base URL
)

print("Client initialized successfully!")
print(
    "You can now use client.v1.workspaces, client.v1.regions, client.v1.rules",
)
