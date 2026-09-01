from datetime import datetime, timedelta
from typing import Any, List
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.ext.asyncio import AsyncSession
from loguru import logger

from app.core import security
from app.core.config import settings
from app.api import deps
from app.db.repository import user_repo, instagram_account_repo, facebook_account_repo, post_repo, facebook_post_repo
from app.utils.text import parse_iso_timestamp
from app.schemas.user import Token, UserCreate
from app.schemas.instagram import MetaOAuthPayload, InstagramAccount as InstagramAccountSchema
from app.schemas.facebook import FacebookAccount as FacebookAccountSchema
from app.integrations.meta.client import meta_client, MetaAPIError
from app.models.user import User

router = APIRouter()


@router.post("/login-json", response_model=Token)
async def login_json(
    *,
    db: AsyncSession = Depends(deps.get_db),
    user_in: UserCreate
) -> Any:
    """JSON-based login flow."""
    user = await user_repo.get_by_email(db, email=user_in.email)
    if not user or not security.verify_password(user_in.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Incorrect email or password"
        )
    elif not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Inactive user"
        )
    
    access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    return {
        "access_token": security.create_access_token(
            user.id, expires_delta=access_token_expires
        ),
        "token_type": "bearer",
    }


@router.post("/login", response_model=Token)
async def login_form(
    db: AsyncSession = Depends(deps.get_db),
    form_data: OAuth2PasswordRequestForm = Depends()
) -> Any:
    """OAuth2 password flow for OpenAPI/Swagger UI login."""
    user = await user_repo.get_by_email(db, email=form_data.username)
    if not user or not security.verify_password(form_data.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Incorrect email or password"
        )
    elif not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Inactive user"
        )
        
    access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    return {
        "access_token": security.create_access_token(
            user.id, expires_delta=access_token_expires
        ),
        "token_type": "bearer",
    }


@router.post("/facebook-connect", response_model=List[InstagramAccountSchema])
async def facebook_connect(
    *,
    db: AsyncSession = Depends(deps.get_db),
    current_user: User = Depends(deps.get_current_user),
    payload: MetaOAuthPayload
) -> Any:
    """
    Connect user's Facebook account:
    1. Exchange short-lived token for a long-lived user token.
    2. Automatically discover Pages and connected Instagram accounts.
    3. Encrypt and save accounts in the DB.
    4. Fetch and cache recent media/posts for each discovered account.
    """
    try:
        # Step 1: Exchange user token
        long_lived_user_token = await meta_client.get_long_lived_user_token(payload.access_token)
        
        # Step 2: Auto-discover Instagram Business accounts
        discovered_accounts = await meta_client.discover_accounts(long_lived_user_token)
        
        if not discovered_accounts:
            raise HTTPException(
                status_code=400,
                detail="No Instagram Business Accounts found connected to your Facebook Pages. "
                       "Please verify page setup."
            )
            
        saved_accounts = []
        for disc in discovered_accounts:
            # Check if account already connected by instagram_business_account_id or page_id
            existing = await instagram_account_repo.get_by_instagram_id(
                db, instagram_business_account_id=disc["instagram_business_account_id"]
            )
            if not existing:
                existing = await instagram_account_repo.get_by_page_id(
                    db, page_id=disc["page_id"]
                )
            
            account_data = {
                "user_id": current_user.id,
                "instagram_business_account_id": disc["instagram_business_account_id"],
                "page_id": disc["page_id"],
                "username": disc["instagram_username"],
                "name": disc["instagram_name"],
                "profile_picture_url": disc["instagram_profile_pic"],
                "page_access_token": disc["page_access_token"],  # Property handles encryption
                "user_access_token": long_lived_user_token       # Property handles encryption
            }
            
            if existing:
                # Update existing account credentials & info
                account = await instagram_account_repo.update(db, db_obj=existing, obj_in=account_data)
            else:
                # Create new account connection
                account = await instagram_account_repo.create(db, obj_in=account_data)
                
            await db.commit()
            await db.refresh(account)

            # Clean up any stale/duplicate Instagram accounts for the same page_id or user_id
            from sqlalchemy import select, or_
            from app.models.instagram import InstagramAccount
            stale_stmt = select(InstagramAccount).where(
                InstagramAccount.user_id == current_user.id,
                or_(
                    InstagramAccount.page_id == disc["page_id"],
                    InstagramAccount.instagram_business_account_id == disc["instagram_business_account_id"]
                ),
                InstagramAccount.id != account.id
            )
            stale_res = await db.execute(stale_stmt)
            for stale_acc in stale_res.scalars().all():
                await db.delete(stale_acc)
            await db.commit()

            saved_accounts.append(account)
            
            # Step 4: Sync posts in background (cache recent media)
            try:
                posts_data = await meta_client.get_instagram_posts(
                    instagram_business_account_id=account.instagram_business_account_id,
                    page_access_token=account.page_access_token
                )
                for post in posts_data:
                    existing_post = await post_repo.get(db, post["id"])
                    
                    ts_val = parse_iso_timestamp(post.get("timestamp"))

                    post_in = {
                        "id": post["id"],
                        "instagram_account_id": account.id,
                        "caption": post.get("caption"),
                        "media_type": post.get("media_type"),
                        "media_url": post.get("media_url"),
                        "permalink": post.get("permalink"),
                        "timestamp": ts_val
                    }
                    if existing_post:
                        await post_repo.update(db, db_obj=existing_post, obj_in=post_in)
                    else:
                        await post_repo.create(db, obj_in=post_in)
                await db.commit()
            except Exception as e:
                logger.warning(f"Failed to sync initial posts for account {account.username}: {str(e)}")

        return saved_accounts

    except HTTPException:
        raise
    except MetaAPIError as e:
        logger.error(f"Meta OAuth connection failed: {e.message}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Meta integration failed: {e.message}"
        )
    except Exception as e:
        logger.error(f"OAuth transaction error: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Internal connection failure: {str(e)}"
        )


