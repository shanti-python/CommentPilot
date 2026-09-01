from typing import Any, List, Optional
from datetime import datetime
from fastapi import APIRouter, Depends, Query, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.api import deps
from app.db.repository import post_repo, instagram_account_repo, facebook_post_repo, facebook_account_repo, facebook_comment_repo
from app.utils.text import parse_iso_timestamp
from app.schemas.instagram import Post as PostSchema
from app.schemas.facebook import FacebookPost as FacebookPostSchema, FacebookComment as FacebookCommentSchema
from app.models.instagram import Post
from app.models.facebook import FacebookPost
from app.models.user import User
from app.integrations.meta.client import meta_client, MetaAPIError

router = APIRouter()


@router.get("", response_model=List[PostSchema])
async def read_posts(
    db: AsyncSession = Depends(deps.get_db),
    current_user: User = Depends(deps.get_current_user),
    instagram_account_id: Optional[int] = Query(None, description="Filter posts by Instagram account ID"),
    skip: int = 0,
    limit: int = 100
) -> Any:
    """Retrieve posts cached for the user's connected Instagram accounts."""
    # First get user's accounts to verify access
    accounts = await instagram_account_repo.get_by_user_id(db, user_id=current_user.id)
    account_ids = [acc.id for acc in accounts]
    
    if not account_ids:
        return []
        
    query = select(Post).where(Post.instagram_account_id.in_(account_ids)).order_by(Post.timestamp.desc())
    
    if instagram_account_id is not None:
        if instagram_account_id in account_ids:
            query = query.where(Post.instagram_account_id == instagram_account_id)
        else:
            return []  # User does not own this account
            
    query = query.offset(skip).limit(limit)
    res = await db.execute(query)
    return res.scalars().all()


@router.post("/sync", response_model=List[PostSchema])
async def sync_posts(
    db: AsyncSession = Depends(deps.get_db),
    current_user: User = Depends(deps.get_current_user),
    instagram_account_id: Optional[int] = Query(None, description="Sync posts for a specific Instagram account ID")
) -> Any:
    """Trigger real-time posts synchronization from the Meta Graph API."""
    accounts = await instagram_account_repo.get_by_user_id(db, user_id=current_user.id)
    if not accounts:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No connected Instagram accounts found to sync."
        )
        
    synced_posts = []
    
    for account in accounts:
        if instagram_account_id is not None and account.id != instagram_account_id:
            continue
            
        try:
            posts_data = await meta_client.get_instagram_posts(
                instagram_business_account_id=account.instagram_business_account_id,
                page_access_token=account.page_access_token
            )
            for post in posts_data:
                existing_post = await post_repo.get(db, post["id"])
                
                ts_val = parse_iso_timestamp(post.get("timestamp"))

                post_in = {
                    "id": post["id"],
                    "instagram_account_id": account.id,
                    "caption": post.get("caption"),
                    "media_type": post.get("media_type"),
                    "media_url": post.get("media_url"),
                    "thumbnail_url": post.get("thumbnail_url"),
                    "permalink": post.get("permalink"),
                    "timestamp": ts_val
                }
                if existing_post:
                    await post_repo.update(db, db_obj=existing_post, obj_in=post_in)
                else:
                    await post_repo.create(db, obj_in=post_in)
                    
            await db.commit()
        except MetaAPIError as e:
            logger.warning(f"Meta sync failed for Instagram @{account.username}: {e.message}")
                
    # Return all posts for the user ordered by published date
    query = select(Post).where(Post.instagram_account_id.in_([acc.id for acc in accounts])).order_by(Post.timestamp.desc())
    res = await db.execute(query)
    return res.scalars().all()


from app.db.repository import comment_repo
from app.schemas.instagram import Comment as CommentSchema
from pydantic import BaseModel

class PostCommentPayload(BaseModel):
    message: str

class PostReplyPayload(BaseModel):
    message: str


from loguru import logger

