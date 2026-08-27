from typing import Any, List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, delete
from loguru import logger

from app.api import deps
from app.db.repository import (
    instagram_account_repo,
    facebook_account_repo,
    facebook_post_repo,
    facebook_comment_repo,
    facebook_comment_event_repo,
    automation_flow_repo,
    flow_node_repo,
    flow_edge_repo
)
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
    accounts = await instagram_account_repo.get_by_user_id(db, user_id=current_user.id)
    fb_accounts = await facebook_account_repo.get_by_user_id(db, user_id=current_user.id)
    
    processed_count = 0
    errors = []

    # Process Instagram comments
    for account in accounts:
        # Get active flows
        active_flows = await automation_flow_repo.get_active_by_instagram_account_id(db, account.id)
        if not active_flows:
            logger.warning(f"No active automation flows for account @{account.username}")
            continue

        # Get posts for this account
        posts = await post_repo.get_by_instagram_account_id(db, instagram_account_id=account.id)
        
        for post in posts:
            try:
                # Fetch comments from Meta
                meta_comments = await meta_client.get_instagram_comments(
                    media_id=post.id,
                    page_access_token=account.page_access_token
                )
                
                # Cache comments in DB
                for mc in meta_comments:
                    ts_val = mc.get("timestamp")
                    if isinstance(ts_val, str):
                        if ts_val.endswith("Z"):
                            ts_val = ts_val[:-1] + "+00:00"
                        try:
                            ts_val = datetime.fromisoformat(ts_val)
                            if ts_val.tzinfo is not None:
                                ts_val = ts_val.astimezone(timezone.utc).replace(tzinfo=None)
                        except ValueError:
                            ts_val = datetime.utcnow()
                    else:
                        ts_val = datetime.utcnow()

                    comment_in = {
                        "id": mc["id"],
                        "media_id": post.id,
                        "text": mc.get("text", ""),
                        "username": mc.get("username", "anonymous"),
                        "timestamp": ts_val,
                        "parent_id": mc.get("parent_id")
                    }
                    existing_comment = await comment_repo.get(db, id=mc["id"])
                    if existing_comment:
                        await comment_repo.update(db, db_obj=existing_comment, obj_in=comment_in)
                    else:
                        await comment_repo.create(db, obj_in=comment_in)
                await db.commit()

                # Get replies from DB to check locally
                db_comments = await comment_repo.get_by_post_id(db, post_id=post.id)
                replied_comment_ids = {c.parent_id for c in db_comments if c.parent_id}

                # Find eligible pending comments
                for mc in meta_comments:
                    comment_id = mc["id"]
                    
                    # 1. Skip replies
                    if mc.get("parent_id"):
                        continue
                        
                    # 2. Skip if already replied in DB
                    if comment_id in replied_comment_ids:
                        continue
                        
                    # 3. Check if there is already a processed or ignored CommentEvent
                    existing_event = await comment_event_repo.get_by_comment_id(db, comment_id)
                    if existing_event:
                        if existing_event.status in ["processed", "ignored"]:
                            continue
                        else:
                            # Delete the event so comment_processor doesn't skip it
                            await db.delete(existing_event)
                            await db.commit()

                    # Otherwise, run comment processor
                    ts_val = mc.get("timestamp")
                    if isinstance(ts_val, str):
                        if ts_val.endswith("Z"):
                            ts_val = ts_val[:-1] + "+00:00"
                        try:
                            ts_val = datetime.fromisoformat(ts_val)
                            if ts_val.tzinfo is not None:
                                ts_val = ts_val.astimezone(timezone.utc).replace(tzinfo=None)
                        except ValueError:
                            ts_val = datetime.utcnow()
                    else:
                        ts_val = datetime.utcnow()

                    # Call the comment processor
                    await comment_processor.process_comment(
                        db=db,
                        instagram_business_account_id=account.instagram_business_account_id,
                        comment_id=comment_id,
                        media_id=post.id,
                        text=mc.get("text", ""),
                        username=mc.get("username", "anonymous"),
                        timestamp=ts_val,
                        commenter_id=mc.get("commenter_id")
                    )
                    processed_count += 1

            except Exception as e:
                logger.error(f"Error running automation on post {post.id}: {str(e)}")
                errors.append(str(e))

    # Process Facebook comments
    for account in fb_accounts:
        # Get active flows
        active_flows = await automation_flow_repo.get_active_by_facebook_account_id(db, account.id)
        if not active_flows:
            logger.warning(f"No active automation flows for Facebook page @{account.name}")
            continue

        # Get posts for this account
        posts = await facebook_post_repo.get_by_facebook_account_id(db, facebook_account_id=account.id)
        
        for post in posts:
            try:
                # Fetch comments from Meta
                meta_comments = await meta_client.get_facebook_comments(
                    post_id=post.id,
                    page_access_token=account.page_access_token
                )
                
                # Cache comments in DB
                for mc in meta_comments:
                    ts_val = mc.get("timestamp")
                    if isinstance(ts_val, str):
                        if ts_val.endswith("Z"):
                            ts_val = ts_val[:-1] + "+00:00"
                        try:
                            ts_val = datetime.fromisoformat(ts_val)
                            if ts_val.tzinfo is not None:
                                ts_val = ts_val.astimezone(timezone.utc).replace(tzinfo=None)
                        except ValueError:
                            ts_val = datetime.utcnow()
                    else:
                        ts_val = datetime.utcnow()

                    comment_in = {
                        "id": mc["id"],
                        "media_id": post.id,
                        "text": mc.get("text", ""),
                        "username": mc.get("username", "anonymous"),
                        "timestamp": ts_val,
                        "parent_id": mc.get("parent_id")
                    }
                    existing_comment = await facebook_comment_repo.get(db, id=mc["id"])
                    if existing_comment:
                        await facebook_comment_repo.update(db, db_obj=existing_comment, obj_in=comment_in)
                    else:
                        await facebook_comment_repo.create(db, obj_in=comment_in)
                await db.commit()

                # Get replies from DB to check locally
                db_comments = await facebook_comment_repo.get_by_post_id(db, post_id=post.id)
                replied_comment_ids = {c.parent_id for c in db_comments if c.parent_id}

                # Find eligible pending comments
                for mc in meta_comments:
                    comment_id = mc["id"]
                    
                    if mc.get("parent_id"):
                        continue
                        
                    if comment_id in replied_comment_ids:
                        continue
                        
                    existing_event = await facebook_comment_event_repo.get_by_comment_id(db, comment_id)
                    if existing_event:
                        if existing_event.status in ["processed", "ignored"]:
                            continue
                        else:
                            await db.delete(existing_event)
                            await db.commit()

                    ts_val = mc.get("timestamp")
                    if isinstance(ts_val, str):
                        if ts_val.endswith("Z"):
                            ts_val = ts_val[:-1] + "+00:00"
                        try:
                            ts_val = datetime.fromisoformat(ts_val)
                            if ts_val.tzinfo is not None:
                                ts_val = ts_val.astimezone(timezone.utc).replace(tzinfo=None)
                        except ValueError:
                            ts_val = datetime.utcnow()
                    else:
                        ts_val = datetime.utcnow()

                    # Call the comment processor
                    await comment_processor.process_facebook_comment(
                        db=db,
                        facebook_page_id=account.facebook_page_id,
                        comment_id=comment_id,
                        media_id=post.id,
                        text=mc.get("text", ""),
                        username=mc.get("username", "anonymous"),
                        timestamp=ts_val
                    )
                    processed_count += 1

            except Exception as e:
                logger.error(f"Error running Facebook automation on post {post.id}: {str(e)}")
                errors.append(str(e))

    return {
        "status": "success",
        "processed_count": processed_count,
        "errors": errors
    }


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

    # Check if flow is active
    if not flow.is_active:
        raise HTTPException(status_code=400, detail="Cannot run an inactive automation flow.")

    processed_count = 0
    errors = []

    # Get posts for this account
    if is_facebook:
        posts = await facebook_post_repo.get_by_facebook_account_id(db, facebook_account_id=account.id)
    else:
        posts = await post_repo.get_by_instagram_account_id(db, instagram_account_id=account.id)
    
    for post in posts:
        try:
            # Fetch comments from Meta
            if is_facebook:
                meta_comments = await meta_client.get_facebook_comments(
                    post_id=post.id,
                    page_access_token=account.page_access_token
                )
            else:
                meta_comments = await meta_client.get_instagram_comments(
                    media_id=post.id,
                    page_access_token=account.page_access_token
                )
            
            # Cache comments in DB
            for mc in meta_comments:
                ts_val = mc.get("timestamp")
                if isinstance(ts_val, str):
                    if ts_val.endswith("Z"):
                        ts_val = ts_val[:-1] + "+00:00"
                    try:
                        ts_val = datetime.fromisoformat(ts_val)
                        if ts_val.tzinfo is not None:
                            ts_val = ts_val.astimezone(timezone.utc).replace(tzinfo=None)
                    except ValueError:
                        ts_val = datetime.utcnow()
                else:
                    ts_val = datetime.utcnow()

                comment_in = {
                    "id": mc["id"],
                    "media_id": post.id,
                    "text": mc.get("text", ""),
                    "username": mc.get("username", "anonymous"),
                    "timestamp": ts_val,
                    "parent_id": mc.get("parent_id")
                }
                if is_facebook:
                    existing_comment = await facebook_comment_repo.get(db, id=mc["id"])
                    if existing_comment:
                        await facebook_comment_repo.update(db, db_obj=existing_comment, obj_in=comment_in)
                    else:
                        await facebook_comment_repo.create(db, obj_in=comment_in)
                else:
                    existing_comment = await comment_repo.get(db, id=mc["id"])
                    if existing_comment:
                        await comment_repo.update(db, db_obj=existing_comment, obj_in=comment_in)
                    else:
                        await comment_repo.create(db, obj_in=comment_in)
            await db.commit()

            # Get replies from DB to check locally
            if is_facebook:
                db_comments = await facebook_comment_repo.get_by_post_id(db, post_id=post.id)
            else:
                db_comments = await comment_repo.get_by_post_id(db, post_id=post.id)
            replied_comment_ids = {c.parent_id for c in db_comments if c.parent_id}

            # Find eligible pending comments matching this flow's triggers
            for mc in meta_comments:
                comment_id = mc["id"]
                
                # 1. Skip replies
                if mc.get("parent_id"):
                    continue
                    
                # 2. Skip if already replied in DB
                if comment_id in replied_comment_ids:
                    continue
                    
                # 3. Check if there is already a processed or ignored CommentEvent
                if is_facebook:
                    existing_event = await facebook_comment_event_repo.get_by_comment_id(db, comment_id)
                else:
                    existing_event = await comment_event_repo.get_by_comment_id(db, comment_id)
                if existing_event:
                    if existing_event.status in ["processed", "ignored"]:
                        continue
                    else:
                        # Delete the event so comment_processor doesn't skip it
                        await db.delete(existing_event)
                        await db.commit()

                # 4. Check if the comment matches the triggers of THIS specific flow
                matched_flow_trigger = False
                for node in flow.nodes:
                    if node.type == "trigger":
                        keywords = node.config.get("keywords", [])
                        exact_word = node.config.get("exact_word", True)
                        for kw in keywords:
                            from app.utils.text import contains_keyword
                            if contains_keyword(mc.get("text", ""), kw, exact_word=exact_word):
                                matched_flow_trigger = True
                                break
                    if matched_flow_trigger:
                        break

                if not matched_flow_trigger:
                    continue

                ts_val = mc.get("timestamp")
                if isinstance(ts_val, str):
                    if ts_val.endswith("Z"):
                        ts_val = ts_val[:-1] + "+00:00"
                    try:
                        ts_val = datetime.fromisoformat(ts_val)
                        if ts_val.tzinfo is not None:
                            ts_val = ts_val.astimezone(timezone.utc).replace(tzinfo=None)
                    except ValueError:
                        ts_val = datetime.utcnow()
                else:
                    ts_val = datetime.utcnow()

                # Call the comment processor
                if is_facebook:
                    await comment_processor.process_facebook_comment(
                        db=db,
                        facebook_page_id=account.facebook_page_id,
                        comment_id=comment_id,
                        media_id=post.id,
                        text=mc.get("text", ""),
                        username=mc.get("username", "anonymous"),
                        timestamp=ts_val,
                        commenter_id=mc.get("commenter_id"),
                        target_flow_id=flow.id
                    )
                else:
                    await comment_processor.process_comment(
                        db=db,
                        instagram_business_account_id=account.instagram_business_account_id,
                        comment_id=comment_id,
                        media_id=post.id,
                        text=mc.get("text", ""),
                        username=mc.get("username", "anonymous"),
                        timestamp=ts_val,
                        commenter_id=mc.get("commenter_id"),
                        target_flow_id=flow.id
                    )
                processed_count += 1

        except Exception as e:
            logger.error(f"Error running single automation flow {flow.id} on post {post.id}: {str(e)}")
            errors.append(str(e))

    return {
        "status": "success",
        "processed_count": processed_count,
        "errors": errors
    }


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
        "is_active": flow_in.is_active
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