@router.post("/facebook-connect-page", response_model=List[FacebookAccountSchema])
async def facebook_connect_page(
    *,
    db: AsyncSession = Depends(deps.get_db),
    current_user: User = Depends(deps.get_current_user),
    payload: MetaOAuthPayload
) -> Any:
    """
    Connect user's Facebook account & Pages:
    1. Exchange short-lived token for a long-lived user token.
    2. Automatically discover Pages.
    3. Encrypt and save Pages in the DB.
    4. Fetch and cache recent feed/posts for each discovered Page.
    """
    try:
        # Step 1: Exchange user token
        long_lived_user_token = await meta_client.get_long_lived_user_token(payload.access_token)
        
        # Step 2: Auto-discover Facebook Pages
        discovered_pages = await meta_client.discover_facebook_pages(long_lived_user_token)
        
        if not discovered_pages:
            raise HTTPException(
                status_code=400,
                detail="No Facebook Pages found. Please verify page setup."
            )
            
        saved_accounts = []
        for disc in discovered_pages:
            # Check if account already connected
            existing = await facebook_account_repo.get_by_page_id(
                db, facebook_page_id=disc["facebook_page_id"]
            )
            
            account_data = {
                "user_id": current_user.id,
                "facebook_page_id": disc["facebook_page_id"],
                "username": disc["username"],
                "name": disc["name"],
                "profile_picture_url": disc["profile_picture_url"],
                "page_access_token": disc["page_access_token"]
            }
            
            if existing:
                account = await facebook_account_repo.update(db, db_obj=existing, obj_in=account_data)
            else:
                account = await facebook_account_repo.create(db, obj_in=account_data)
                
            await db.commit()
            await db.refresh(account)

            # Clean up any duplicate facebook accounts for the same page_id
            from sqlalchemy import select
            from app.models.facebook import FacebookAccount
            stale_stmt = select(FacebookAccount).where(
                FacebookAccount.user_id == current_user.id,
                FacebookAccount.facebook_page_id == disc["facebook_page_id"],
                FacebookAccount.id != account.id
            )
            stale_res = await db.execute(stale_stmt)
            for stale_acc in stale_res.scalars().all():
                await db.delete(stale_acc)
            await db.commit()

            saved_accounts.append(account)
            
            # Step 4: Sync posts in background (cache recent media)
            try:
                posts_data = await meta_client.get_facebook_posts(
                    page_id=account.facebook_page_id,
                    page_access_token=account.page_access_token
                )
                for post in posts_data:
                    existing_post = await facebook_post_repo.get(db, post["id"])
                    
                    ts_val = parse_iso_timestamp(post.get("timestamp"))

                    post_in = {
                        "id": post["id"],
                        "facebook_account_id": account.id,
                        "caption": post.get("caption"),
                        "media_type": post.get("media_type"),
                        "media_url": post.get("media_url"),
                        "thumbnail_url": post.get("thumbnail_url"),
                        "permalink": post.get("permalink"),
                        "timestamp": ts_val
                    }
                    if existing_post:
                        await facebook_post_repo.update(db, db_obj=existing_post, obj_in=post_in)
                    else:
                        await facebook_post_repo.create(db, obj_in=post_in)
                await db.commit()
            except Exception as e:
                logger.warning(f"Failed to sync initial Facebook posts for page {account.name}: {str(e)}")

        return saved_accounts

    except HTTPException:
        raise
    except MetaAPIError as e:
        logger.error(f"Meta OAuth Page connection failed: {e.message}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Meta integration failed: {e.message}"
        )
    except Exception as e:
        logger.error(f"OAuth page transaction error: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Internal connection failure: {str(e)}"
        )


@router.get("/meta-config")
async def get_meta_config() -> Any:
    """Retrieve public Meta configuration (e.g. App ID)."""
    return {
        "app_id": settings.META_APP_ID,
        "scopes": settings.META_OAUTH_SCOPES
    }
