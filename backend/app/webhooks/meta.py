import hmac
import hashlib
import datetime
from typing import Dict, Any
from fastapi import APIRouter, Request, Header, HTTPException, Query
from fastapi.responses import PlainTextResponse
from loguru import logger

from app.core.config import settings
from app.workers.tasks import process_comment_task, process_dm_task

router = APIRouter()


async def verify_webhook_signature(request: Request):
    """Validate that webhook payload was sent by Meta using HMAC-SHA256."""
    signature_header = request.headers.get("x-hub-signature-256")
    if not signature_header:
        logger.error("Missing x-hub-signature-256 header")
        raise HTTPException(status_code=403, detail="Missing signature header")
        
    if not signature_header.startswith("sha256="):
        logger.error("Signature header must start with 'sha256='")
        raise HTTPException(status_code=403, detail="Invalid signature format")
        
    expected_signature = signature_header.split("sha256=")[1]
    
    # Read raw body
    body = await request.body()
    
    # Calculate HMAC
    computed_signature = hmac.new(
        settings.META_APP_SECRET.encode("utf-8"),
        body,
        hashlib.sha256
    ).hexdigest()
    
    if not hmac.compare_digest(expected_signature, computed_signature):
        logger.error("Webhook signature mismatch!")
        raise HTTPException(status_code=403, detail="Signature verification failed")


@router.get("/meta", response_class=PlainTextResponse)
async def verify_webhook(
    hub_mode: str = Query(..., alias="hub.mode"),
    hub_challenge: str = Query(..., alias="hub.challenge"),
    hub_verify_token: str = Query(..., alias="hub.verify_token"),
):
    """
    Handle Meta Webhook verification handshake.
    GET /webhooks/meta
    """
    logger.info("Received Meta Webhook validation handshake request")
    if hub_mode == "subscribe" and hub_verify_token == settings.META_VERIFY_TOKEN:
        logger.info("Webhook subscription verified successfully")
        return hub_challenge
        
    logger.warning("Webhook subscription validation failed: Invalid token")
    raise HTTPException(status_code=403, detail="Verification token mismatch")


@router.post("/meta")
async def receive_webhook(request: Request):
    """
    Handle Meta Webhook event notifications.
    POST /webhooks/meta
    """
    # 1. Verify signature
    await verify_webhook_signature(request)
    
    # 2. Parse JSON body
    try:
        payload = await request.json()
    except Exception as e:
        logger.error(f"Failed to parse webhook JSON body: {str(e)}")
        raise HTTPException(status_code=400, detail="Invalid JSON body")
        
    logger.info(f"Received Meta Webhook event: {payload.get('object')}")
    
    # Check if object is instagram
    if payload.get("object") != "instagram":
        # We only handle instagram object updates
        return {"status": "ignored", "reason": "not_instagram_object"}

    entries = payload.get("entry", [])
    events_queued = 0
    
    for entry in entries:
        instagram_business_account_id = entry.get("id")
        changes = entry.get("changes", [])
        
        for change in changes:
            field = change.get("field")
            if field == "comments":
                value = change.get("value", {})
                comment_id = value.get("id")
                text = value.get("text")
                
                # Retrieve media ID
                media = value.get("media", {})
                media_id = media.get("id") if isinstance(media, dict) else media
                
                # Retrieve username and commenter_id (scoped user ID)
                from_obj = value.get("from")
                username = value.get("username")
                commenter_id = None
                if isinstance(from_obj, dict):
                    commenter_id = from_obj.get("id")
                    if not username:
                        username = from_obj.get("username")
                
                # Retrieve timestamp (can be epoch timestamp)
                timestamp_raw = value.get("timestamp", datetime.datetime.utcnow().timestamp())
                try:
                    if isinstance(timestamp_raw, (int, float)):
                        dt = datetime.datetime.fromtimestamp(timestamp_raw, tz=datetime.timezone.utc)
                    else:
                        dt = datetime.datetime.fromisoformat(str(timestamp_raw))
                    timestamp_str = dt.isoformat()
                except Exception:
                    timestamp_str = datetime.datetime.utcnow().isoformat()

                if all([instagram_business_account_id, comment_id, media_id, text, username]):
                    logger.info(f"Queueing process_comment_task for comment: {comment_id}")
                    # Dispatch to Celery background task
                    process_comment_task.delay(
                        instagram_business_account_id=instagram_business_account_id,
                        comment_id=comment_id,
                        media_id=media_id,
                        text=text,
                        username=username,
                        timestamp_str=timestamp_str,
                        commenter_id=commenter_id
                    )
                    events_queued += 1
                else:
                    logger.warning(
                        f"Missing fields in comment change payload: comment_id={comment_id}, "
                        f"media_id={media_id}, text={text}, username={username}"
                    )

        # Check for direct messages: entry.messaging
        messaging_events = entry.get("messaging", [])
        for messaging in messaging_events:
            sender = messaging.get("sender", {})
            recipient = messaging.get("recipient", {})
            message = messaging.get("message", {})
            
            sender_id = sender.get("id")
            recipient_id = recipient.get("id")
            message_id = message.get("mid")
            text = message.get("text")
            
            timestamp_raw = messaging.get("timestamp")
            try:
                if timestamp_raw:
                    dt = datetime.datetime.fromtimestamp(timestamp_raw / 1000.0, tz=datetime.timezone.utc)
                else:
                    dt = datetime.timezone.utc
                timestamp_str = dt.isoformat()
            except Exception:
                timestamp_str = datetime.datetime.utcnow().isoformat()
                
            if all([instagram_business_account_id, sender_id, recipient_id, message_id, text]):
                logger.info(f"Queueing process_dm_task for message: {message_id}")
                process_dm_task.delay(
                    instagram_business_account_id=instagram_business_account_id,
                    sender_id=sender_id,
                    recipient_id=recipient_id,
                    message_id=message_id,
                    text=text,
                    timestamp_str=timestamp_str
                )
                events_queued += 1
            else:
                logger.warning(
                    f"Missing fields in messaging payload: sender_id={sender_id}, recipient_id={recipient_id}, "
                    f"message_id={message_id}, text={text}"
                )

    return {"status": "success", "events_queued": events_queued}
