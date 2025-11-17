# API Documentation

## Base URL

```
http://localhost:8000/api
```

## Authentication

All authenticated endpoints require a Bearer token in the Authorization header:

```
Authorization: Bearer <access_token>
```

## Endpoints

### Authentication

#### POST /auth/register
Register a new user.

**Request Body:**
```json
{
  "email": "user@example.com",
  "username": "learner123",
  "password": "SecurePass123!",
  "full_name": "John Doe"
}
```

**Response:** `201 Created`
```json
{
  "access_token": "eyJhbGc...",
  "refresh_token": "eyJhbGc...",
  "token_type": "bearer"
}
```

#### POST /auth/login
Login with email and password.

**Form Data:**
```
username=user@example.com
password=SecurePass123!
```

**Response:** `200 OK`
```json
{
  "access_token": "eyJhbGc...",
  "refresh_token": "eyJhbGc...",
  "token_type": "bearer"
}
```

#### POST /auth/refresh
Refresh access token.

**Request Body:**
```json
{
  "refresh_token": "eyJhbGc..."
}
```

**Response:** `200 OK`
```json
{
  "access_token": "eyJhbGc...",
  "refresh_token": "eyJhbGc...",
  "token_type": "bearer"
}
```

### Users

#### GET /users/me
Get current user profile.

**Headers:** `Authorization: Bearer <token>`

**Response:** `200 OK`
```json
{
  "id": 1,
  "email": "user@example.com",
  "username": "learner123",
  "full_name": "John Doe",
  "role": "user",
  "is_active": true,
  "created_at": "2024-01-15T10:30:00Z",
  "last_login_at": "2024-01-20T14:22:00Z"
}
```

#### PUT /users/me
Update user profile.

**Headers:** `Authorization: Bearer <token>`

**Request Body:**
```json
{
  "full_name": "John Smith",
  "timezone": "America/New_York",
  "preferred_session_time": "09:00",
  "daily_learning_goal_minutes": 30
}
```

**Response:** `200 OK`

### Learning Sessions

#### POST /sessions/create
Create a personalized learning session.

**Headers:** `Authorization: Bearer <token>`

**Request Body:**
```json
{
  "goal_id": 1,
  "duration_minutes": 20
}
```

**Response:** `200 OK`
```json
{
  "session_id": 42,
  "topic": "Python Basics",
  "subtopics": ["Variables", "Data Types", "Functions"],
  "difficulty": "beginner",
  "session_plan": {
    "total_duration_minutes": 20,
    "time_allocation": {
      "intro": 1,
      "content_review": 8,
      "practice": 8,
      "spaced_repetition": 2,
      "wrap_up": 1
    },
    "flow": [...]
  },
  "content": [
    {
      "title": "Python Variables Explained",
      "description": "...",
      "url": "https://...",
      "type": "video",
      "source": "youtube",
      "duration_minutes": 10
    }
  ],
  "problems": [
    {
      "id": "prob_123",
      "question": "What is the output of print(type(42))?",
      "type": "multiple_choice",
      "difficulty": "beginner",
      "hints": ["Think about Python's type system"]
    }
  ],
  "review_cards": [...],
  "next_recommendations": {...}
}
```

#### GET /sessions
Get user's learning sessions.

**Headers:** `Authorization: Bearer <token>`

**Query Parameters:**
- `skip` (optional): Number of records to skip (default: 0)
- `limit` (optional): Max records to return (default: 20)

**Response:** `200 OK`
```json
[
  {
    "id": 42,
    "user_id": 1,
    "title": "Daily Session: Python Basics",
    "topic": "Python Basics",
    "status": "completed",
    "difficulty_level": "beginner",
    "scheduled_at": "2024-01-20T09:00:00Z",
    "completed_at": "2024-01-20T09:22:00Z",
    "duration_seconds": 1320,
    "accuracy": 85.0,
    "problems_attempted": 5,
    "problems_correct": 4
  }
]
```

#### GET /sessions/{session_id}
Get detailed session information.

**Headers:** `Authorization: Bearer <token>`

**Response:** `200 OK`

#### POST /sessions/{session_id}/complete
Mark session as completed and update metrics.

**Headers:** `Authorization: Bearer <token>`

**Request Body:**
```json
{
  "duration_seconds": 1200,
  "problems_attempted": 5,
  "problems_correct": 4,
  "user_rating": 5,
  "user_feedback": "Great session, learned a lot!"
}
```

**Response:** `200 OK`

### Progress & Analytics

#### GET /progress/metrics
Get comprehensive user metrics.

**Headers:** `Authorization: Bearer <token>`

**Response:** `200 OK`
```json
{
  "topics_studied": 5,
  "average_skill_level": 65.5,
  "total_sessions": 15,
  "total_time_hours": 5.2,
  "current_streak": 7,
  "topics": [
    {
      "topic": "Python Basics",
      "skill_level": 75.0,
      "mastery": 68.5
    },
    {
      "topic": "Data Structures",
      "skill_level": 60.0,
      "mastery": 55.2
    }
  ]
}
```

#### GET /progress/topics/{topic}
Get progress for a specific topic.

**Headers:** `Authorization: Bearer <token>`

