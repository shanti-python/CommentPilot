import datetime
from typing import Optional
from pydantic import BaseModel, ConfigDict

# InstagramAccount Schemas
class InstagramAccountBase(BaseModel):
    instagram_business_account_id: str
    page_id: str
    username: str
    name: Optional[str] = None
    profile_picture_url: Optional[str] = None


class InstagramAccountCreate(InstagramAccountBase):
    page_access_token: str
    user_access_token: Optional[str] = None


class InstagramAccount(InstagramAccountBase):
    id: int
    user_id: int

    model_config = ConfigDict(from_attributes=True)


# Post Schemas
class PostBase(BaseModel):
    id: str
    instagram_account_id: int
    caption: Optional[str] = None
    media_type: Optional[str] = None
    media_url: Optional[str] = None
    thumbnail_url: Optional[str] = None
    permalink: Optional[str] = None
    timestamp: Optional[datetime.datetime] = None
    automation_status: Optional[str] = "setup"
    keyword: Optional[str] = None
    reply_message: Optional[str] = None
    dm_message: Optional[str] = None
    is_future_post: Optional[bool] = False


class PostCreate(PostBase):
    pass


class Post(PostBase):
    model_config = ConfigDict(from_attributes=True)


# Comment Schemas
class CommentBase(BaseModel):
    id: str
    media_id: str
    text: str
    username: str
    timestamp: datetime.datetime
    parent_id: Optional[str] = None


class CommentCreate(CommentBase):
    pass


class Comment(CommentBase):
    model_config = ConfigDict(from_attributes=True)


# CommentEvent Schemas
class CommentEventBase(BaseModel):
    comment_id: str
    media_id: str
    text: str
    username: str
    timestamp: datetime.datetime
    status: str = "pending"


class CommentEventCreate(CommentEventBase):
    pass


class CommentEvent(CommentEventBase):
    id: int
    processed_at: Optional[datetime.datetime] = None
    error_message: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)


# Facebook Login Request Schema
class MetaOAuthPayload(BaseModel):
    access_token: str  # Short-lived user access token received from FB login on the frontend


# DMAutomation Schemas
class DMAutomationBase(BaseModel):
    instagram_account_id: int
    name: str
    trigger_type: str  # exact_keyword, contains_keyword, first_message, any_message
    keyword: Optional[str] = None
    reply_text: str
    is_active: bool = True


class DMAutomationCreate(DMAutomationBase):
    pass


class DMAutomationUpdate(BaseModel):
    name: Optional[str] = None
    trigger_type: Optional[str] = None
    keyword: Optional[str] = None
    reply_text: Optional[str] = None
    is_active: Optional[bool] = None


class DMAutomation(DMAutomationBase):
    id: str
    created_at: datetime.datetime
    updated_at: datetime.datetime

    model_config = ConfigDict(from_attributes=True)


# IGMessage Schemas
class IGMessageBase(BaseModel):
    id: str
    instagram_account_id: int
    sender_id: str
    recipient_id: str
    text: Optional[str] = None
    timestamp: datetime.datetime
    status: str = "pending"


class IGMessage(IGMessageBase):
    processed_at: Optional[datetime.datetime] = None
    error_message: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)


# IGConversation Schemas
class IGConversationBase(BaseModel):
    id: str
    instagram_account_id: int
    participant_id: str
    last_message_at: datetime.datetime
    created_at: datetime.datetime


class IGConversation(IGConversationBase):
    model_config = ConfigDict(from_attributes=True)


# DMAutomationExecution Schemas
class DMAutomationExecutionBase(BaseModel):
    id: str
    automation_id: str
    message_id: str
    status: str
    error_message: Optional[str] = None
    executed_at: datetime.datetime


class DMAutomationExecution(DMAutomationExecutionBase):
    model_config = ConfigDict(from_attributes=True)

