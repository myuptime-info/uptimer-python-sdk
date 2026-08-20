"""Set up a client and confirm the server speaks API v2."""

from uptimer.client import UptimerClient
from uptimer.errors import IncompatibleServerError

client = UptimerClient(
    api_key="your-api-key-here",
    base_url="https://myuptime.info/api",  # or your self-hosted URL + /api
)

# Optional but recommended: fail fast with a message that names the fix, rather
# than a 404 on the first real call.
try:
    print("Server version:", client.check_compatibility())
except IncompatibleServerError as exc:
    raise SystemExit(str(exc)) from exc

print("Available: client.workspaces, client.locations,")
print("           client.incidents, client.monitoring.websites")