**Response:** `200 OK`
```json
{
  "topic": "Python Basics",
  "skill_level": 75.0,
  "mastery_percentage": 68.5,
  "total_sessions": 8,
  "total_time_hours": 2.7,
  "average_accuracy": 82.5,
  "last_practiced_at": "2024-01-20T09:22:00Z"
}
```

#### GET /progress/analytics
Get time-series learning analytics.

**Headers:** `Authorization: Bearer <token>`

**Query Parameters:**
- `days` (optional): Number of days to analyze (default: 30)

**Response:** `200 OK`
```json
{
  "period_days": 30,
  "daily_accuracy": [85.0, 90.0, 78.5, ...],
  "daily_time_minutes": [20, 25, 15, ...],
  "dates": ["2024-01-01", "2024-01-02", ...]
}
```

#### GET /progress/streak
Get learning streak information.

**Headers:** `Authorization: Bearer <token>`

**Response:** `200 OK`
```json
{
  "current_streak": 7,
  "longest_streak": 15,
  "total_days_active": 45,
  "total_sessions": 52,
  "total_minutes": 1040
}
```

#### GET /progress/reviews/due
Get spaced repetition cards due for review.

**Headers:** `Authorization: Bearer <token>`

**Response:** `200 OK`
```json
{
  "count": 5,
  "cards": [
    {
      "id": 1,
      "topic": "Python Basics",
      "question": "What is a variable?",
      "next_review_date": "2024-01-20T10:00:00Z"
    }
  ]
}
```

### Content & Problems

#### POST /content/curate
Curate learning content for a topic.

**Headers:** `Authorization: Bearer <token>`

**Request Body:**
```json
{
  "topic": "Machine Learning",
  "difficulty": "intermediate",
  "content_types": ["article", "video", "tutorial"],
  "max_items": 5
}
```

**Response:** `200 OK`
```json
[
  {
    "title": "Introduction to Machine Learning",
    "description": "...",
    "url": "https://...",
    "content_type": "video",
    "source": "youtube",
    "difficulty": "intermediate",
    "author": "Tech Educator",
    "duration_minutes": 15,
    "quality_score": 92.5
  }
]
```

#### POST /content/problems/generate
Generate practice problems using AI.

**Headers:** `Authorization: Bearer <token>`

**Request Body:**
```json
{
  "topic": "Data Structures",
  "subtopic": "Arrays",
  "difficulty": "intermediate",
  "problem_types": ["coding", "multiple_choice"],
  "count": 5
}
```

**Response:** `200 OK`
```json
[
  {
    "id": "prob_456",
    "question": "Write a function to reverse an array in-place",
    "problem_type": "coding",
    "difficulty": "intermediate",
    "hints": [
      "Use two pointers",
      "Swap elements from both ends"
    ]
  }
]
```

#### POST /content/problems/evaluate
Evaluate user's answer to a problem.

**Headers:** `Authorization: Bearer <token>`

**Request Body:**
```json
{
  "problem_id": "prob_456",
  "answer": "def reverse_array(arr):\\n    left, right = 0, len(arr)-1\\n    ...",
  "time_taken_seconds": 180
}
```

**Response:** `200 OK`
```json
{
  "is_correct": true,
  "score": 95.0,
  "feedback": "Excellent solution! Your implementation is efficient with O(n) time and O(1) space complexity.",
  "explanation": "..."
}
```

#### GET /content/search
Semantic search for learning content.

**Headers:** `Authorization: Bearer <token>`

**Query Parameters:**
- `query`: Search query (required)
- `topic` (optional): Filter by topic
- `difficulty` (optional): Filter by difficulty
- `limit` (optional): Max results (default: 5)

**Response:** `200 OK`
```json
{
  "results": [...]
}
```

## Error Responses

### 400 Bad Request
```json
{
  "detail": "Invalid request data"
}
```

### 401 Unauthorized
```json
{
  "detail": "Could not validate credentials"
}
```

### 404 Not Found
```json
{
  "detail": "Resource not found"
}
```

### 500 Internal Server Error
```json
{
  "detail": "Internal server error",
  "type": "server_error"
}
```

## Rate Limiting

- **Anonymous requests**: 60 requests per hour
- **Authenticated requests**: 1000 requests per hour
- **AI-powered endpoints** (generate, evaluate): 100 requests per hour

## Pagination

List endpoints support pagination:

**Query Parameters:**
- `skip`: Number of records to skip (default: 0)
- `limit`: Maximum records to return (default: 20, max: 100)

**Response Headers:**
- `X-Total-Count`: Total number of records
- `X-Page`: Current page number
- `X-Per-Page`: Records per page

## Webhooks

Configure webhooks to receive real-time updates:

### Events
- `session.completed`: When a user completes a session
- `goal.achieved`: When a learning goal is achieved
- `streak.milestone`: When streak reaches a milestone (7, 30, 100 days)
- `skill.leveled_up`: When skill level increases significantly

Configure webhooks in user settings or via API:

```bash
POST /api/webhooks
{
  "url": "https://your-app.com/webhook",
  "events": ["session.completed", "goal.achieved"],
  "secret": "webhook_secret_key"
}
```
