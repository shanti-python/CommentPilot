import datetime
import pytest
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.utils.text import normalize_text, contains_keyword
from app.services.comment_processor import comment_processor
from app.models.instagram import CommentEvent, Comment
from app.models.log import AutomationLog
from app.models.automation import AutomationFlow
from app.models.user import User

def test_keyword_normalization():
    """Test text normalization removes punctuation, emojis, and lowercases text."""
    raw_text = "Get the Guide! 👍!!! "
    assert normalize_text(raw_text) == "get the guide"
    
    accented_text = "Café & Tea ☕"
    assert normalize_text(accented_text) == "café tea"


def test_keyword_matching():
    """Test contains_keyword with word boundary checks."""
    comment = "I want the guide now"
    # Exact word match
    assert contains_keyword(comment, "guide", exact_word=True) is True
    # Substring match
    assert contains_keyword("myguidedtour", "guide", exact_word=False) is True
    # Word boundary should fail on substring matches to prevent false positives
    assert contains_keyword("myguidedtour", "guide", exact_word=True) is False
    # Case insensitivity and punctuation resilience
    assert contains_keyword("GUIDE!!! 👍", "guide", exact_word=True) is True


@pytest.mark.asyncio
async def test_automation_flow_execution(
    db_session: AsyncSession,
    test_instagram_account,
    test_post,
    test_automation_flow: AutomationFlow,
    mock_meta_client
):
    """
    Test direct flow execution by CommentProcessorService:
    1. Deliver comment matching 'guide' keyword.
    2. Execute mock Graph API actions: Reply, DM, Tag.
    3. Verify DB state updates: CommentEvent, Comment, and execution logs.
    """
    # 1. Trigger comment processing
    comment_time = datetime.datetime.utcnow() - datetime.timedelta(seconds=5)
    event = await comment_processor.process_comment(
        db=db_session,
        instagram_business_account_id="98765",
        comment_id="comment_id_abc_123",
        media_id="media_post_1",
        text="I need that GUIDE! 👍",
        username="jane_commenter",
        timestamp=comment_time
    )

    # Assert comment event status is processed successfully
    assert event.status == "processed"
    assert event.error_message is None
    assert event.processed_at is not None

    # Verify Comment is cached in the DB
    cached_comment = await db_session.get(Comment, "comment_id_abc_123")
    assert cached_comment is not None
    assert cached_comment.text == "I need that GUIDE! 👍"
    assert cached_comment.username == "jane_commenter"

    # Verify Meta API calls were invoked correctly
    # 1. Reply to comment (placeholders substituted)
    mock_meta_client.reply_to_comment.assert_called_once_with(
        page_access_token="page_token_123",
        comment_id="comment_id_abc_123",
        message="Hi jane_commenter! Check your DMs for the guide."
    )
    # 2. Send private DM
    mock_meta_client.send_dm_by_comment.assert_called_once_with(
        page_access_token="page_token_123",
        comment_id="comment_id_abc_123",
        message_text="Hey jane_commenter, here is your guide URL: https://example.com/guide"
    )

    # Verify execution logs recorded in DB
    logs_res = await db_session.execute(
        select(AutomationLog).where(AutomationLog.comment_id == "comment_id_abc_123").order_by(AutomationLog.created_at)
    )
    logs = logs_res.scalars().all()
    
    assert len(logs) == 4
    assert logs[0].action_type == "trigger_match"
    assert logs[0].status == "success"
    
    assert logs[1].action_type == "reply_sent"
    assert logs[1].status == "success"
    assert logs[1].details["reply_id"] == "reply_comment_id_999"
    
    assert logs[2].action_type == "dm_sent"
    assert logs[2].status == "success"
    assert logs[2].details["message_id"] == "message_id_888"
    
    assert logs[3].action_type == "tag_added"
    assert logs[3].status == "success"
    assert logs[3].details["tag"] == "guide_sent"


