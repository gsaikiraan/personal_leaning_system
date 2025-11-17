"""
Pydantic schemas for API request/response models
"""
from datetime import datetime
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, EmailStr, Field


# Auth Schemas
class UserRegister(BaseModel):
    email: EmailStr
    username: str = Field(..., min_length=3, max_length=50)
    password: str = Field(..., min_length=8)
    full_name: Optional[str] = None


class UserLogin(BaseModel):
    email: EmailStr
    password: str


class Token(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class TokenData(BaseModel):
    user_id: Optional[int] = None


# User Schemas
class UserBase(BaseModel):
    email: EmailStr
    username: str
    full_name: Optional[str] = None


class UserResponse(UserBase):
    id: int
    role: str
    is_active: bool
    created_at: datetime
    last_login_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class UserUpdate(BaseModel):
    full_name: Optional[str] = None
    timezone: Optional[str] = None
    preferred_session_time: Optional[str] = None
    daily_learning_goal_minutes: Optional[int] = None


# Learning Goal Schemas
class LearningGoalCreate(BaseModel):
    title: str
    description: Optional[str] = None
    category: Optional[str] = None
    target_skills: List[str] = []
    estimated_duration_days: Optional[int] = None


class LearningGoalResponse(LearningGoalCreate):
    id: int
    user_id: int
    is_active: bool
    completion_percentage: float
    created_at: datetime

    class Config:
        from_attributes = True


# Learning Session Schemas
class SessionCreate(BaseModel):
    goal_id: Optional[int] = None
    duration_minutes: int = Field(default=20, ge=5, le=60)


class SessionResponse(BaseModel):
    id: int
    user_id: int
    title: str
    topic: str
    status: str
    difficulty_level: Optional[str] = None
    scheduled_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    duration_seconds: Optional[int] = None
    accuracy: Optional[float] = None
    problems_attempted: int
    problems_correct: int

    class Config:
        from_attributes = True


class SessionDetailResponse(SessionResponse):
    description: Optional[str] = None
    subtopics: Optional[List[str]] = None
    content_ids: Optional[List[str]] = None
    practice_problem_ids: Optional[List[str]] = None
    user_rating: Optional[int] = None
    user_feedback: Optional[str] = None


class SessionComplete(BaseModel):
    duration_seconds: int
    problems_attempted: int
    problems_correct: int
    user_rating: Optional[int] = Field(None, ge=1, le=5)
    user_feedback: Optional[str] = None


# Progress Schemas
class ProgressResponse(BaseModel):
    topic: str
    skill_level: float
    mastery_percentage: float
    total_sessions: int
    total_time_hours: float
    average_accuracy: Optional[float] = None
    last_practiced_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class UserMetricsResponse(BaseModel):
    topics_studied: int
    average_skill_level: float
    total_sessions: int
    total_time_hours: float
    current_streak: int
    topics: List[Dict[str, Any]]


# Content Schemas
class ContentRequest(BaseModel):
    topic: str
    difficulty: str = "intermediate"
    content_types: List[str] = ["article", "video", "tutorial"]
    max_items: int = 5


class ContentResponse(BaseModel):
    title: str
    description: str
    url: Optional[str] = None
    content_type: str
    source: str
    difficulty: str
    author: Optional[str] = None
    duration_minutes: Optional[int] = None
    quality_score: float


# Practice Problem Schemas
class ProblemRequest(BaseModel):
    topic: str
    subtopic: Optional[str] = None
    difficulty: str = "intermediate"
    problem_types: List[str] = ["multiple_choice", "short_answer"]
    count: int = Field(default=5, ge=1, le=20)


class ProblemResponse(BaseModel):
    id: str
    question: str
    problem_type: str
    difficulty: str
    hints: List[str] = []
    options: Optional[List[str]] = None  # For MCQ


class SubmitAnswer(BaseModel):
    problem_id: str
    answer: Any  # String or code
    time_taken_seconds: int


class AnswerEvaluation(BaseModel):
    is_correct: bool
    score: float
    feedback: str
    correct_answer: Optional[str] = None
    explanation: str


# Session Plan Schemas
class SessionPlanRequest(BaseModel):
    user_id: int
    goal_id: Optional[int] = None
    duration_minutes: int = 20


class SessionPlanResponse(BaseModel):
    session_id: int
    topic: str
    subtopics: List[str]
    difficulty: str
    session_plan: Dict[str, Any]
    content: List[Dict[str, Any]]
    problems: List[Dict[str, Any]]
    review_cards: List[Dict[str, Any]]
    next_recommendations: Dict[str, Any]


# Analytics Schemas
class AnalyticsRequest(BaseModel):
    days: int = Field(default=30, ge=1, le=365)


class AnalyticsResponse(BaseModel):
    period_days: int
    daily_accuracy: List[float]
    daily_time_minutes: List[float]
    dates: List[str]
    total_sessions: int
    average_accuracy: float
    total_learning_time_hours: float
