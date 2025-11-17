# 🎓 Personal Learning & Skill Development Agent

An AI-powered personal learning assistant that delivers personalized 15-20 minute daily micro-learning sessions with intelligent content curation, adaptive practice generation, spaced repetition, and progress tracking.

## 🌟 Features

### 🤖 **Multi-Agent AI System**
- **Goal Analyzer Agent**: Understands your learning goals and identifies skill gaps using LangChain + GPT-4
- **Content Curator Agent**: Finds and ranks high-quality learning content from YouTube, GitHub, Medium, Dev.to
- **Practice Generator Agent**: Creates personalized practice problems (MCQ, coding, short answer) adapted to your skill level
- **Progress Tracker Agent**: Tracks metrics, manages spaced repetition (SM-2 algorithm), and provides analytics

### 🔄 **LangGraph Workflow Orchestration**
- Coordinates all agents in a stateful workflow
- Creates complete learning sessions in 7 steps:
  1. Analyze user state and skill levels
  2. Select optimal topic based on learning path
  3. Curate relevant content
  4. Generate adaptive practice problems
  5. Schedule spaced repetition reviews
  6. Create structured session plan
  7. Save and track progress

### 🎯 **CrewAI Multi-Agent Coordination**
- Parallel content generation for efficiency
- Specialized agents for research, problem creation, explanation writing, and analysis
- Hierarchical task execution

### 📊 **Comprehensive Progress Tracking**
- Real-time skill level tracking (0-100 scale)
- Learning streaks and consistency metrics
- Time-series analytics (InfluxDB)
- Spaced repetition scheduling
- Adaptive difficulty adjustment

### 🗄️ **Multi-Database Architecture**
- **PostgreSQL**: User data, sessions, progress
- **Neo4j**: Knowledge graph (topics, prerequisites, learning paths)
- **MongoDB**: Content, problems, session transcripts
- **Redis**: Caching, session state
- **InfluxDB**: Time-series metrics
- **Pinecone**: Vector embeddings for semantic search

### 🔐 **Authentication & Security**
- JWT-based authentication
- Password hashing with bcrypt
- Role-based access control
- Secure API endpoints

## 🏗️ System Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    USER INTERFACE LAYER                      │
│  Web App (React/Next.js) | Mobile App (React Native)        │
└─────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────┐
│                    API GATEWAY LAYER                         │
│  FastAPI Backend | GraphQL | Rate Limiting | Caching        │
└─────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────┐
│              AGENTIC AI ORCHESTRATION LAYER                  │
│  LangGraph Workflow | CrewAI Multi-Agent System             │
└─────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────┐
│                   ML/AI SERVICES LAYER                       │
│  LLMs (GPT-4, Claude, Gemini) | Embeddings | ML Models      │
└─────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────┐
│                 DATA & KNOWLEDGE LAYER                       │
│  PostgreSQL | Neo4j | MongoDB | Redis | InfluxDB | Pinecone │
└─────────────────────────────────────────────────────────────┘
```

## 🚀 Quick Start

### Prerequisites

- Python 3.11+
- Docker & Docker Compose
- Node.js 18+ (for frontend)
- OpenAI API key
- (Optional) Anthropic, Google API keys

### 1. Clone the Repository

```bash
git clone <repository-url>
cd personal_leaning_system
```

### 2. Environment Setup

```bash
# Copy environment template
cp .env.example .env

# Edit .env and add your API keys
nano .env
```

**Required Environment Variables:**
```env
# Essential
OPENAI_API_KEY=your-openai-key
PINECONE_API_KEY=your-pinecone-key
SECRET_KEY=your-secret-key-32-chars
JWT_SECRET_KEY=your-jwt-secret-32-chars
POSTGRES_PASSWORD=strong-password
NEO4J_PASSWORD=strong-password
INFLUXDB_TOKEN=your-token

# Optional for enhanced features
YOUTUBE_API_KEY=your-youtube-key
GITHUB_TOKEN=your-github-token
ANTHROPIC_API_KEY=your-anthropic-key
```

### 3. Start Infrastructure Services

```bash
# Start all databases and services using Docker Compose
docker-compose up -d postgres neo4j mongodb redis influxdb weaviate
```

**Verify Services:**
```bash
# Check all services are running
docker-compose ps

# Expected output: postgres, neo4j, mongodb, redis, influxdb, weaviate all "Up"
```

### 4. Initialize Databases

```bash
# Install Python dependencies
pip install -r requirements.txt

# Run database migrations and initialization
python scripts/init_databases.py
```

### 5. Start the Backend API

```bash
cd backend
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

**API Documentation:** http://localhost:8000/api/docs

### 6. (Optional) Start Frontend

```bash
cd frontend
npm install
npm run dev
```

