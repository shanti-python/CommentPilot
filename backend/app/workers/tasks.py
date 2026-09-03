import asyncio
import datetime
from celery.utils.log import get_task_logger
from app.core.cel_app import celery_app
from app.db.session import SessionLocal
from app.services.comment_processor import comment_processor

celery_logger = get_task_logger(__name__)


def run_async(coro):
    """Run an async coroutine in the synchronous Celery worker context."""
    try:
        loop = asyncio.get_event_loop()
        if loop.is_closed():
            raise RuntimeError("Event loop is closed")
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
    return loop.run_until_complete(coro)


# ---------------------------------------------------------------------------
# Instagram comment task
# ---------------------------------------------------------------------------

@celery_app.task(
    name="app.workers.tasks.process_comment_task",
    max_retries=3,
    default_retry_delay=10,
)
def process_comment_task(
    instagram_business_account_id: str,
    comment_id: str,
    media_id: str,
    text: str,
    username: str,
    timestamp_str: str,
    commenter_id: str = None,
):
    """
    Celery background task triggered by the Instagram Webhook handler.
    Examines a new comment and runs any matching automation flows.
    """
    celery_logger.info(f"[Instagram] Processing comment task: comment_id={comment_id}")

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
                commenter_id=commenter_id,
            )

    try:
        run_async(_execute())
        celery_logger.info(f"[Instagram] Comment task succeeded: comment_id={comment_id}")
    except Exception as exc:
        celery_logger.error(f"[Instagram] Comment task failed for comment_id={comment_id}: {exc}")
        raise process_comment_task.retry(exc=exc)


# ---------------------------------------------------------------------------
# Facebook comment task
# ---------------------------------------------------------------------------

@celery_app.task(
    name="app.workers.tasks.process_facebook_comment_task",
    max_retries=3,
    default_retry_delay=10,
)
def process_facebook_comment_task(
    facebook_page_id: str,
    comment_id: str,
    media_id: str,
    text: str,
    username: str,
    timestamp_str: str,
    commenter_id: str = None,
):
    """
    Celery background task triggered by the Facebook Page Webhook handler.
    Examines a new comment on a Facebook post and runs any matching automation flows.
    """
    celery_logger.info(
        f"[Facebook] Processing comment task: comment_id={comment_id} post={media_id} page={facebook_page_id}"
    )

    try:
        timestamp = datetime.datetime.fromisoformat(timestamp_str)
        if timestamp.tzinfo is not None:
            timestamp = timestamp.astimezone(datetime.timezone.utc).replace(tzinfo=None)
    except Exception:
        timestamp = datetime.datetime.utcnow()

    async def _execute():
        async with SessionLocal() as db:
            await comment_processor.process_facebook_comment(
                db=db,
                facebook_page_id=facebook_page_id,
                comment_id=comment_id,
                media_id=media_id,
                text=text,
                username=username,
                timestamp=timestamp,
                commenter_id=commenter_id,
            )

    try:
        run_async(_execute())
        celery_logger.info(f"[Facebook] Comment task succeeded: comment_id={comment_id}")
    except Exception as exc:
        celery_logger.error(f"[Facebook] Comment task failed for comment_id={comment_id}: {exc}")
        raise process_facebook_comment_task.retry(exc=exc)


# ---------------------------------------------------------------------------
# Instagram DM task
# ---------------------------------------------------------------------------

@celery_app.task(
    name="app.workers.tasks.process_dm_task",
    max_retries=3,
    default_retry_delay=10,
)
def process_dm_task(
    instagram_business_account_id: str,
    sender_id: str,
    recipient_id: str,
    message_id: str,
    text: str,
    timestamp_str: str,
):
    """
    Celery background task triggered by the Instagram Webhook handler for DMs.
    Examines an incoming message and triggers matching DM automations.
    """
    celery_logger.info(f"[Instagram] Processing DM task: message_id={message_id}")

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
                timestamp=timestamp,
            )

    try:
        run_async(_execute())
        celery_logger.info(f"[Instagram] DM task succeeded: message_id={message_id}")
    except Exception as exc:
        celery_logger.error(f"[Instagram] DM task failed for message_id={message_id}: {exc}")
        raise process_dm_task.retry(exc=exc)


# ---------------------------------------------------------------------------
# Future Flow: Periodic scan task (runs every 5 minutes via Celery Beat)
# ---------------------------------------------------------------------------

