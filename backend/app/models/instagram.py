from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey, Boolean
from sqlalchemy.orm import relationship
from app.db.base_class import Base
from app.utils.encryption import encrypt_token, decrypt_token
import datetime

class InstagramAccount(Base):
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    instagram_business_account_id = Column(String, unique=True, index=True, nullable=False)
    page_id = Column(String, index=True, nullable=False)
    
    # Secure storage (encrypted in DB)
    _page_access_token = Column("page_access_token", String, nullable=False)
    _user_access_token = Column("user_access_token", String, nullable=True)
    
    username = Column(String, nullable=False)
    name = Column(String, nullable=True)
    profile_picture_url = Column(Text, nullable=True)
    
    user = relationship("User", back_populates="instagram_accounts")
    posts = relationship("Post", back_populates="instagram_account", cascade="all, delete-orphan")
    flows = relationship("AutomationFlow", back_populates="instagram_account", cascade="all, delete-orphan")
    dm_automations = relationship("DMAutomation", back_populates="instagram_account", cascade="all, delete-orphan")

    @property
    def page_access_token(self) -> str:
        return decrypt_token(self._page_access_token)

    @page_access_token.setter
    def page_access_token(self, val: str):
        self._page_access_token = encrypt_token(val)

    @property
    def user_access_token(self) -> str:
        return decrypt_token(self._user_access_token) if self._user_access_token else ""

    @user_access_token.setter
    def user_access_token(self, val: str):
        self._user_access_token = encrypt_token(val) if val else None


class Post(Base):
    id = Column(String, primary_key=True, index=True)  # Instagram Media ID
    instagram_account_id = Column(Integer, ForeignKey("instagram_accounts.id", ondelete="CASCADE"), nullable=False)
    caption = Column(Text, nullable=True)
    media_type = Column(String, nullable=True)
    media_url = Column(Text, nullable=True)
    thumbnail_url = Column(Text, nullable=True)
    permalink = Column(Text, nullable=True)
    timestamp = Column(DateTime, nullable=True)
    
    # Automation Setup on a Post level
    automation_status = Column(String, default="setup")  # setup, active, paused
    keyword = Column(String, nullable=True)
    reply_message = Column(Text, nullable=True)
    dm_message = Column(Text, nullable=True)
    is_future_post = Column(Boolean, default=False)
    
    instagram_account = relationship("InstagramAccount", back_populates="posts")
    comments = relationship("Comment", back_populates="post", cascade="all, delete-orphan")
    flows = relationship("AutomationFlow", back_populates="instagram_post", cascade="all, delete-orphan")


class Comment(Base):
    id = Column(String, primary_key=True, index=True)  # Instagram Comment ID
    media_id = Column(String, ForeignKey("posts.id", ondelete="CASCADE"), nullable=False)
    text = Column(Text, nullable=False)
    username = Column(String, nullable=False)
    timestamp = Column(DateTime, default=datetime.datetime.utcnow)
    parent_id = Column(String, nullable=True)  # To support nested replies if needed
    
    post = relationship("Post", back_populates="comments")


class CommentEvent(Base):
    id = Column(Integer, primary_key=True, index=True)
    comment_id = Column(String, index=True, nullable=False)
    media_id = Column(String, index=True, nullable=False)
    text = Column(Text, nullable=False)
    username = Column(String, nullable=False)
    timestamp = Column(DateTime, nullable=False)
    commenter_id = Column(String, nullable=True)
    
    status = Column(String, default="pending")  # pending, processed, ignored, failed
    processed_at = Column(DateTime, nullable=True)
    error_message = Column(Text, nullable=True)


import uuid

def generate_uuid() -> str:
    return str(uuid.uuid4())

class DMAutomation(Base):
    __tablename__ = "dm_automations"
    id = Column(String(36), primary_key=True, default=generate_uuid)
    instagram_account_id = Column(Integer, ForeignKey("instagram_accounts.id", ondelete="CASCADE"), nullable=False)
    name = Column(String, nullable=False)
    trigger_type = Column(String, nullable=False)  # exact_keyword, contains_keyword, first_message, any_message
    keyword = Column(String, nullable=True)
    reply_text = Column(Text, nullable=False)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow)

    instagram_account = relationship("InstagramAccount", back_populates="dm_automations")
    executions = relationship("DMAutomationExecution", back_populates="automation", cascade="all, delete-orphan")


class IGMessage(Base):
    __tablename__ = "ig_messages"
    id = Column(String, primary_key=True, index=True)  # Meta messaging mid
    instagram_account_id = Column(Integer, ForeignKey("instagram_accounts.id", ondelete="CASCADE"), nullable=False)
    sender_id = Column(String, index=True, nullable=False)
    recipient_id = Column(String, index=True, nullable=False)
    text = Column(Text, nullable=True)
    timestamp = Column(DateTime, nullable=False)
    
    status = Column(String, default="pending")  # pending, processed, ignored, failed
    processed_at = Column(DateTime, nullable=True)
    error_message = Column(Text, nullable=True)

    instagram_account = relationship("InstagramAccount")
    executions = relationship("DMAutomationExecution", back_populates="message", cascade="all, delete-orphan")


class IGConversation(Base):
    __tablename__ = "ig_conversations"
    id = Column(String, primary_key=True, index=True)  # composite: f"{instagram_account_id}_{participant_id}"
    instagram_account_id = Column(Integer, ForeignKey("instagram_accounts.id", ondelete="CASCADE"), nullable=False)
    participant_id = Column(String, index=True, nullable=False)
    last_message_at = Column(DateTime, default=datetime.datetime.utcnow)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

    instagram_account = relationship("InstagramAccount")


class DMAutomationExecution(Base):
    __tablename__ = "dm_automation_executions"
    id = Column(String(36), primary_key=True, default=generate_uuid)
    automation_id = Column(String(36), ForeignKey("dm_automations.id", ondelete="CASCADE"), nullable=False)
    message_id = Column(String, ForeignKey("ig_messages.id", ondelete="CASCADE"), nullable=False)
    status = Column(String, nullable=False)  # success, failed
    error_message = Column(Text, nullable=True)
    executed_at = Column(DateTime, default=datetime.datetime.utcnow)

    automation = relationship("DMAutomation", back_populates="executions")
    message = relationship("IGMessage", back_populates="executions")

