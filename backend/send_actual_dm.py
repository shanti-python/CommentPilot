import asyncio
import sys
from app.db.session import SessionLocal
# Import models to resolve mappings
from app.models.user import User
from app.models.instagram import InstagramAccount, Post, Comment, CommentEvent, DMAutomation, IGMessage, IGConversation, DMAutomationExecution
from app.models.facebook import FacebookAccount, FacebookPost, FacebookComment, FacebookCommentEvent
from app.models.automation import FlowNode, FlowEdge, AutomationFlow
from app.models.log import AutomationLog

from app.integrations.meta.client import meta_client, MetaAPIError

async def main():
    if len(sys.argv) < 3:
        print("Usage: PYTHONPATH=. venv/bin/python send_actual_dm.py <recipient_id> <message_text>")
        print("Example: PYTHONPATH=. venv/bin/python send_actual_dm.py 123456789 'Hello from DM automation'")
        return

    recipient_id = sys.argv[1]
    message_text = sys.argv[2]

    async with SessionLocal() as db:
        from sqlalchemy import select
        res_acc = await db.execute(select(InstagramAccount))
        accounts = res_acc.scalars().all()
        if not accounts:
            print("ERROR: No Instagram account found in database.")
            return
        
        account = accounts[0]
        print(f"Using Instagram Account: {account.username} (ID: {account.id}, Biz ID: {account.instagram_business_account_id})")
        print(f"Attempting to send real DM to User {recipient_id} using stored access token...")
        
        try:
            message_id = await meta_client.send_direct_dm(
                page_access_token=account.page_access_token,
                recipient_id=recipient_id,
                message_text=message_text
            )
            print(f"SUCCESS! Message sent successfully. Meta Message ID: {message_id}")
        except MetaAPIError as e:
            print(f"FAILED! Meta API Error: {e.message} (status code: {e.status_code}, error code: {e.error_code})")
        except Exception as e:
            print(f"FAILED! Unexpected Error: {str(e)}")

if __name__ == "__main__":
    asyncio.run(main())
