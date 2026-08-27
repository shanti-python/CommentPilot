from typing import Any, List, Optional
from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File, Request
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.api import deps
from app.db.repository import (
    dm_automation_repo,
    ig_message_repo,
    ig_conversation_repo,
    dm_automation_execution_repo,
    instagram_account_repo
)
from app.schemas.instagram import (
    DMAutomation as DMAutomationSchema,
    DMAutomationCreate,
    DMAutomationUpdate,
    IGMessage as IGMessageSchema,
    IGConversation as IGConversationSchema,
    DMAutomationExecution as DMAutomationExecutionSchema
)
from app.models.instagram import IGMessage
from app.models.user import User

router = APIRouter()


@router.get("", response_model=List[DMAutomationSchema])
async def read_dm_automations(
    instagram_account_id: Optional[int] = None,
    db: AsyncSession = Depends(deps.get_db),
    current_user: User = Depends(deps.get_current_user)
) -> Any:
    """Retrieve DM automations. If instagram_account_id is provided, filters by it."""
    if instagram_account_id:
        acc = await instagram_account_repo.get(db, id=instagram_account_id)
        if not acc or acc.user_id != current_user.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Not enough permissions to access this Instagram account"
            )
        res = await db.execute(
            select(dm_automation_repo.model).filter(
                dm_automation_repo.model.instagram_account_id == instagram_account_id
            )
        )
        return res.scalars().all()
    
    user_accs = await instagram_account_repo.get_by_user_id(db, user_id=current_user.id)
    acc_ids = [acc.id for acc in user_accs]
    if not acc_ids:
        return []
        
    res = await db.execute(
        select(dm_automation_repo.model).filter(
            dm_automation_repo.model.instagram_account_id.in_(acc_ids)
        )
    )
    return res.scalars().all()


@router.post("", response_model=DMAutomationSchema, status_code=status.HTTP_201_CREATED)
async def create_dm_automation(
    obj_in: DMAutomationCreate,
    db: AsyncSession = Depends(deps.get_db),
    current_user: User = Depends(deps.get_current_user)
) -> Any:
    """Create a new DM automation rule."""
    acc = await instagram_account_repo.get(db, id=obj_in.instagram_account_id)
    if not acc or acc.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not enough permissions to access this Instagram account"
        )
    
    if obj_in.trigger_type in ("exact_keyword", "contains_keyword") and not obj_in.keyword:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Keyword is required for keyword trigger types"
        )

    aut = await dm_automation_repo.create(db, obj_in=obj_in.model_dump())
    await db.commit()
    await db.refresh(aut)
    return aut


@router.post("/upload")
async def upload_media(
    request: Request,
    file: UploadFile = File(...),
    current_user: User = Depends(deps.get_current_user)
) -> Any:
    """Upload media file for button template or image response."""
    import os
    import uuid
    import shutil

    # Ensure upload directory exists
    current_dir = os.path.dirname(os.path.abspath(__file__))
    for _ in range(4):
        current_dir = os.path.dirname(current_dir)
    uploads_dir = os.path.join(current_dir, "uploads")
    os.makedirs(uploads_dir, exist_ok=True)

    # Generate a unique file name
    file_ext = os.path.splitext(file.filename)[1]
    filename = f"{uuid.uuid4()}{file_ext}"
    file_path = os.path.join(uploads_dir, filename)

    # Save file
    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    # Get base URL of backend
    base_url = str(request.base_url)
    
    # Return file url
    file_url = f"{base_url}uploads/{filename}"
    return {"url": file_url}


@router.put("/{id}", response_model=DMAutomationSchema)
async def update_dm_automation(
    id: str,
    obj_in: DMAutomationUpdate,
    db: AsyncSession = Depends(deps.get_db),
    current_user: User = Depends(deps.get_current_user)
) -> Any:
    """Update a DM automation rule."""
    aut = await dm_automation_repo.get(db, id=id)
    if not aut:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="DM Automation rule not found"
        )
    
    acc = await instagram_account_repo.get(db, id=aut.instagram_account_id)
    if not acc or acc.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not enough permissions to modify this automation"
        )
        
    aut = await dm_automation_repo.update(db, db_obj=aut, obj_in=obj_in.model_dump(exclude_unset=True))
    await db.commit()
    await db.refresh(aut)
    return aut