@router.get("/{post_id}/comments", response_model=List[CommentSchema])
async def read_post_comments(
    post_id: str,
    db: AsyncSession = Depends(deps.get_db),
    current_user: User = Depends(deps.get_current_user),
) -> Any:
    """Fetch comments for a specific post, syncing them from Meta API first."""
    post = await post_repo.get(db, id=post_id)
    if not post:
        raise HTTPException(status_code=404, detail="Post not found")
        
    # Verify ownership
    account = await instagram_account_repo.get(db, id=post.instagram_account_id)
    if not account or account.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not authorized to access comments for this post")
        
    # Fetch and cache comments from Meta
    try:
        meta_comments = await meta_client.get_instagram_comments(
            media_id=post_id,
            page_access_token=account.page_access_token
        )
        for mc in meta_comments:
            existing_comment = await comment_repo.get(db, id=mc["id"])
            
            ts_val = parse_iso_timestamp(mc.get("timestamp")) or datetime.utcnow()

            comment_in = {
                "id": mc["id"],
                "media_id": post_id,
                "text": mc.get("text", ""),
                "username": mc.get("username", "anonymous"),
                "timestamp": ts_val,
                "parent_id": mc.get("parent_id")
            }
            if existing_comment:
                await comment_repo.update(db, db_obj=existing_comment, obj_in=comment_in)
            else:
                await comment_repo.create(db, obj_in=comment_in)
        await db.commit()
    except Exception as e:
        logger.warning(f"Could not sync comments from Meta: {str(e)}")

    comments = await comment_repo.get_by_post_id(db, post_id=post_id)
    return comments


@router.post("/{post_id}/comments", response_model=CommentSchema)
async def post_comment_on_media(
    post_id: str,
    payload: PostCommentPayload,
    db: AsyncSession = Depends(deps.get_db),
    current_user: User = Depends(deps.get_current_user),
) -> Any:
    """Post a comment publicly on an Instagram post."""
    post = await post_repo.get(db, id=post_id)
    if not post:
        raise HTTPException(status_code=404, detail="Post not found")
        
    account = await instagram_account_repo.get(db, id=post.instagram_account_id)
    if not account or account.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not authorized to write to this post")
        
    try:
        res = await meta_client._request(
            "POST",
            f"/{post_id}/comments",
            params={
                "message": payload.message,
                "access_token": account.page_access_token
            }
        )
        comment_id = res.get("id", f"manual_comment_{int(datetime.utcnow().timestamp())}")
        
        comment_in = {
            "id": comment_id,
            "media_id": post_id,
            "text": payload.message,
            "username": account.username,
            "timestamp": datetime.utcnow()
        }
        comment_obj = await comment_repo.create(db, obj_in=comment_in)
        await db.commit()
        return comment_obj
    except MetaAPIError as e:
        raise HTTPException(status_code=400, detail=f"Meta API error: {e.message}")


@router.post("/{post_id}/comments/{comment_id}/replies", response_model=CommentSchema)
async def post_reply_to_comment(
    post_id: str,
    comment_id: str,
    payload: PostReplyPayload,
    db: AsyncSession = Depends(deps.get_db),
    current_user: User = Depends(deps.get_current_user),
) -> Any:
    """Post a reply publicly to a comment."""
    post = await post_repo.get(db, id=post_id)
    if not post:
        raise HTTPException(status_code=404, detail="Post not found")
        
    account = await instagram_account_repo.get(db, id=post.instagram_account_id)
    if not account or account.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not authorized")
        
    try:
        res = await meta_client._request(
            "POST",
            f"/{comment_id}/replies",
            params={
                "message": payload.message,
                "access_token": account.page_access_token
            }
        )
        reply_id = res.get("id", f"manual_reply_{int(datetime.utcnow().timestamp())}")
        
        comment_in = {
            "id": reply_id,
            "media_id": post_id,
            "text": payload.message,
            "username": account.username,
            "timestamp": datetime.utcnow(),
            "parent_id": comment_id
        }
        reply_obj = await comment_repo.create(db, obj_in=comment_in)
        await db.commit()
        return reply_obj
    except MetaAPIError as e:
        raise HTTPException(status_code=400, detail=f"Meta API error: {e.message}")


from typing import Dict

