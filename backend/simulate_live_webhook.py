import hmac
import hashlib
import json
import httpx
import sys
import time
from app.core.config import settings

# Load config settings
app_secret = settings.META_APP_SECRET
verify_token = settings.META_VERIFY_TOKEN

print(f"Loaded META_APP_SECRET: {app_secret}")
print(f"Loaded META_VERIFY_TOKEN: {verify_token}")

comment_id = f"comment_{int(time.time())}"

# Construct the webhook payload
payload = {
    "object": "instagram",
    "entry": [
        {
            "id": "991122", # Instagram Business Account ID (Sandbox)
            "time": 1774883492,
            "changes": [
                {
                    "field": "comments",
                    "value": {
                        "id": comment_id, # Simulated unique Comment ID
                        "media": {
                            "id": "media_post_1"
                        },
                        "text": "Best", # Keyword trigger text
                        "username": "alex_gym",
                        "timestamp": 1774883492
                    }
                }
            ]
        }
    ]
}

body_bytes = json.dumps(payload).encode("utf-8")

# Compute HMAC signature using APP SECRET
computed_signature = hmac.new(
    app_secret.encode("utf-8"),
    body_bytes,
    hashlib.sha256
).hexdigest()

signature_header = f"sha256={computed_signature}"
headers = {
    "Content-Type": "application/json",
    "x-hub-signature-256": signature_header
}

print("\n--- Payload ---")
print(json.dumps(payload, indent=2))
print(f"Computed Signature Header: {signature_header}")

# Send the request
try:
    print("\nSending Webhook POST request to http://localhost:8000/webhooks/meta...")
    response = httpx.post(
        "http://localhost:8000/webhooks/meta",
        content=body_bytes,
        headers=headers
    )
    print(f"Status Code: {response.status_code}")
    print(f"Response: {response.text}")
except Exception as e:
    print(f"Connection failed: {str(e)}")
    sys.exit(1)
