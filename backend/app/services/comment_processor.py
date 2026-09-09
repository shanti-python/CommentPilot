import datetime
import re
import json
from typing import Dict, Any, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from loguru import logger

from app.db.repository import (
    instagram_account_repo,
    facebook_account_repo,
    comment_event_repo,
    facebook_comment_event_repo,
    automation_flow_repo,
    comment_repo,
    facebook_comment_repo,
    post_repo,
    facebook_post_repo
)
from app.models.instagram import CommentEvent
from app.models.facebook import FacebookCommentEvent
from app.services.automation_engine import AutomationEngine
from app.utils.text import contains_keyword
from app.integrations.meta.client import meta_client

class CommentProcessorService:
    async def process_comment(
        self,
        db: AsyncSession,
        instagram_business_account_id: str,
        comment_id: str,
        media_id: str,
        text: str,
        username: str,
        timestamp: datetime.datetime,
        commenter_id: str = None,
        target_flow_id: str = None
    ) -> CommentEvent:
        """
        Main entry point for comment processing:
        1. Ensure CommentEvent is logged.
        2. Identify connected Instagram Account.
        3. Identify matching active automation flows.
        4. Execute flows asynchronously via AutomationEngine.
        """
        logger.info(f"Processing comment {comment_id} from {username} on media {media_id}")
        
        # Check if already processed
        existing_event = await comment_event_repo.get_by_comment_id(db, comment_id)
        if existing_event:
            logger.info(f"Comment {comment_id} has already been recorded. Status: {existing_event.status}")
            return existing_event

        # 1. Save comment event to DB
        event_in = {
            "comment_id": comment_id,
            "media_id": media_id,
            "text": text,
            "username": username,
            "timestamp": timestamp,
            "commenter_id": commenter_id,
            "status": "pending"
        }
        event = await comment_event_repo.create(db, obj_in=event_in)
        await db.commit()

        # 2. Get Instagram Account connected
        account = await instagram_account_repo.get_by_instagram_id(db, instagram_business_account_id)
        if not account:
            logger.error(f"No registered Instagram Business Account found for ID: {instagram_business_account_id}")
            event.status = "failed"
            event.error_message = f"Instagram business account {instagram_business_account_id} not registered in platform."
            db.add(event)
            await db.commit()
            return event

        # Check for self-comments (business account commenting on their own posts)
        if username and account.username and username.lower() == account.username.lower():
            logger.info(f"Skipping comment {comment_id} because it was written by the account owner '{username}' themselves.")
            event.status = "ignored"
            event.error_message = "Skipped self comment"
            db.add(event)
            await db.commit()
            return event

        # Cache comment in standard Comments table. Ensure Post exists (create placeholder if needed)
        try:
            post = await post_repo.get(db, media_id)
            if not post:
                logger.info(f"Post {media_id} not found in cache. Creating placeholder post.")
                post_data = {
                    "id": media_id,
                    "instagram_account_id": account.id,
                    "caption": "Instagram Post (Fetched via Webhook)",
                    "media_type": "IMAGE",
                    "media_url": "https://images.unsplash.com/photo-1611162617213-7d7a39e9b1d7?w=500&auto=format&fit=crop&q=80",
                    "permalink": f"https://instagram.com/p/{media_id}",
                    "timestamp": timestamp or datetime.datetime.utcnow()
                }
                post = await post_repo.create(db, obj_in=post_data)
                await db.commit()

            comment_in = {
                "id": comment_id,
                "media_id": media_id,
                "text": text,
                "username": username,
                "timestamp": timestamp
            }
            existing_comment = await comment_repo.get(db, id=comment_id)
            if existing_comment:
                await comment_repo.update(db, db_obj=existing_comment, obj_in=comment_in)
            else:
                await comment_repo.create(db, obj_in=comment_in)
            await db.commit()
        except Exception as e:
            logger.warning(f"Could not cache comment in comments table: {str(e)}")

        # Check if this post has a post-specific active automation rule setup on this post
        if post and post.automation_status == "active" and post.keyword:
            if contains_keyword(text, post.keyword):
                logger.info(f"Comment matches post-specific automation keyword '{post.keyword}' on post {media_id}")
                
                # 1. Reply to comment if message set
                if post.reply_message:
                    from sqlalchemy import select
                    from app.models.instagram import Comment
                    
                    stmt = select(Comment).filter(Comment.parent_id == comment_id)
                    res = await db.execute(stmt)
                    if res.scalars().first():
                        logger.info(f"Comment {comment_id} has already been replied to. Skipping post-specific reply.")
                    else:
                        replacements = {
                            "username": username,
                            "comment_text": text,
                            "post_id": media_id,
                            "comment_id": comment_id
                        }
                        reply_text = post.reply_message
                        for k, v in replacements.items():
                            reply_text = re.sub(r'(?i)\{\{\s*' + re.escape(k) + r'\s*\}\}', str(v), reply_text)
                        try:
                            reply_id = await meta_client.reply_to_comment(
                                page_access_token=account.page_access_token,
                                comment_id=comment_id,
                                message=reply_text
                            )
                            logger.info(f"Sent post-specific reply: {reply_id}")
                            try:
                                await comment_repo.create(db, obj_in={
                                    "id": reply_id or f"post_reply_{int(datetime.datetime.utcnow().timestamp())}",
                                    "media_id": media_id,
                                    "text": reply_text,
                                    "username": account.username,
                                    "timestamp": datetime.datetime.utcnow(),
                                    "parent_id": comment_id
                                })
                                await db.commit()
                            except Exception as cache_ex:
                                logger.warning(f"Could not cache post-specific reply: {str(cache_ex)}")
                        except Exception as e_reply:
                            logger.error(f"Failed to send post-specific reply: {str(e_reply)}")
                
                # 2. Send DM if message set
                if post.dm_message:
                    replacements = {
                        "username": username,
                        "comment_text": text,
                        "post_id": media_id,
                        "comment_id": comment_id
                    }
                    dm_text = post.dm_message
                    try:
                        stripped = dm_text.strip()
                        if stripped.startswith("{") and stripped.endswith("}"):
                            parsed_dm = json.loads(stripped)
                            def replace_in_obj(obj):
                                if isinstance(obj, str):
                                    for k, v in replacements.items():
                                        obj = re.sub(r'(?i)\{\{\s*' + re.escape(k) + r'\s*\}\}', str(v), obj)
                                    return obj
                                elif isinstance(obj, dict):
                                    return {k: replace_in_obj(v) for k, v in obj.items()}
                                elif isinstance(obj, list):
                                    return [replace_in_obj(item) for item in obj]
                                return obj
                            parsed_dm = replace_in_obj(parsed_dm)
                            dm_text = json.dumps(parsed_dm)
                        else:
                            for k, v in replacements.items():
                                dm_text = re.sub(r'(?i)\{\{\s*' + re.escape(k) + r'\s*\}\}', str(v), dm_text)
                    except Exception as e_json:
                        logger.warning(f"Failed parsing JSON for post-specific DM: {str(e_json)}")
                        for k, v in replacements.items():
                            dm_text = re.sub(r'(?i)\{\{\s*' + re.escape(k) + r'\s*\}\}', str(v), dm_text)
                    
                    try:
                        await meta_client.send_dm_by_comment(
                            page_access_token=account.page_access_token,
                            comment_id=comment_id,
                            message_text=dm_text
                        )
                        if commenter_id:
                            await meta_client.send_direct_dm(
                                page_access_token=account.page_access_token,
                                recipient_id=commenter_id,
                                message_text=dm_text
                            )
                        logger.info("Sent post-specific DM successfully")
                    except Exception as e_dm:
                        logger.error(f"Failed to send post-specific DM: {str(e_dm)}")
                        
                event.status = "processed"
                event.processed_at = datetime.datetime.utcnow()
                db.add(event)
                await db.commit()
                return event

        # 3. Retrieve all active flows for the account
        active_flows = await automation_flow_repo.get_active_by_instagram_account_id(db, account.id)
        if target_flow_id:
            active_flows = [f for f in active_flows if f.id == target_flow_id]
        else:
            # Filter active flows:
            # 1. Post-specific flows matched to this media_id (or resolved future flow for this media_id)
            post_specific_flows = [f for f in active_flows if f.instagram_post_id == media_id]
            # 2. Future flows with apply_to_all_future_posts enabled
            future_all_flows = []
            if post and post.timestamp:
                for f in active_flows:
                    if f.is_future_flow and f.apply_to_all_future_posts:
                        if f.created_at and post.timestamp >= (f.created_at - datetime.timedelta(hours=1)):
                            future_all_flows.append(f)

            if post_specific_flows or future_all_flows:
                seen_flow_ids = set()
                combined = []
                for f in post_specific_flows + future_all_flows:
                    if f.id not in seen_flow_ids:
                        seen_flow_ids.add(f.id)
                        combined.append(f)
                active_flows = combined
            else:
                active_flows = [f for f in active_flows if f.instagram_post_id is None and not f.is_future_flow]
        
        matched_any_flow = False
        flows_to_run = []

        # Find flows with triggers matching the comment keywords
        for flow in active_flows:
            for node in flow.nodes:
                if node.type == "trigger":
                    keywords = node.config.get("keywords", [])
                    exact_word = node.config.get("exact_word", True)
                    
                    for kw in keywords:
                        if contains_keyword(text, kw, exact_word=exact_word):
                            flows_to_run.append(flow)
                            matched_any_flow = True
                            break
                            
                if matched_any_flow:
                    # Break outer loop once a match for this flow is found
                    break
            # Reset flag for next flow
            matched_any_flow = False

        if not flows_to_run:
            logger.info(f"No automation rules matched for comment '{text}'")
            event.status = "ignored"
            db.add(event)
            await db.commit()
            return event

        # 4. Execute all matching flows
        # Use single engine instance
        engine = AutomationEngine(db, account, event)
        
        has_error = False
        error_msg = ""
        
        for flow in flows_to_run:
            try:
                await engine.run_flow(flow)
            except Exception as e:
                logger.error(f"Error executing flow {flow.id}: {str(e)}")
                has_error = True
                error_msg += f"[Flow {flow.id} failed: {str(e)}] "

        # 5. Update comment event status
        if has_error:
            event.status = "failed"
            event.error_message = error_msg.strip()
        else:
            event.status = "processed"
            
        event.processed_at = datetime.datetime.utcnow()
        db.add(event)
        await db.commit()
        
        logger.info(f"Finished processing comment {comment_id}. Final status: {event.status}")
        return event

    async def process_facebook_comment(
        self,
        db: AsyncSession,
        facebook_page_id: str,
        comment_id: str,
        media_id: str,
        text: str,
        username: str,
        timestamp: datetime.datetime,
        commenter_id: str = None,
        target_flow_id: str = None
    ) -> FacebookCommentEvent:
        """
        Main entry point for Facebook comment processing.
        """
        logger.info(f"Processing Facebook comment {comment_id} from {username} on media {media_id}")
        
        # Check if already processed
        existing_event = await facebook_comment_event_repo.get_by_comment_id(db, comment_id)
        if existing_event:
            logger.info(f"Facebook comment {comment_id} has already been recorded. Status: {existing_event.status}")
            return existing_event

        # 1. Save comment event to DB
        event_in = {
            "comment_id": comment_id,
            "media_id": media_id,
            "text": text,
            "username": username,
            "timestamp": timestamp,
            "commenter_id": commenter_id,
            "status": "pending"
        }
        event = await facebook_comment_event_repo.create(db, obj_in=event_in)
        await db.commit()

        # 2. Get Facebook Page Account connected
        account = await facebook_account_repo.get_by_page_id(db, facebook_page_id)
        if not account:
            logger.error(f"No registered Facebook Page found for Page ID: {facebook_page_id}")
            event.status = "failed"
            event.error_message = f"Facebook page {facebook_page_id} not registered in platform."
            db.add(event)
            await db.commit()
            return event

        # Check for self-comments (page commenting on their own posts)
        if username and account.username and username.lower() == account.username.lower():
            logger.info(f"Skipping Facebook comment {comment_id} because it was written by the page owner '{username}' themselves.")
            event.status = "ignored"
            event.error_message = "Skipped self comment"
            db.add(event)
            await db.commit()
            return event

        # Cache comment in standard FacebookComments table. Ensure Post exists (create placeholder if needed)
        try:
            post = await facebook_post_repo.get(db, media_id)
            if not post:
                logger.info(f"Facebook Post {media_id} not found in cache. Creating placeholder post.")
                post_data = {
                    "id": media_id,
                    "facebook_account_id": account.id,
                    "caption": "Facebook Post (Fetched via Webhook)",
                    "media_type": "post",
                    "media_url": "https://images.unsplash.com/photo-1611162617213-7d7a39e9b1d7?w=500&auto=format&fit=crop&q=80",
                    "permalink": f"https://facebook.com/{media_id}",
                    "timestamp": timestamp or datetime.datetime.utcnow()
                }
                post = await facebook_post_repo.create(db, obj_in=post_data)
                await db.commit()

            comment_in = {
                "id": comment_id,
                "media_id": media_id,
                "text": text,
                "username": username,
                "timestamp": timestamp
            }
            existing_comment = await facebook_comment_repo.get(db, id=comment_id)
            if existing_comment:
                await facebook_comment_repo.update(db, db_obj=existing_comment, obj_in=comment_in)
            else:
                await facebook_comment_repo.create(db, obj_in=comment_in)
            await db.commit()
        except Exception as e:
            logger.warning(f"Could not cache Facebook comment in comments table: {str(e)}")

        # Check if this Facebook post has a post-specific active automation rule setup
        if post and post.automation_status == "active" and post.keyword:
            if contains_keyword(text, post.keyword):
                logger.info(f"Comment matches post-specific Facebook automation keyword '{post.keyword}' on post {media_id}")
                
                # 1. Reply to comment if message set
                if post.reply_message:
                    from sqlalchemy import select
                    from app.models.facebook import FacebookComment
                    
                    stmt = select(FacebookComment).filter(FacebookComment.parent_id == comment_id)
                    res = await db.execute(stmt)
                    if res.scalars().first():
                        logger.info(f"Facebook comment {comment_id} has already been replied to. Skipping post-specific Facebook reply.")
                    else:
                        replacements = {
                            "username": username,
                            "comment_text": text,
                            "post_id": media_id,
                            "comment_id": comment_id
                        }
                        reply_text = post.reply_message
                        for k, v in replacements.items():
                            reply_text = re.sub(r'(?i)\{\{\s*' + re.escape(k) + r'\s*\}\}', str(v), reply_text)
                        try:
                            reply_id = await meta_client.reply_to_comment(
                                page_access_token=account.page_access_token,
                                comment_id=comment_id,
                                message=reply_text
                            )
                            logger.info(f"Sent post-specific Facebook reply: {reply_id}")
                            try:
                                await facebook_comment_repo.create(db, obj_in={
                                    "id": reply_id or f"fb_post_reply_{int(datetime.datetime.utcnow().timestamp())}",
                                    "media_id": media_id,
                                    "text": reply_text,
                                    "username": account.name or account.username,
                                    "timestamp": datetime.datetime.utcnow(),
                                    "parent_id": comment_id
                                })
                                await db.commit()
                            except Exception as cache_ex:
                                logger.warning(f"Could not cache post-specific Facebook reply: {str(cache_ex)}")
                        except Exception as e_reply:
                            logger.error(f"Failed to send post-specific Facebook reply: {str(e_reply)}")
                
                # 2. Send DM via private comment reply if message set
                if post.dm_message:
                    replacements = {
                        "username": username,
                        "comment_text": text,
                        "post_id": media_id,
                        "comment_id": comment_id
                    }
                    dm_text = post.dm_message
                    try:
                        stripped = dm_text.strip()
                        if stripped.startswith("{") and stripped.endswith("}"):
                            parsed_dm = json.loads(stripped)
                            def replace_in_obj(obj):
                                if isinstance(obj, str):
                                    for k, v in replacements.items():
                                        obj = re.sub(r'(?i)\{\{\s*' + re.escape(k) + r'\s*\}\}', str(v), obj)
                                    return obj
                                elif isinstance(obj, dict):
                                    return {k: replace_in_obj(v) for k, v in obj.items()}
                                elif isinstance(obj, list):
                                    return [replace_in_obj(item) for item in obj]
                                return obj
                            parsed_dm = replace_in_obj(parsed_dm)
                            dm_text = json.dumps(parsed_dm)
                        else:
                            for k, v in replacements.items():
                                dm_text = re.sub(r'(?i)\{\{\s*' + re.escape(k) + r'\s*\}\}', str(v), dm_text)
                    except Exception as e_json:
                        logger.warning(f"Failed parsing JSON for post-specific DM: {str(e_json)}")
                        for k, v in replacements.items():
                            dm_text = re.sub(r'(?i)\{\{\s*' + re.escape(k) + r'\s*\}\}', str(v), dm_text)
                    
                    try:
                        # Private replies work on Facebook using comment ID
                        await meta_client.send_dm_by_comment(
                            page_access_token=account.page_access_token,
                            comment_id=comment_id,
                            message_text=dm_text
                        )
                        logger.info("Sent post-specific Facebook DM successfully")
                    except Exception as e_dm:
                        logger.error(f"Failed to send post-specific Facebook DM: {str(e_dm)}")
                        
                event.status = "processed"
                event.processed_at = datetime.datetime.utcnow()
                db.add(event)
                await db.commit()
                return event

        # 3. Retrieve all active flows for the Facebook account
        active_flows = await automation_flow_repo.get_active_by_facebook_account_id(db, account.id)
        if target_flow_id:
            active_flows = [f for f in active_flows if f.id == target_flow_id]
        else:
            # Filter active flows:
            post_specific_flows = [f for f in active_flows if f.facebook_post_id == media_id]
            future_all_flows = []
            if post and post.timestamp:
                for f in active_flows:
                    if f.is_future_flow and f.apply_to_all_future_posts:
                        if f.created_at and post.timestamp >= (f.created_at - datetime.timedelta(hours=1)):
                            future_all_flows.append(f)

            if post_specific_flows or future_all_flows:
                seen_flow_ids = set()
                combined = []
                for f in post_specific_flows + future_all_flows:
                    if f.id not in seen_flow_ids:
                        seen_flow_ids.add(f.id)
                        combined.append(f)
                active_flows = combined
            else:
                active_flows = [f for f in active_flows if f.facebook_post_id is None and not f.is_future_flow]
        
        matched_any_flow = False
        flows_to_run = []

        # Find flows with triggers matching the comment keywords
        for flow in active_flows:
            for node in flow.nodes:
                if node.type == "trigger":
                    keywords = node.config.get("keywords", [])
                    exact_word = node.config.get("exact_word", True)
                    
                    for kw in keywords:
                        if contains_keyword(text, kw, exact_word=exact_word):
                            flows_to_run.append(flow)
                            matched_any_flow = True
                            break
                            
                if matched_any_flow:
                    break
            matched_any_flow = False

        if not flows_to_run:
            logger.info(f"No Facebook automation rules matched for comment '{text}'")
            event.status = "ignored"
            db.add(event)
            await db.commit()
            return event

        # 4. Execute all matching flows
        engine = AutomationEngine(db, account, event)
        
        has_error = False
        error_msg = ""
        
        for flow in flows_to_run:
            try:
                await engine.run_flow(flow)
            except Exception as e:
                logger.error(f"Error executing Facebook flow {flow.id}: {str(e)}")
                has_error = True
                error_msg += f"[Flow {flow.id} failed: {str(e)}] "

        # 5. Update comment event status
        if has_error:
            event.status = "failed"
            event.error_message = error_msg.strip()
        else:
            event.status = "processed"
            
        event.processed_at = datetime.datetime.utcnow()
        db.add(event)
        await db.commit()
        
        logger.info(f"Finished processing Facebook comment {comment_id}. Final status: {event.status}")
        return event

    async def scan_and_process_pending_comments(
        self,
        db: AsyncSession,
        user_id: Optional[int] = None,
        account_id: Optional[int] = None,
        target_post_id: Optional[str] = None,
        target_flow_id: Optional[str] = None,
        since_timestamp: Optional[datetime.datetime] = None
    ) -> Dict[str, Any]:
        """
        Scan comments from Meta Graph API for posts linked to active flows (or all posts),
        cache comments, and execute matching automation rules for unreplied comments.
        """
        from app.utils.text import parse_iso_timestamp
        processed_comment_ids = set()
        errors = []

        # 1. Instagram Accounts
        if user_id:
            insta_accounts = await instagram_account_repo.get_by_user_id(db, user_id=user_id)
        else:
            insta_accounts = await instagram_account_repo.get_multi(db, limit=500)

        if account_id:
            insta_accounts = [acc for acc in insta_accounts if acc.id == account_id]

        for account in insta_accounts:
            try:
                active_flows = await automation_flow_repo.get_active_by_instagram_account_id(db, account.id)
                if target_flow_id:
                    active_flows = [f for f in active_flows if f.id == target_flow_id]
                if not active_flows:
                    continue

                # 1. Sync fresh posts from Meta Graph API so new posts are discovered
                try:
                    fresh_posts = await meta_client.get_instagram_posts(
                        instagram_business_account_id=account.instagram_business_account_id,
                        page_access_token=account.page_access_token,
                        max_items=10
                    )
                    for p in fresh_posts:
                        raw_ts = p.get("timestamp") or p.get("created_time")
                        ts_val = parse_iso_timestamp(raw_ts) or datetime.datetime.utcnow()
                        post_in = {
                            "id": p["id"],
                            "instagram_account_id": account.id,
                            "caption": p.get("caption"),
                            "media_type": p.get("media_type"),
                            "media_url": p.get("media_url"),
                            "thumbnail_url": p.get("thumbnail_url"),
                            "permalink": p.get("permalink"),
                            "timestamp": ts_val,
                        }
                        existing_p = await post_repo.get(db, p["id"])
                        if existing_p:
                            await post_repo.update(db, db_obj=existing_p, obj_in=post_in)
                        else:
                            await post_repo.create(db, obj_in=post_in)
                    await db.commit()
                except Exception as sync_err:
                    logger.warning(f"Could not sync fresh posts from Instagram for account {account.id}: {sync_err}")

                # 2. Check if any pending future flows can be resolved to newly synced posts
                for f in active_flows:
                    if f.is_future_flow:
                        account_posts = await post_repo.get_by_instagram_account_id(db, instagram_account_id=account.id)
                        eligible_posts = [
                            p for p in account_posts
                            if not str(p.id).startswith("future_")
                            and p.timestamp is not None
                            and p.timestamp >= (f.created_at - datetime.timedelta(hours=1))
                        ]
                        if f.apply_to_all_future_posts:
                            for ep in eligible_posts:
                                if ep.automation_status != "active":
                                    ep.automation_status = "active"
                                    db.add(ep)
                            await db.commit()

                        if f.future_flow_status == 'pending' or not f.instagram_post_id:
                            if eligible_posts:
                                best_p = None
                                if f.future_post_caption:
                                    from app.api.api_v1.endpoints.automation import _caption_similarity
                                    best_s = 0.0
                                    for ep in eligible_posts:
                                        s = _caption_similarity(f.future_post_caption, ep.caption or "")
                                        if s > best_s:
                                            best_s = s
                                            best_p = ep
                                    if best_s < 0.35:
                                        best_p = None
                                else:
                                    sorted_p = sorted(eligible_posts, key=lambda x: x.timestamp or datetime.datetime.min, reverse=True)
                                    best_p = sorted_p[0]

                                if best_p:
                                    logger.info(f"[PeriodicScanner] Resolving future flow {f.id} to post {best_p.id}")
                                    f.future_flow_status = "resolved"
                                    f.instagram_post_id = best_p.id
                                    f.future_flow_last_scanned_at = datetime.datetime.utcnow()
                                    best_p.automation_status = "active"
                                    db.add(best_p)
                                    db.add(f)
                                    await db.commit()

                posts = await post_repo.get_by_instagram_account_id(db, instagram_account_id=account.id)
                if target_post_id:
                    posts = [p for p in posts if p.id == target_post_id]
                else:
                    linked_post_ids = {f.instagram_post_id for f in active_flows if f.instagram_post_id}
                    has_future_all = any(f.is_future_flow and f.apply_to_all_future_posts for f in active_flows)
                    has_general_flow = any(f.instagram_post_id is None and not f.is_future_flow for f in active_flows)

                    if has_future_all:
                        future_flows = [f for f in active_flows if f.is_future_flow and f.apply_to_all_future_posts and f.created_at]
                        if future_flows:
                            min_created = min(f.created_at for f in future_flows)
                            future_eligible_ids = {p.id for p in posts if p.timestamp and p.timestamp >= (min_created - datetime.timedelta(hours=1))}
                            linked_post_ids = linked_post_ids.union(future_eligible_ids)

                    if has_general_flow or has_future_all:
                        posts_dict = {p.id: p for p in posts[:5]}
                        for p in posts:
                            if p.id in linked_post_ids:
                                posts_dict[p.id] = p
                        posts = list(posts_dict.values())
                    elif linked_post_ids:
                        posts = [p for p in posts if p.id in linked_post_ids]
                    else:
                        posts = posts[:3]

                for post in posts:
                    try:
                        meta_comments = await meta_client.get_instagram_comments(
                            media_id=post.id,
                            page_access_token=account.page_access_token
                        )

                        # Cache comments in DB
                        for mc in meta_comments:
                            raw_ts = mc.get("timestamp")
                            ts_val = parse_iso_timestamp(raw_ts) or datetime.datetime.utcnow()

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

                        # Collect all replied-to comment IDs from DB and API
                        db_comments = await comment_repo.get_by_post_id(db, post_id=post.id)
                        replied_comment_ids = {c.parent_id for c in db_comments if c.parent_id}
                        for mc in meta_comments:
                            if mc.get("parent_id"):
                                replied_comment_ids.add(mc.get("parent_id"))

                        for mc in meta_comments:
                            comment_id = mc["id"]
                            # Skip replies
                            if mc.get("parent_id"):
                                continue

                            # Check existing event
                            existing_event = await comment_event_repo.get_by_comment_id(db, comment_id)
                            if existing_event:
                                if existing_event.status == "processed":
                                    if since_timestamp and existing_event.processed_at and existing_event.processed_at >= since_timestamp:
                                        processed_comment_ids.add(comment_id)
                                    continue
                                elif existing_event.status == "ignored":
                                    continue
                                else:
                                    await db.delete(existing_event)
                                    await db.commit()

                            # Skip if already replied to on Instagram
                            if comment_id in replied_comment_ids:
                                continue

                            raw_ts = mc.get("timestamp")
                            ts_val = parse_iso_timestamp(raw_ts) or datetime.datetime.utcnow()

                            logger.info(f"[PeriodicScanner] Triggering processing for Instagram comment {comment_id} on post {post.id}")
                            proc_res = await self.process_comment(
                                db=db,
                                instagram_business_account_id=account.instagram_business_account_id,
                                comment_id=comment_id,
                                media_id=post.id,
                                text=mc.get("text", ""),
                                username=mc.get("username", "anonymous"),
                                timestamp=ts_val,
                                commenter_id=mc.get("commenter_id"),
                                target_flow_id=target_flow_id
                            )
                            if proc_res and getattr(proc_res, "status", None) == "processed":
                                processed_comment_ids.add(comment_id)
                    except Exception as post_err:
                        logger.error(f"Error scanning comments for IG post {post.id}: {post_err}")
                        errors.append(str(post_err))
            except Exception as acc_err:
                logger.error(f"Error scanning comments for IG account {account.id}: {acc_err}")
                errors.append(str(acc_err))

        # 2. Facebook Accounts
        if user_id:
            fb_accounts = await facebook_account_repo.get_by_user_id(db, user_id=user_id)
        else:
            fb_accounts = await facebook_account_repo.get_multi(db, limit=500)

        if account_id:
            fb_accounts = [acc for acc in fb_accounts if acc.id == account_id]

        for account in fb_accounts:
            try:
                active_flows = await automation_flow_repo.get_active_by_facebook_account_id(db, account.id)
                if target_flow_id:
                    active_flows = [f for f in active_flows if f.id == target_flow_id]
                if not active_flows:
                    continue

                # 1. Sync fresh posts from Facebook Page
                try:
                    fresh_posts = await meta_client.get_facebook_posts(
                        page_id=account.facebook_page_id,
                        page_access_token=account.page_access_token
                    )
                    for p in fresh_posts:
                        raw_ts = p.get("timestamp") or p.get("created_time")
                        ts_val = parse_iso_timestamp(raw_ts) or datetime.datetime.utcnow()
                        post_in = {
                            "id": p["id"],
                            "facebook_account_id": account.id,
                            "caption": p.get("caption"),
                            "media_type": p.get("media_type"),
                            "media_url": p.get("media_url"),
                            "thumbnail_url": p.get("thumbnail_url"),
                            "permalink": p.get("permalink"),
                            "timestamp": ts_val,
                        }
                        existing_p = await facebook_post_repo.get(db, p["id"])
                        if existing_p:
                            await facebook_post_repo.update(db, db_obj=existing_p, obj_in=post_in)
                        else:
                            await facebook_post_repo.create(db, obj_in=post_in)
                    await db.commit()
                except Exception as sync_err:
                    logger.warning(f"Could not sync fresh posts from Facebook for account {account.id}: {sync_err}")

                # 2. Check if any pending future flows can be resolved to newly synced posts
                for f in active_flows:
                    if f.is_future_flow:
                        account_posts = await facebook_post_repo.get_by_facebook_account_id(db, facebook_account_id=account.id)
                        eligible_posts = [
                            p for p in account_posts
                            if not str(p.id).startswith("future_")
                            and p.timestamp is not None
                            and p.timestamp >= (f.created_at - datetime.timedelta(hours=1))
                        ]
                        if f.apply_to_all_future_posts:
                            for ep in eligible_posts:
                                if ep.automation_status != "active":
                                    ep.automation_status = "active"
                                    db.add(ep)
                            await db.commit()

                        if f.future_flow_status == 'pending' or not f.facebook_post_id:
                            if eligible_posts:
                                best_p = None
                                if f.future_post_caption:
                                    from app.api.api_v1.endpoints.automation import _caption_similarity
                                    best_s = 0.0
                                    for ep in eligible_posts:
                                        s = _caption_similarity(f.future_post_caption, ep.caption or "")
                                        if s > best_s:
                                            best_s = s
                                            best_p = ep
                                    if best_s < 0.35:
                                        best_p = None
                                else:
                                    sorted_p = sorted(eligible_posts, key=lambda x: x.timestamp or datetime.datetime.min, reverse=True)
                                    best_p = sorted_p[0]

                                if best_p:
                                    logger.info(f"[PeriodicScanner] Resolving Facebook future flow {f.id} to post {best_p.id}")
                                    f.future_flow_status = "resolved"
                                    f.facebook_post_id = best_p.id
                                    f.future_flow_last_scanned_at = datetime.datetime.utcnow()
                                    best_p.automation_status = "active"
                                    db.add(best_p)
                                    db.add(f)
                                    await db.commit()

                posts = await facebook_post_repo.get_by_facebook_account_id(db, facebook_account_id=account.id)
                if target_post_id:
                    posts = [p for p in posts if p.id == target_post_id]
                else:
                    linked_post_ids = {f.facebook_post_id for f in active_flows if f.facebook_post_id}
                    has_future_all = any(f.is_future_flow and f.apply_to_all_future_posts for f in active_flows)
                    has_general_flow = any(f.facebook_post_id is None and not f.is_future_flow for f in active_flows)

                    if has_future_all:
                        future_flows = [f for f in active_flows if f.is_future_flow and f.apply_to_all_future_posts and f.created_at]
                        if future_flows:
                            min_created = min(f.created_at for f in future_flows)
                            future_eligible_ids = {p.id for p in posts if p.timestamp and p.timestamp >= (min_created - datetime.timedelta(hours=1))}
                            linked_post_ids = linked_post_ids.union(future_eligible_ids)

                    if has_general_flow or has_future_all:
                        posts_dict = {p.id: p for p in posts[:5]}
                        for p in posts:
                            if p.id in linked_post_ids:
                                posts_dict[p.id] = p
                        posts = list(posts_dict.values())
                    elif linked_post_ids:
                        posts = [p for p in posts if p.id in linked_post_ids]
                    else:
                        posts = posts[:3]

                for post in posts:
                    try:
                        meta_comments = await meta_client.get_facebook_comments(
                            post_id=post.id,
                            page_access_token=account.page_access_token
                        )

                        for mc in meta_comments:
                            raw_ts = mc.get("timestamp")
                            ts_val = parse_iso_timestamp(raw_ts) or datetime.datetime.utcnow()

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

                        db_comments = await facebook_comment_repo.get_by_post_id(db, post_id=post.id)
                        replied_comment_ids = {c.parent_id for c in db_comments if c.parent_id}
                        for mc in meta_comments:
                            if mc.get("parent_id"):
                                replied_comment_ids.add(mc.get("parent_id"))

                        for mc in meta_comments:
                            comment_id = mc["id"]
                            # Skip replies
                            if mc.get("parent_id"):
                                continue

                            existing_event = await facebook_comment_event_repo.get_by_comment_id(db, comment_id)
                            if existing_event:
                                if existing_event.status == "processed":
                                    if since_timestamp and existing_event.processed_at and existing_event.processed_at >= since_timestamp:
                                        processed_comment_ids.add(comment_id)
                                    continue
                                elif existing_event.status == "ignored":
                                    continue
                                else:
                                    await db.delete(existing_event)
                                    await db.commit()

                            # Skip if already replied to on Facebook
                            if comment_id in replied_comment_ids:
                                continue

                            raw_ts = mc.get("timestamp")
                            ts_val = parse_iso_timestamp(raw_ts) or datetime.datetime.utcnow()

                            logger.info(f"[PeriodicScanner] Triggering processing for Facebook comment {comment_id} on post {post.id}")
                            proc_res = await self.process_facebook_comment(
                                db=db,
                                facebook_page_id=account.facebook_page_id,
                                comment_id=comment_id,
                                media_id=post.id,
                                text=mc.get("text", ""),
                                username=mc.get("username", "anonymous"),
                                timestamp=ts_val,
                                commenter_id=mc.get("commenter_id"),
                                target_flow_id=target_flow_id
                            )
                            if proc_res and getattr(proc_res, "status", None) == "processed":
                                processed_comment_ids.add(comment_id)
                    except Exception as post_err:
                        logger.error(f"Error scanning comments for FB post {post.id}: {post_err}")
                        errors.append(str(post_err))
            except Exception as acc_err:
                logger.error(f"Error scanning comments for FB account {account.id}: {acc_err}")
                errors.append(str(acc_err))

        return {
            "status": "success",
            "processed_count": len(processed_comment_ids),
            "errors": errors
        }


comment_processor = CommentProcessorService()