@router.delete("/{post_id}/comments/{comment_id}", response_model=Dict[str, Any])
async def delete_comment_endpoint(
    post_id: str,
    comment_id: str,
    db: AsyncSession = Depends(deps.get_db),
    current_user: User = Depends(deps.get_current_user),
) -> Any:
    """Delete a comment or reply from Instagram and the database."""
    post = await post_repo.get(db, id=post_id)
    if not post:
        raise HTTPException(status_code=404, detail="Post not found")
        
    account = await instagram_account_repo.get(db, id=post.instagram_account_id)
    if not account or account.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not authorized")
        
    comment = await comment_repo.get(db, id=comment_id)
    if not comment:
        raise HTTPException(status_code=404, detail="Comment not found in database")
        
    try:
        try:
            success = await meta_client.delete_comment(
                page_access_token=account.page_access_token,
                comment_id=comment_id
            )
            if not success:
                raise MetaAPIError("Meta API did not confirm deletion", status_code=400)
        except MetaAPIError as e:
            # If the comment is already deleted on Meta or cannot be loaded, still remove it from our local database
            if e.error_code == 100 or "does not exist" in e.message or "cannot be loaded" in e.message:
                logger.warning(f"Comment {comment_id} already deleted or inaccessible on Meta. Removing locally. Error: {e.message}")
            else:
                raise e
            
        await comment_repo.remove(db, id=comment_id)
        # Clean up nested replies locally
        replies = await comment_repo.get_by_post_id(db, post_id=post_id)
        for r in replies:
            if r.parent_id == comment_id:
                await comment_repo.remove(db, id=r.id)
                
        await db.commit()
        return {"status": "success", "message": "Comment successfully deleted"}
    except MetaAPIError as e:
        raise HTTPException(status_code=400, detail=f"Meta API error: {e.message}")


# --- Facebook Endpoints ---

@router.get("/facebook", response_model=List[FacebookPostSchema])
async def read_facebook_posts(
    db: AsyncSession = Depends(deps.get_db),
    current_user: User = Depends(deps.get_current_user),
    facebook_account_id: Optional[int] = Query(None, description="Filter posts by Facebook Page account ID"),
    skip: int = 0,
    limit: int = 100
) -> Any:
    """Retrieve posts cached for the user's connected Facebook Page accounts."""
    accounts = await facebook_account_repo.get_by_user_id(db, user_id=current_user.id)
    account_ids = [acc.id for acc in accounts]
    
    if not account_ids:
        return []
        
    query = select(FacebookPost).where(FacebookPost.facebook_account_id.in_(account_ids)).order_by(FacebookPost.timestamp.desc())
    
    if facebook_account_id is not None:
        if facebook_account_id in account_ids:
            query = query.where(FacebookPost.facebook_account_id == facebook_account_id)
        else:
            return []
            
    query = query.offset(skip).limit(limit)
    res = await db.execute(query)
    return res.scalars().all()


@router.post("/facebook/sync", response_model=List[FacebookPostSchema])
async def sync_facebook_posts(
    db: AsyncSession = Depends(deps.get_db),
    current_user: User = Depends(deps.get_current_user),
    facebook_account_id: Optional[int] = Query(None, description="Sync posts for a specific Facebook Page account ID")
) -> Any:
    """Trigger real-time Facebook posts synchronization from the Meta Graph API."""
    accounts = await facebook_account_repo.get_by_user_id(db, user_id=current_user.id)
    if not accounts:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No connected Facebook Pages found to sync."
        )
        
    for account in accounts:
        if facebook_account_id is not None and account.id != facebook_account_id:
            continue
            
        try:
            posts_data = await meta_client.get_facebook_posts(
                page_id=account.facebook_page_id,
                page_access_token=account.page_access_token
            )
            for post in posts_data:
                existing_post = await facebook_post_repo.get(db, post["id"])
                
                ts_val = parse_iso_timestamp(post.get("timestamp"))

                post_in = {
                    "id": post["id"],
                    "facebook_account_id": account.id,
                    "caption": post.get("caption"),
                    "media_type": post.get("media_type"),
                    "media_url": post.get("media_url"),
                    "thumbnail_url": post.get("thumbnail_url"),
                    "permalink": post.get("permalink"),
                    "timestamp": ts_val
                }
                if existing_post:
                    await facebook_post_repo.update(db, db_obj=existing_post, obj_in=post_in)
                else:
                    await facebook_post_repo.create(db, obj_in=post_in)
                    
            await db.commit()
        except MetaAPIError as e:
            logger.warning(f"Meta sync failed for Facebook Page @{account.name}: {e.message}")
                
    # Return all posts for the user ordered by published date
    query = select(FacebookPost).where(FacebookPost.facebook_account_id.in_([acc.id for acc in accounts])).order_by(FacebookPost.timestamp.desc())
    res = await db.execute(query)
    return res.scalars().all()


