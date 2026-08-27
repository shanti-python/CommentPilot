import datetime
from typing import List, Dict, Optional, Any
from pydantic import BaseModel, Field, ConfigDict

# FlowNode Schemas
class FlowNodeBase(BaseModel):
    id: str
    type: str  # 'trigger', 'condition', 'action_reply', 'action_dm', 'action_tag'
    config: Dict[str, Any] = Field(default_factory=dict)


class FlowNodeCreate(FlowNodeBase):
    pass


class FlowNode(FlowNodeBase):
    flow_id: str

    model_config = ConfigDict(from_attributes=True)


# FlowEdge Schemas
class FlowEdgeBase(BaseModel):
    id: Optional[str] = None
    source_node_id: str
    target_node_id: str
    condition_value: Optional[str] = None


class FlowEdgeCreate(FlowEdgeBase):
    pass


class FlowEdge(FlowEdgeBase):
    id: str
    flow_id: str

    model_config = ConfigDict(from_attributes=True)


# AutomationFlow Schemas
class AutomationFlowBase(BaseModel):
    name: str
    is_active: bool = True


class AutomationFlowCreate(AutomationFlowBase):
    instagram_account_id: Optional[int] = None
    facebook_account_id: Optional[int] = None
    instagram_post_id: Optional[str] = None
    facebook_post_id: Optional[str] = None
    nodes: List[FlowNodeCreate] = []
    edges: List[FlowEdgeCreate] = []


class AutomationFlowUpdate(BaseModel):
    name: Optional[str] = None
    is_active: Optional[bool] = None
    instagram_account_id: Optional[int] = None
    facebook_account_id: Optional[int] = None
    instagram_post_id: Optional[str] = None
    facebook_post_id: Optional[str] = None
    nodes: Optional[List[FlowNodeCreate]] = None
    edges: Optional[List[FlowEdgeCreate]] = None


class AutomationFlow(AutomationFlowBase):
    id: str
    instagram_account_id: Optional[int] = None
    facebook_account_id: Optional[int] = None
    instagram_post_id: Optional[str] = None
    facebook_post_id: Optional[str] = None
    created_at: datetime.datetime
    updated_at: datetime.datetime
    nodes: List[FlowNode] = []
    edges: List[FlowEdge] = []

    model_config = ConfigDict(from_attributes=True)
