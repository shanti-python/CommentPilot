from typing import Any, Dict
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import func, select

from app.api import deps
from app.db.repository import instagram_account_repo
from app.schemas.log import AnalyticsResponse
from app.models.instagram import CommentEvent, Post
from app.models.automation import AutomationFlow
from app.models.log import AutomationLog
from app.models.user import User

router = APIRouter()


from typing import Any, Dict
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import func, select, or_

from app.api import deps
from app.db.repository import instagram_account_repo, facebook_account_repo
from app.schemas.log import AnalyticsResponse
from app.models.instagram import CommentEvent, Post
from app.models.facebook import FacebookCommentEvent, FacebookPost
from app.models.automation import AutomationFlow
from app.models.log import AutomationLog
from app.models.user import User

router = APIRouter()


@router.get("", response_model=AnalyticsResponse)
async def get_analytics(
    db: AsyncSession = Depends(deps.get_db),
    current_user: User = Depends(deps.get_current_user)
) -> Any:
    """
    Get aggregated analytics metrics for the current user's connected Instagram and Facebook accounts.
    """
    insta_accounts = await instagram_account_repo.get_by_user_id(db, user_id=current_user.id)
    insta_ids = [acc.id for acc in insta_accounts]
    
    fb_accounts = await facebook_account_repo.get_by_user_id(db, user_id=current_user.id)
    fb_ids = [acc.id for acc in fb_accounts]
    
    if not insta_ids and not fb_ids:
        return {
            "total_comments": 0,
            "replies_sent": 0,
            "dms_sent": 0,
            "keyword_counts": {},
            "failed_replies": 0,
            "avg_response_time_seconds": 0.0
        }

    # 1. Total Comments Received (Instagram + Facebook)
    total_comments = 0
    
    if insta_ids:
        comments_query = select(func.count(CommentEvent.id)).join(
            Post, CommentEvent.media_id == Post.id
        ).where(Post.instagram_account_id.in_(insta_ids))
        res_comments = await db.execute(comments_query)
        total_comments += res_comments.scalar_one_or_none() or 0

    if fb_ids:
        fb_comments_query = select(func.count(FacebookCommentEvent.id)).join(
            FacebookPost, FacebookCommentEvent.media_id == FacebookPost.id
        ).where(FacebookPost.facebook_account_id.in_(fb_ids))
        res_fb_comments = await db.execute(fb_comments_query)
        total_comments += res_fb_comments.scalar_one_or_none() or 0

    # Flow Filter helper
    flow_filter = or_(
        AutomationFlow.instagram_account_id.in_(insta_ids) if insta_ids else False,
        AutomationFlow.facebook_account_id.in_(fb_ids) if fb_ids else False
    )

    # 2. Replies Sent successfully
    replies_query = select(func.count(AutomationLog.id)).join(
        AutomationFlow, AutomationLog.flow_id == AutomationFlow.id
    ).where(
        flow_filter,
        AutomationLog.action_type == "reply_sent",
        AutomationLog.status == "success"
    )
    res_replies = await db.execute(replies_query)
    replies_sent = res_replies.scalar_one_or_none() or 0

    # 3. DMs Sent successfully
    dms_query = select(func.count(AutomationLog.id)).join(
        AutomationFlow, AutomationLog.flow_id == AutomationFlow.id
    ).where(
        flow_filter,
        AutomationLog.action_type == "dm_sent",
        AutomationLog.status == "success"
    )
    res_dms = await db.execute(dms_query)
    dms_sent = res_dms.scalar_one_or_none() or 0

    # 4. Failed Actions (both replies and DMs)
    failed_query = select(func.count(AutomationLog.id)).join(
        AutomationFlow, AutomationLog.flow_id == AutomationFlow.id
    ).where(
        flow_filter,
        AutomationLog.action_type.in_(["reply_sent", "dm_sent"]),
        AutomationLog.status == "failed"
    )
    res_failed = await db.execute(failed_query)
    failed_replies = res_failed.scalar_one_or_none() or 0

    # 5. Keyword trigger counts
    kw_query = select(AutomationLog.details).join(
        AutomationFlow, AutomationLog.flow_id == AutomationFlow.id
    ).where(
        flow_filter,
        AutomationLog.action_type == "trigger_match"
    )
    res_kw = await db.execute(kw_query)
    details_list = res_kw.scalars().all()
    
    keyword_counts: Dict[str, int] = {}
    for details in details_list:
        if isinstance(details, dict):
            matched = details.get("matched_keywords", [])
            for kw in matched:
                keyword_counts[kw] = keyword_counts.get(kw, 0) + 1

    # 6. Average Response Time (Instagram + Facebook)
    total_seconds = 0.0
    total_records = 0

    if insta_ids:
        time_query = select(CommentEvent.timestamp, CommentEvent.processed_at).join(
            Post, CommentEvent.media_id == Post.id
        ).where(
            Post.instagram_account_id.in_(insta_ids),
            CommentEvent.status == "processed",
            CommentEvent.processed_at.isnot(None)
        )
        res_times = await db.execute(time_query)
        time_records = res_times.all()
        for rec in time_records:
            dt_diff = rec.processed_at - rec.timestamp
            total_seconds += dt_diff.total_seconds()
            total_records += 1

    if fb_ids:
        fb_time_query = select(FacebookCommentEvent.timestamp, FacebookCommentEvent.processed_at).join(
            FacebookPost, FacebookCommentEvent.media_id == FacebookPost.id
        ).where(
            FacebookPost.facebook_account_id.in_(fb_ids),
            FacebookCommentEvent.status == "processed",
            FacebookCommentEvent.processed_at.isnot(None)
        )
        res_fb_times = await db.execute(fb_time_query)
        fb_time_records = res_fb_times.all()
        for rec in fb_time_records:
            dt_diff = rec.processed_at - rec.timestamp
            total_seconds += dt_diff.total_seconds()
            total_records += 1
            
    avg_response_time = 0.0
    if total_records > 0:
        avg_response_time = total_seconds / total_records

    return {
        "total_comments": total_comments,
        "replies_sent": replies_sent,
        "dms_sent": dms_sent,
        "keyword_counts": keyword_counts,
        "failed_replies": failed_replies,
        "avg_response_time_seconds": round(avg_response_time, 2)
    }
