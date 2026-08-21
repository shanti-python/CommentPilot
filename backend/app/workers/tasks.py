import asyncio
import datetime
from celery.utils.log import get_task_logger
from app.core.cel_app import celery_app
from app.db.session import SessionLocal
from app.services.comment_processor import comment_processor

celery_logger = get_task_logger(__name__)

def run_async(coro):
    """Run an async coroutine in the synchronous celery context."""
    try:
        loop = asyncio.get_event_loop()
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
    return loop.run_until_complete(coro)


@celery_app.task(
    name="app.workers.tasks.process_comment_task",
    max_retries=3,
    default_retry_delay=10
)
def process_comment_task(
    instagram_business_account_id: str,
    comment_id: str,
    media_id: str,
    text: str,
    username: str,
    timestamp_str: str,
    commenter_id: str = None
):
    """
    Celery background task triggered by the Webhook handler.
    Examines comments and runs automation flows asynchronously.
    """
    celery_logger.info(f"Celery task received for comment: {comment_id}")
    
    # Parse timestamp back to datetime
    try:
        timestamp = datetime.datetime.fromisoformat(timestamp_str)
        if timestamp.tzinfo is not None:
            timestamp = timestamp.astimezone(datetime.timezone.utc).replace(tzinfo=None)
    except Exception:
        timestamp = datetime.datetime.utcnow()

    async def _execute():
        async with SessionLocal() as db:
            await comment_processor.process_comment(
                db=db,
                instagram_business_account_id=instagram_business_account_id,
                comment_id=comment_id,
                media_id=media_id,
                text=text,
                username=username,
                timestamp=timestamp,
                commenter_id=commenter_id
            )

    try:
        run_async(_execute())
        celery_logger.info(f"Celery task succeeded for comment: {comment_id}")
    except Exception as exc:
        celery_logger.error(f"Celery task failed for comment {comment_id}: {str(exc)}")
        # Auto-retry on standard failures
        raise process_comment_task.retry(exc=exc)


@celery_app.task(
    name="app.workers.tasks.process_dm_task",
    max_retries=3,
    default_retry_delay=10
)
def process_dm_task(
    instagram_business_account_id: str,
    sender_id: str,
    recipient_id: str,
    message_id: str,
    text: str,
    timestamp_str: str
):
    """
    Celery background task triggered by the Webhook handler for DMs.
    Examines incoming messages, logs them, and triggers matching DM automations.
    """
    celery_logger.info(f"Celery task received for DM message: {message_id}")
    
    # Parse timestamp back to datetime
    try:
        timestamp = datetime.datetime.fromisoformat(timestamp_str)
        if timestamp.tzinfo is not None:
            timestamp = timestamp.astimezone(datetime.timezone.utc).replace(tzinfo=None)
    except Exception:
        timestamp = datetime.datetime.utcnow()

    async def _execute():
        from app.services.dm_processor import dm_processor
        async with SessionLocal() as db:
            await dm_processor.process_dm(
                db=db,
                instagram_business_account_id=instagram_business_account_id,
                sender_id=sender_id,
                recipient_id=recipient_id,
                message_id=message_id,
                text=text,
                timestamp=timestamp
            )

    try:
        run_async(_execute())
        celery_logger.info(f"Celery task succeeded for DM message: {message_id}")
    except Exception as exc:
        celery_logger.error(f"Celery task failed for DM message {message_id}: {str(exc)}")
        raise process_dm_task.retry(exc=exc)

