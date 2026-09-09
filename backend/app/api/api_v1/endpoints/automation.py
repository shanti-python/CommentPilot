from typing import Any, List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, delete
from loguru import logger

from app.api import deps
from app.db.repository import (
    instagram_account_repo,
    facebook_account_repo,
    post_repo,
    facebook_post_repo,
    facebook_comment_repo,
    facebook_comment_event_repo,
    automation_flow_repo,
    flow_node_repo,
    flow_edge_repo
)
from app.integrations.meta.client import meta_client
from app.schemas.automation import (
    AutomationFlow as AutomationFlowSchema,
    AutomationFlowCreate,
    AutomationFlowUpdate
)
from app.models.automation import AutomationFlow, FlowNode, FlowEdge
from app.models.user import User
from sqlalchemy import or_

router = APIRouter()


@router.get("", response_model=List[AutomationFlowSchema])
async def read_flows(
    db: AsyncSession = Depends(deps.get_db),
    current_user: User = Depends(deps.get_current_user),
    skip: int = 0,
    limit: int = 100
) -> Any:
    """Retrieve all automation flows created for the user's accounts."""
    insta_accounts = await instagram_account_repo.get_by_user_id(db, user_id=current_user.id)
    insta_ids = [acc.id for acc in insta_accounts]
    
    fb_accounts = await facebook_account_repo.get_by_user_id(db, user_id=current_user.id)
    fb_ids = [acc.id for acc in fb_accounts]
    
    if not insta_ids and not fb_ids:
        return []
        
    query = select(AutomationFlow).where(
        or_(
            AutomationFlow.instagram_account_id.in_(insta_ids) if insta_ids else False,
            AutomationFlow.facebook_account_id.in_(fb_ids) if fb_ids else False
        )
    ).order_by(AutomationFlow.created_at.desc()).offset(skip).limit(limit)
    
    res = await db.execute(query)
    return res.scalars().all()


from datetime import datetime, timezone
from app.db.repository import post_repo, comment_repo, comment_event_repo
from app.integrations.meta.client import meta_client
from app.services.comment_processor import comment_processor

@router.post("/run", response_model=dict)
async def run_bulk_automation(
    db: AsyncSession = Depends(deps.get_db),
    current_user: User = Depends(deps.get_current_user)
) -> Any:
    """
    Detect pending comments across all posts and Reels for user's accounts,
    generate replies, and post them.
    """
    return await comment_processor.scan_and_process_pending_comments(db=db, user_id=current_user.id)


@router.post("/{flow_id}/run", response_model=dict)
async def run_single_flow(
    flow_id: str,
    db: AsyncSession = Depends(deps.get_db),
    current_user: User = Depends(deps.get_current_user)
) -> Any:
    """
    Run a single automation flow: fetch posts/comments, filter comments matching this flow's triggers,
    and process them.
    """
    flow = await automation_flow_repo.get(db, flow_id)
    if not flow:
        raise HTTPException(status_code=404, detail="Flow not found")

    is_facebook = bool(flow.facebook_account_id)

    # Verify ownership
    if is_facebook:
        account = await facebook_account_repo.get(db, flow.facebook_account_id)
    else:
        account = await instagram_account_repo.get(db, flow.instagram_account_id)
        
    if not account or account.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not enough permissions")

    if not flow.is_active:
        raise HTTPException(status_code=400, detail="Cannot run an inactive automation flow.")

    target_post = flow.facebook_post_id if is_facebook else flow.instagram_post_id
    return await comment_processor.scan_and_process_pending_comments(
        db=db,
        user_id=current_user.id,
        account_id=account.id,
        target_post_id=target_post,
        target_flow_id=flow.id
    )


@router.get("/{flow_id}", response_model=AutomationFlowSchema)
async def read_flow(
    flow_id: str,
    db: AsyncSession = Depends(deps.get_db),
    current_user: User = Depends(deps.get_current_user)
) -> Any:
    """Retrieve details of a single automation flow."""
    flow = await automation_flow_repo.get(db, flow_id)
    if not flow:
        raise HTTPException(status_code=404, detail="Flow not found")
        
    # Verify ownership
    if flow.facebook_account_id:
        account = await facebook_account_repo.get(db, flow.facebook_account_id)
    else:
        account = await instagram_account_repo.get(db, flow.instagram_account_id)
    if not account or account.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not enough permissions")
        
    return flow