@pytest.mark.asyncio
async def test_automation_flow_execution_two_step(
    db_session: AsyncSession,
    test_instagram_account,
    test_post,
    test_automation_flow: AutomationFlow,
    mock_meta_client
):
    """
    Test that when commenter_id is provided, the automation engine executes the
    two-step delivery strategy: comment private reply followed by direct DM.
    """
    # 1. Trigger comment processing with commenter_id
    comment_time = datetime.datetime.utcnow() - datetime.timedelta(seconds=5)
    event = await comment_processor.process_comment(
        db=db_session,
        instagram_business_account_id="98765",
        comment_id="comment_id_two_step",
        media_id="media_post_1",
        text="I need that GUIDE! 👍",
        username="jane_commenter",
        timestamp=comment_time,
        commenter_id="user_igsid_123"
    )

    assert event.status == "processed"
    assert event.commenter_id == "user_igsid_123"

    # Verify BOTH Meta client methods were called
    # Step 1: comment private reply
    mock_meta_client.send_dm_by_comment.assert_called_with(
        page_access_token="page_token_123",
        comment_id="comment_id_two_step",
        message_text="Hey jane_commenter, here is your guide URL: https://example.com/guide"
    )
    # Step 2: direct DM using IGSID
    mock_meta_client.send_direct_dm.assert_called_once_with(
        page_access_token="page_token_123",
        recipient_id="user_igsid_123",
        message_text="Hey jane_commenter, here is your guide URL: https://example.com/guide"
    )


@pytest.mark.asyncio
async def test_json_aware_placeholder_replacement(db_session: AsyncSession, test_instagram_account):
    """Test that _replace_placeholders handles JSON strings correctly without corrupting quotes."""
    from app.services.automation_engine import AutomationEngine
    from app.models.instagram import CommentEvent
    
    event = CommentEvent(
        comment_id="comment_123",
        media_id="media_post_1",
        text="some comment",
        username='cool"user',  # Username containing quotes
        timestamp=datetime.datetime.utcnow(),
        commenter_id="user_igsid"
    )
    
    engine = AutomationEngine(db=db_session, account=test_instagram_account, comment_event=event)
    
    # 1. Test standard string template
    text_tmpl = "Hello {{username}}!"
    text_res = await engine._replace_placeholders(text_tmpl)
    assert text_res == 'Hello cool"user!'
    
    # 2. Test JSON template with username placeholder
    json_tmpl = '{"text": "Welcome {{username}}!", "dm_type": "button_template"}'
    json_res = await engine._replace_placeholders(json_tmpl)
    
    # Verify the result is valid JSON and preserves the quotes safely
    import json
    parsed = json.loads(json_res)
    assert parsed["text"] == 'Welcome cool"user!'
    assert parsed["dm_type"] == 'button_template'


@pytest.mark.asyncio
async def test_automation_flow_execution_direct_dm_permission_error(
    db_session: AsyncSession,
    test_instagram_account,
    test_post,
    test_automation_flow: AutomationFlow,
    mock_meta_client
):
    """
    Test that when send_direct_dm fails with a permission error (e.g. MetaPermissionError),
    the flow execution continues, logs a success status for the overall DM action (since the comment
    private reply succeeded), but records the direct DM error details in the log.
    """
    from app.integrations.meta.client import MetaPermissionError

    # Override send_direct_dm mock to raise MetaPermissionError
    mock_meta_client.send_direct_dm.side_effect = MetaPermissionError(
        "Requires pages_messaging permission to manage the object",
        status_code=400,
        error_code=230
    )

    # Trigger comment processing with commenter_id to trigger the two-step direct DM delivery
    comment_time = datetime.datetime.utcnow() - datetime.timedelta(seconds=5)
    event = await comment_processor.process_comment(
        db=db_session,
        instagram_business_account_id="98765",
        comment_id="comment_id_perm_error",
        media_id="media_post_1",
        text="I need that GUIDE! 👍",
        username="jane_commenter",
        timestamp=comment_time,
        commenter_id="user_igsid_123"
    )

    assert event.status == "processed"

    # Verify logs recorded in DB
    logs_res = await db_session.execute(
        select(AutomationLog).where(AutomationLog.comment_id == "comment_id_perm_error").order_by(AutomationLog.created_at)
    )
    logs = logs_res.scalars().all()

    # Find the dm_sent action log
    dm_log = next(log for log in logs if log.action_type == "dm_sent")
    assert dm_log.status == "success"  # Overall success because Step 1 (send_dm_by_comment) succeeded
    assert dm_log.details["message_id"] == "message_id_888"
    assert dm_log.details["direct_message_id"] is None
    assert "direct_dm_error" in dm_log.details
    assert "Requires pages_messaging permission" in dm_log.details["direct_dm_error"]

