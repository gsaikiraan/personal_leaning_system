"""
SQLAlchemy models for PostgreSQL database
"""
from datetime import datetime
from typing import Optional
from sqlalchemy import (
    Boolean, Column, DateTime, Float, ForeignKey, Integer,
    String, Text, JSON, Enum as SQLEnum, Index
)
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
import enum


Base = declarative_base()


class UserRole(str, enum.Enum):
    """User roles"""
    USER = "user"
    PREMIUM = "premium"
    ADMIN = "admin"


class DifficultyLevel(str, enum.Enum):
    """Difficulty levels for content and problems"""
    BEGINNER = "beginner"
    INTERMEDIATE = "intermediate"
    ADVANCED = "advanced"
    EXPERT = "expert"


class SessionStatus(str, enum.Enum):
    """Learning session status"""
    SCHEDULED = "scheduled"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    SKIPPED = "skipped"


class User(Base):
    """User account model"""
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String(255), unique=True, index=True, nullable=False)
    username = Column(String(100), unique=True, index=True, nullable=False)
    hashed_password = Column(String(255), nullable=False)
    full_name = Column(String(255))

    role = Column(SQLEnum(UserRole), default=UserRole.USER)
    is_active = Column(Boolean, default=True)
    is_verified = Column(Boolean, default=False)

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    last_login_at = Column(DateTime)

    # User preferences
    timezone = Column(String(50), default="UTC")
    preferred_session_time = Column(String(5))  # HH:MM format
    daily_learning_goal_minutes = Column(Integer, default=20)

    # Relationships
    learning_goals = relationship("LearningGoal", back_populates="user", cascade="all, delete-orphan")
    sessions = relationship("LearningSession", back_populates="user", cascade="all, delete-orphan")
    progress = relationship("UserProgress", back_populates="user", cascade="all, delete-orphan")
    streaks = relationship("LearningStreak", back_populates="user", cascade="all, delete-orphan")


class LearningGoal(Base):
    """User's learning goals"""
    __tablename__ = "learning_goals"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)

    title = Column(String(255), nullable=False)
    description = Column(Text)
    category = Column(String(100))  # e.g., "programming", "data_science", "ml_engineering"
    target_skills = Column(JSON)  # List of skills to learn

    difficulty_level = Column(SQLEnum(DifficultyLevel), default=DifficultyLevel.INTERMEDIATE)
    estimated_duration_days = Column(Integer)

    is_active = Column(Boolean, default=True)
    is_completed = Column(Boolean, default=False)
    completion_percentage = Column(Float, default=0.0)

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    completed_at = Column(DateTime)

    # Relationships
    user = relationship("User", back_populates="learning_goals")
    sessions = relationship("LearningSession", back_populates="goal")


class LearningSession(Base):
    """Individual learning sessions"""
    __tablename__ = "learning_sessions"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    goal_id = Column(Integer, ForeignKey("learning_goals.id"))

    title = Column(String(255), nullable=False)
    description = Column(Text)
    topic = Column(String(200), index=True)
    subtopics = Column(JSON)  # List of subtopics covered

    status = Column(SQLEnum(SessionStatus), default=SessionStatus.SCHEDULED)
    difficulty_level = Column(SQLEnum(DifficultyLevel))

    # Content
    content_ids = Column(JSON)  # References to content in MongoDB
    practice_problem_ids = Column(JSON)  # References to problems in MongoDB

    # Timing
    scheduled_at = Column(DateTime)
    started_at = Column(DateTime)
    completed_at = Column(DateTime)
    duration_seconds = Column(Integer)

    # Performance metrics
    completion_percentage = Column(Float, default=0.0)
    problems_attempted = Column(Integer, default=0)
    problems_correct = Column(Integer, default=0)
    accuracy = Column(Float)
    engagement_score = Column(Float)  # 0-100

    # Feedback
    user_rating = Column(Integer)  # 1-5 stars
    user_feedback = Column(Text)
    difficulty_rating = Column(Integer)  # 1-5 (too easy to too hard)

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    user = relationship("User", back_populates="sessions")
    goal = relationship("LearningGoal", back_populates="sessions")

    # Indexes for querying
    __table_args__ = (
        Index('ix_sessions_user_topic', 'user_id', 'topic'),
        Index('ix_sessions_status_scheduled', 'status', 'scheduled_at'),
    )


