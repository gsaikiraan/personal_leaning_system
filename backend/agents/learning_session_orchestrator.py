"""
Learning Session Orchestrator using LangGraph
Coordinates all agents to create and deliver personalized learning sessions
"""
from typing import Dict, List, Any, Optional, TypedDict, Annotated
from datetime import datetime
import operator
from langgraph.graph import StateGraph, END
from langchain_openai import ChatOpenAI
from sqlalchemy.ext.asyncio import AsyncSession

from backend.core.config import settings
from backend.agents.goal_analyzer_agent import GoalAnalyzerAgent
from backend.agents.content_curator_agent import ContentCuratorAgent
from backend.agents.practice_generator_agent import PracticeGeneratorAgent
from backend.agents.progress_tracker_agent import ProgressTrackerAgent
from backend.db.models import LearningSession, LearningGoal, SessionStatus


class LearningSessionState(TypedDict):
    """State that flows through the LangGraph workflow"""

    # Input
    user_id: int
    goal_id: Optional[int]
    session_duration_minutes: int

    # User context
    user_skill_levels: Dict[str, float]
    learning_goals: List[str]
    recent_performance: Dict[str, List[bool]]

    # Session planning
    selected_topic: str
    selected_subtopics: List[str]
    difficulty_level: str

    # Content
    curated_content: List[Dict[str, Any]]
    practice_problems: List[Dict[str, Any]]
    spaced_repetition_cards: List[Dict[str, Any]]

    # Session flow
    session_plan: Dict[str, Any]
    session_id: int

    # Results
    session_completed: bool
    next_session_recommendations: Dict[str, Any]

    # Agent messages (for debugging/logging)
    messages: Annotated[List[str], operator.add]