@router.post("", response_model=AutomationFlowSchema)
async def create_flow(
    *,
    db: AsyncSession = Depends(deps.get_db),
    current_user: User = Depends(deps.get_current_user),
    flow_in: AutomationFlowCreate
) -> Any:
    """
    Create a new automation flow with nodes and edges.
    """
    # 1. Verify user owns the account
    if flow_in.facebook_account_id:
        account = await facebook_account_repo.get(db, flow_in.facebook_account_id)
        if not account or account.user_id != current_user.id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid Facebook account ID or unauthorized"
            )
    else:
        account = await instagram_account_repo.get(db, flow_in.instagram_account_id)
        if not account or account.user_id != current_user.id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid Instagram account ID or unauthorized"
            )
        
    import uuid
    id_mapping = {}
    for node_in in flow_in.nodes:
        if node_in.id in ["node_trig", "node_rep", "node_dm", "node_tag"]:
            id_mapping[node_in.id] = f"{node_in.id}_{uuid.uuid4().hex[:8]}"
        else:
            id_mapping[node_in.id] = node_in.id

    # 2. Create the flow parent
    flow = await automation_flow_repo.create(db, obj_in={
        "instagram_account_id": flow_in.instagram_account_id,
        "facebook_account_id": flow_in.facebook_account_id,
        "instagram_post_id": flow_in.instagram_post_id,
        "facebook_post_id": flow_in.facebook_post_id,
        "name": flow_in.name,
        "is_active": flow_in.is_active,
        "is_future_flow": flow_in.is_future_flow,
        "future_post_caption": flow_in.future_post_caption,
        "future_post_scheduled_at": flow_in.future_post_scheduled_at,
        "future_flow_status": "pending" if flow_in.is_future_flow else None,
        "apply_to_all_future_posts": flow_in.apply_to_all_future_posts,
    })
    await db.commit()
    
    # 3. Create nodes
    for node_in in flow_in.nodes:
        await flow_node_repo.create(db, obj_in={
            "id": id_mapping.get(node_in.id, node_in.id),
            "flow_id": flow.id,
            "type": node_in.type,
            "config": node_in.config
        })
        
    # 4. Create edges
    for edge_in in flow_in.edges:
        edge_id = edge_in.id
        if not edge_id or edge_id == "edge_trig_rep":
            edge_id = f"edge_{uuid.uuid4().hex[:8]}"
        await flow_edge_repo.create(db, obj_in={
            "id": edge_id,
            "flow_id": flow.id,
            "source_node_id": id_mapping.get(edge_in.source_node_id, edge_in.source_node_id),
            "target_node_id": id_mapping.get(edge_in.target_node_id, edge_in.target_node_id),
            "condition_value": edge_in.condition_value
        })
        
    await db.commit()
    await db.refresh(flow)
    return flow


