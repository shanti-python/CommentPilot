from typing import Any, List, Optional
from fastapi import APIRouter, Depends, Query, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.api import deps
from app.db.repository import instagram_account_repo, facebook_account_repo, automation_flow_repo
from app.schemas.log import AutomationLog as AutomationLogSchema
from app.models.log import AutomationLog
from app.models.automation import AutomationFlow
from app.models.instagram import CommentEvent, Post
from app.models.facebook import FacebookCommentEvent, FacebookPost
from app.models.user import User
from sqlalchemy import or_, and_

router = APIRouter()


@router.get("", response_model=List[AutomationLogSchema])
async def read_logs(
    db: AsyncSession = Depends(deps.get_db),
    current_user: User = Depends(deps.get_current_user),
    flow_id: Optional[str] = Query(None, description="Filter logs by automation flow ID"),
    comment_id: Optional[str] = Query(None, description="Filter logs by comment ID"),
    skip: int = 0,
    limit: int = 100
) -> Any:
    """Retrieve execution logs for the user's automation flows."""
    insta_accounts = await instagram_account_repo.get_by_user_id(db, user_id=current_user.id)
    insta_ids = [acc.id for acc in insta_accounts]
    
    fb_accounts = await facebook_account_repo.get_by_user_id(db, user_id=current_user.id)
    fb_ids = [acc.id for acc in fb_accounts]
    
    if not insta_ids and not fb_ids:
        return []

    # Build query joining AutomationFlow to verify ownership (using outerjoin to retain logs for deleted flows)
    query = select(AutomationLog).outerjoin(
        AutomationFlow, AutomationLog.flow_id == AutomationFlow.id
    ).outerjoin(
        CommentEvent, AutomationLog.comment_id == CommentEvent.comment_id
    ).outerjoin(
        Post, CommentEvent.media_id == Post.id
    ).outerjoin(
        FacebookCommentEvent, AutomationLog.comment_id == FacebookCommentEvent.comment_id
    ).outerjoin(
        FacebookPost, FacebookCommentEvent.media_id == FacebookPost.id
    ).where(
        or_(
            or_(
                AutomationFlow.instagram_account_id.in_(insta_ids) if insta_ids else False,
                AutomationFlow.facebook_account_id.in_(fb_ids) if fb_ids else False
            ),
            Post.instagram_account_id.in_(insta_ids) if insta_ids else False,
            FacebookPost.facebook_account_id.in_(fb_ids) if fb_ids else False
        )
    )

    if flow_id is not None:
        # Verify flow ownership
        flow = await automation_flow_repo.get(db, flow_id)
        if not flow:
            raise HTTPException(status_code=404, detail="Flow not found")
        
        has_access = False
        if flow.facebook_account_id and flow.facebook_account_id in fb_ids:
            has_access = True
        elif flow.instagram_account_id and flow.instagram_account_id in insta_ids:
            has_access = True
            
        if not has_access:
            raise HTTPException(status_code=403, detail="Access denied to this flow's logs")
        query = query.where(AutomationLog.flow_id == flow_id)

    if comment_id is not None:
        query = query.where(AutomationLog.comment_id == comment_id)

    query = query.order_by(AutomationLog.created_at.desc()).offset(skip).limit(limit)
    res = await db.execute(query)
    return res.scalars().all()
