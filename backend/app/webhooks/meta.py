import hmac
import hashlib
import datetime
from typing import Dict, Any
from fastapi import APIRouter, Request, Header, HTTPException, Query
from fastapi.responses import PlainTextResponse
from loguru import logger

from app.core.config import settings
from app.workers.tasks import process_comment_task, process_facebook_comment_task, process_dm_task

router = APIRouter()


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

async def _verify_webhook_signature(request: Request) -> bytes:
    """
    Validate that the webhook payload was sent by Meta using HMAC-SHA256.
    Returns the raw body bytes so the caller can still parse JSON.
    """
    signature_header = request.headers.get("x-hub-signature-256", "")

    body = await request.body()

    # If Meta app secret is not configured, skip verification (dev mode)
    if not settings.META_APP_SECRET:
        logger.warning("META_APP_SECRET not set – skipping webhook signature verification (dev mode)")
        return body

    if not signature_header or not signature_header.startswith("sha256="):
        logger.error("Missing or malformed x-hub-signature-256 header")
        raise HTTPException(status_code=403, detail="Missing or invalid signature header")

    expected_sig = signature_header[len("sha256="):]
    computed_sig = hmac.new(
        settings.META_APP_SECRET.encode("utf-8"),
        body,
        hashlib.sha256,
    ).hexdigest()

    if not hmac.compare_digest(expected_sig, computed_sig):
        logger.error("Webhook HMAC signature mismatch – rejecting request")
        raise HTTPException(status_code=403, detail="Signature verification failed")

    return body


def _parse_timestamp(raw) -> str:
    """Normalize a raw Meta timestamp (epoch int or ISO string) to an ISO string."""
    try:
        if isinstance(raw, (int, float)):
            dt = datetime.datetime.fromtimestamp(raw, tz=datetime.timezone.utc)
        else:
            dt = datetime.datetime.fromisoformat(str(raw))
        return dt.isoformat()
    except Exception:
        return datetime.datetime.utcnow().isoformat()


# ---------------------------------------------------------------------------
# GET  /webhooks/meta  –  Meta verification handshake
# ---------------------------------------------------------------------------

@router.get("/meta", response_class=PlainTextResponse, tags=["Webhooks"])
async def verify_webhook(
    hub_mode: str = Query(..., alias="hub.mode"),
    hub_challenge: str = Query(..., alias="hub.challenge"),
    hub_verify_token: str = Query(..., alias="hub.verify_token"),
):
    """
    Meta calls this endpoint once when you subscribe / edit a webhook in the
    App Dashboard.  We must echo back hub.challenge if the verify token matches.
    """
    logger.info(f"Received Meta webhook verification handshake (mode={hub_mode})")

    if hub_mode == "subscribe" and hub_verify_token == settings.META_VERIFY_TOKEN:
        logger.info("Webhook verification handshake passed – returning hub.challenge")
        return hub_challenge

    logger.warning("Webhook verification failed: token mismatch or wrong hub.mode")
    raise HTTPException(status_code=403, detail="Verification token mismatch")


# ---------------------------------------------------------------------------
# POST /webhooks/meta  –  Receive real-time events from Meta
# ---------------------------------------------------------------------------

@router.post("/meta", tags=["Webhooks"])
async def receive_webhook(request: Request):
    """
    Main event receiver for Meta Webhooks.

    Handles two object types:
      • "instagram" – Instagram Business comment / DM events
      • "page"      – Facebook Page comment / feed events
    """
    # 1. Verify HMAC signature (or skip in dev mode)
    body = await _verify_webhook_signature(request)

    # 2. Parse JSON body
    try:
        import json as _json
        payload: Dict[str, Any] = _json.loads(body)
    except Exception as exc:
        logger.error(f"Failed to parse webhook JSON body: {exc}")
        raise HTTPException(status_code=400, detail="Invalid JSON body")

    object_type = payload.get("object", "")
    logger.info(f"Received Meta webhook event – object='{object_type}'")

    if object_type == "instagram":
        events_queued = await _handle_instagram_events(payload)
    elif object_type == "page":
        events_queued = await _handle_facebook_events(payload)
    else:
        logger.info(f"Ignoring webhook for unknown object type: '{object_type}'")
        return {"status": "ignored", "reason": f"unsupported_object_type:{object_type}"}

    return {"status": "success", "object": object_type, "events_queued": events_queued}


# ---------------------------------------------------------------------------
# Instagram event handler
# ---------------------------------------------------------------------------