**Frontend:** http://localhost:3000

## 📖 API Usage

### Authentication

**Register a new user:**
```bash
curl -X POST "http://localhost:8000/api/auth/register" \
  -H "Content-Type: application/json" \
  -d '{
    "email": "user@example.com",
    "username": "learner123",
    "password": "SecurePass123!",
    "full_name": "John Doe"
  }'
```

**Login:**
```bash
curl -X POST "http://localhost:8000/api/auth/login" \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "username=user@example.com&password=SecurePass123!"
```

Response:
```json
{
  "access_token": "eyJhbGc...",
  "refresh_token": "eyJhbGc...",
  "token_type": "bearer"
}
```

### Create Learning Session

```bash
curl -X POST "http://localhost:8000/api/sessions/create" \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "duration_minutes": 20
  }'
```

Response:
```json
{
  "session_id": 1,
  "topic": "Python Basics",
  "subtopics": ["Variables", "Data Types"],
  "difficulty": "beginner",
  "session_plan": {
    "total_duration_minutes": 20,
    "flow": [
      {
        "step": 1,
        "activity": "Introduction",
        "duration_minutes": 1
      },
      {
        "step": 2,
        "activity": "Content Review",
        "duration_minutes": 8,
        "content_items": [...]
      },
      {
        "step": 3,
        "activity": "Practice Problems",
        "duration_minutes": 8,
        "problems": [...]
      },
      {
        "step": 4,
        "activity": "Spaced Repetition Review",
        "duration_minutes": 2
      },
      {
        "step": 5,
        "activity": "Wrap-up",
        "duration_minutes": 1
      }
    ]
  },
  "content": [...],
  "problems": [...],
  "review_cards": [...]
}
```

### Complete a Session

```bash
curl -X POST "http://localhost:8000/api/sessions/1/complete" \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "duration_seconds": 1200,
    "problems_attempted": 5,
    "problems_correct": 4,
    "user_rating": 5,
    "user_feedback": "Great session!"
  }'
```

### Get Progress Metrics

```bash
curl "http://localhost:8000/api/progress/metrics" \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN"
```

Response:
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
    ...
  ]
}
```

### Generate Practice Problems

```bash
curl -X POST "http://localhost:8000/api/content/problems/generate" \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "topic": "Data Structures",
    "difficulty": "intermediate",
    "problem_types": ["coding", "multiple_choice"],
    "count": 5
  }'
```

## 🧠 Agent System Details

### Goal Analyzer Agent

**Purpose:** Understands user's learning goals and creates personalized learning paths

**Technologies:**
- LangChain for agent orchestration
- OpenAI GPT-4 for goal parsing
- Neo4j for knowledge graph traversal
- XGBoost for skill level prediction

**Key Methods:**
- `analyze_goal()`: Analyzes learning goal and creates action plan
- `assess_skill_level()`: Evaluates current skill level (0-100)
- `estimate_learning_time()`: Predicts time needed to reach target

### Content Curator Agent

**Purpose:** Finds and ranks high-quality learning content

**Sources:**
- YouTube (videos with transcripts)
- GitHub (repositories, code examples)
- Medium (articles)
- Dev.to (tutorials)
- Stack Overflow (Q&A)

**Key Features:**
- Parallel content fetching
- AI-powered quality ranking
- Semantic search with Pinecone
- Content embeddings for similarity

### Practice Generator Agent

**Purpose:** Creates personalized practice problems

**Problem Types:**
- Multiple Choice Questions
- Coding Problems (with test cases)
- Short Answer Questions
- Debugging Challenges
- Code Review Tasks

**Key Features:**
- Adaptive difficulty based on user skill
- AI-powered answer evaluation
- Detailed feedback and explanations
- Progress-based problem selection

### Progress Tracker Agent

**Purpose:** Tracks learning progress and manages spaced repetition

**Metrics Tracked:**
- Skill level per topic (0-100)
- Mastery percentage
- Learning streaks
- Time spent
- Accuracy trends
- Engagement scores

**Spaced Repetition:**
- SM-2 algorithm implementation
- Automatic review scheduling
- Ease factor adjustment
- Forgetting curve prediction

## 🗄️ Database Schemas

### PostgreSQL (Relational Data)

**Tables:**
- `users`: User accounts and preferences
- `learning_goals`: User's learning objectives
- `learning_sessions`: Session history and results
- `user_progress`: Skill levels and mastery per topic
- `learning_streaks`: Consistency tracking
- `spaced_repetition_cards`: Flashcards for review
- `skill_assessments`: Initial and periodic assessments
- `user_feedback`: Ratings and comments

### Neo4j (Knowledge Graph)

**Nodes:**
- `Topic`: Learning topics (e.g., "Python Basics", "Machine Learning")
- `Concept`: Specific concepts within topics
- `Skill`: Required skills
- `User`: User knowledge state

**Relationships:**
- `PREREQUISITE_FOR`: Topic prerequisites
- `BELONGS_TO`: Concepts belong to topics
- `RELATED_TO`: Related topics
- `KNOWS`: User knows topic (with mastery level)

### MongoDB (Documents)

**Collections:**
- `learning_content`: Curated articles, videos, tutorials
- `practice_problems`: Generated practice problems
- `session_transcripts`: Complete session records
- `user_notes`: User-generated notes
- `generated_explanations`: AI-generated explanations

### InfluxDB (Time-Series)

**Measurements:**
- `learning_session`: Session metrics over time
- `skill_progression`: Skill level changes
- `engagement`: Engagement scores

## 📊 Monitoring & Analytics

### Health Checks

```bash
# Backend health
curl http://localhost:8000/health

