"""
Progress and Analytics router
Handles progress tracking, metrics, and analytics
"""
from typing import List
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from backend.api import schemas
from backend.api.auth import get_current_active_user
from backend.db import get_db, get_redis, get_influxdb
from backend.db.models import User
from backend.agents.progress_tracker_agent import ProgressTrackerAgent


router = APIRouter()


@router.get("/metrics", response_model=schemas.UserMetricsResponse)
async def get_user_metrics(
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
    redis = Depends(get_redis),
    influxdb = Depends(get_influxdb)
):
    """Get comprehensive user learning metrics"""

    progress_tracker = ProgressTrackerAgent(db, influxdb, redis)

    metrics = await progress_tracker.get_user_metrics(current_user.id)

    return metrics


@router.get("/topics/{topic}", response_model=schemas.ProgressResponse)
async def get_topic_progress(
    topic: str,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
    redis = Depends(get_redis),
    influxdb = Depends(get_influxdb)
):
    """Get progress for a specific topic"""

    progress_tracker = ProgressTrackerAgent(db, influxdb, redis)

    progress = await progress_tracker.get_user_metrics(current_user.id, topic)

    if not progress:
        raise HTTPException(
            status_code=404,
            detail=f"No progress found for topic: {topic}"
        )

    return progress


@router.get("/analytics", response_model=schemas.AnalyticsResponse)
async def get_learning_analytics(
    days: int = 30,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
    redis = Depends(get_redis),
    influxdb = Depends(get_influxdb)
):
    """
    Get time-series learning analytics

    Returns daily metrics over the specified period:
    - Accuracy trends
    - Time spent learning
    - Session frequency
    """

    progress_tracker = ProgressTrackerAgent(db, influxdb, redis)

    analytics = await progress_tracker.get_learning_analytics(
        current_user.id,
        days=days
    )

    return analytics


@router.get("/streak")
async def get_learning_streak(
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """Get user's current learning streak"""

    from sqlalchemy import select
    from backend.db.models import LearningStreak

    query = select(LearningStreak).where(
        LearningStreak.user_id == current_user.id
    )

    result = await db.execute(query)
    streak = result.scalar_one_or_none()

    if not streak:
        return {
            "current_streak": 0,
            "longest_streak": 0,
            "total_days_active": 0
        }

    return {
        "current_streak": streak.current_streak,
        "longest_streak": streak.longest_streak,
        "total_days_active": streak.total_days_active,
        "total_sessions": streak.total_sessions,
        "total_minutes": streak.total_minutes
    }


@router.get("/reviews/due")
async def get_due_reviews(
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
    redis = Depends(get_redis),
    influxdb = Depends(get_influxdb)
):
    """Get spaced repetition cards due for review"""

    progress_tracker = ProgressTrackerAgent(db, influxdb, redis)

    due_cards = await progress_tracker.get_due_reviews(current_user.id)

    return {
        "count": len(due_cards),
        "cards": [
            {
                "id": card.id,
                "topic": card.topic,
                "question": card.question,
                "next_review_date": card.next_review_date.isoformat()
            }
            for card in due_cards
        ]
    }