@router.get("/facebook/{post_id}/comments", response_model=List[FacebookCommentSchema])
async def read_facebook_post_comments(
    post_id: str,
    db: AsyncSession = Depends(deps.get_db),
    current_user: User = Depends(deps.get_current_user),
) -> Any:
    """Fetch comments for a specific Facebook post, syncing them from Meta API first."""
    post = await facebook_post_repo.get(db, id=post_id)
    if not post:
        raise HTTPException(status_code=404, detail="Facebook Post not found")
        
    # Verify ownership
    account = await facebook_account_repo.get(db, id=post.facebook_account_id)
    if not account or account.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not authorized to access comments for this post")
        
    # Fetch and cache comments from Meta
    try:
        meta_comments = await meta_client.get_facebook_comments(
            post_id=post_id,
            page_access_token=account.page_access_token
        )
        for mc in meta_comments:
            existing_comment = await facebook_comment_repo.get(db, id=mc["id"])
            
            ts_val = parse_iso_timestamp(mc.get("timestamp")) or datetime.utcnow()

            comment_in = {
                "id": mc["id"],
                "media_id": post_id,
                "text": mc.get("text", ""),
                "username": mc.get("username", "anonymous"),
                "timestamp": ts_val,
                "parent_id": mc.get("parent_id")
            }
            if existing_comment:
                await facebook_comment_repo.update(db, db_obj=existing_comment, obj_in=comment_in)
            else:
                await facebook_comment_repo.create(db, obj_in=comment_in)
        await db.commit()
    except Exception as e:
        logger.warning(f"Could not sync Facebook comments from Meta: {str(e)}")

    comments = await facebook_comment_repo.get_by_post_id(db, post_id=post_id)
    return comments


@router.post("/facebook/{post_id}/comments", response_model=FacebookCommentSchema)
async def post_comment_on_facebook_post(
    post_id: str,
    payload: PostCommentPayload,
    db: AsyncSession = Depends(deps.get_db),
    current_user: User = Depends(deps.get_current_user),
) -> Any:
    """Post a comment publicly on a Facebook post."""
    post = await facebook_post_repo.get(db, id=post_id)
    if not post:
        raise HTTPException(status_code=404, detail="Facebook Post not found")
        
    account = await facebook_account_repo.get(db, id=post.facebook_account_id)
    if not account or account.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not authorized to write to this post")
        
    try:
        if account.page_access_token == "mock_page_token" or str(account.page_access_token).startswith("mock"):
            comment_id = f"manual_fb_comment_{int(datetime.utcnow().timestamp())}"
        else:
            res = await meta_client._request(
                "POST",
                f"/{post_id}/comments",
                params={
                    "message": payload.message,
                    "access_token": account.page_access_token
                }
            )
            comment_id = res.get("id", f"manual_fb_comment_{int(datetime.utcnow().timestamp())}")
        
        comment_in = {
            "id": comment_id,
            "media_id": post_id,
            "text": payload.message,
            "username": account.name or account.username,
            "timestamp": datetime.utcnow()
        }
        comment_obj = await facebook_comment_repo.create(db, obj_in=comment_in)
        await db.commit()
        return comment_obj
    except MetaAPIError as e:
        raise HTTPException(status_code=400, detail=f"Meta API error: {e.message}")


