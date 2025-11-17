"""
MongoDB document schemas for unstructured data
Using Pydantic for validation
"""
from datetime import datetime
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field, HttpUrl
from enum import Enum


class ContentType(str, Enum):
    """Types of learning content"""
    ARTICLE = "article"
    VIDEO = "video"
    DOCUMENTATION = "documentation"
    TUTORIAL = "tutorial"
    COURSE = "course"
    BOOK = "book"
    CODE_EXAMPLE = "code_example"
    INTERACTIVE = "interactive"


class ContentSource(str, Enum):
    """Sources of content"""
    YOUTUBE = "youtube"
    GITHUB = "github"
    MEDIUM = "medium"
    DEV_TO = "dev_to"
    STACK_OVERFLOW = "stack_overflow"
    ARXIV = "arxiv"
    COURSERA = "coursera"
    UDEMY = "udemy"
    CUSTOM = "custom"


class DifficultyLevel(str, Enum):
    """Content difficulty levels"""
    BEGINNER = "beginner"
    INTERMEDIATE = "intermediate"
    ADVANCED = "advanced"
    EXPERT = "expert"


class LearningContent(BaseModel):
    """Learning content document"""
    id: Optional[str] = Field(default=None, alias="_id")
    title: str
    description: str
    content_type: ContentType
    source: ContentSource

    url: Optional[HttpUrl] = None
    content_text: Optional[str] = None  # Extracted text content
    content_html: Optional[str] = None

    topic: str
    subtopics: List[str] = []
    difficulty: DifficultyLevel

    # Metadata
    author: Optional[str] = None
    publish_date: Optional[datetime] = None
    duration_minutes: Optional[int] = None  # For videos/courses
    word_count: Optional[int] = None

    # Content quality metrics
    quality_score: float = 0.0  # 0-100
    engagement_score: float = 0.0
    relevance_score: float = 0.0

    # External metrics
    views: Optional[int] = None
    likes: Optional[int] = None
    rating: Optional[float] = None

    # Embeddings for semantic search
    embedding: Optional[List[float]] = None
    embedding_model: Optional[str] = None

    # Tags and keywords
    tags: List[str] = []
    keywords: List[str] = []

    # Learning objectives
    learning_objectives: List[str] = []
    prerequisites: List[str] = []

    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    class Config:
        populate_by_name = True


class ProblemType(str, Enum):
    """Types of practice problems"""
    MULTIPLE_CHOICE = "multiple_choice"
    CODING = "coding"
    SHORT_ANSWER = "short_answer"
    ESSAY = "essay"
    FILL_BLANK = "fill_blank"
    TRUE_FALSE = "true_false"
    DEBUGGING = "debugging"
    CODE_REVIEW = "code_review"


class PracticeProblem(BaseModel):
    """Practice problem document"""
    id: Optional[str] = Field(default=None, alias="_id")

    topic: str
    subtopic: Optional[str] = None
    difficulty: DifficultyLevel
    problem_type: ProblemType

    # Problem content
    question: str
    description: Optional[str] = None
    hints: List[str] = []

    # For multiple choice
    options: Optional[List[str]] = None
    correct_answer: str

    # For coding problems
    test_cases: Optional[List[Dict[str, Any]]] = None
    starter_code: Optional[str] = None
    solution_code: Optional[str] = None

    # Explanation
    explanation: str
    solution_walkthrough: Optional[str] = None

    # Related concepts
    concepts: List[str] = []
    skills_tested: List[str] = []

    # Problem metrics
    difficulty_rating: float = 0.0  # 0-10 based on user data
    average_solve_time_seconds: Optional[int] = None
    success_rate: float = 0.0  # percentage

    # Usage stats
    times_attempted: int = 0
    times_solved: int = 0

    # Embeddings
    embedding: Optional[List[float]] = None

    # Tags
    tags: List[str] = []
    companies: List[str] = []  # For interview prep

    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    class Config:
        populate_by_name = True


class UserResponse(BaseModel):
    """User's response to a problem"""
    problem_id: str
    user_answer: Any  # String or code
    is_correct: bool
    time_taken_seconds: int
    hints_used: int


class SessionTranscript(BaseModel):
    """Complete transcript of a learning session"""
    id: Optional[str] = Field(default=None, alias="_id")
    session_id: int  # References PostgreSQL session
    user_id: int

    # Content delivered
    content_items: List[Dict[str, Any]] = []
    problems_presented: List[str] = []  # Problem IDs

    # User interactions
    user_responses: List[UserResponse] = []
    notes: Optional[str] = None
    bookmarks: List[str] = []  # Content IDs

    # Agent interactions
    agent_conversations: List[Dict[str, str]] = []  # {role, message, timestamp}

    # Session flow
    session_flow: List[Dict[str, Any]] = []  # Track what happened when

    created_at: datetime = Field(default_factory=datetime.utcnow)

    class Config:
        populate_by_name = True


class UserNote(BaseModel):
    """User-generated notes and annotations"""
    id: Optional[str] = Field(default=None, alias="_id")
    user_id: int
    topic: str

    title: str
    content: str
    markdown_content: Optional[str] = None

    # Related items
    related_content_ids: List[str] = []
    related_problem_ids: List[str] = []

    tags: List[str] = []
    is_public: bool = False

    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    class Config:
        populate_by_name = True


class GeneratedExplanation(BaseModel):
    """AI-generated explanations for concepts"""
    id: Optional[str] = Field(default=None, alias="_id")
    concept_id: str
    topic: str

    question: str
    explanation: str

    # Generation metadata
    model_used: str
    generation_timestamp: datetime = Field(default_factory=datetime.utcnow)

    # Quality metrics
    quality_score: float = 0.0
    user_ratings: List[int] = []

    embedding: Optional[List[float]] = None

    class Config:
        populate_by_name = True


# Helper functions for MongoDB operations

def learning_content_to_dict(content: LearningContent) -> dict:
    """Convert LearningContent to MongoDB document"""
    return content.model_dump(by_alias=True, exclude_none=True)


def practice_problem_to_dict(problem: PracticeProblem) -> dict:
    """Convert PracticeProblem to MongoDB document"""
    return problem.model_dump(by_alias=True, exclude_none=True)


def session_transcript_to_dict(transcript: SessionTranscript) -> dict:
    """Convert SessionTranscript to MongoDB document"""
    return transcript.model_dump(by_alias=True, exclude_none=True)
