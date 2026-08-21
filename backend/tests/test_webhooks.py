import hmac
import hashlib
import json
import pytest
from httpx import AsyncClient
from unittest.mock import patch

from app.core.config import settings

def compute_signature(payload_bytes: bytes) -> str:
    """Compute the Meta webhook signature header."""
    sig = hmac.new(
        settings.META_APP_SECRET.encode("utf-8"),
        payload_bytes,
        hashlib.sha256
    ).hexdigest()
    return f"sha256={sig}"


@pytest.mark.asyncio
async def test_webhook_verification_handshake(client: AsyncClient):
    """Test webhook subscription GET validation."""
    params = {
        "hub.mode": "subscribe",
        "hub.challenge": "1158201444",
        "hub.verify_token": settings.META_VERIFY_TOKEN
    }
    response = await client.get("/webhooks/meta", params=params)
    assert response.status_code == 200
    assert response.text == "1158201444"


@pytest.mark.asyncio
async def test_webhook_verification_handshake_invalid_token(client: AsyncClient):
    """Test GET validation rejects incorrect verify tokens."""
    params = {
        "hub.mode": "subscribe",
        "hub.challenge": "1158201444",
        "hub.verify_token": "wrong_token_here"
    }
    response = await client.get("/webhooks/meta", params=params)
    assert response.status_code == 403
    assert "Verification token mismatch" in response.json()["detail"]


@pytest.mark.asyncio
async def test_webhook_post_signature_mismatch(client: AsyncClient):
    """Test webhook POST rejects requests with invalid signatures."""
    payload = {"object": "instagram", "entry": []}
    headers = {"x-hub-signature-256": "sha256=invalid_signature_hex"}
    response = await client.post("/webhooks/meta", json=payload, headers=headers)
    assert response.status_code == 403
    assert "Signature verification failed" in response.json()["detail"]


@pytest.mark.asyncio
async def test_webhook_post_success_and_queue(client: AsyncClient):
    """Test webhook POST parses comment values and triggers Celery task."""
    payload = {
        "object": "instagram",
        "entry": [
            {
                "id": "98765",  # Instagram Business Account ID
                "time": 1700000000,
                "changes": [
                    {
                        "field": "comments",
                        "value": {
                            "id": "comment_id_100",
                            "text": "Send me the guide please!",
                            "media": {"id": "media_post_1"},
                            "from": {
                                "id": "commenter_user_id_44",
                                "username": "jane_doe"
                            },
                            "timestamp": 1700000000
                        }
                    }
                ]
            }
        ]
    }
    
    payload_bytes = json.dumps(payload).encode("utf-8")
    headers = {
        "x-hub-signature-256": compute_signature(payload_bytes),
        "Content-Type": "application/json"
    }

    # Patch the celery task delay method to verify it was called
    with patch("app.webhooks.meta.process_comment_task.delay") as mock_delay:
        response = await client.post("/webhooks/meta", content=payload_bytes, headers=headers)
        
        assert response.status_code == 200
        assert response.json()["status"] == "success"
        assert response.json()["events_queued"] == 1
        
        # Verify background task dispatched with matching arguments
        mock_delay.assert_called_once()
        kwargs = mock_delay.call_args[1] if mock_delay.call_args[1] else mock_delay.call_args[0]
        # Check positional parameters or kwargs
        args = mock_delay.call_args[0]
        if args:
            assert args[0] == "98765"  # business account id
            assert args[1] == "comment_id_100"  # comment id
            assert args[2] == "media_post_1"  # media id
            assert args[3] == "Send me the guide please!"  # text
            assert args[4] == "jane_doe"  # username
