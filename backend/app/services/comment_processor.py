import datetime
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

        # 3. Retrieve all active flows for the account
        active_flows = await automation_flow_repo.get_active_by_instagram_account_id(db, account.id)
        if target_flow_id:
            active_flows = [f for f in active_flows if f.id == target_flow_id]
        
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

        # 3. Retrieve all active flows for the Facebook account
        active_flows = await automation_flow_repo.get_active_by_facebook_account_id(db, account.id)
        if target_flow_id:
            active_flows = [f for f in active_flows if f.id == target_flow_id]
        
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
