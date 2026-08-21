import datetime
import pytest
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.services.dm_processor import dm_processor
from app.models.instagram import IGMessage, IGConversation, DMAutomationExecution, DMAutomation
from app.db.repository import dm_automation_repo


@pytest.mark.asyncio
async def test_dm_processor_priority_matching(
    db_session: AsyncSession,
    test_instagram_account,
    mock_meta_client
):
    """
    Test DMProcessorService priority matching:
    Exact Keyword -> Contains Keyword -> First Message -> Any Message / Default.
    """
    # 1. Create DM automations with different trigger types and priorities
    # Exact keyword trigger
    auto_exact = DMAutomation(
        id="auto_exact_id",
        instagram_account_id=test_instagram_account.id,
        name="Exact Guide trigger",
        trigger_type="exact_keyword",
        keyword="guide",
        reply_text="This is the exact guide response",
        is_active=True
    )
    # Contains keyword trigger
    auto_contains = DMAutomation(
        id="auto_contains_id",
        instagram_account_id=test_instagram_account.id,
        name="Contains Guide trigger",
        trigger_type="contains_keyword",
        keyword="guide",
        reply_text="This is the contains guide response",
        is_active=True
    )
    # First message trigger
    auto_first = DMAutomation(
        id="auto_first_id",
        instagram_account_id=test_instagram_account.id,
        name="First Message trigger",
        trigger_type="first_message",
        reply_text="Welcome! This is your first message",
        is_active=True
    )
    # Any message / default trigger
    auto_any = DMAutomation(
        id="auto_any_id",
        instagram_account_id=test_instagram_account.id,
        name="Any Message trigger",
        trigger_type="any_message",
        reply_text="This is the default any message response",
        is_active=True
    )

    db_session.add_all([auto_exact, auto_contains, auto_first, auto_any])
    await db_session.commit()

    # --- Scenario 1: Exact keyword match ---
    # Deliver message "GUIDE" (should trigger exact match, matching auto_exact)
    msg1 = await dm_processor.process_dm(
        db=db_session,
        instagram_business_account_id="98765",
        sender_id="sender_user_1",
        recipient_id="98765",
        message_id="mid_111",
        text="GUIDE",
        timestamp=datetime.datetime.utcnow()
    )
    assert msg1.status == "processed"
    mock_meta_client.send_direct_dm.assert_called_with(
        page_access_token="page_token_123",
        recipient_id="sender_user_1",
        message_text="This is the exact guide response"
    )

    # Verify execution log
    exec1_res = await db_session.execute(
        select(DMAutomationExecution).filter(DMAutomationExecution.message_id == "mid_111")
    )
    exec1 = exec1_res.scalars().first()
    assert exec1 is not None
    assert exec1.automation_id == "auto_exact_id"
    assert exec1.status == "success"

    # --- Scenario 2: Contains keyword match ---
    # Deliver message "Can you give me the guide please?" (should trigger contains match, matching auto_contains)
    msg2 = await dm_processor.process_dm(
        db=db_session,
        instagram_business_account_id="98765",
        sender_id="sender_user_2",
        recipient_id="98765",
        message_id="mid_222",
        text="Can you give me the guide please?",
        timestamp=datetime.datetime.utcnow()
    )
    assert msg2.status == "processed"
    mock_meta_client.send_direct_dm.assert_called_with(
        page_access_token="page_token_123",
        recipient_id="sender_user_2",
        message_text="This is the contains guide response"
    )

    # Verify execution log
    exec2_res = await db_session.execute(
        select(DMAutomationExecution).filter(DMAutomationExecution.message_id == "mid_222")
    )
    exec2 = exec2_res.scalars().first()
    assert exec2 is not None
    assert exec2.automation_id == "auto_contains_id"
    assert exec2.status == "success"

    # --- Scenario 3: First message match ---
    # Deliver message "Hello" from a completely new sender "sender_user_3" (should trigger first message, matching auto_first)
    msg3 = await dm_processor.process_dm(
        db=db_session,
        instagram_business_account_id="98765",
        sender_id="sender_user_3",
        recipient_id="98765",
        message_id="mid_333",
        text="Hello",
        timestamp=datetime.datetime.utcnow()
    )
    assert msg3.status == "processed"
    mock_meta_client.send_direct_dm.assert_called_with(
        page_access_token="page_token_123",
        recipient_id="sender_user_3",
        message_text="Welcome! This is your first message"
    )

    # Verify execution log
    exec3_res = await db_session.execute(
        select(DMAutomationExecution).filter(DMAutomationExecution.message_id == "mid_333")
    )
    exec3 = exec3_res.scalars().first()
    assert exec3 is not None
    assert exec3.automation_id == "auto_first_id"

    # --- Scenario 4: Any message / default match ---
    # Deliver another message "Hello" from the same sender "sender_user_3" (since it's not the first message anymore, should trigger auto_any)
    msg4 = await dm_processor.process_dm(
        db=db_session,
        instagram_business_account_id="98765",
        sender_id="sender_user_3",
        recipient_id="98765",
        message_id="mid_444",
        text="Hello again",
        timestamp=datetime.datetime.utcnow()
    )
    assert msg4.status == "processed"
    mock_meta_client.send_direct_dm.assert_called_with(
        page_access_token="page_token_123",
        recipient_id="sender_user_3",
        message_text="This is the default any message response"
    )

    # Verify execution log
    exec4_res = await db_session.execute(
        select(DMAutomationExecution).filter(DMAutomationExecution.message_id == "mid_444")
    )
    exec4 = exec4_res.scalars().first()
    assert exec4 is not None
    assert exec4.automation_id == "auto_any_id"

    # --- Scenario 5: Self messages ignored ---
    # Message sent by account itself (e.g. sender_id matches business account id)
    msg_self = await dm_processor.process_dm(
        db=db_session,
        instagram_business_account_id="98765",
        sender_id="98765",
        recipient_id="sender_user_3",
        message_id="mid_self",
        text="Hello",
        timestamp=datetime.datetime.utcnow()
    )
    assert msg_self is None

    # --- Scenario 6: Duplicate messages ignored ---
    # Re-delivering msg1's ID "mid_111"
    msg_dup = await dm_processor.process_dm(
        db=db_session,
        instagram_business_account_id="98765",
        sender_id="sender_user_1",
        recipient_id="98765",
        message_id="mid_111",
        text="GUIDE",
        timestamp=datetime.datetime.utcnow()
    )
    assert msg_dup.status == "processed" # returns existing processed record
