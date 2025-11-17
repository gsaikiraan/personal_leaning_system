"""
Learning Sessions router
Handles session creation, management, and execution
"""
from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc

from backend.api import schemas
from backend.api.auth import get_current_active_user
from backend.db import get_db, get_neo4j, get_mongodb, get_redis, get_influxdb
from backend.db.models import User, LearningSession
from backend.agents.learning_session_orchestrator import LearningSessionOrchestrator
from backend.agents.progress_tracker_agent import ProgressTrackerAgent


router = APIRouter()


@router.post("/create", response_model=schemas.SessionPlanResponse)
async def create_learning_session(
    session_request: schemas.SessionCreate,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
    neo4j = Depends(get_neo4j),
    mongodb = Depends(get_mongodb),
    redis = Depends(get_redis),
    influxdb = Depends(get_influxdb)
):
    """
    Create a personalized learning session using AI agents

    This endpoint orchestrates all agents to create a complete learning session:
    - Analyzes user's current state and goals
    - Selects optimal topic based on learning path
    - Curates relevant content
    - Generates practice problems
    - Creates spaced repetition reviews
    """

    # Initialize orchestrator
    orchestrator = LearningSessionOrchestrator(
        db_session=db,
        neo4j_session=neo4j,
        mongodb_db=mongodb,
        redis_client=redis,
        influxdb_client=influxdb
    )

    # Create session
    try:
        session_plan = await orchestrator.create_learning_session(
            user_id=current_user.id,
            goal_id=session_request.goal_id,
            session_duration_minutes=session_request.duration_minutes
        )

        return session_plan

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create learning session: {str(e)}"
        )


@router.get("/", response_model=List[schemas.SessionResponse])
async def get_user_sessions(
    skip: int = 0,
    limit: int = 20,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """Get user's learning sessions"""

    query = select(LearningSession).where(
        LearningSession.user_id == current_user.id
    ).order_by(desc(LearningSession.created_at)).offset(skip).limit(limit)

    result = await db.execute(query)
    sessions = result.scalars().all()

    return sessions


@router.get("/{session_id}", response_model=schemas.SessionDetailResponse)
async def get_session_detail(
    session_id: int,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """Get detailed information about a specific session"""

    query = select(LearningSession).where(
        LearningSession.id == session_id,
        LearningSession.user_id == current_user.id
    )

    result = await db.execute(query)
    session = result.scalar_one_or_none()

    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Session not found"
        )

    return session


@router.post("/{session_id}/complete", response_model=schemas.SessionResponse)
async def complete_session(
    session_id: int,
    completion_data: schemas.SessionComplete,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
    redis = Depends(get_redis),
    influxdb = Depends(get_influxdb)
):
    """
    Mark a session as completed and update all metrics

    This triggers:
    - Progress tracking updates
    - Skill level adjustments
    - Streak updates
    - Spaced repetition scheduling
    """

    # Get session
    query = select(LearningSession).where(
        LearningSession.id == session_id,
        LearningSession.user_id == current_user.id
    )

    result = await db.execute(query)
    session = result.scalar_one_or_none()

    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Session not found"
        )

    # Initialize progress tracker
    progress_tracker = ProgressTrackerAgent(db, influxdb, redis)

    # Track completion
    await progress_tracker.track_session_completion(
        session_id=session_id,
        user_id=current_user.id,
        topic=session.topic,
        duration_seconds=completion_data.duration_seconds,
        problems_attempted=completion_data.problems_attempted,
        problems_correct=completion_data.problems_correct,
        user_rating=completion_data.user_rating
    )

    # Update session with feedback
    if completion_data.user_feedback:
        session.user_feedback = completion_data.user_feedback

    await db.commit()
    await db.refresh(session)

    return session


@router.delete("/{session_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_session(
    session_id: int,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """Delete a session"""

    query = select(LearningSession).where(
        LearningSession.id == session_id,
        LearningSession.user_id == current_user.id
    )

    result = await db.execute(query)
    session = result.scalar_one_or_none()

    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Session not found"
        )

    await db.delete(session)
    await db.commit()

    return None
