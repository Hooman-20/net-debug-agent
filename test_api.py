"""Step 1: confirm the Meta Model API works."""
import sys

from model import MODEL, _get_client, ask_model

# List models (not all servers support this; failure here is not fatal)
try:
    ids = [m.id for m in _get_client().models.list().data]
    print("Available models:", ", ".join(ids))
except Exception as e:
    print("Could not list models:", e)

try:
    reply = ask_model([{"role": "user", "content": "Reply with exactly: API OK"}])
except Exception as e:
    print(f"FAIL ({MODEL}): {e}")
    sys.exit(1)

print(f"Model {MODEL} replied: {reply!r}")
print("PASS" if "API OK" in reply else "WARN: unexpected reply, but the API responded")