class LearningSessionOrchestrator:
    """
    Orchestrates the entire learning session workflow using LangGraph
    """

    def __init__(
        self,
        db_session: AsyncSession,
        neo4j_session,
        mongodb_db,
        redis_client,
        influxdb_client
    ):
        self.db = db_session
        self.neo4j = neo4j_session
        self.mongodb = mongodb_db
        self.redis = redis_client
        self.influx = influxdb_client

        # Initialize all agents
        self.goal_analyzer = GoalAnalyzerAgent(db_session, neo4j_session)
        self.content_curator = ContentCuratorAgent(db_session, mongodb_db)
        self.practice_generator = PracticeGeneratorAgent(db_session, mongodb_db)
        self.progress_tracker = ProgressTrackerAgent(db_session, influxdb_client, redis_client)

        # Initialize LLM for coordination decisions
        self.coordinator_llm = ChatOpenAI(
            model="gpt-4-turbo-preview",
            temperature=0.3,
            api_key=settings.OPENAI_API_KEY
        )

        # Build the workflow graph
        self.workflow = self._build_workflow()

    def _build_workflow(self) -> StateGraph:
        """Build the LangGraph workflow for learning sessions"""

        workflow = StateGraph(LearningSessionState)

        # Add nodes (each represents a step in the workflow)
        workflow.add_node("analyze_user_state", self._analyze_user_state)
        workflow.add_node("select_topic", self._select_topic)
        workflow.add_node("curate_content", self._curate_content)
        workflow.add_node("generate_problems", self._generate_problems)
        workflow.add_node("get_spaced_repetition", self._get_spaced_repetition)
        workflow.add_node("create_session_plan", self._create_session_plan)
        workflow.add_node("save_session", self._save_session)

        # Define the flow
        workflow.set_entry_point("analyze_user_state")

        workflow.add_edge("analyze_user_state", "select_topic")
        workflow.add_edge("select_topic", "curate_content")
        workflow.add_edge("curate_content", "generate_problems")
        workflow.add_edge("generate_problems", "get_spaced_repetition")
        workflow.add_edge("get_spaced_repetition", "create_session_plan")
        workflow.add_edge("create_session_plan", "save_session")
        workflow.add_edge("save_session", END)

        return workflow.compile()

    async def create_learning_session(
        self,
        user_id: int,
        goal_id: Optional[int] = None,
        session_duration_minutes: int = 20
    ) -> Dict[str, Any]:
        """
        Main entry point: Create a personalized learning session

        Args:
            user_id: User ID
            goal_id: Optional specific learning goal
            session_duration_minutes: Desired session duration

        Returns:
            Complete learning session plan
        """

        # Initialize state
        initial_state = LearningSessionState(
            user_id=user_id,
            goal_id=goal_id,
            session_duration_minutes=session_duration_minutes,
            user_skill_levels={},
            learning_goals=[],
            recent_performance={},
            selected_topic="",
            selected_subtopics=[],
            difficulty_level="intermediate",
            curated_content=[],
            practice_problems=[],
            spaced_repetition_cards=[],
            session_plan={},
            session_id=0,
            session_completed=False,
            next_session_recommendations={},
            messages=[]
        )

        # Run the workflow
        final_state = await self.workflow.ainvoke(initial_state)

        return {
            "session_id": final_state["session_id"],
            "topic": final_state["selected_topic"],
            "subtopics": final_state["selected_subtopics"],
            "difficulty": final_state["difficulty_level"],
            "session_plan": final_state["session_plan"],
            "content": final_state["curated_content"],
            "problems": final_state["practice_problems"],
            "review_cards": final_state["spaced_repetition_cards"],
            "next_recommendations": final_state["next_session_recommendations"]
        }

    async def _analyze_user_state(self, state: LearningSessionState) -> LearningSessionState:
        """Step 1: Analyze user's current state and context"""

        state["messages"].append("Analyzing user state...")

        user_id = state["user_id"]

        # Get user's current skill levels across topics
        metrics = await self.progress_tracker.get_user_metrics(user_id)
        state["user_skill_levels"] = {
            topic["topic"]: topic["skill_level"]
            for topic in metrics.get("topics", [])
        }

        # Get learning goals
        from sqlalchemy import select
        goals_query = select(LearningGoal).where(
            LearningGoal.user_id == user_id,
            LearningGoal.is_active == True
        )
        result = await self.db.execute(goals_query)
        goals = result.scalars().all()
        state["learning_goals"] = [goal.title for goal in goals]

        # Get recent performance for adaptive difficulty
        # Simplified: get last 5 sessions per topic
        state["recent_performance"] = {}  # topic -> [bool, bool, ...]

        state["messages"].append(f"Found {len(state['learning_goals'])} active goals")
        state["messages"].append(f"Skill levels: {state['user_skill_levels']}")

        return state

    async def _select_topic(self, state: LearningSessionState) -> LearningSessionState:
        """Step 2: Intelligently select topic for this session"""

        state["messages"].append("Selecting optimal topic...")

        user_id = state["user_id"]
        goal_id = state["goal_id"]

        if goal_id:
            # Get specific goal
            from sqlalchemy import select
            goal_query = select(LearningGoal).where(LearningGoal.id == goal_id)
            result = await self.db.execute(goal_query)
            goal = result.scalar_one()

            # Use goal analyzer to determine next topic
            analysis = await self.goal_analyzer.analyze_goal(
                user_id,
                goal.description,
                {"timeline": goal.estimated_duration_days}
            )

            # Parse analysis to extract topic (simplified)
            state["selected_topic"] = goal.target_skills[0] if goal.target_skills else "Python Basics"

        else:
            # No specific goal, select based on:
            # 1. Topics that need review (spaced repetition)
            # 2. Prerequisites for user's goals
            # 3. Topics where user is making progress

            due_cards = await self.progress_tracker.get_due_reviews(user_id)

            if due_cards:
                # Prioritize topics with due reviews
                topic_counts = {}
                for card in due_cards:
                    topic_counts[card.topic] = topic_counts.get(card.topic, 0) + 1

                # Select topic with most due reviews
                state["selected_topic"] = max(topic_counts, key=topic_counts.get)
                state["messages"].append(f"Selected topic with {topic_counts[state['selected_topic']]} due reviews")

            else:
                # Select topic where user is around 50-70% skill level (optimal learning zone)
                optimal_topics = [
                    topic for topic, level in state["user_skill_levels"].items()
                    if 50 <= level <= 70
                ]

                if optimal_topics:
                    state["selected_topic"] = optimal_topics[0]
                else:
                    # Default to beginner topic
                    state["selected_topic"] = "Python Basics"

        # Determine difficulty based on skill level
        skill_level = state["user_skill_levels"].get(state["selected_topic"], 0)
        if skill_level < 30:
            state["difficulty_level"] = "beginner"
        elif skill_level < 70:
            state["difficulty_level"] = "intermediate"
        else:
            state["difficulty_level"] = "advanced"

        state["messages"].append(f"Selected: {state['selected_topic']} ({state['difficulty_level']})")

        return state

    async def _curate_content(self, state: LearningSessionState) -> LearningSessionState:
        """Step 3: Curate learning content"""

        state["messages"].append("Curating content...")

        topic = state["selected_topic"]
        difficulty = state["difficulty_level"]

        # Determine content types based on session duration
        if state["session_duration_minutes"] <= 15:
            content_types = ["article", "video"]
            max_items = 2
        elif state["session_duration_minutes"] <= 25:
            content_types = ["article", "video", "tutorial"]
            max_items = 3
        else:
            content_types = ["article", "video", "tutorial", "documentation"]
            max_items = 5

        # Curate content
        content = await self.content_curator.curate_content(
            topic=topic,
            difficulty=difficulty,
            content_types=content_types,
            max_items=max_items
        )

        # Convert to dict for state
        state["curated_content"] = [
            {
                "title": c.title,
                "description": c.description,
                "url": c.url,
                "type": c.content_type.value,
                "source": c.source.value,
                "duration_minutes": c.duration_minutes
            }
            for c in content
        ]

        state["messages"].append(f"Curated {len(state['curated_content'])} content items")

        return state

    async def _generate_problems(self, state: LearningSessionState) -> LearningSessionState:
        """Step 4: Generate practice problems"""

        state["messages"].append("Generating practice problems...")

        topic = state["selected_topic"]
        difficulty = state["difficulty_level"]
        skill_level = state["user_skill_levels"].get(topic, 0)

        # Determine problem types based on topic and duration
        problem_types = ["multiple_choice", "short_answer"]

        if "programming" in topic.lower() or "python" in topic.lower():
            problem_types.append("coding")

        # Number of problems based on duration
        problem_count = max(3, state["session_duration_minutes"] // 5)

        # Generate problems
        problems = await self.practice_generator.generate_problems(
            topic=topic,
            subtopic=None,
            difficulty=difficulty,
            problem_types=problem_types,
            count=problem_count,
            user_skill_level=skill_level
        )

        # Convert to dict
        state["practice_problems"] = [
            {
                "id": str(p.id) if p.id else "new",
                "question": p.question,
                "type": p.problem_type.value,
                "difficulty": p.difficulty.value,
                "hints": p.hints
            }
            for p in problems
        ]

        state["messages"].append(f"Generated {len(state['practice_problems'])} problems")

        return state

    async def _get_spaced_repetition(self, state: LearningSessionState) -> LearningSessionState:
        """Step 5: Get spaced repetition cards due for review"""

        state["messages"].append("Fetching spaced repetition cards...")

        user_id = state["user_id"]
        topic = state["selected_topic"]

        # Get due cards for this topic
        due_cards = await self.progress_tracker.get_due_reviews(user_id)

        # Filter for current topic and limit to 5
        topic_cards = [card for card in due_cards if card.topic == topic][:5]

        state["spaced_repetition_cards"] = [
            {
                "id": card.id,
                "question": card.question,
                "answer": card.answer,
                "explanation": card.explanation
            }
            for card in topic_cards
        ]

        state["messages"].append(f"Added {len(state['spaced_repetition_cards'])} review cards")

        return state

    async def _create_session_plan(self, state: LearningSessionState) -> LearningSessionState:
        """Step 6: Create structured session plan"""

        state["messages"].append("Creating session plan...")

        # Allocate time across activities
        total_minutes = state["session_duration_minutes"]

        # Time allocation (flexible based on content)
        time_allocation = {
            "intro": 1,
            "content_review": int(total_minutes * 0.4),
            "practice": int(total_minutes * 0.4),
            "spaced_repetition": int(total_minutes * 0.15),
            "wrap_up": int(total_minutes * 0.05)
        }

        session_plan = {
            "total_duration_minutes": total_minutes,
            "time_allocation": time_allocation,
            "flow": [
                {
                    "step": 1,
                    "activity": "Introduction",
                    "duration_minutes": time_allocation["intro"],
                    "description": f"Today's topic: {state['selected_topic']}"
                },
                {
                    "step": 2,
                    "activity": "Content Review",
                    "duration_minutes": time_allocation["content_review"],
                    "content_items": state["curated_content"]
                },
                {
                    "step": 3,
                    "activity": "Practice Problems",
                    "duration_minutes": time_allocation["practice"],
                    "problems": state["practice_problems"]
                },
                {
                    "step": 4,
                    "activity": "Spaced Repetition Review",
                    "duration_minutes": time_allocation["spaced_repetition"],
                    "review_cards": state["spaced_repetition_cards"]
                },
                {
                    "step": 5,
                    "activity": "Wrap-up & Summary",
                    "duration_minutes": time_allocation["wrap_up"],
                    "description": "Session summary and next steps"
                }
            ]
        }

        state["session_plan"] = session_plan
        state["messages"].append("Session plan created")

        return state

    async def _save_session(self, state: LearningSessionState) -> LearningSessionState:
        """Step 7: Save session to database"""

        state["messages"].append("Saving session...")

        # Create session record
        session = LearningSession(
            user_id=state["user_id"],
            goal_id=state["goal_id"],
            title=f"Daily Session: {state['selected_topic']}",
            description=f"Personalized learning session on {state['selected_topic']}",
            topic=state["selected_topic"],
            subtopics=state["selected_subtopics"],
            status=SessionStatus.SCHEDULED,
            difficulty_level=state["difficulty_level"],
            scheduled_at=datetime.utcnow(),
            content_ids=[c["title"] for c in state["curated_content"]],
            practice_problem_ids=[p["id"] for p in state["practice_problems"]]
        )

        self.db.add(session)
        await self.db.commit()
        await self.db.refresh(session)

        state["session_id"] = session.id
        state["session_completed"] = True

        # Generate recommendations for next session
        state["next_session_recommendations"] = {
            "recommended_topics": [state["selected_topic"]],  # Continue or progress
            "estimated_progress": "10%",
            "next_difficulty": state["difficulty_level"]
        }

        state["messages"].append(f"Session saved with ID: {session.id}")

        return state