class UserProgress(Base):
    """Track user's progress on specific topics/skills"""
    __tablename__ = "user_progress"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)

    topic = Column(String(200), nullable=False, index=True)
    skill_level = Column(Float, default=0.0)  # 0-100
    mastery_percentage = Column(Float, default=0.0)  # 0-100

    # Statistics
    total_sessions = Column(Integer, default=0)
    total_time_seconds = Column(Integer, default=0)
    last_practiced_at = Column(DateTime)

    # Performance metrics
    average_accuracy = Column(Float)
    problems_solved = Column(Integer, default=0)
    concepts_mastered = Column(Integer, default=0)

    # Spaced repetition
    next_review_date = Column(DateTime)
    review_interval_days = Column(Integer, default=1)
    ease_factor = Column(Float, default=2.5)  # SM-2 algorithm

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    user = relationship("User", back_populates="progress")

    # Unique constraint
    __table_args__ = (
        Index('ix_progress_user_topic', 'user_id', 'topic', unique=True),
    )


class LearningStreak(Base):
    """Track user's learning streaks"""
    __tablename__ = "learning_streaks"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)

    current_streak = Column(Integer, default=0)
    longest_streak = Column(Integer, default=0)

    last_activity_date = Column(DateTime)
    streak_start_date = Column(DateTime)

    total_days_active = Column(Integer, default=0)
    total_sessions = Column(Integer, default=0)
    total_minutes = Column(Integer, default=0)

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    user = relationship("User", back_populates="streaks")


class SpacedRepetitionCard(Base):
    """Spaced repetition flashcards using SM-2 algorithm"""
    __tablename__ = "spaced_repetition_cards"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)

    topic = Column(String(200), nullable=False)
    concept_id = Column(String(100))  # Reference to knowledge graph

    question = Column(Text, nullable=False)
    answer = Column(Text, nullable=False)
    explanation = Column(Text)

    # SM-2 Algorithm parameters
    ease_factor = Column(Float, default=2.5)
    interval_days = Column(Integer, default=1)
    repetition_count = Column(Integer, default=0)

    next_review_date = Column(DateTime, nullable=False)
    last_reviewed_at = Column(DateTime)

    # Performance
    correct_count = Column(Integer, default=0)
    incorrect_count = Column(Integer, default=0)
    total_reviews = Column(Integer, default=0)

    is_active = Column(Boolean, default=True)

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    __table_args__ = (
        Index('ix_sr_cards_user_next_review', 'user_id', 'next_review_date'),
    )


class SkillAssessment(Base):
    """Initial skill assessments and periodic re-assessments"""
    __tablename__ = "skill_assessments"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)

    topic = Column(String(200), nullable=False)
    assessment_type = Column(String(50))  # "initial", "periodic", "final"

    questions_data = Column(JSON)  # List of questions and responses

    score = Column(Float)  # 0-100
    percentile = Column(Float)
    skill_level = Column(SQLEnum(DifficultyLevel))

    # Detailed results
    strengths = Column(JSON)  # List of strong areas
    weaknesses = Column(JSON)  # List of weak areas
    recommendations = Column(JSON)  # Suggested learning paths

    completed_at = Column(DateTime, default=datetime.utcnow)
    created_at = Column(DateTime, default=datetime.utcnow)


class UserFeedback(Base):
    """User feedback and ratings"""
    __tablename__ = "user_feedback"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    session_id = Column(Integer, ForeignKey("learning_sessions.id"))

    feedback_type = Column(String(50))  # "session", "content", "problem", "feature"
    rating = Column(Integer)  # 1-5
    comment = Column(Text)

    tags = Column(JSON)  # ["too_hard", "engaging", "clear", etc.]

    created_at = Column(DateTime, default=datetime.utcnow)