@router.post("/facebook/{post_id}/comments/{comment_id}/replies", response_model=FacebookCommentSchema)
async def post_reply_to_facebook_comment(
    post_id: str,
    comment_id: str,
    payload: PostReplyPayload,
    db: AsyncSession = Depends(deps.get_db),
    current_user: User = Depends(deps.get_current_user),
) -> Any:
    """Post a reply publicly to a Facebook comment."""
    post = await facebook_post_repo.get(db, id=post_id)
    if not post:
        raise HTTPException(status_code=404, detail="Facebook Post not found")
        
    account = await facebook_account_repo.get(db, id=post.facebook_account_id)
    if not account or account.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not authorized")
        
    try:
        if account.page_access_token == "mock_page_token" or str(account.page_access_token).startswith("mock"):
            reply_id = f"manual_fb_reply_{int(datetime.utcnow().timestamp())}"
        else:
            res = await meta_client._request(
                "POST",
                f"/{comment_id}/comments",
                params={
                    "message": payload.message,
                    "access_token": account.page_access_token
                }
            )
            reply_id = res.get("id", f"manual_fb_reply_{int(datetime.utcnow().timestamp())}")
        
        comment_in = {
            "id": reply_id,
            "media_id": post_id,
            "text": payload.message,
            "username": account.name or account.username,
            "timestamp": datetime.utcnow(),
            "parent_id": comment_id
        }
        reply_obj = await facebook_comment_repo.create(db, obj_in=comment_in)
        await db.commit()
        return reply_obj
    except MetaAPIError as e:
        raise HTTPException(status_code=400, detail=f"Meta API error: {e.message}")


@router.delete("/facebook/{post_id}/comments/{comment_id}", response_model=Dict[str, Any])
async def delete_facebook_comment_endpoint(
    post_id: str,
    comment_id: str,
    db: AsyncSession = Depends(deps.get_db),
    current_user: User = Depends(deps.get_current_user),
) -> Any:
    """Delete a Facebook comment or reply."""
    post = await facebook_post_repo.get(db, id=post_id)
    if not post:
        raise HTTPException(status_code=404, detail="Facebook Post not found")
        
    account = await facebook_account_repo.get(db, id=post.facebook_account_id)
    if not account or account.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not authorized")
        
    comment = await facebook_comment_repo.get(db, id=comment_id)
    if not comment:
        raise HTTPException(status_code=404, detail="Facebook Comment not found in database")
        
    try:
        try:
            success = await meta_client.delete_comment(
                page_access_token=account.page_access_token,
                comment_id=comment_id
            )
            if not success:
                raise MetaAPIError("Meta API did not confirm deletion", status_code=400)
        except MetaAPIError as e:
            if e.error_code == 100 or "does not exist" in e.message or "cannot be loaded" in e.message:
                logger.warning(f"Facebook Comment {comment_id} already deleted or inaccessible on Meta. Removing locally. Error: {e.message}")
            else:
                raise e
            
        await facebook_comment_repo.remove(db, id=comment_id)
        # Clean up nested replies locally
        replies = await facebook_comment_repo.get_by_post_id(db, post_id=post_id)
        for r in replies:
            if r.parent_id == comment_id:
                await facebook_comment_repo.remove(db, id=r.id)
                
        await db.commit()
        return {"status": "success", "message": "Facebook Comment successfully deleted"}
    except MetaAPIError as e:
        raise HTTPException(status_code=400, detail=f"Meta API error: {e.message}")


import uuid

class FuturePostCreatePayload(BaseModel):
    instagram_account_id: int
    caption: str
    media_type: str = "IMAGE"
    media_url: Optional[str] = None
    keyword: Optional[str] = None
    reply_message: Optional[str] = None
    dm_message: Optional[str] = None

class FacebookFuturePostCreatePayload(BaseModel):
    facebook_account_id: int
    caption: str
    media_type: str = "post"
    media_url: Optional[str] = None
    keyword: Optional[str] = None
    reply_message: Optional[str] = None
    dm_message: Optional[str] = None

class PostAutomationUpdatePayload(BaseModel):
    automation_status: str  # setup, active, paused
    keyword: Optional[str] = None
    reply_message: Optional[str] = None
    dm_message: Optional[str] = None