async def _handle_instagram_events(payload: Dict[str, Any]) -> int:
    """
    Process entries from an Instagram webhook payload.
    Dispatches Celery tasks for 'comments' changes and 'messaging' events.
    """
    events_queued = 0

    for entry in payload.get("entry", []):
        ig_business_account_id = entry.get("id")

        # ── Instagram comments ──────────────────────────────────────────────
        for change in entry.get("changes", []):
            if change.get("field") != "comments":
                continue

            value = change.get("value", {})
            comment_id = value.get("id")
            text = value.get("text")

            media = value.get("media", {})
            media_id = media.get("id") if isinstance(media, dict) else media

            from_obj = value.get("from") or {}
            username = value.get("username") or (from_obj.get("username") if isinstance(from_obj, dict) else None)
            commenter_id = from_obj.get("id") if isinstance(from_obj, dict) else None

            timestamp_str = _parse_timestamp(value.get("timestamp"))

            if all([ig_business_account_id, comment_id, media_id, text, username]):
                logger.info(
                    f"Queuing Instagram comment task | comment={comment_id} media={media_id} user={username}"
                )
                process_comment_task.delay(
                    instagram_business_account_id=ig_business_account_id,
                    comment_id=comment_id,
                    media_id=media_id,
                    text=text,
                    username=username,
                    timestamp_str=timestamp_str,
                    commenter_id=commenter_id,
                )
                events_queued += 1
            else:
                logger.warning(
                    f"Skipping Instagram comment change – missing fields: "
                    f"comment_id={comment_id} media_id={media_id} text={text!r} username={username}"
                )

        # ── Instagram DMs (messaging) ───────────────────────────────────────
        for messaging in entry.get("messaging", []):
            sender = messaging.get("sender", {})
            recipient = messaging.get("recipient", {})
            message = messaging.get("message", {})

            sender_id = sender.get("id")
            recipient_id = recipient.get("id")
            message_id = message.get("mid")
            text = message.get("text")
            timestamp_str = _parse_timestamp(
                (messaging.get("timestamp") or 0) / 1000.0
                if messaging.get("timestamp")
                else None
            )

            if all([ig_business_account_id, sender_id, recipient_id, message_id, text]):
                logger.info(f"Queuing Instagram DM task | message_id={message_id} sender={sender_id}")
                process_dm_task.delay(
                    instagram_business_account_id=ig_business_account_id,
                    sender_id=sender_id,
                    recipient_id=recipient_id,
                    message_id=message_id,
                    text=text,
                    timestamp_str=timestamp_str,
                )
                events_queued += 1
            else:
                logger.warning(
                    f"Skipping Instagram DM – missing fields: "
                    f"sender={sender_id} recipient={recipient_id} mid={message_id} text={text!r}"
                )

    return events_queued


# ---------------------------------------------------------------------------
# Facebook Page event handler
# ---------------------------------------------------------------------------

async def _handle_facebook_events(payload: Dict[str, Any]) -> int:
    """
    Process entries from a Facebook Page webhook payload.
    Handles 'feed' changes which include comments on page posts.

    Meta sends page webhook events in this shape:
    {
      "object": "page",
      "entry": [{
        "id": "<page_id>",
        "time": 123456789,
        "changes": [{
          "field": "feed",
          "value": {
            "item":    "comment",
            "verb":    "add",
            "comment_id": "...",
            "post_id":    "...",
            "message":    "...",
            "from": {"id": "...", "name": "..."},
            "created_time": 123456789
          }
        }]
      }]
    }
    """
    events_queued = 0

    for entry in payload.get("entry", []):
        facebook_page_id = entry.get("id")

        for change in entry.get("changes", []):
            field = change.get("field")
            value = change.get("value", {})

            # ── Facebook comments on page posts ─────────────────────────────
            if field == "feed" and value.get("item") == "comment" and value.get("verb") == "add":
                comment_id = value.get("comment_id")
                post_id = value.get("post_id")
                text = value.get("message")

                from_obj = value.get("from") or {}
                commenter_fb_id = from_obj.get("id") if isinstance(from_obj, dict) else None
                username = from_obj.get("name") or commenter_fb_id  # FB gives name, not username

                timestamp_str = _parse_timestamp(value.get("created_time"))

                if all([facebook_page_id, comment_id, post_id, text]):
                    logger.info(
                        f"Queuing Facebook comment task | comment={comment_id} post={post_id} user={username}"
                    )
                    process_facebook_comment_task.delay(
                        facebook_page_id=facebook_page_id,
                        comment_id=comment_id,
                        media_id=post_id,
                        text=text,
                        username=username or "unknown",
                        timestamp_str=timestamp_str,
                        commenter_id=commenter_fb_id,
                    )
                    events_queued += 1
                else:
                    logger.warning(
                        f"Skipping Facebook comment – missing fields: "
                        f"comment_id={comment_id} post_id={post_id} text={text!r}"
                    )

            # ── Facebook reactions / other feed items (ignored) ────────────
            elif field == "feed":
                logger.debug(
                    f"Ignoring Facebook feed change: item={value.get('item')} verb={value.get('verb')}"
                )

    return events_queued