# Database health
curl http://localhost:8000/api/system/health/databases
```

### Metrics Endpoints

- **User Metrics**: `/api/progress/metrics`
- **Topic Progress**: `/api/progress/topics/{topic}`
- **Learning Analytics**: `/api/progress/analytics?days=30`
- **Streak Info**: `/api/progress/streak`

### Logs

```bash
# View backend logs
docker-compose logs -f backend

# View database logs
docker-compose logs -f postgres neo4j mongodb
```

## 🧪 Testing

```bash
# Run unit tests
pytest tests/unit -v

# Run integration tests
pytest tests/integration -v

# Run with coverage
pytest --cov=backend --cov-report=html
```

## 🔧 Configuration

### Adjusting Session Parameters

Edit `backend/core/config.py`:

```python
# Default session duration
DEFAULT_SESSION_DURATION_MINUTES = 20

# Content items per session
MAX_CONTENT_ITEMS = 5

# Problems per session
PROBLEMS_PER_SESSION = 5

# Spaced repetition parameters
SM2_INITIAL_EASE_FACTOR = 2.5
SM2_MIN_EASE_FACTOR = 1.3
```

### Adding New Content Sources

Implement a new method in `backend/agents/content_curator_agent.py`:

```python
async def _search_new_source(self, topic: str, difficulty: str) -> List[LearningContent]:
    # Your implementation
    pass
```

### Custom ML Models

Place trained models in `backend/ml/models/`:
- `skill_gap_predictor.json` (XGBoost)
- `retention_model.pkl` (LSTM)
- `recommendation_engine.pkl` (Collaborative Filtering)

## 🚢 Deployment

### Docker Production Build

```bash
# Build production images
docker-compose -f docker-compose.prod.yml build

# Start production stack
docker-compose -f docker-compose.prod.yml up -d
```

### Environment Variables for Production

```env
ENVIRONMENT=production
DEBUG=false
API_WORKERS=4

# Use strong secrets
SECRET_KEY=<generate-with-openssl-rand-hex-32>
JWT_SECRET_KEY=<generate-with-openssl-rand-hex-32>

# Production databases
DATABASE_URL=postgresql+asyncpg://user:pass@prod-db:5432/db
REDIS_URL=redis://prod-redis:6379/0

# Monitoring
SENTRY_DSN=https://your-sentry-dsn
LOG_LEVEL=WARNING
```

### Scaling

**Horizontal Scaling:**
```bash
# Scale backend workers
docker-compose up -d --scale backend=4

# Scale Celery workers
docker-compose up -d --scale celery_worker=3
```

**Database Scaling:**
- PostgreSQL: Use read replicas
- Neo4j: Enable clustering
- MongoDB: Sharding for large content databases
- Redis: Redis Cluster for caching
- Pinecone: Scales automatically

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch: `git checkout -b feature/amazing-feature`
3. Commit changes: `git commit -m 'Add amazing feature'`
4. Push to branch: `git push origin feature/amazing-feature`
5. Open a Pull Request

## 📝 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🙏 Acknowledgments

- OpenAI for GPT-4 and embeddings
- LangChain for agent orchestration
- LangGraph for workflow management
- CrewAI for multi-agent coordination
- FastAPI for the excellent web framework

## 📧 Support

- **Documentation**: [Link to full docs]
- **Issues**: [GitHub Issues](https://github.com/your-repo/issues)
- **Discord**: [Join our community]
- **Email**: support@yourapp.com

## 🗺️ Roadmap

- [ ] Mobile app (React Native)
- [ ] Voice-based learning sessions
- [ ] Collaborative learning (study groups)
- [ ] Integration with LeetCode/HackerRank APIs
- [ ] Gamification (badges, leaderboards)
- [ ] Multi-language support
- [ ] Offline mode
- [ ] AR/VR learning experiences

---

**Built with ❤️ for lifelong learners**
