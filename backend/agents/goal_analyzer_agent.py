"""
Goal Analyzer Agent: Understands user goals, assesses current knowledge, identifies skill gaps
Uses LangChain, OpenAI GPT-4, and integrates with knowledge graph
"""
from typing import Dict, List, Any, Optional
from datetime import datetime, timedelta
from langchain.agents import AgentExecutor, create_openai_functions_agent
from langchain.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain.tools import Tool
from langchain_openai import ChatOpenAI
from langchain.memory import ConversationBufferMemory
from langchain.schema import HumanMessage, SystemMessage
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
import asyncio

from backend.core.config import settings
from backend.db.models import User, UserProgress, LearningSession, SkillAssessment
from backend.db.neo4j_schema import get_learning_path, get_related_topics


class GoalAnalyzerAgent:
    """
    Analyzes user learning goals and creates personalized learning plans
    """

    def __init__(self, db_session: AsyncSession, neo4j_session):
        self.db = db_session
        self.neo4j = neo4j_session

        # Initialize LLM
        self.llm = ChatOpenAI(
            model="gpt-4-turbo-preview",
            temperature=0.2,
            api_key=settings.OPENAI_API_KEY
        )

        # Memory for conversation context
        self.memory = ConversationBufferMemory(
            memory_key="chat_history",
            return_messages=True
        )

        # Define tools for the agent
        self.tools = [
            Tool(
                name="analyze_user_history",
                func=self._analyze_user_history_sync,
                description="""
                Analyzes user's past learning sessions and performance.
                Input: user_id (int)
                Returns: Dictionary with topics learned, performance metrics, and recency data
                """
            ),
            Tool(
                name="query_knowledge_graph",
                func=self._query_knowledge_graph_sync,
                description="""
                Queries the knowledge graph to understand topic prerequisites and relationships.
                Input: topic_name (str)
                Returns: Dictionary with prerequisites, related topics, and learning path
                """
            ),
            Tool(
                name="assess_skill_level",
                func=self._assess_skill_level_sync,
                description="""
                Assesses user's current skill level for a specific topic.
                Input: user_id (int), topic (str)
                Returns: Skill level score (0-100) and mastery details
                """
            ),
            Tool(
                name="estimate_learning_time",
                func=self._estimate_learning_time_sync,
                description="""
                Estimates time needed to reach a skill level for a topic.
                Input: topic (str), current_level (float), target_level (float)
                Returns: Estimated hours needed
                """
            )
        ]

        # Create the agent
        self.prompt = ChatPromptTemplate.from_messages([
            ("system", """You are an expert learning advisor and goal analyzer. Your job is to:

1. UNDERSTAND the user's learning goal deeply:
   - What specific skills do they want to learn?
   - What's their motivation? (job interview, career switch, personal interest, etc.)
   - What's their timeline?
   - What's their current knowledge level?

2. ANALYZE their current state:
   - Review their past learning history
   - Assess current skill levels
   - Identify knowledge gaps
   - Check for prerequisite knowledge

3. CREATE a personalized learning plan:
   - Break down the goal into specific topics and skills
   - Prioritize topics based on prerequisites and importance
   - Estimate time needed for each topic
   - Identify the critical path to achieving the goal

4. PROVIDE actionable recommendations:
   - What to learn first
   - How to approach each topic
   - Expected timeline with milestones
   - Resources and learning strategies

Use the available tools to gather data and make informed decisions.
Be specific, practical, and encouraging in your analysis.
"""),
            MessagesPlaceholder(variable_name="chat_history"),
            ("human", "{input}"),
            ("assistant", "{agent_scratchpad}")
        ])

        self.agent = create_openai_functions_agent(
            llm=self.llm,
            tools=self.tools,
            prompt=self.prompt
        )

        self.executor = AgentExecutor(
            agent=self.agent,
            tools=self.tools,
            verbose=True,
            max_iterations=10,
            memory=self.memory
        )

    async def analyze_goal(
        self,
        user_id: int,
        goal_description: str,
        additional_context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Main entry point: Analyze user's learning goal and create a plan

        Args:
            user_id: User ID
            goal_description: User's learning goal description
            additional_context: Optional additional context (timeline, current level, etc.)

        Returns:
            Comprehensive analysis with learning plan
        """

        # Get user context
        user_context = await self._get_user_context(user_id)

        # Build the analysis prompt
        context_str = "\n".join([f"- {k}: {v}" for k, v in additional_context.items()]) if additional_context else "None provided"

        analysis_prompt = f"""
User ID: {user_id}

LEARNING GOAL:
{goal_description}

USER BACKGROUND:
- Current topics studied: {', '.join(user_context['topics_studied'])}
- Total learning sessions: {user_context['total_sessions']}
- Average session performance: {user_context['avg_performance']:.1f}%
- Learning streak: {user_context['current_streak']} days

ADDITIONAL CONTEXT:
{context_str}

Please analyze this learning goal and provide:
1. Goal breakdown: What specific topics and skills are needed?
2. Current assessment: Where is the user now? What do they already know?
3. Skill gaps: What are the critical gaps to fill?
4. Learning path: Step-by-step path from current state to goal
5. Time estimate: Realistic timeline with milestones
6. First steps: What should they start learning today?

Use the available tools to gather data about the user's history, the knowledge graph structure,
and skill assessments. Be specific and actionable.
"""

        # Run the agent
        result = await asyncio.to_thread(
            self.executor.invoke,
            {"input": analysis_prompt}
        )

        # Parse and structure the output
        analysis = self._parse_agent_output(result['output'])

        # Save the analysis
        await self._save_goal_analysis(user_id, goal_description, analysis)

        return analysis

    def _analyze_user_history_sync(self, user_id: str) -> str:
        """Synchronous wrapper for async user history analysis"""
        loop = asyncio.get_event_loop()
        result = loop.run_until_complete(self._analyze_user_history(int(user_id)))
        return str(result)

    async def _analyze_user_history(self, user_id: int) -> Dict[str, Any]:
        """Analyze user's past learning sessions"""

        # Get recent sessions
        query = select(LearningSession).where(
            LearningSession.user_id == user_id
        ).order_by(LearningSession.created_at.desc()).limit(20)

        result = await self.db.execute(query)
        sessions = result.scalars().all()

        if not sessions:
            return {
                "message": "No learning history found",
                "topics_learned": [],
                "performance": {}
            }

        # Aggregate stats
        topics = {}
        for session in sessions:
            if session.topic not in topics:
                topics[session.topic] = {
                    "count": 0,
                    "total_score": 0,
                    "last_practiced": session.completed_at
                }

            topics[session.topic]["count"] += 1
            if session.accuracy:
                topics[session.topic]["total_score"] += session.accuracy

        # Calculate averages
        for topic, stats in topics.items():
            stats["avg_score"] = stats["total_score"] / stats["count"] if stats["count"] > 0 else 0
            stats["days_since_practice"] = (datetime.utcnow() - stats["last_practiced"]).days if stats["last_practiced"] else None

        return {
            "topics_learned": list(topics.keys()),
            "performance_by_topic": topics,
            "total_sessions": len(sessions),
            "recent_activity": [
                {
                    "topic": s.topic,
                    "date": s.completed_at.isoformat() if s.completed_at else None,
                    "score": s.accuracy
                }
                for s in sessions[:5]
            ]
        }

    def _query_knowledge_graph_sync(self, topic: str) -> str:
        """Synchronous wrapper for knowledge graph query"""
        loop = asyncio.get_event_loop()
        result = loop.run_until_complete(self._query_knowledge_graph(topic))
        return str(result)

    async def _query_knowledge_graph(self, topic: str) -> Dict[str, Any]:
        """Query Neo4j knowledge graph for topic information"""

        # Get prerequisites
        prereq_query = """
        MATCH (t:Topic {name: $topic})<-[:PREREQUISITE_FOR]-(prereq:Topic)
        RETURN prereq.name as name, prereq.difficulty as difficulty
        """
        prereq_result = await self.neo4j.run(prereq_query, topic=topic)
        prerequisites = [dict(record) async for record in prereq_result]

        # Get related topics
        related = await get_related_topics(self.neo4j, topic)

        # Get concepts
        concepts_query = """
        MATCH (c:Concept)-[:BELONGS_TO]->(t:Topic {name: $topic})
        RETURN c.name as name, c.difficulty as difficulty
        """
        concepts_result = await self.neo4j.run(concepts_query, topic=topic)
        concepts = [dict(record) async for record in concepts_result]

        return {
            "topic": topic,
            "prerequisites": prerequisites,
            "related_topics": related,
            "key_concepts": concepts
        }

    def _assess_skill_level_sync(self, user_id_and_topic: str) -> str:
        """Synchronous wrapper for skill assessment"""
        parts = user_id_and_topic.split(',')
        user_id = int(parts[0].strip())
        topic = parts[1].strip() if len(parts) > 1 else "unknown"
        loop = asyncio.get_event_loop()
        result = loop.run_until_complete(self._assess_skill_level(user_id, topic))
        return str(result)

    async def _assess_skill_level(self, user_id: int, topic: str) -> Dict[str, Any]:
        """Assess user's current skill level for a topic"""

        # Get user progress
        query = select(UserProgress).where(
            UserProgress.user_id == user_id,
            UserProgress.topic == topic
        )
        result = await self.db.execute(query)
        progress = result.scalar_one_or_none()

        if not progress:
            return {
                "topic": topic,
                "skill_level": 0,
                "mastery": 0,
                "status": "not_started"
            }

        return {
            "topic": topic,
            "skill_level": progress.skill_level,
            "mastery": progress.mastery_percentage,
            "total_sessions": progress.total_sessions,
            "avg_accuracy": progress.average_accuracy,
            "last_practiced": progress.last_practiced_at.isoformat() if progress.last_practiced_at else None
        }

    def _estimate_learning_time_sync(self, params: str) -> str:
        """Synchronous wrapper for time estimation"""
        parts = params.split(',')
        topic = parts[0].strip()
        current_level = float(parts[1].strip()) if len(parts) > 1 else 0
        target_level = float(parts[2].strip()) if len(parts) > 2 else 70
        loop = asyncio.get_event_loop()
        result = loop.run_until_complete(self._estimate_learning_time(topic, current_level, target_level))
        return str(result)

    async def _estimate_learning_time(
        self,
        topic: str,
        current_level: float,
        target_level: float
    ) -> Dict[str, Any]:
        """Estimate learning time needed"""

        # Get topic info from knowledge graph
        topic_query = """
        MATCH (t:Topic {name: $topic})
        RETURN t.estimated_hours as base_hours, t.difficulty as difficulty
        """
        result = await self.neo4j.run(topic_query, topic=topic)
        record = await result.single()

        if not record:
            return {"estimated_hours": 20, "confidence": "low"}

        base_hours = record["base_hours"] or 40
        difficulty = record["difficulty"] or "intermediate"

        # Adjust based on current level
        level_diff = target_level - current_level
        hours_needed = (base_hours * level_diff / 100)

        # Difficulty multiplier
        difficulty_multipliers = {
            "beginner": 0.8,
            "intermediate": 1.0,
            "advanced": 1.3,
            "expert": 1.6
        }
        hours_needed *= difficulty_multipliers.get(difficulty, 1.0)

        return {
            "estimated_hours": round(hours_needed, 1),
            "estimated_days_20min": round(hours_needed * 3, 1),  # at 20min/day
            "difficulty": difficulty,
            "confidence": "medium"
        }

    async def _get_user_context(self, user_id: int) -> Dict[str, Any]:
        """Get comprehensive user context"""

        # Get user progress
        progress_query = select(UserProgress).where(UserProgress.user_id == user_id)
        result = await self.db.execute(progress_query)
        progress_records = result.scalars().all()

        # Get session stats
        session_query = select(
            func.count(LearningSession.id),
            func.avg(LearningSession.accuracy)
        ).where(LearningSession.user_id == user_id)
        result = await self.db.execute(session_query)
        session_stats = result.first()

        return {
            "topics_studied": [p.topic for p in progress_records],
            "total_sessions": session_stats[0] or 0,
            "avg_performance": session_stats[1] or 0,
            "current_streak": 0  # TODO: Calculate from streak table
        }

    def _parse_agent_output(self, output: str) -> Dict[str, Any]:
        """Parse the agent's output into structured format"""

        # This is a simplified parser - in production, use more robust parsing
        return {
            "raw_analysis": output,
            "timestamp": datetime.utcnow().isoformat(),
            "agent_version": "1.0"
        }

    async def _save_goal_analysis(
        self,
        user_id: int,
        goal_description: str,
        analysis: Dict[str, Any]
    ):
        """Save the goal analysis to database"""
        # Implementation to save analysis
        pass


    async def quick_skill_check(self, user_id: int, topic: str) -> float:
        """Quick check of user's skill level (0-100)"""
        progress_query = select(UserProgress.skill_level).where(
            UserProgress.user_id == user_id,
            UserProgress.topic == topic
        )
        result = await self.db.execute(progress_query)
        skill_level = result.scalar_one_or_none()
        return skill_level or 0.0