@router.delete("/{id}", response_model=DMAutomationSchema)
async def delete_dm_automation(
    id: str,
    db: AsyncSession = Depends(deps.get_db),
    current_user: User = Depends(deps.get_current_user)
) -> Any:
    """Delete a DM automation rule."""
    aut = await dm_automation_repo.get(db, id=id)
    if not aut:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="DM Automation rule not found"
        )
        
    acc = await instagram_account_repo.get(db, id=aut.instagram_account_id)
    if not acc or acc.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not enough permissions to modify this automation"
        )
        
    aut = await dm_automation_repo.remove(db, id=id)
    await db.commit()
    return aut


@router.get("/messages", response_model=List[IGMessageSchema])
async def read_dm_messages(
    instagram_account_id: Optional[int] = None,
    db: AsyncSession = Depends(deps.get_db),
    current_user: User = Depends(deps.get_current_user)
) -> Any:
    """Retrieve logged direct messages."""
    if instagram_account_id:
        acc = await instagram_account_repo.get(db, id=instagram_account_id)
        if not acc or acc.user_id != current_user.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Not enough permissions to access this Instagram account"
            )
        res = await db.execute(
            select(ig_message_repo.model).filter(
                ig_message_repo.model.instagram_account_id == instagram_account_id
            ).order_by(ig_message_repo.model.timestamp.desc())
        )
        return res.scalars().all()

    user_accs = await instagram_account_repo.get_by_user_id(db, user_id=current_user.id)
    acc_ids = [acc.id for acc in user_accs]
    if not acc_ids:
        return []
        
    res = await db.execute(
        select(ig_message_repo.model).filter(
            ig_message_repo.model.instagram_account_id.in_(acc_ids)
        ).order_by(ig_message_repo.model.timestamp.desc())
    )
    return res.scalars().all()


@router.get("/conversations", response_model=List[IGConversationSchema])
async def read_dm_conversations(
    instagram_account_id: Optional[int] = None,
    db: AsyncSession = Depends(deps.get_db),
    current_user: User = Depends(deps.get_current_user)
) -> Any:
    """Retrieve conversations for the user's accounts."""
    if instagram_account_id:
        acc = await instagram_account_repo.get(db, id=instagram_account_id)
        if not acc or acc.user_id != current_user.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Not enough permissions to access this Instagram account"
            )
        res = await db.execute(
            select(ig_conversation_repo.model).filter(
                ig_conversation_repo.model.instagram_account_id == instagram_account_id
            ).order_by(ig_conversation_repo.model.last_message_at.desc())
        )
        return res.scalars().all()

    user_accs = await instagram_account_repo.get_by_user_id(db, user_id=current_user.id)
    acc_ids = [acc.id for acc in user_accs]
    if not acc_ids:
        return []
        
    res = await db.execute(
        select(ig_conversation_repo.model).filter(
            ig_conversation_repo.model.instagram_account_id.in_(acc_ids)
        ).order_by(ig_conversation_repo.model.last_message_at.desc())
    )
    return res.scalars().all()


@router.get("/executions", response_model=List[DMAutomationExecutionSchema])
async def read_dm_executions(
    instagram_account_id: Optional[int] = None,
    db: AsyncSession = Depends(deps.get_db),
    current_user: User = Depends(deps.get_current_user)
) -> Any:
    """Retrieve logs of executed DM automation rules."""
    user_accs = await instagram_account_repo.get_by_user_id(db, user_id=current_user.id)
    acc_ids = [acc.id for acc in user_accs]
    if instagram_account_id:
        if instagram_account_id not in acc_ids:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Not enough permissions to access this Instagram account"
            )
        acc_ids = [instagram_account_id]
        
    if not acc_ids:
        return []
        
    res = await db.execute(
        select(dm_automation_execution_repo.model)
        .join(IGMessage, IGMessage.id == dm_automation_execution_repo.model.message_id)
        .filter(IGMessage.instagram_account_id.in_(acc_ids))
        .order_by(dm_automation_execution_repo.model.executed_at.desc())
    )
    return res.scalars().all()

