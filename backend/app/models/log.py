import datetime
from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, JSON
from app.db.base_class import Base

class AutomationLog(Base):
    id = Column(Integer, primary_key=True, index=True)
    flow_id = Column(String(36), nullable=True)  # Store flow ID (no hard FK to avoid log loss on delete)
    comment_id = Column(String, index=True, nullable=True)  # Instagram Comment ID trigger
    
    # Types: 'trigger_match', 'condition_check', 'reply_sent', 'dm_sent', 'tag_added', 'failed'
    action_type = Column(String, nullable=False, index=True)
    status = Column(String, nullable=False)  # 'success' or 'failed'
    
    # Store arbitrary metadata about execution details (e.g. response payload, error traceback)
    details = Column(JSON, nullable=True, default=dict)
    
    created_at = Column(DateTime, default=datetime.datetime.utcnow, index=True)
