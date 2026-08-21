import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.models.instagram import InstagramAccount, Post
from app.models.user import User

@pytest.mark.asyncio
async def test_user_login(client: AsyncClient, test_user: User):
    """Test standard JSON login generates valid JWT token."""
    login_data = {
        "email": test_user.email,
        "password": "password123"
    }
    response = await client.post("/api/v1/auth/login-json", json=login_data)
    assert response.status_code == 200
    token_json = response.json()
    assert "access_token" in token_json
    assert token_json["token_type"] == "bearer"


@pytest.mark.asyncio
async def test_facebook_connect_discovery(client: AsyncClient, test_user: User, db_session: AsyncSession):
    """
    Test Facebook connection & auto account discovery flow:
    1. Authenticate user.
    2. Post Facebook connect token.
    3. Verify account discovery, token encryption, and initial posts caching.
    """
    # Authenticate by fetching token
    login_data = {
        "email": test_user.email,
        "password": "password123"
    }
    login_res = await client.post("/api/v1/auth/login-json", json=login_data)
    token = login_res.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # Call Facebook connect with fake token
    connect_payload = {"access_token": "short_lived_user_token_123"}
    response = await client.post(
        "/api/v1/auth/facebook-connect",
        json=connect_payload,
        headers=headers
    )
    
    assert response.status_code == 200
    accounts_json = response.json()
    
    # Assert discovery details are returned correctly
    assert len(accounts_json) == 1
    account = accounts_json[0]
    assert account["instagram_business_account_id"] == "98765"
    assert account["username"] == "test_insta_biz"
    assert account["name"] == "Test Instagram Biz"
    
    # Assert database state matches discovery
    res = await db_session.execute(select(InstagramAccount).where(InstagramAccount.instagram_business_account_id == "98765"))
    db_account = res.scalars().first()
    assert db_account is not None
    assert db_account.user_id == test_user.id
    
    # Assert access token decryption matches mock value (transparent encryption/decryption properties)
    assert db_account.page_access_token == "page_token_123"
    assert db_account.user_access_token == "long_lived_user_token_abc"
    
    # Assert initial post list is cached successfully
    post_res = await db_session.execute(select(Post).where(Post.instagram_account_id == db_account.id))
    db_posts = post_res.scalars().all()
    assert len(db_posts) == 1
    assert db_posts[0].id == "media_post_1"
    assert "guide" in db_posts[0].caption
