import datetime
from sqlalchemy.ext.asyncio import AsyncSession
from loguru import logger

from app.db.repository import (
    instagram_account_repo,
    ig_message_repo,
    ig_conversation_repo,
    dm_automation_repo,
    dm_automation_execution_repo
)
from app.models.instagram import IGMessage, IGConversation, DMAutomationExecution
from app.integrations.meta.client import meta_client, MetaAPIError
from app.utils.text import contains_keyword, normalize_text

class DMProcessorService:
    async def process_dm(
        self,
        db: AsyncSession,
        instagram_business_account_id: str,
        sender_id: str,
        recipient_id: str,
        message_id: str,
        text: str,
        timestamp: datetime.datetime
    ) -> IGMessage:
        """
        Process an incoming DM message:
        1. Identify the connected Instagram account.
        2. Ignore messages sent by the account itself.
        3. Prevent duplicate processing using the message/event ID.
        4. Save the incoming message and update the conversation.
        5. Find and match active DM automations based on priority:
           Exact Keyword -> Contains Keyword -> First Message -> Any Message / Default.
        6. Execute the highest priority match, send reply, and log execution.
        """
        logger.info(f"Processing incoming DM {message_id} from {sender_id} to {recipient_id}")

        # 1. Get Instagram Account connected
        account = await instagram_account_repo.get_by_instagram_id(db, instagram_business_account_id)
        if not account:
            logger.error(f"No registered Instagram Account found for ID: {instagram_business_account_id}")
            return None

        # 2. Ignore messages sent by the account itself
        if sender_id == instagram_business_account_id or sender_id == account.username:
            logger.info(f"Ignoring message {message_id} sent by the account itself ({sender_id})")
            return None

        # 3. Prevent duplicate processing using the message/event ID
        existing_msg = await ig_message_repo.get_by_message_id(db, message_id)
        if existing_msg:
            logger.info(f"Message {message_id} already processed. Status: {existing_msg.status}")
            return existing_msg

        # Determine if it is the first message before inserting this message
        has_prev = await ig_message_repo.has_previous_messages(db, account.id, sender_id)
        is_first_message = not has_prev

        # 4. Save incoming message to DB
        msg_in = {
            "id": message_id,
            "instagram_account_id": account.id,
            "sender_id": sender_id,
            "recipient_id": recipient_id,
            "text": text,
            "timestamp": timestamp,
            "status": "pending"
        }
        msg = await ig_message_repo.create(db, obj_in=msg_in)
        await db.commit()

        # Update or create the conversation
        conv_id = f"{account.id}_{sender_id}"
        conv = await ig_conversation_repo.get_by_participant_id(db, account.id, sender_id)
        if conv:
            conv.last_message_at = timestamp
            db.add(conv)
        else:
            conv_in = {
                "id": conv_id,
                "instagram_account_id": account.id,
                "participant_id": sender_id,
                "last_message_at": timestamp,
                "created_at": timestamp
            }
            await ig_conversation_repo.create(db, obj_in=conv_in)
        await db.commit()

        # 5. Find active DM automations for that account
        active_automations = await dm_automation_repo.get_active_by_instagram_account_id(db, account.id)
        
        # Match incoming message by priority:
        # Priority: Exact Keyword -> Contains Keyword -> First Message -> Any Message / Default.
        matched_automation = None
        
        # 5.1 Exact Keyword match
        normalized_text = normalize_text(text)
        for aut in active_automations:
            if aut.trigger_type == "exact_keyword" and aut.keyword:
                if normalized_text == normalize_text(aut.keyword):
                    matched_automation = aut
                    break

        # 5.2 Contains Keyword match (if not matched yet)
        if not matched_automation:
            for aut in active_automations:
                if aut.trigger_type == "contains_keyword" and aut.keyword:
                    if normalize_text(aut.keyword) in normalized_text:
                        matched_automation = aut
                        break

        # 5.3 First Message match (if not matched yet and this is the first message)
        if not matched_automation and is_first_message:
            for aut in active_automations:
                if aut.trigger_type == "first_message":
                    matched_automation = aut
                    break

        # 5.4 Any Message / Default response (if not matched yet)
        if not matched_automation:
            for aut in active_automations:
                if aut.trigger_type == "any_message":
                    matched_automation = aut
                    break

        if not matched_automation:
            logger.info(f"No active DM automation matched for message {message_id}")
            msg.status = "ignored"
            db.add(msg)
            await db.commit()
            return msg

        logger.info(f"Matched automation '{matched_automation.name}' ({matched_automation.id}) for message {message_id}")

        # 6. Execute automation, send configured automatic reply using existing Meta messaging integration
        execution_status = "success"
        error_msg = None
        try:
            await meta_client.send_direct_dm(
                page_access_token=account.page_access_token,
                recipient_id=sender_id,
                message_text=matched_automation.reply_text
            )
        except MetaAPIError as e:
            execution_status = "failed"
            error_msg = f"Meta API Error: {e.message} (status: {e.status_code})"
            logger.error(f"Failed to send automatic DM reply: {error_msg}")
        except Exception as e:
            execution_status = "failed"
            error_msg = f"Unexpected Error: {str(e)}"
            logger.error(f"Failed to send automatic DM reply: {error_msg}")

        # Save automation execution
        execution_in = {
            "automation_id": matched_automation.id,
            "message_id": msg.id,
            "status": execution_status,
            "error_message": error_msg,
            "executed_at": datetime.datetime.utcnow()
        }
        await dm_automation_execution_repo.create(db, obj_in=execution_in)

        # Update message status
        msg.status = "processed" if execution_status == "success" else "failed"
        msg.error_message = error_msg
        msg.processed_at = datetime.datetime.utcnow()
        db.add(msg)
        await db.commit()

        logger.info(f"Finished processing message {message_id}. Status: {msg.status}")
        return msg

dm_processor = DMProcessorService()