@router.put("/{flow_id}", response_model=AutomationFlowSchema)
async def update_flow(
    *,
    flow_id: str,
    db: AsyncSession = Depends(deps.get_db),
    current_user: User = Depends(deps.get_current_user),
    flow_in: AutomationFlowUpdate
) -> Any:
    """
    Update an existing automation flow.
    Updates the core properties, and overwrites the nodes/edges list.
    """
    flow = await automation_flow_repo.get(db, flow_id)
    if not flow:
        raise HTTPException(status_code=404, detail="Flow not found")
        
    # Verify ownership
    if flow.facebook_account_id:
        account = await facebook_account_repo.get(db, flow.facebook_account_id)
    else:
        account = await instagram_account_repo.get(db, flow.instagram_account_id)
    if not account or account.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not enough permissions")

    # Update basic metadata
    update_data = {}
    if flow_in.name is not None:
        update_data["name"] = flow_in.name
    if flow_in.is_active is not None:
        update_data["is_active"] = flow_in.is_active
    if "instagram_account_id" in flow_in.model_fields_set:
        update_data["instagram_account_id"] = flow_in.instagram_account_id
    if "facebook_account_id" in flow_in.model_fields_set:
        update_data["facebook_account_id"] = flow_in.facebook_account_id
    if "instagram_post_id" in flow_in.model_fields_set:
        update_data["instagram_post_id"] = flow_in.instagram_post_id
    if "facebook_post_id" in flow_in.model_fields_set:
        update_data["facebook_post_id"] = flow_in.facebook_post_id
    # Future flow fields
    if flow_in.is_future_flow is not None:
        update_data["is_future_flow"] = flow_in.is_future_flow
    if flow_in.future_post_caption is not None:
        update_data["future_post_caption"] = flow_in.future_post_caption
    if flow_in.future_post_scheduled_at is not None:
        update_data["future_post_scheduled_at"] = flow_in.future_post_scheduled_at
    if flow_in.future_flow_status is not None:
        update_data["future_flow_status"] = flow_in.future_flow_status
    if flow_in.apply_to_all_future_posts is not None:
        update_data["apply_to_all_future_posts"] = flow_in.apply_to_all_future_posts
        
    if update_data:
        await automation_flow_repo.update(db, db_obj=flow, obj_in=update_data)
        
    # Overwrite Nodes if provided
    import uuid
    id_mapping = {}
    if flow_in.nodes is not None:
        for node_in in flow_in.nodes:
            if node_in.id in ["node_trig", "node_rep", "node_dm", "node_tag"]:
                id_mapping[node_in.id] = f"{node_in.id}_{uuid.uuid4().hex[:8]}"
            else:
                id_mapping[node_in.id] = node_in.id

        # Delete existing nodes
        await db.execute(delete(FlowNode).where(FlowNode.flow_id == flow.id))
        # Insert new nodes
        for node_in in flow_in.nodes:
            await flow_node_repo.create(db, obj_in={
                "id": id_mapping.get(node_in.id, node_in.id),
                "flow_id": flow.id,
                "type": node_in.type,
                "config": node_in.config
            })
            
    # Overwrite Edges if provided
    if flow_in.edges is not None:
        # Delete existing edges
        await db.execute(delete(FlowEdge).where(FlowEdge.flow_id == flow.id))
        # Insert new edges
        for edge_in in flow_in.edges:
            edge_id = edge_in.id
            if not edge_id or edge_id == "edge_trig_rep":
                edge_id = f"edge_{uuid.uuid4().hex[:8]}"
            await flow_edge_repo.create(db, obj_in={
                "id": edge_id,
                "flow_id": flow.id,
                "source_node_id": id_mapping.get(edge_in.source_node_id, edge_in.source_node_id),
                "target_node_id": id_mapping.get(edge_in.target_node_id, edge_in.target_node_id),
                "condition_value": edge_in.condition_value
            })
            
    await db.commit()
    await db.refresh(flow)
    return flow



@router.delete("/{flow_id}", response_model=AutomationFlowSchema)
async def delete_flow(
    *,
    flow_id: str,
    db: AsyncSession = Depends(deps.get_db),
    current_user: User = Depends(deps.get_current_user)
) -> Any:
    """Delete an automation flow."""
    flow = await automation_flow_repo.get(db, flow_id)
    if not flow:
        raise HTTPException(status_code=404, detail="Flow not found")
        
    # Verify ownership
    if flow.facebook_account_id:
        account = await facebook_account_repo.get(db, flow.facebook_account_id)
    else:
        account = await instagram_account_repo.get(db, flow.instagram_account_id)
    if not account or account.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not enough permissions")
        
    # Delete cascade takes care of nodes and edges
    await automation_flow_repo.remove(db, id=flow.id)
    await db.commit()
    return flow


# ---------------------------------------------------------------------------
# Future Flow: Scan for the newly published post and auto-link it
# ---------------------------------------------------------------------------

