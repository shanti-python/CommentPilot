from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey, Boolean
from sqlalchemy.orm import relationship
from app.db.base_class import Base
from app.utils.encryption import encrypt_token, decrypt_token
import datetime

class FacebookAccount(Base):
    __tablename__ = "facebook_accounts"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    facebook_page_id = Column(String, unique=True, index=True, nullable=False)
    
    _page_access_token = Column("page_access_token", String, nullable=False)
    
    username = Column(String, nullable=False)
    name = Column(String, nullable=True)
    profile_picture_url = Column(Text, nullable=True)
    
    user = relationship("User", back_populates="facebook_accounts")
    posts = relationship("FacebookPost", back_populates="facebook_account", cascade="all, delete-orphan")
    flows = relationship("AutomationFlow", back_populates="facebook_account", cascade="all, delete-orphan")

    @property
    def page_access_token(self) -> str:
        return decrypt_token(self._page_access_token)

    @page_access_token.setter
    def page_access_token(self, val: str):
        self._page_access_token = encrypt_token(val)


class FacebookPost(Base):
    __tablename__ = "facebook_posts"
    
    id = Column(String, primary_key=True, index=True)  # Facebook Post ID
    facebook_account_id = Column(Integer, ForeignKey("facebook_accounts.id", ondelete="CASCADE"), nullable=False)
    caption = Column(Text, nullable=True)
    media_type = Column(String, nullable=True)  # post, reel, etc.
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
    
    facebook_account = relationship("FacebookAccount", back_populates="posts")
    comments = relationship("FacebookComment", back_populates="post", cascade="all, delete-orphan")
    flows = relationship("AutomationFlow", back_populates="facebook_post", cascade="all, delete-orphan")


class FacebookComment(Base):
    __tablename__ = "facebook_comments"
    
    id = Column(String, primary_key=True, index=True)  # Facebook Comment ID
    media_id = Column(String, ForeignKey("facebook_posts.id", ondelete="CASCADE"), nullable=False)
    text = Column(Text, nullable=False)
    username = Column(String, nullable=False)
    timestamp = Column(DateTime, default=datetime.datetime.utcnow)
    parent_id = Column(String, nullable=True)  # Nested replies
    
    post = relationship("FacebookPost", back_populates="comments")


class FacebookCommentEvent(Base):
    __tablename__ = "facebook_comment_events"
    
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
