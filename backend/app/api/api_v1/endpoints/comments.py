from typing import Any, List, Optional
from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.api import deps
from app.db.repository import instagram_account_repo, facebook_account_repo
from app.schemas.instagram import CommentEvent as CommentEventSchema
from app.schemas.facebook import FacebookCommentEvent as FacebookCommentEventSchema
from app.models.instagram import CommentEvent, Post
from app.models.facebook import FacebookCommentEvent, FacebookPost
from app.models.user import User

router = APIRouter()


@router.get("", response_model=List[CommentEventSchema])
async def read_comments(
    db: AsyncSession = Depends(deps.get_db),
    current_user: User = Depends(deps.get_current_user),
    status: Optional[str] = Query(None, description="Filter by status (pending, processed, ignored, failed)"),
    instagram_account_id: Optional[int] = Query(None, description="Filter by Instagram account ID"),
    skip: int = 0,
    limit: int = 100
) -> Any:
    """Retrieve list of comment events (webhooks received and processed)."""
    accounts = await instagram_account_repo.get_by_user_id(db, user_id=current_user.id)
    account_ids = [acc.id for acc in accounts]
    
    if not account_ids:
        return []

    # Join CommentEvent with Post to check permissions and filter by account
    query = select(CommentEvent).join(
        Post, CommentEvent.media_id == Post.id
    ).where(Post.instagram_account_id.in_(account_ids))

    if instagram_account_id is not None:
        if instagram_account_id in account_ids:
            query = query.where(Post.instagram_account_id == instagram_account_id)
        else:
            return []  # User does not own this account

    if status:
        query = query.where(CommentEvent.status == status)

    query = query.order_by(CommentEvent.timestamp.desc()).offset(skip).limit(limit)
    res = await db.execute(query)
    return res.scalars().all()


@router.get("/facebook", response_model=List[FacebookCommentEventSchema])
async def read_facebook_comments(
    db: AsyncSession = Depends(deps.get_db),
    current_user: User = Depends(deps.get_current_user),
    status: Optional[str] = Query(None, description="Filter by status (pending, processed, ignored, failed)"),
    facebook_account_id: Optional[int] = Query(None, description="Filter by Facebook Page account ID"),
    skip: int = 0,
    limit: int = 100
) -> Any:
    """Retrieve list of Facebook comment events."""
    accounts = await facebook_account_repo.get_by_user_id(db, user_id=current_user.id)
    account_ids = [acc.id for acc in accounts]
    
    if not account_ids:
        return []

    # Join FacebookCommentEvent with FacebookPost to check permissions and filter by account
    query = select(FacebookCommentEvent).join(
        FacebookPost, FacebookCommentEvent.media_id == FacebookPost.id
    ).where(FacebookPost.facebook_account_id.in_(account_ids))

    if facebook_account_id is not None:
        if facebook_account_id in account_ids:
            query = query.where(FacebookPost.facebook_account_id == facebook_account_id)
        else:
            return []

    if status:
        query = query.where(FacebookCommentEvent.status == status)

    query = query.order_by(FacebookCommentEvent.timestamp.desc()).offset(skip).limit(limit)
    res = await db.execute(query)
    return res.scalars().all()
