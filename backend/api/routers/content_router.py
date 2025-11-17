"""
Content and Problems router
Handles content curation and practice problem generation
"""
from typing import List
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from backend.api import schemas
from backend.api.auth import get_current_active_user
from backend.db import get_db, get_mongodb
from backend.db.models import User
from backend.agents.content_curator_agent import ContentCuratorAgent
from backend.agents.practice_generator_agent import PracticeGeneratorAgent


router = APIRouter()


@router.post("/curate", response_model=List[schemas.ContentResponse])
async def curate_content(
    request: schemas.ContentRequest,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
    mongodb = Depends(get_mongodb)
):
    """
    Curate learning content for a topic

    Searches multiple sources and ranks content by quality and relevance
    """

    curator = ContentCuratorAgent(db, mongodb)

    try:
        content = await curator.curate_content(
            topic=request.topic,
            difficulty=request.difficulty,
            content_types=request.content_types,
            max_items=request.max_items
        )

        return [
            schemas.ContentResponse(
                title=c.title,
                description=c.description,
                url=str(c.url) if c.url else None,
                content_type=c.content_type.value,
                source=c.source.value,
                difficulty=c.difficulty.value,
                author=c.author,
                duration_minutes=c.duration_minutes,
                quality_score=c.quality_score
            )
            for c in content
        ]

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to curate content: {str(e)}"
        )
    finally:
        await curator.close()


@router.post("/problems/generate", response_model=List[schemas.ProblemResponse])
async def generate_problems(
    request: schemas.ProblemRequest,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
    mongodb = Depends(get_mongodb)
):
    """
    Generate practice problems using AI

    Creates personalized problems adapted to user's skill level
    """

    generator = PracticeGeneratorAgent(db, mongodb)

    try:
        # Get user's skill level for adaptive difficulty
        from backend.agents.progress_tracker_agent import ProgressTrackerAgent
        from backend.db import get_redis, get_influxdb

        problems = await generator.generate_problems(
            topic=request.topic,
            subtopic=request.subtopic,
            difficulty=request.difficulty,
            problem_types=request.problem_types,
            count=request.count,
            user_skill_level=50.0  # Default, should fetch from user progress
        )

        return [
            schemas.ProblemResponse(
                id=str(p.id) if p.id else "new",
                question=p.question,
                problem_type=p.problem_type.value,
                difficulty=p.difficulty.value,
                hints=p.hints,
                options=p.options
            )
            for p in problems
        ]

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to generate problems: {str(e)}"
        )


@router.post("/problems/evaluate", response_model=schemas.AnswerEvaluation)
async def evaluate_answer(
    submission: schemas.SubmitAnswer,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
    mongodb = Depends(get_mongodb)
):
    """
    Evaluate user's answer to a practice problem

    Uses AI to provide detailed feedback
    """

    generator = PracticeGeneratorAgent(db, mongodb)

    try:
        # Get problem from MongoDB
        problems_collection = mongodb.practice_problems
        problem_doc = await problems_collection.find_one({"_id": submission.problem_id})

        if not problem_doc:
            raise HTTPException(
                status_code=404,
                detail="Problem not found"
            )

        from backend.db.mongodb_schemas import PracticeProblem
        problem = PracticeProblem(**problem_doc)

        # Evaluate answer
        evaluation = await generator.evaluate_answer(problem, submission.answer)

        return schemas.AnswerEvaluation(
            is_correct=evaluation["is_correct"],
            score=evaluation["score"],
            feedback=evaluation["feedback"],
            correct_answer=evaluation.get("correct_answer"),
            explanation=problem.explanation
        )

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to evaluate answer: {str(e)}"
        )


@router.get("/search")
async def semantic_search(
    query: str,
    topic: str = None,
    difficulty: str = None,
    limit: int = 5,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
    mongodb = Depends(get_mongodb)
):
    """
    Semantic search for learning content

    Uses vector similarity to find relevant content
    """

    curator = ContentCuratorAgent(db, mongodb)

    try:
        results = await curator.semantic_search(
            query=query,
            topic=topic,
            difficulty=difficulty,
            limit=limit
        )

        return {"results": results}

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Search failed: {str(e)}"
        )
    finally:
        await curator.close()