@router.post("/future", response_model=PostSchema)
async def create_future_post(
    payload: FuturePostCreatePayload,
    db: AsyncSession = Depends(deps.get_db),
    current_user: User = Depends(deps.get_current_user),
) -> Any:
    """Create a future Instagram post placeholder in advance for automation."""
    account = await instagram_account_repo.get(db, id=payload.instagram_account_id)
    if not account or account.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not authorized to access this Instagram account")
        
    post_id = f"future_ig_{str(uuid.uuid4())}"
    status_val = "active" if (payload.keyword and payload.reply_message) else "setup"
    
    post_in = {
        "id": post_id,
        "instagram_account_id": account.id,
        "caption": payload.caption,
        "media_type": payload.media_type,
        "media_url": payload.media_url or "https://images.unsplash.com/photo-1618005182384-a83a8bd57fbe?w=500&auto=format&fit=crop&q=80",
        "permalink": f"https://instagram.com/p/{post_id}",
        "timestamp": datetime.utcnow(),
        "automation_status": status_val,
        "keyword": payload.keyword,
        "reply_message": payload.reply_message,
        "dm_message": payload.dm_message,
        "is_future_post": True
    }
    
    post_obj = await post_repo.create(db, obj_in=post_in)
    await db.commit()
    return post_obj


@router.post("/facebook/future", response_model=FacebookPostSchema)
async def create_facebook_future_post(
    payload: FacebookFuturePostCreatePayload,
    db: AsyncSession = Depends(deps.get_db),
    current_user: User = Depends(deps.get_current_user),
) -> Any:
    """Create a future Facebook post placeholder in advance for automation."""
    account = await facebook_account_repo.get(db, id=payload.facebook_account_id)
    if not account or account.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not authorized to access this Facebook page")
        
    post_id = f"future_fb_{str(uuid.uuid4())}"
    status_val = "active" if (payload.keyword and payload.reply_message) else "setup"
    
    post_in = {
        "id": post_id,
        "facebook_account_id": account.id,
        "caption": payload.caption,
        "media_type": payload.media_type,
        "media_url": payload.media_url or "https://images.unsplash.com/photo-1618005182384-a83a8bd57fbe?w=500&auto=format&fit=crop&q=80",
        "permalink": f"https://facebook.com/{post_id}",
        "timestamp": datetime.utcnow(),
        "automation_status": status_val,
        "keyword": payload.keyword,
        "reply_message": payload.reply_message,
        "dm_message": payload.dm_message,
        "is_future_post": True
    }
    
    post_obj = await facebook_post_repo.create(db, obj_in=post_in)
    await db.commit()
    return post_obj


@router.put("/{post_id}/automation", response_model=PostSchema)
async def update_post_automation(
    post_id: str,
    payload: PostAutomationUpdatePayload,
    db: AsyncSession = Depends(deps.get_db),
    current_user: User = Depends(deps.get_current_user),
) -> Any:
    """Update post-specific automation config for an Instagram post."""
    post = await post_repo.get(db, id=post_id)
    if not post:
        raise HTTPException(status_code=404, detail="Post not found")
        
    account = await instagram_account_repo.get(db, id=post.instagram_account_id)
    if not account or account.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not authorized")
        
    post.automation_status = payload.automation_status
    post.keyword = payload.keyword
    post.reply_message = payload.reply_message
    post.dm_message = payload.dm_message
    
    db.add(post)
    await db.commit()
    await db.refresh(post)
    return post


@router.put("/facebook/{post_id}/automation", response_model=FacebookPostSchema)
async def update_facebook_post_automation(
    post_id: str,
    payload: PostAutomationUpdatePayload,
    db: AsyncSession = Depends(deps.get_db),
    current_user: User = Depends(deps.get_current_user),
) -> Any:
    """Update post-specific automation config for a Facebook post."""
    post = await facebook_post_repo.get(db, id=post_id)
    if not post:
        raise HTTPException(status_code=404, detail="Facebook Post not found")
        
    account = await facebook_account_repo.get(db, id=post.facebook_account_id)
    if not account or account.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not authorized")
        
    post.automation_status = payload.automation_status
    post.keyword = payload.keyword
    post.reply_message = payload.reply_message
    post.dm_message = payload.dm_message
    
    db.add(post)
    await db.commit()
    await db.refresh(post)
    return post
