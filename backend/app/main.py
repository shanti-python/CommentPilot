from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from loguru import logger
from contextlib import asynccontextmanager

from app.core.config import settings
from app.api.api_v1.api import api_router
from app.webhooks import meta as webhook_meta
from app.db.session import engine
from app.db.base import Base
from app.db.session import SessionLocal
from app.db.repository import user_repo
from app.core.security import get_password_hash

# Setup Loguru logger format
import sys
logger.remove()
logger.add(
    sys.stdout,
    format="<green>{time:YYYY-MM-DD HH:mm:ss.SSS}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - <level>{message}</level>",
    level="INFO"
)

@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Initializing database tables...")
    async with engine.begin() as conn:
        # Create all tables (if they do not exist)
        await conn.run_sync(Base.metadata.create_all)
        # Ensure posts table has thumbnail_url column
        from sqlalchemy import text
        await conn.execute(text("ALTER TABLE posts ADD COLUMN IF NOT EXISTS thumbnail_url TEXT;"))
        
    logger.info("Database tables initialized successfully.")
    
    # Create default admin user if not exists
    async with SessionLocal() as db:
        admin_email = settings.FIRST_SUPERUSER
        existing_admin = await user_repo.get_by_email(db, email=admin_email)
        if not existing_admin:
            logger.info(f"Creating default superuser: {admin_email}")
            admin_in = {
                "email": admin_email,
                "hashed_password": get_password_hash(settings.FIRST_SUPERUSER_PASSWORD),
                "is_superuser": True,
                "is_active": True
            }
            await user_repo.create(db, obj_in=admin_in)
            await db.commit()
            logger.info("Default superuser created.")
        else:
            logger.info(f"Default superuser already exists: {admin_email}")

    yield
    # Shutdown tasks
    logger.info("Shutting down API services...")
    await engine.dispose()


app = FastAPI(
    title=settings.PROJECT_NAME,
    openapi_url=f"{settings.API_V1_STR}/openapi.json",
    lifespan=lifespan
)

# Set all CORS enabled origins
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_headers=["*"],
    allow_methods=["*"],
)

# Mount routes
app.include_router(api_router, prefix=settings.API_V1_STR)
app.include_router(webhook_meta.router, prefix="/webhooks")

from fastapi.staticfiles import StaticFiles
import os
uploads_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "uploads"))
os.makedirs(uploads_dir, exist_ok=True)
app.mount("/uploads", StaticFiles(directory=uploads_dir), name="uploads")

@app.get("/", tags=["Root"])
def root():
    return {
        "message": "Welcome to the Instagram Comment Automation Platform API",
        "docs_url": "/docs",
        "redoc_url": "/redoc"
    }
