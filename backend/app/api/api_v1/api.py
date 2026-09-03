from fastapi import APIRouter

from app.api.api_v1.endpoints import (
    auth,
    accounts,
    posts,
    comments,
    automation,
    dm_automation,
    logs,
    analytics,
    webhooks,
)

api_router = APIRouter()

api_router.include_router(auth.router, prefix="/auth", tags=["Authentication"])
api_router.include_router(accounts.router, prefix="/accounts", tags=["Instagram Accounts"])
api_router.include_router(posts.router, prefix="/posts", tags=["Posts Cache"])
api_router.include_router(comments.router, prefix="/comments", tags=["Comments Log"])
api_router.include_router(automation.router, prefix="/automation", tags=["Automation Engine"])
api_router.include_router(dm_automation.router, prefix="/dm-automation", tags=["Instagram Personal DM Automation"])
api_router.include_router(logs.router, prefix="/logs", tags=["Execution Logs"])
api_router.include_router(analytics.router, prefix="/analytics", tags=["Platform Analytics"])
api_router.include_router(webhooks.router, prefix="/webhooks", tags=["Webhook Management"])

