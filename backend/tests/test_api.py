import datetime
import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.models.user import User
from app.models.automation import AutomationFlow
from app.models.instagram import CommentEvent
from app.models.log import AutomationLog

@pytest.mark.asyncio
async def test_dashboard_apis_flow(
    client: AsyncClient,
    test_user: User,
    test_instagram_account,
    test_post,
    test_automation_flow,
    db_session: AsyncSession
):
    """
    Test all Dashboard APIs sequentially under authenticated session:
    1. Authenticate & fetch user headers.
    2. GET /accounts
    3. GET /posts
    4. GET /comments
    5. GET /automation, POST /automation, PUT /automation, DELETE /automation
    6. GET /logs
    7. GET /analytics
    """
    # 1. Login to get token
    login_data = {"email": test_user.email, "password": "password123"}
    login_res = await client.post("/api/v1/auth/login-json", json=login_data)
    token = login_res.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # 2. GET /accounts
    accounts_res = await client.get("/api/v1/accounts", headers=headers)
    assert accounts_res.status_code == 200
    assert len(accounts_res.json()) == 1
    assert accounts_res.json()[0]["username"] == "test_insta_biz"

    # 3. GET /posts
    posts_res = await client.get("/api/v1/posts", headers=headers)
    assert posts_res.status_code == 200
    assert len(posts_res.json()) == 1
    assert posts_res.json()[0]["id"] == "media_post_1"

    # 4. GET /comments (empty initially)
    comments_res = await client.get("/api/v1/comments", headers=headers)
    assert comments_res.status_code == 200
    assert len(comments_res.json()) == 0

    # 5. GET /automation
    flows_res = await client.get("/api/v1/automation", headers=headers)
    assert flows_res.status_code == 200
    assert len(flows_res.json()) == 1
    assert flows_res.json()[0]["id"] == "flow-uuid-111"

    # POST /automation (Create new flow)
    new_flow_payload = {
        "instagram_account_id": test_instagram_account.id,
        "name": "Promo Flow",
        "is_active": True,
        "nodes": [
            {"id": "trig_1", "type": "trigger", "config": {"keywords": ["promo"]}},
            {"id": "reply_1", "type": "action_reply", "config": {"message": "Hi!"}}
        ],
        "edges": [
            {"id": "ed_1", "source_node_id": "trig_1", "target_node_id": "reply_1"}
        ]
    }
    create_res = await client.post("/api/v1/automation", json=new_flow_payload, headers=headers)
    assert create_res.status_code == 200
    created_flow = create_res.json()
    assert created_flow["name"] == "Promo Flow"
    assert len(created_flow["nodes"]) == 2
    assert len(created_flow["edges"]) == 1

    # PUT /automation (Update flow)
    update_flow_payload = {
        "name": "Updated Promo Flow",
        "nodes": [
            {"id": "trig_1", "type": "trigger", "config": {"keywords": ["promo", "discount"]}},
            {"id": "reply_1", "type": "action_reply", "config": {"message": "Hello!"}},
            {"id": "tag_1", "type": "action_tag", "config": {"tag": "promo_used"}}
        ],
        "edges": [
            {"id": "ed_1", "source_node_id": "trig_1", "target_node_id": "reply_1"},
            {"id": "ed_2", "source_node_id": "reply_1", "target_node_id": "tag_1"}
        ]
    }
    update_res = await client.put(f"/api/v1/automation/{created_flow['id']}", json=update_flow_payload, headers=headers)
    assert update_res.status_code == 200
    updated_flow = update_res.json()
    assert updated_flow["name"] == "Updated Promo Flow"
    assert len(updated_flow["nodes"]) == 3
    assert len(updated_flow["edges"]) == 2

    # DELETE /automation
    del_res = await client.delete(f"/api/v1/automation/{created_flow['id']}", headers=headers)
    assert del_res.status_code == 200
    # Verify DB delete
    db_flow = await db_session.get(AutomationFlow, created_flow["id"])
    assert db_flow is None

    # 6. GET /logs (mock a log first)
    log_db = AutomationLog(
        flow_id="flow-uuid-111",
        comment_id="comment_id_mock",
        action_type="reply_sent",
        status="success",
        details={"text": "Hi"}
    )
    db_session.add(log_db)
    # Mock comment event as well to verify analytics
    ev_db = CommentEvent(
        comment_id="comment_id_mock",
        media_id="media_post_1",
        text="guide",
        username="john",
        timestamp=datetime.datetime.utcnow(),
        status="processed",
        processed_at=datetime.datetime.utcnow()
    )
    db_session.add(ev_db)
    
    # Mock trigger match log for keyword stats
    trig_log = AutomationLog(
        flow_id="flow-uuid-111",
        comment_id="comment_id_mock",
        action_type="trigger_match",
        status="success",
        details={"matched_keywords": ["guide"]}
    )
    db_session.add(trig_log)
    await db_session.commit()

    logs_res = await client.get("/api/v1/logs", headers=headers)
    assert logs_res.status_code == 200
    assert len(logs_res.json()) >= 2

    # 7. GET /analytics
    analytics_res = await client.get("/api/v1/analytics", headers=headers)
    assert analytics_res.status_code == 200
    analytics = analytics_res.json()
    assert analytics["total_comments"] == 1
    assert analytics["replies_sent"] == 1
    assert analytics["keyword_counts"]["guide"] == 1


