import datetime
import re
import json
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
            # Filter active flows: prefer post-specific flows, fallback to general ones
            post_specific_flows = [f for f in active_flows if f.instagram_post_id == media_id]
            if post_specific_flows:
                active_flows = post_specific_flows
            else:
                active_flows = [f for f in active_flows if f.instagram_post_id is None]
        
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
            # Filter active flows: prefer post-specific flows, fallback to general ones
            post_specific_flows = [f for f in active_flows if f.facebook_post_id == media_id]
            if post_specific_flows:
                active_flows = post_specific_flows
            else:
                active_flows = [f for f in active_flows if f.facebook_post_id is None]
        
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


comment_processor = CommentProcessorService()
