import uuid
import datetime
from sqlalchemy import Column, Integer, String, Boolean, DateTime, ForeignKey, JSON, Text
from sqlalchemy.orm import relationship
from app.db.base_class import Base

def generate_uuid() -> str:
    return str(uuid.uuid4())

class AutomationFlow(Base):
    id = Column(String(36), primary_key=True, default=generate_uuid)
    instagram_account_id = Column(Integer, ForeignKey("instagram_accounts.id", ondelete="CASCADE"), nullable=True)
    facebook_account_id = Column(Integer, ForeignKey("facebook_accounts.id", ondelete="CASCADE"), nullable=True)
    instagram_post_id = Column(String, ForeignKey("posts.id", ondelete="CASCADE"), nullable=True)
    facebook_post_id = Column(String, ForeignKey("facebook_posts.id", ondelete="CASCADE"), nullable=True)
    name = Column(String, nullable=False)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow)

    # --- Future Flow Fields ---
    # When True, this flow is waiting for a not-yet-published post to appear.
    is_future_flow = Column(Boolean, default=False, nullable=False)
    # User-provided snippet of the upcoming post caption (used for fuzzy matching).
    future_post_caption = Column(Text, nullable=True)
    # Optional: user-expected publish timestamp to help narrow matching window.
    future_post_scheduled_at = Column(DateTime, nullable=True)
    # Tracks the resolution status: 'pending' | 'resolved' | 'failed'
    future_flow_status = Column(String(20), default="pending", nullable=True)
    # Last time we ran a scan for this future flow's post
    future_flow_last_scanned_at = Column(DateTime, nullable=True)
    # Apply to all future posts continuously
    apply_to_all_future_posts = Column(Boolean, default=False, nullable=True)

    instagram_account = relationship("InstagramAccount", back_populates="flows")
    facebook_account = relationship("FacebookAccount", back_populates="flows")
    instagram_post = relationship("Post", back_populates="flows")
    facebook_post = relationship("FacebookPost", back_populates="flows")
    nodes = relationship("FlowNode", back_populates="flow", cascade="all, delete-orphan", lazy="selectin")
    edges = relationship("FlowEdge", back_populates="flow", cascade="all, delete-orphan", lazy="selectin")


class FlowNode(Base):
    id = Column(String(50), primary_key=True)  # Can be UUID or custom frontend ID (e.g. node_1)
    flow_id = Column(String(36), ForeignKey("automation_flows.id", ondelete="CASCADE"), nullable=False)
    
    # Node types: 'trigger', 'condition', 'action_reply', 'action_dm', 'action_tag'
    type = Column(String, nullable=False)
    
    # Store configuration options such as keyword list, reply templates, DM message etc.
    config = Column(JSON, nullable=False, default=dict)

    flow = relationship("AutomationFlow", back_populates="nodes")


class FlowEdge(Base):
    id = Column(String(50), primary_key=True, default=generate_uuid)
    flow_id = Column(String(36), ForeignKey("automation_flows.id", ondelete="CASCADE"), nullable=False)
    
    source_node_id = Column(String(50), nullable=False)
    target_node_id = Column(String(50), nullable=False)
    
    # Optional condition string to branch the flow execution (e.g. "yes", "no")
    condition_value = Column(String, nullable=True)

    flow = relationship("AutomationFlow", back_populates="edges")
