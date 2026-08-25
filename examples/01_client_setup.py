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

# API v2 lives under client.v2 — the SDK keeps the API version visible, because
# the API itself is versioned by path.
print("Available: client.v2.workspaces, client.v2.locations,")
print("           client.v2.incidents, client.v2.monitoring.websites")