@pytest.mark.asyncio
async def test_dm_automation_apis(
    client: AsyncClient,
    test_user: User,
    test_instagram_account,
    db_session: AsyncSession
):
    """
    Test DM Automation API endpoints:
    1. Login.
    2. POST /dm-automation (Create rule)
    3. GET /dm-automation
    4. PUT /dm-automation/{id} (Update rule)
    5. GET /dm-automation/messages
    6. GET /dm-automation/conversations
    7. GET /dm-automation/executions
    8. DELETE /dm-automation/{id} (Delete rule)
    """
    # 1. Login
    login_data = {"email": test_user.email, "password": "password123"}
    login_res = await client.post("/api/v1/auth/login-json", json=login_data)
    token = login_res.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # 2. POST /dm-automation (Create rule)
    payload = {
        "instagram_account_id": test_instagram_account.id,
        "name": "API DM Rule",
        "trigger_type": "exact_keyword",
        "keyword": "api_test",
        "reply_text": "API response text",
        "is_active": True
    }
    create_res = await client.post("/api/v1/dm-automation", json=payload, headers=headers)
    assert create_res.status_code == 201
    created_rule = create_res.json()
    assert created_rule["name"] == "API DM Rule"
    assert created_rule["keyword"] == "api_test"

    # 3. GET /dm-automation
    get_res = await client.get("/api/v1/dm-automation", headers=headers)
    assert get_res.status_code == 200
    rules = get_res.json()
    assert len(rules) == 1
    assert rules[0]["id"] == created_rule["id"]

    # 4. PUT /dm-automation/{id}
    update_payload = {
        "reply_text": "Updated API reply",
        "is_active": False
    }
    update_res = await client.put(f"/api/v1/dm-automation/{created_rule['id']}", json=update_payload, headers=headers)
    assert update_res.status_code == 200
    updated_rule = update_res.json()
    assert updated_rule["reply_text"] == "Updated API reply"
    assert updated_rule["is_active"] is False

    # 5. GET /dm-automation/messages
    msg_res = await client.get("/api/v1/dm-automation/messages", headers=headers)
    assert msg_res.status_code == 200
    assert len(msg_res.json()) == 0

    # 6. GET /dm-automation/conversations
    conv_res = await client.get("/api/v1/dm-automation/conversations", headers=headers)
    assert conv_res.status_code == 200
    assert len(conv_res.json()) == 0

    # 7. GET /dm-automation/executions
    exec_res = await client.get("/api/v1/dm-automation/executions", headers=headers)
    assert exec_res.status_code == 200
    assert len(exec_res.json()) == 0

    # 8. DELETE /dm-automation/{id}
    del_res = await client.delete(f"/api/v1/dm-automation/{created_rule['id']}", headers=headers)
    assert del_res.status_code == 200
    
    # Verify not found on subsequent get/update
    get_after_del = await client.get("/api/v1/dm-automation", headers=headers)
    assert len(get_after_del.json()) == 0

