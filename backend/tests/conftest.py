import asyncio
import datetime
from typing import AsyncGenerator, Generator
import pytest
import pytest_asyncio
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from unittest.mock import AsyncMock, patch

from app.main import app
from app.api.deps import get_db
from app.db.base import Base
from app.core.security import get_password_hash
from app.models.user import User
from app.models.instagram import InstagramAccount, Post
from app.models.automation import AutomationFlow, FlowNode, FlowEdge
from app.integrations.meta.client import meta_client

# Setup async test engine using aiosqlite (SQLite in-memory)
TEST_DATABASE_URL = "sqlite+aiosqlite:///:memory:"
engine = create_async_engine(TEST_DATABASE_URL, connect_args={"check_same_thread": False})
TestingSessionLocal = async_sessionmaker(bind=engine, class_=AsyncSession, expire_on_commit=False)


@pytest.fixture(scope="session")
def event_loop() -> Generator:
    """Create an instance of the default event loop for the test session."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest_asyncio.fixture(scope="function", autouse=True)
async def init_db():
    """Create database tables before tests and drop them after."""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


@pytest_asyncio.fixture(scope="function")
async def db_session() -> AsyncGenerator[AsyncSession, None]:
    """Yield a test database session."""
    async with TestingSessionLocal() as session:
        yield session


@pytest_asyncio.fixture(scope="function")
async def client(db_session: AsyncSession) -> AsyncGenerator[AsyncClient, None]:
    """Yield an async test client with database override."""
    async def _override_get_db():
        try:
            yield db_session
            await db_session.commit()
        except Exception:
            await db_session.rollback()
            raise
        finally:
            await db_session.close()

    from httpx import ASGITransport
    app.dependency_overrides[get_db] = _override_get_db
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        yield ac
    app.dependency_overrides.clear()


@pytest.fixture(scope="function", autouse=True)
def mock_meta_client():
    """Mock the meta_client instance methods directly."""
    from app.integrations.meta.client import meta_client
    
    # Save original methods
    orig_get_token = meta_client.get_long_lived_user_token
    orig_discover = meta_client.discover_accounts
    orig_reply = meta_client.reply_to_comment
    orig_send_dm = meta_client.send_dm_by_comment
    orig_get_posts = meta_client.get_instagram_posts
    orig_send_direct_dm = getattr(meta_client, "send_direct_dm", None)

    # Override with AsyncMocks
    meta_client.get_long_lived_user_token = AsyncMock(return_value="long_lived_user_token_abc")
    meta_client.discover_accounts = AsyncMock(return_value=[
        {
            "page_id": "12345",
            "page_name": "Test FB Page",
            "page_access_token": "page_token_123",
            "instagram_business_account_id": "98765",
            "instagram_username": "test_insta_biz",
            "instagram_name": "Test Instagram Biz",
            "instagram_profile_pic": "http://image.url/pic.jpg"
        }
    ])
    meta_client.reply_to_comment = AsyncMock(return_value="reply_comment_id_999")
    meta_client.send_dm_by_comment = AsyncMock(return_value="message_id_888")
    meta_client.send_direct_dm = AsyncMock(return_value="direct_message_id_777")
    meta_client.get_instagram_posts = AsyncMock(return_value=[
        {
            "id": "media_post_1",
            "caption": "Check out this guide #guide",
            "media_type": "IMAGE",
            "media_url": "http://insta.com/post1.jpg",
            "permalink": "http://insta.com/p/post1",
            "timestamp": datetime.datetime.utcnow().isoformat()
        }
    ])

    yield meta_client

    # Restore original methods
    meta_client.get_long_lived_user_token = orig_get_token
    meta_client.discover_accounts = orig_discover
    meta_client.reply_to_comment = orig_reply
    meta_client.send_dm_by_comment = orig_send_dm
    if orig_send_direct_dm is not None:
        meta_client.send_direct_dm = orig_send_direct_dm
    meta_client.get_instagram_posts = orig_get_posts


@pytest_asyncio.fixture(scope="function")
async def test_user(db_session: AsyncSession) -> User:
    """Create a default test user in the database."""
    user = User(
        email="testuser@example.com",
        hashed_password=get_password_hash("password123"),
        is_active=True,
        is_superuser=False
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)
    return user


@pytest_asyncio.fixture(scope="function")
async def test_admin(db_session: AsyncSession) -> User:
    """Create an admin test user."""
    user = User(
        email="admin@example.com",
        hashed_password=get_password_hash("adminpwd"),
        is_active=True,
        is_superuser=True
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)
    return user


@pytest_asyncio.fixture(scope="function")
async def test_instagram_account(db_session: AsyncSession, test_user: User) -> InstagramAccount:
    """Create and connect a test Instagram account."""
    account = InstagramAccount(
        user_id=test_user.id,
        instagram_business_account_id="98765",
        page_id="12345",
        username="test_insta_biz",
        name="Test Instagram Biz",
        profile_picture_url="http://image.url/pic.jpg"
    )
    account.page_access_token = "page_token_123"
    account.user_access_token = "user_token_xyz"
    db_session.add(account)
    await db_session.commit()
    await db_session.refresh(account)
    return account


@pytest_asyncio.fixture(scope="function")
async def test_post(db_session: AsyncSession, test_instagram_account: InstagramAccount) -> Post:
    """Create a test post for the connected Instagram account."""
    post = Post(
        id="media_post_1",
        instagram_account_id=test_instagram_account.id,
        caption="Check out this guide #guide",
        media_type="IMAGE",
        media_url="http://insta.com/post1.jpg",
        permalink="http://insta.com/p/post1",
        timestamp=datetime.datetime.utcnow()
    )
    db_session.add(post)
    await db_session.commit()
    await db_session.refresh(post)
    return post


@pytest_asyncio.fixture(scope="function")
async def test_automation_flow(db_session: AsyncSession, test_instagram_account: InstagramAccount) -> AutomationFlow:
    """Create a test ManyChat automation flow (Comment -> Keyword 'guide' -> Reply -> DM -> Tag)."""
    flow = AutomationFlow(
        id="flow-uuid-111",
        instagram_account_id=test_instagram_account.id,
        name="Guide Lead Magnet",
        is_active=True
    )
    db_session.add(flow)
    await db_session.commit()

    # Trigger Node
    trigger = FlowNode(
        id="node_trigger",
        flow_id=flow.id,
        type="trigger",
        config={"keywords": ["guide"], "exact_word": True}
    )
    # Reply Action Node
    reply = FlowNode(
        id="node_reply",
        flow_id=flow.id,
        type="action_reply",
        config={"message": "Hi {{username}}! Check your DMs for the guide."}
    )
    # DM Action Node
    dm = FlowNode(
        id="node_dm",
        flow_id=flow.id,
        type="action_dm",
        config={"message": "Hey {{username}}, here is your guide URL: https://example.com/guide"}
    )
    # Tag Action Node
    tag = FlowNode(
        id="node_tag",
        flow_id=flow.id,
        type="action_tag",
        config={"tag": "guide_sent"}
    )

    db_session.add_all([trigger, reply, dm, tag])
    await db_session.commit()

    # Edges
    edge1 = FlowEdge(
        id="edge_1",
        flow_id=flow.id,
        source_node_id="node_trigger",
        target_node_id="node_reply"
    )
    edge2 = FlowEdge(
        id="edge_2",
        flow_id=flow.id,
        source_node_id="node_reply",
        target_node_id="node_dm"
    )
    edge3 = FlowEdge(
        id="edge_3",
        flow_id=flow.id,
        source_node_id="node_dm",
        target_node_id="node_tag"
    )

    db_session.add_all([edge1, edge2, edge3])
    await db_session.commit()
    await db_session.refresh(flow)
    return flow
