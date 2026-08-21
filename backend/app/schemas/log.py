import datetime
from typing import Optional, Dict, Any
from pydantic import BaseModel, ConfigDict

# AutomationLog Schemas
class AutomationLogBase(BaseModel):
    flow_id: Optional[str] = None
    comment_id: Optional[str] = None
    action_type: str
    status: str
    details: Optional[Dict[str, Any]] = None


class AutomationLogCreate(AutomationLogBase):
    pass


class AutomationLog(AutomationLogBase):
    id: int
    created_at: datetime.datetime

    model_config = ConfigDict(from_attributes=True)


# Analytics Response Schema
class AnalyticsResponse(BaseModel):
    total_comments: int
    replies_sent: int
    dms_sent: int
    keyword_counts: Dict[str, int]
    failed_replies: int
    avg_response_time_seconds: float
