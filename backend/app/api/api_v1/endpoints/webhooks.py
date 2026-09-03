"""
Webhook management endpoints.

Provides:
  GET  /api/v1/webhooks/status   – Returns current webhook configuration & verify token
  POST /api/v1/webhooks/test     – Simulates a webhook comment event (dev/test only)
"""
import datetime
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from loguru import logger

from app.api.deps import get_current_user, get_db
from app.core.config import settings
from app.workers.tasks import process_comment_task, process_facebook_comment_task

router = APIRouter()


@router.get("/status", summary="Webhook configuration status")
async def get_webhook_status(
    current_user=Depends(get_current_user),
):
    """
    Returns the current Meta Webhook configuration details.
    The VERIFY_TOKEN must be pasted into the Meta App Dashboard when setting up the webhook.
    """
    return {
        "webhook_endpoint": "/webhooks/meta",
        "verify_token": settings.META_VERIFY_TOKEN,
        "meta_app_id": settings.META_APP_ID,
        "signature_verification_enabled": bool(settings.META_APP_SECRET),
        "supported_objects": ["instagram", "page"],
        "supported_fields": {
            "instagram": ["comments", "messages"],
            "page": ["feed"],
        },
        "instructions": {
            "step1": "Copy the verify_token above",
            "step2": "Go to Meta App Dashboard → Webhooks → Add Subscription",
            "step3": "Set Callback URL to: https://<your-domain>/webhooks/meta",
            "step4": "Paste the verify_token and click Verify",
            "step5": "Subscribe to 'comments' field for Instagram / 'feed' field for Facebook Page",
            "dev_note": "For local development, use ngrok: ngrok http 8000"
        }
    }


@router.post("/test/instagram-comment", summary="Simulate an Instagram comment webhook event (dev only)")
async def test_instagram_comment_webhook(
    instagram_business_account_id: str,
    comment_id: str,
    media_id: str,
    text: str,
    username: str,
    commenter_id: str = None,
    current_user=Depends(get_current_user),
):
    """
    Simulate a Meta webhook comment event for an Instagram post.
    Useful for testing automation flows without waiting for a real comment.
    Only available in development.
    """
    timestamp_str = datetime.datetime.utcnow().isoformat()

    logger.info(
        f"[TEST] Simulating Instagram webhook comment: "
        f"comment_id={comment_id} media_id={media_id} user={username} text='{text}'"
    )

    process_comment_task.delay(
        instagram_business_account_id=instagram_business_account_id,
        comment_id=comment_id,
        media_id=media_id,
        text=text,
        username=username,
        timestamp_str=timestamp_str,
        commenter_id=commenter_id,
    )

    return {
        "status": "queued",
        "message": "Instagram comment task dispatched to Celery worker",
        "comment_id": comment_id,
        "media_id": media_id,
        "text": text,
        "username": username,
        "timestamp": timestamp_str,
    }


@router.post("/test/facebook-comment", summary="Simulate a Facebook page comment webhook event (dev only)")
async def test_facebook_comment_webhook(
    facebook_page_id: str,
    comment_id: str,
    post_id: str,
    text: str,
    username: str,
    commenter_id: str = None,
    current_user=Depends(get_current_user),
):
    """
    Simulate a Meta webhook comment event for a Facebook Page post.
    Useful for testing automation flows without waiting for a real comment.
    Only available in development.
    """
    timestamp_str = datetime.datetime.utcnow().isoformat()

    logger.info(
        f"[TEST] Simulating Facebook webhook comment: "
        f"comment_id={comment_id} post_id={post_id} user={username} text='{text}'"
    )

    process_facebook_comment_task.delay(
        facebook_page_id=facebook_page_id,
        comment_id=comment_id,
        media_id=post_id,
        text=text,
        username=username,
        timestamp_str=timestamp_str,
        commenter_id=commenter_id,
    )

    return {
        "status": "queued",
        "message": "Facebook comment task dispatched to Celery worker",
        "comment_id": comment_id,
        "post_id": post_id,
        "text": text,
        "username": username,
        "timestamp": timestamp_str,
    }
