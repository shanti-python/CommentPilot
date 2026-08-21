# Import all the models, so that Base has them before being
# imported by Alembic
from app.db.base_class import Base  # noqa
from app.models.user import User  # noqa
from app.models.instagram import InstagramAccount, Post, Comment, CommentEvent, DMAutomation, IGMessage, IGConversation, DMAutomationExecution  # noqa
from app.models.facebook import FacebookAccount, FacebookPost, FacebookComment, FacebookCommentEvent  # noqa
from app.models.automation import AutomationFlow, FlowNode, FlowEdge  # noqa
from app.models.log import AutomationLog  # noqa