@celery_app.task(
    name="app.workers.tasks.scan_future_flows_task",
    max_retries=1,
    default_retry_delay=60,
)
def scan_future_flows_task():
    """
    Periodic task (every 5 minutes) that checks all unresolved Future Flows
    and tries to match them to a newly published post from Meta.

    For each pending future flow:
    1. Syncs latest posts from the Meta Graph API for the linked account.
    2. Fuzzy-matches the `future_post_caption` snippet against real post captions
       (Jaccard word-overlap >= 35%).
    3. On match: links the real post to the flow and sets status = 'resolved'.
    """
    import re as _re

    celery_logger.info("[FutureFlow] Starting periodic scan for unresolved future flows...")

    def _caption_similarity(flow_caption: str, post_caption: str) -> float:
        if not flow_caption or not post_caption:
            return 0.0
        flow_words = set(_re.sub(r'[^\w\s]', '', flow_caption.lower()).split())
        post_words = set(_re.sub(r'[^\w\s]', '', post_caption.lower()).split())
        if not flow_words:
            return 0.0
        intersection = flow_words & post_words
        union = flow_words | post_words
        return len(intersection) / len(union) if union else 0.0

    SIMILARITY_THRESHOLD = 0.35

    async def _scan_all():
        from app.db.repository import (
            automation_flow_repo,
            instagram_account_repo,
            facebook_account_repo,
            post_repo,
            facebook_post_repo,
        )
        from app.integrations.meta.client import meta_client
        from app.utils.text import parse_iso_timestamp

        async with SessionLocal() as db:
            future_flows = await automation_flow_repo.get_unresolved_future_flows(db)
            celery_logger.info(f"[FutureFlow] Found {len(future_flows)} unresolved future flow(s).")

            for flow in future_flows:
                now = datetime.datetime.utcnow()
                is_facebook = bool(flow.facebook_account_id)

                try:
                    # Get account
                    if is_facebook:
                        account = await facebook_account_repo.get(db, flow.facebook_account_id)
                    else:
                        account = await instagram_account_repo.get(db, flow.instagram_account_id)

                    if not account:
                        celery_logger.warning(f"[FutureFlow] No account for flow {flow.id}. Skipping.")
                        continue

                    # Update last scanned timestamp
                    flow.future_flow_last_scanned_at = now
                    db.add(flow)
                    await db.commit()

                    # Sync posts from Meta
                    if is_facebook:
                        posts_data = await meta_client.get_facebook_posts(
                            page_id=account.facebook_page_id,
                            page_access_token=account.page_access_token
                        )
                        for p in posts_data:
                            existing = await facebook_post_repo.get(db, p["id"])
                            ts_val = parse_iso_timestamp(p.get("timestamp") or p.get("created_time"))
                            post_in = {
                                "id": p["id"],
                                "facebook_account_id": account.id,
                                "caption": p.get("caption"),
                                "media_type": p.get("media_type"),
                                "media_url": p.get("media_url"),
                                "thumbnail_url": p.get("thumbnail_url"),
                                "permalink": p.get("permalink"),
                                "timestamp": ts_val or now,
                            }
                            if existing:
                                await facebook_post_repo.update(db, db_obj=existing, obj_in=post_in)
                            else:
                                await facebook_post_repo.create(db, obj_in=post_in)
                        await db.commit()
                        all_posts = await facebook_post_repo.get_by_facebook_account_id(db, account.id)
                    else:
                        posts_data = await meta_client.get_instagram_posts(
                            instagram_business_account_id=account.instagram_business_account_id,
                            page_access_token=account.page_access_token
                        )
                        for p in posts_data:
                            existing = await post_repo.get(db, p["id"])
                            ts_val = parse_iso_timestamp(p.get("timestamp") or p.get("created_time"))
                            post_in = {
                                "id": p["id"],
                                "instagram_account_id": account.id,
                                "caption": p.get("caption"),
                                "media_type": p.get("media_type"),
                                "media_url": p.get("media_url"),
                                "thumbnail_url": p.get("thumbnail_url"),
                                "permalink": p.get("permalink"),
                                "timestamp": ts_val or now,
                            }
                            if existing:
                                await post_repo.update(db, db_obj=existing, obj_in=post_in)
                            else:
                                await post_repo.create(db, obj_in=post_in)
                        await db.commit()
                        all_posts = await post_repo.get_by_instagram_account_id(db, account.id)

                    # Filter real posts published after flow creation (with 1h grace)
                    real_posts = [
                        p for p in all_posts
                        if not str(p.id).startswith("future_")
                        and p.timestamp is not None
                        and p.timestamp >= (flow.created_at - datetime.timedelta(hours=1))
                    ]

                    # Narrow by scheduled window if provided
                    if flow.future_post_scheduled_at and real_posts:
                        sched = flow.future_post_scheduled_at
                        window = [p for p in real_posts if abs((p.timestamp - sched).total_seconds()) <= 6 * 3600]
                        if window:
                            real_posts = window

                    # Find best match
                    best_match = None
                    best_score = 0.0

                    if flow.future_post_caption:
                        for post in real_posts:
                            score = _caption_similarity(flow.future_post_caption, post.caption or "")
                            if score > best_score:
                                best_score = score
                                best_match = post
                    elif real_posts:
                        real_posts_sorted = sorted(real_posts, key=lambda p: p.timestamp or datetime.datetime.min, reverse=True)
                        best_match = real_posts_sorted[0]
                        best_score = 1.0

                    if best_match and best_score >= SIMILARITY_THRESHOLD:
                        celery_logger.info(
                            f"[FutureFlow] ✅ Flow {flow.id} matched post {best_match.id} (score={best_score:.2f})"
                        )
                        update_data = {
                            "future_flow_status": "resolved",
                            "future_flow_last_scanned_at": now,
                        }
                        if is_facebook:
                            update_data["facebook_post_id"] = best_match.id
                        else:
                            update_data["instagram_post_id"] = best_match.id

                        await automation_flow_repo.update(db, db_obj=flow, obj_in=update_data)
                        await db.commit()
                    else:
                        celery_logger.info(
                            f"[FutureFlow] ⏳ No match for flow {flow.id}. "
                            f"Best score={best_score:.2f} (threshold={SIMILARITY_THRESHOLD}). "
                            f"Scanned {len(real_posts)} posts."
                        )

                except Exception as e:
                    celery_logger.error(f"[FutureFlow] Error scanning flow {flow.id}: {e}")

    try:
        run_async(_scan_all())
        celery_logger.info("[FutureFlow] Periodic scan complete.")
    except Exception as exc:
        celery_logger.error(f"[FutureFlow] Periodic scan task failed: {exc}")
        raise scan_future_flows_task.retry(exc=exc)
