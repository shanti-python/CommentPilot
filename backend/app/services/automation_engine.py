import datetime
import re
from typing import Dict, Any, List, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from loguru import logger

from app.models.instagram import InstagramAccount, CommentEvent
from app.models.facebook import FacebookAccount, FacebookCommentEvent
from app.models.automation import AutomationFlow, FlowNode, FlowEdge
from app.models.log import AutomationLog
from app.db.repository import automation_log_repo, comment_repo, facebook_comment_repo
from app.integrations.meta.client import meta_client, MetaAPIError
from app.utils.text import contains_keyword

class AutomationEngine:
    def __init__(self, db: AsyncSession, account: Any, comment_event: Any):
        self.db = db
        self.account = account
        self.comment_event = comment_event
        self.tags: List[str] = []
        self.is_facebook = hasattr(account, "facebook_page_id")

    async def _replace_placeholders(self, text: str) -> str:
        """Replace placeholders like {{username}}, {{post_title}}, and {{comment_text}} in templates."""
        if not text:
            return ""
        
        post_title = ""
        if self.comment_event.media_id:
            try:
                from sqlalchemy import select
                if self.is_facebook:
                    from app.models.facebook import FacebookPost
                    stmt = select(FacebookPost).filter(FacebookPost.id == self.comment_event.media_id)
                    res = await self.db.execute(stmt)
                    post_obj = res.scalar_one_or_none()
                    if post_obj:
                        post_title = post_obj.caption or ""
                else:
                    from app.models.instagram import Post
                    stmt = select(Post).filter(Post.id == self.comment_event.media_id)
                    res = await self.db.execute(stmt)
                    post_obj = res.scalar_one_or_none()
                    if post_obj:
                        post_title = post_obj.caption or ""
            except Exception as e:
                logger.warning(f"Failed to fetch post title for placeholder replacement: {str(e)}")

        replacements = {
            "username": self.comment_event.username or "",
            "comment_text": self.comment_event.text or "",
            "post_id": self.comment_event.media_id or "",
            "comment_id": self.comment_event.comment_id or "",
            "post_title": post_title
        }

        def replace_in_obj(obj):
            if isinstance(obj, str):
                for k, v in replacements.items():
                    escaped_key = re.escape(k)
                    pattern = r'(?i)\{\{\s*' + escaped_key + r'\s*\}\}'
                    obj = re.sub(pattern, str(v), obj)
                return obj
            elif isinstance(obj, dict):
                return {k: replace_in_obj(v) for k, v in obj.items()}
            elif isinstance(obj, list):
                return [replace_in_obj(item) for item in obj]
            return obj

        import json
        try:
            stripped = text.strip()
            if stripped.startswith("{") and stripped.endswith("}"):
                data = json.loads(stripped)
                data = replace_in_obj(data)
                return json.dumps(data)
        except Exception as e:
            logger.warning(f"Failed JSON-aware placeholder replacement: {str(e)}")

        for k, v in replacements.items():
            escaped_key = re.escape(k)
            pattern = r'(?i)\{\{\s*' + escaped_key + r'\s*\}\}'
            text = re.sub(pattern, str(v), text)
        return text

    async def log_step(self, flow_id: str, action_type: str, status: str, details: Dict[str, Any]):
        """Write execution step details to the database logs."""
        try:
            log_data = {
                "flow_id": flow_id,
                "comment_id": self.comment_event.comment_id,
                "action_type": action_type,
                "status": status,
                "details": details
            }
            await automation_log_repo.create(self.db, obj_in=log_data)
        except Exception as e:
            logger.error(f"Failed to save automation log: {str(e)}")

    async def run_flow(self, flow: AutomationFlow):
        """Execute the automation flow starting from the matched keyword trigger."""
        logger.info(f"Running flow '{flow.name}' (ID: {flow.id}) for comment {self.comment_event.comment_id}")
        
        # Load nodes and edges mapping
        nodes_map = {node.id: node for node in flow.nodes}
        
        # Find trigger node that matched
        trigger_node = None
        for node in flow.nodes:
            if node.type == "trigger":
                keywords = node.config.get("keywords", [])
                exact_word = node.config.get("exact_word", True)
                for kw in keywords:
                    if contains_keyword(self.comment_event.text, kw, exact_word=exact_word):
                        trigger_node = node
                        break
            if trigger_node:
                break
                
        if not trigger_node:
            logger.warning(f"Could not locate matching trigger node in flow {flow.id}")
            return
            
        # Log trigger match success
        await self.log_step(
            flow_id=flow.id,
            action_type="trigger_match",
            status="success",
            details={
                "trigger_node_id": trigger_node.id,
                "comment_text": self.comment_event.text,
                "matched_keywords": trigger_node.config.get("keywords", [])
            }
        )
        
        # Start BFS/DFS traversal from trigger node
        visited = set()
        queue = [(trigger_node.id, None)]  # list of (node_id, incoming_condition_value)
        
        while queue:
            node_id, incoming_cond = queue.pop(0)
            if node_id in visited:
                continue
                
            node = nodes_map.get(node_id)
            if not node:
                continue
                
            visited.add(node_id)
            
            # Execute node logic (skip trigger node execution, as it is just the starting point)
            next_condition_val = None
            success = True
            
            if node.type == "action_reply":
                template = node.config.get("message") or "@{{username}} Link sent! Check your messages 📩"
                reply_text = await self._replace_placeholders(template)
                try:
                    from sqlalchemy import select
                    from app.models.instagram import Comment
                    from app.models.facebook import FacebookComment
                    
                    Model = FacebookComment if self.is_facebook else Comment
                    stmt = select(Model).filter(Model.parent_id == self.comment_event.comment_id)
                    res = await self.db.execute(stmt)
                    existing_reply = res.scalars().first()
                    
                    if existing_reply:
                        logger.info(f"Comment {self.comment_event.comment_id} has already been replied to (reply id {existing_reply.id}). Skipping API reply call.")
                        reply_id = existing_reply.id
                    else:
                        reply_id = await meta_client.reply_to_comment(
                            page_access_token=self.account.page_access_token,
                            comment_id=self.comment_event.comment_id,
                            message=reply_text
                        )
                        try:
                            repo_to_use = facebook_comment_repo if self.is_facebook else comment_repo
                            await repo_to_use.create(self.db, obj_in={
                                "id": reply_id or f"bot_reply_{int(datetime.datetime.utcnow().timestamp())}",
                                "media_id": self.comment_event.media_id,
                                "text": reply_text,
                                "username": self.account.username,
                                "timestamp": datetime.datetime.utcnow(),
                                "parent_id": self.comment_event.comment_id
                            })
                            await self.db.commit()
                        except Exception as ex:
                            logger.warning(f"Could not cache automated reply in comments table: {str(ex)}")

                    await self.log_step(
                        flow_id=flow.id,
                        action_type="reply_sent",
                        status="success",
                        details={"reply_id": reply_id, "text": reply_text}
                    )
                except MetaAPIError as e:
                    success = False
                    await self.log_step(
                        flow_id=flow.id,
                        action_type="reply_sent",
                        status="failed",
                        details={"error": str(e), "status_code": e.status_code, "text": reply_text}
                    )
                    
            elif node.type == "action_dm":
                template = None
                
                # Retrieve matching user-defined DM template from DMAutomation table
                if not self.is_facebook:
                    from app.models.instagram import DMAutomation
                    from sqlalchemy import select
                    
                    # Find keywords of trigger nodes in this flow
                    trigger_keywords = []
                    for n in flow.nodes:
                        if n.type == "trigger":
                            trigger_keywords.extend([kw.lower() for kw in n.config.get("keywords", [])])
                    
                    if trigger_keywords:
                        stmt = select(DMAutomation).filter(
                            DMAutomation.instagram_account_id == self.account.id,
                            DMAutomation.is_active == True
                        )
                        res = await self.db.execute(stmt)
                        automations = res.scalars().all()
                        for aut in automations:
                            if aut.keyword and aut.keyword.lower() in trigger_keywords:
                                template = aut.reply_text
                                logger.info(f"Retrieved user-defined DM template for keyword(s) {trigger_keywords}: {template[:50]}")
                                break

                # Fallback to the configured node config message
                if not template:
                    template = node.config.get("message", "Hello!")

                dm_text = await self._replace_placeholders(template)
                try:
                    # Step 1: Send text-based private reply via comment_id
                    dm_id = await meta_client.send_dm_by_comment(
                        page_access_token=self.account.page_access_token,
                        comment_id=self.comment_event.comment_id,
                        message_text=dm_text
                    )
                    
                    # Step 2: Send the actual rich template via direct DM using commenter_id (IGSID) if available
                    commenter_id = getattr(self.comment_event, "commenter_id", None)
                    direct_dm_id = None
                    direct_dm_error = None
                    if commenter_id:
                        try:
                            direct_dm_id = await meta_client.send_direct_dm(
                                page_access_token=self.account.page_access_token,
                                recipient_id=commenter_id,
                                message_text=dm_text
                            )
                            logger.info(f"Successfully sent rich DM template via direct message to {commenter_id}: {direct_dm_id}")
                        except Exception as e_direct:
                            direct_dm_error = str(e_direct)
                            logger.warning(f"Failed to send rich direct DM template to commenter {commenter_id}: {str(e_direct)}")
                            
                    log_details = {"message_id": dm_id, "direct_message_id": direct_dm_id, "text": dm_text}
                    if direct_dm_error:
                        log_details["direct_dm_error"] = direct_dm_error

                    await self.log_step(
                        flow_id=flow.id,
                        action_type="dm_sent",
                        status="success",
                        details=log_details
                    )
                except MetaAPIError as e:
                    # Handle Meta platform limits on private replies
                    is_platform_limit = (
                        (e.error_code == 100 and e.error_subcode == 2534025) or
                        "invalid for a private reply" in str(e).lower() or
                        "already has a reply" in str(e).lower()
                    )

                    if is_platform_limit:
                        logger.info(f"Private reply skipped due to Meta platform limit: {str(e)}")
                        await self.log_step(
                            flow_id=flow.id,
                            action_type="dm_sent",
                            status="skipped",
                            details={
                                "reason": "Meta platform limit: Comment already replied to, or user has already received a private reply on this post.",
                                "error": str(e)
                            }
                        )
                        # Do not halt path traversal for Meta platform limitations
                        success = True
                    else:
                        success = False
                        await self.log_step(
                            flow_id=flow.id,
                            action_type="dm_sent",
                            status="failed",
                            details={"error": str(e), "status_code": e.status_code, "text": dm_text}
                        )
                    
            elif node.type == "action_tag":
                tag_name = node.config.get("tag", "new_tag")
                self.tags.append(tag_name)
                await self.log_step(
                    flow_id=flow.id,
                    action_type="tag_added",
                    status="success",
                    details={"tag": tag_name}
                )
                
            elif node.type == "condition":
                # Evaluate condition based on configurations
                # Example: check if commenter's username is in list, or text length > value
                field = node.config.get("field", "text")
                operator = node.config.get("operator", "contains")
                value = node.config.get("value", "")
                
                check_val = ""
                if field == "text":
                    check_val = self.comment_event.text.lower()
                elif field == "username":
                    check_val = self.comment_event.username.lower()
                    
                match = False
                if operator == "contains":
                    match = value.lower() in check_val
                elif operator == "equals":
                    match = value.lower() == check_val
                elif operator == "starts_with":
                    match = check_val.startswith(value.lower())
                    
                next_condition_val = "yes" if match else "no"
                
                await self.log_step(
                    flow_id=flow.id,
                    action_type="condition_check",
                    status="success",
                    details={"field": field, "operator": operator, "expected": value, "matched": match}
                )

            # If node execution failed, halt path traversal
            if not success:
                logger.error(f"Node {node_id} ({node.type}) failed execution. Halting this path.")
                continue

            # Queue next nodes from outgoing edges
            for edge in flow.edges:
                if edge.source_node_id == node_id:
                    # If it's a condition node, verify the condition value matching the edge criteria
                    if node.type == "condition":
                        if edge.condition_value == next_condition_val:
                            queue.append((edge.target_node_id, edge.condition_value))
                    else:
                        # Standard sequence transition
                        queue.append((edge.target_node_id, None))
                        
        logger.info(f"Finished executing flow {flow.id}")