def _caption_similarity(flow_caption: str, post_caption: str) -> float:
    """
    Simple word-overlap score between the flow's expected caption snippet and a real post caption.
    Returns 0.0–1.0. Score ≥ 0.35 is considered a match.
    """
    if not flow_caption or not post_caption:
        return 0.0
    
    import re as _re
    flow_words = set(_re.sub(r'[^\w\s]', '', flow_caption.lower()).split())
    post_words = set(_re.sub(r'[^\w\s]', '', post_caption.lower()).split())
    
    if not flow_words:
        return 0.0
    
    # Compute Jaccard similarity
    intersection = flow_words & post_words
    union = flow_words | post_words
    return len(intersection) / len(union) if union else 0.0


@router.post("/{flow_id}/scan-for-post", response_model=dict)
async def scan_future_flow_for_post(
    flow_id: str,
    db: AsyncSession = Depends(deps.get_db),
    current_user: User = Depends(deps.get_current_user)
) -> Any:
    """
    Future Flow resolver endpoint.

    Syncs the latest posts from Meta Graph API for the flow's linked account,
    then attempts to fuzzy-match the user-provided `future_post_caption` snippet
    against recently published posts.

    When a match is found (similarity ≥ 35 % word overlap):
    - Links the real post ID to the flow (`instagram_post_id` / `facebook_post_id`).
    - Sets `future_flow_status = 'resolved'`.
    - The flow transitions into a normal post-specific automation flow.
    
    Returns the updated flow or a 'no_match' message.
    """
    import datetime as _dt

    flow = await automation_flow_repo.get(db, flow_id)
    if not flow:
        raise HTTPException(status_code=404, detail="Flow not found")
    
    if not flow.is_future_flow:
        raise HTTPException(status_code=400, detail="This flow is not a Future Flow.")
    
    if flow.future_flow_status == "resolved":
        return {"status": "already_resolved", "message": "This future flow has already been matched to a post.", "flow_id": flow_id}
    
    is_facebook = bool(flow.facebook_account_id)
    
    # Verify ownership
    if is_facebook:
        account = await facebook_account_repo.get(db, flow.facebook_account_id)
    else:
        account = await instagram_account_repo.get(db, flow.instagram_account_id)
    
    if not account or account.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not enough permissions")
    
    # Record scan time
    now = _dt.datetime.utcnow()
    flow.future_flow_last_scanned_at = now
    db.add(flow)
    await db.commit()

    # ---------------------------------------------------------------------------
    # Step 1: Sync fresh posts from Meta
    # ---------------------------------------------------------------------------
    synced_posts = []
    try:
        if is_facebook:
            posts_data = await meta_client.get_facebook_posts(
                page_id=account.facebook_page_id,
                page_access_token=account.page_access_token
            )
            for post in posts_data:
                existing_post = await facebook_post_repo.get(db, post["id"])
                from app.utils.text import parse_iso_timestamp
                raw_ts = post.get("timestamp") or post.get("created_time")
                ts_val = parse_iso_timestamp(raw_ts)
                post_in = {
                    "id": post["id"],
                    "facebook_account_id": account.id,
                    "caption": post.get("caption"),
                    "media_type": post.get("media_type"),
                    "media_url": post.get("media_url"),
                    "thumbnail_url": post.get("thumbnail_url"),
                    "permalink": post.get("permalink"),
                    "timestamp": ts_val or now,
                }
                if existing_post:
                    await facebook_post_repo.update(db, db_obj=existing_post, obj_in=post_in)
                    synced_posts.append(existing_post)
                else:
                    new_post = await facebook_post_repo.create(db, obj_in=post_in)
                    synced_posts.append(new_post)
            await db.commit()
            # Reload all real posts for this FB account (exclude future placeholders)
            all_posts = await facebook_post_repo.get_by_facebook_account_id(db, account.id)
        else:
            posts_data = await meta_client.get_instagram_posts(
                instagram_business_account_id=account.instagram_business_account_id,
                page_access_token=account.page_access_token
            )
            for post in posts_data:
                existing_post = await post_repo.get(db, post["id"])
                from app.utils.text import parse_iso_timestamp
                raw_ts = post.get("timestamp") or post.get("created_time")
                ts_val = parse_iso_timestamp(raw_ts)
                post_in = {
                    "id": post["id"],
                    "instagram_account_id": account.id,
                    "caption": post.get("caption"),
                    "media_type": post.get("media_type"),
                    "media_url": post.get("media_url"),
                    "thumbnail_url": post.get("thumbnail_url"),
                    "permalink": post.get("permalink"),
                    "timestamp": ts_val or now,
                }
                if existing_post:
                    await post_repo.update(db, db_obj=existing_post, obj_in=post_in)
                    synced_posts.append(existing_post)
                else:
                    new_post = await post_repo.create(db, obj_in=post_in)
                    synced_posts.append(new_post)
            await db.commit()
            all_posts = await post_repo.get_by_instagram_account_id(db, account.id)
    except Exception as sync_err:
        logger.error(f"[FutureFlow] Post sync failed for flow {flow_id}: {sync_err}")
        raise HTTPException(status_code=500, detail=f"Failed to sync posts from Meta: {str(sync_err)}")

    # ---------------------------------------------------------------------------
    # Step 2: Filter real posts (not future placeholders), published AFTER flow creation
    # ---------------------------------------------------------------------------
    real_posts = [
        p for p in all_posts
        if not str(p.id).startswith("future_")
        and p.timestamp is not None
        and p.timestamp >= (flow.created_at - _dt.timedelta(hours=1))  # 1h grace period
    ]
    
    # If user provided an expected schedule time, prefer posts published near that time (±6 hours)
    if flow.future_post_scheduled_at and real_posts:
        sched = flow.future_post_scheduled_at
        window_posts = [
            p for p in real_posts
            if abs((p.timestamp - sched).total_seconds()) <= 6 * 3600
        ]
        if window_posts:
            real_posts = window_posts

    # ---------------------------------------------------------------------------
    # Step 3: Fuzzy-match caption
    # ---------------------------------------------------------------------------
    SIMILARITY_THRESHOLD = 0.35

    best_match = None
    best_score = 0.0

    if flow.future_post_caption:
        for post in real_posts:
            caption = post.caption or ""
            score = _caption_similarity(flow.future_post_caption, caption)
            if score > best_score:
                best_score = score
                best_match = post
    elif real_posts:
        # If no caption hint, take the most recent post published after flow creation
        real_posts_sorted = sorted(real_posts, key=lambda p: p.timestamp or _dt.datetime.min, reverse=True)
        best_match = real_posts_sorted[0]
        best_score = 1.0  # Perfect confidence since it's the newest post

    if best_match and best_score >= SIMILARITY_THRESHOLD:
        logger.info(f"[FutureFlow] Match found for flow {flow_id}: post {best_match.id} (score={best_score:.2f})")
        
        # Link real post to the flow
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
        await db.refresh(flow)

        # Immediately trigger comment scan for newly resolved post
        try:
            await comment_processor.scan_and_process_pending_comments(
                db=db,
                account_id=account.id,
                target_post_id=best_match.id,
                target_flow_id=flow.id
            )
        except Exception as c_err:
            logger.warning(f"[FutureFlow] Post-resolution comment scan warning: {c_err}")
        
        return {
            "status": "resolved",
            "message": f"Future flow matched to post '{best_match.id}' with similarity {best_score:.0%}.",
            "matched_post_id": best_match.id,
            "matched_post_caption": (best_match.caption or "")[:100],
            "similarity_score": round(best_score, 3),
            "flow_id": flow_id
        }
    
    # No match found
    logger.info(f"[FutureFlow] No match found for flow {flow_id}. Best score was {best_score:.2f} (threshold={SIMILARITY_THRESHOLD})")
    return {
        "status": "no_match",
        "message": "No matching post found yet. The post may not have been published, or the caption hint is too different.",
        "posts_scanned": len(real_posts),
        "best_score": round(best_score, 3),
        "flow_id": flow_id
    }
