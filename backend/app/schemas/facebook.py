import datetime
from typing import Optional
from pydantic import BaseModel, ConfigDict

# FacebookAccount Schemas
class FacebookAccountBase(BaseModel):
    facebook_page_id: str
    username: str
    name: Optional[str] = None
    profile_picture_url: Optional[str] = None


class FacebookAccountCreate(FacebookAccountBase):
    page_access_token: str


class FacebookAccount(FacebookAccountBase):
    id: int
    user_id: int

    model_config = ConfigDict(from_attributes=True)


# Post Schemas
class FacebookPostBase(BaseModel):
    id: str
    facebook_account_id: int
    caption: Optional[str] = None
    media_type: Optional[str] = None
    media_url: Optional[str] = None
    thumbnail_url: Optional[str] = None
    permalink: Optional[str] = None
    timestamp: Optional[datetime.datetime] = None


class FacebookPostCreate(FacebookPostBase):
    pass


class FacebookPost(FacebookPostBase):
    model_config = ConfigDict(from_attributes=True)


# Comment Schemas
class FacebookCommentBase(BaseModel):
    id: str
    media_id: str
    text: str
    username: str
    timestamp: datetime.datetime
    parent_id: Optional[str] = None


class FacebookCommentCreate(FacebookCommentBase):
    pass


class FacebookComment(FacebookCommentBase):
    model_config = ConfigDict(from_attributes=True)


# CommentEvent Schemas
class FacebookCommentEventBase(BaseModel):
    comment_id: str
    media_id: str
    text: str
    username: str
    timestamp: datetime.datetime
    status: str = "pending"


class FacebookCommentEventCreate(FacebookCommentEventBase):
    pass


class FacebookCommentEvent(FacebookCommentEventBase):
    id: int
    processed_at: Optional[datetime.datetime] = None
    error_message: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)
