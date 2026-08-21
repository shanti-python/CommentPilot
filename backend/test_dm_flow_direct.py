import asyncio
import datetime
import uuid
from unittest.mock import patch
from app.db.session import SessionLocal

# Import all models to compile SQLAlchemy mapper relationships
from app.models.user import User
from app.models.instagram import InstagramAccount, Post, Comment, CommentEvent, DMAutomation, IGMessage, IGConversation, DMAutomationExecution
from app.models.facebook import FacebookAccount, FacebookPost, FacebookComment, FacebookCommentEvent
from app.models.automation import FlowNode, FlowEdge, AutomationFlow
from app.models.log import AutomationLog

from app.services.dm_processor import dm_processor

async def main():
    async with SessionLocal() as db:
        from sqlalchemy import select
        
        # 1. Get or create InstagramAccount in DB
        res_acc = await db.execute(select(InstagramAccount))
        accounts = res_acc.scalars().all()
        if not accounts:
            print("ERROR: No Instagram account found in database. Run seed script or login first.")
            return
        
        account = accounts[0]
        print(f"Using Instagram Account: {account.username} (ID: {account.id}, Biz ID: {account.instagram_business_account_id})")
        
        # 2. Clean up existing mock records to start fresh
        from sqlalchemy import delete
        await db.execute(delete(DMAutomationExecution))
        await db.execute(delete(IGMessage))
        await db.execute(delete(IGConversation))
        await db.execute(delete(DMAutomation).where(DMAutomation.name.like("%Test Rule%")))
        await db.commit()
        print("Cleaned up existing test records.")
        
        # 3. Create a Personal DM Automation Rule
        rule_in = {
            "instagram_account_id": account.id,
            "name": "Test Rule: Help Response",
            "trigger_type": "exact_keyword",
            "keyword": "help",
            "reply_text": "Hello there! This is a test response for the keyword 'help'. How can we help you?",
            "is_active": True
        }
        
        rule_id = f"dm_rule_{uuid.uuid4().hex[:8]}"
        rule = DMAutomation(
            id=rule_id,
            instagram_account_id=rule_in["instagram_account_id"],
            name=rule_in["name"],
            trigger_type=rule_in["trigger_type"],
            keyword=rule_in["keyword"],
            reply_text=rule_in["reply_text"],
            is_active=rule_in["is_active"],
            created_at=datetime.datetime.utcnow(),
            updated_at=datetime.datetime.utcnow()
        )
        db.add(rule)
        await db.commit()
        print(f"Created DM Automation Rule: {rule.name} (Keyword: '{rule.keyword}')")
        
        # 4. Simulate receiving a DM with keyword 'help'
        sender_id = "test_user_12345"
        recipient_id = account.instagram_business_account_id
        message_id = f"mid.12345_{uuid.uuid4().hex[:8]}"
        incoming_text = "help"
        timestamp = datetime.datetime.utcnow()
        
        print(f"\nSimulating incoming DM: '{incoming_text}' from Sender: {sender_id} to Recipient: {recipient_id}")
        
        # Mock send_direct_dm to simulate successful Meta response
        async def mock_send_direct_dm(page_access_token, recipient_id, message_text):
            print(f"[MOCK META API] Sending DM to {recipient_id} with text: '{message_text}'")
            return "mock_meta_message_id_999"
            
        with patch("app.integrations.meta.client.meta_client.send_direct_dm", side_effect=mock_send_direct_dm):
            processed_msg = await dm_processor.process_dm(
                db=db,
                instagram_business_account_id=account.instagram_business_account_id,
                sender_id=sender_id,
                recipient_id=recipient_id,
                message_id=message_id,
                text=incoming_text,
                timestamp=timestamp
            )
            
        # 5. Verify the DB entries
        print("\n--- Verifying Results in DB ---")
        
        # Get messages
        res_msgs = await db.execute(select(IGMessage))
        msgs = res_msgs.scalars().all()
        print(f"\nSaved Messages in DB ({len(msgs)}):")
        for m in msgs:
            print(f"- Msg ID: {m.id}")
            print(f"  Sender: {m.sender_id}")
            print(f"  Text: '{m.text}'")
            print(f"  Status: {m.status}")
            print(f"  Processed At: {m.processed_at}")
            
        # Get conversations
        res_convs = await db.execute(select(IGConversation))
        convs = res_convs.scalars().all()
        print(f"\nSaved Conversations in DB ({len(convs)}):")
        for c in convs:
            print(f"- Conv ID: {c.id}")
            print(f"  Participant: {c.participant_id}")
            print(f"  Last Active: {c.last_message_at}")
            
        # Get executions
        res_execs = await db.execute(select(DMAutomationExecution))
        execs = res_execs.scalars().all()
        print(f"\nSaved Rule Executions in DB ({len(execs)}):")
        for e in execs:
            print(f"- Exec ID: {e.id}")
            print(f"  Rule ID: {e.automation_id}")
            print(f"  Message ID: {e.message_id}")
            print(f"  Status: {e.status}")

if __name__ == "__main__":
    asyncio.run(main())
