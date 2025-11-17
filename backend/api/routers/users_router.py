"""
Users router
Handles user profile and settings management
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from backend.api import schemas
from backend.api.auth import get_current_active_user
from backend.db import get_db
from backend.db.models import User


router = APIRouter()


@router.get("/me", response_model=schemas.UserResponse)
async def get_current_user_profile(
    current_user: User = Depends(get_current_active_user)
):
    """Get current user's profile"""
    return current_user


@router.put("/me", response_model=schemas.UserResponse)
async def update_user_profile(
    user_update: schemas.UserUpdate,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """Update current user's profile"""

    if user_update.full_name is not None:
        current_user.full_name = user_update.full_name

    if user_update.timezone is not None:
        current_user.timezone = user_update.timezone

    if user_update.preferred_session_time is not None:
        current_user.preferred_session_time = user_update.preferred_session_time

    if user_update.daily_learning_goal_minutes is not None:
        current_user.daily_learning_goal_minutes = user_update.daily_learning_goal_minutes

    await db.commit()
    await db.refresh(current_user)

    return current_user


@router.delete("/me", status_code=status.HTTP_204_NO_CONTENT)
async def delete_user_account(
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """Delete current user's account"""

    # Mark as inactive instead of deleting
    current_user.is_active = False
    await db.commit()

    return None
