"""
Practice Generator Agent: Generates personalized practice problems and assessments
Uses LLMs to create contextual, adaptive problems based on user's skill level
"""
from typing import List, Dict, Any, Optional
from datetime import datetime
import asyncio
import json
from langchain_openai import ChatOpenAI
from langchain.schema import HumanMessage, SystemMessage
from langchain.prompts import ChatPromptTemplate
from sqlalchemy.ext.asyncio import AsyncSession

from backend.core.config import settings
from backend.db.mongodb_schemas import (
    PracticeProblem, ProblemType, DifficultyLevel
)


class PracticeGeneratorAgent:
    """
    Generates personalized practice problems adapted to user's skill level
    """

    def __init__(self, db_session: AsyncSession, mongodb_db):
        self.db = db_session
        self.mongodb = mongodb_db
        self.problems_collection = mongodb_db.practice_problems

        # Initialize LLM for problem generation
        self.llm = ChatOpenAI(
            model="gpt-4-turbo-preview",
            temperature=0.7,  # Higher temperature for creativity
            api_key=settings.OPENAI_API_KEY
        )

        # Specialized LLM for code problems
        self.code_llm = ChatOpenAI(
            model="gpt-4-turbo-preview",
            temperature=0.5,
            api_key=settings.OPENAI_API_KEY
        )

    async def generate_problems(
        self,
        topic: str,
        subtopic: Optional[str],
        difficulty: str,
        problem_types: List[str],
        count: int = 5,
        user_skill_level: float = 50.0,
        focus_areas: Optional[List[str]] = None
    ) -> List[PracticeProblem]:
        """
        Generate practice problems for a topic

        Args:
            topic: Main topic
            subtopic: Specific subtopic
            difficulty: Difficulty level
            problem_types: Types of problems to generate
            count: Number of problems to generate
            user_skill_level: User's current skill level (0-100)
            focus_areas: Specific areas to focus on

        Returns:
            List of generated practice problems
        """

        problems = []

        # Generate different types of problems
        for problem_type in problem_types:
            if problem_type == "coding":
                generated = await self._generate_coding_problems(
                    topic, subtopic, difficulty, count // len(problem_types), user_skill_level
                )
            elif problem_type == "multiple_choice":
                generated = await self._generate_mcq_problems(
                    topic, subtopic, difficulty, count // len(problem_types), focus_areas
                )
            elif problem_type == "short_answer":
                generated = await self._generate_short_answer_problems(
                    topic, subtopic, difficulty, count // len(problem_types)
                )
            else:
                continue

            problems.extend(generated)

        # Store problems in MongoDB
        await self._store_problems(problems)

        return problems[:count]

    async def _generate_coding_problems(
        self,
        topic: str,
        subtopic: Optional[str],
        difficulty: str,
        count: int,
        skill_level: float
    ) -> List[PracticeProblem]:
        """Generate coding problems"""

        # Adjust difficulty based on skill level
        adjusted_difficulty = self._adjust_difficulty(difficulty, skill_level)

        prompt = ChatPromptTemplate.from_messages([
            ("system", """You are an expert programming instructor who creates practical coding problems.

Your problems should:
1. Test understanding of key concepts
2. Be clear and unambiguous
3. Include realistic scenarios
4. Have multiple test cases
5. Provide detailed explanations

Generate problems in JSON format with this structure:
{{
  "problems": [
    {{
      "question": "Problem statement",
      "description": "Detailed description with constraints",
      "hints": ["hint 1", "hint 2"],
      "test_cases": [
        {{"input": "...", "expected_output": "...", "explanation": "..."}},
        ...
      ],
      "starter_code": "def solution():\\n    pass",
      "solution_code": "Complete solution",
      "explanation": "Detailed explanation of solution",
      "concepts": ["concept1", "concept2"],
      "skills_tested": ["skill1", "skill2"]
    }}
  ]
}}
"""),
            ("human", f"""Generate {count} {adjusted_difficulty} coding problems for:

Topic: {topic}
Subtopic: {subtopic or "General"}

Requirements:
- Difficulty: {adjusted_difficulty}
- User skill level: {skill_level}/100
- Include test cases
- Provide starter code and solution
- Explain the approach

Focus on practical, real-world scenarios that help learners build intuition.
""")
        ])

        try:
            response = await asyncio.to_thread(
                self.code_llm.invoke,
                prompt.format_messages()
            )

            # Parse JSON response
            content = response.content
            # Extract JSON from markdown code blocks if present
            if "```json" in content:
                content = content.split("```json")[1].split("```")[0].strip()
            elif "```" in content:
                content = content.split("```")[1].split("```")[0].strip()

            data = json.loads(content)

            problems = []
            for problem_data in data.get("problems", []):
                problem = PracticeProblem(
                    topic=topic,
                    subtopic=subtopic,
                    difficulty=DifficultyLevel(difficulty),
                    problem_type=ProblemType.CODING,
                    question=problem_data["question"],
                    description=problem_data.get("description"),
                    hints=problem_data.get("hints", []),
                    correct_answer="",  # Not applicable for coding
                    test_cases=problem_data.get("test_cases", []),
                    starter_code=problem_data.get("starter_code"),
                    solution_code=problem_data.get("solution_code"),
                    explanation=problem_data["explanation"],
                    concepts=problem_data.get("concepts", []),
                    skills_tested=problem_data.get("skills_tested", []),
                )
                problems.append(problem)

            return problems

        except Exception as e:
            print(f"Error generating coding problems: {e}")
            return []

    async def _generate_mcq_problems(
        self,
        topic: str,
        subtopic: Optional[str],
        difficulty: str,
        count: int,
        focus_areas: Optional[List[str]]
    ) -> List[PracticeProblem]:
        """Generate multiple choice questions"""

        focus_str = f"Focus on: {', '.join(focus_areas)}" if focus_areas else ""

        prompt = f"""Generate {count} {difficulty} multiple choice questions about:

Topic: {topic}
Subtopic: {subtopic or "General"}
{focus_str}

For each question, provide:
1. Clear question text
2. 4 answer options (A, B, C, D)
3. Correct answer
4. Detailed explanation
5. Concepts being tested

Return as JSON array:
[
  {{
    "question": "Question text",
    "options": ["A) option 1", "B) option 2", "C) option 3", "D) option 4"],
    "correct_answer": "A) option 1",
    "explanation": "Why this is correct...",
    "concepts": ["concept1", "concept2"]
  }},
  ...
]
"""

        try:
            response = await asyncio.to_thread(
                self.llm.invoke,
                [HumanMessage(content=prompt)]
            )

            content = response.content
            if "```json" in content:
                content = content.split("```json")[1].split("```")[0].strip()
            elif "```" in content:
                content = content.split("```")[1].split("```")[0].strip()

            data = json.loads(content)

            problems = []
            for problem_data in data:
                problem = PracticeProblem(
                    topic=topic,
                    subtopic=subtopic,
                    difficulty=DifficultyLevel(difficulty),
                    problem_type=ProblemType.MULTIPLE_CHOICE,
                    question=problem_data["question"],
                    options=problem_data["options"],
                    correct_answer=problem_data["correct_answer"],
                    explanation=problem_data["explanation"],
                    concepts=problem_data.get("concepts", []),
                )
                problems.append(problem)

            return problems

        except Exception as e:
            print(f"Error generating MCQ problems: {e}")
            return []

    async def _generate_short_answer_problems(
        self,
        topic: str,
        subtopic: Optional[str],
        difficulty: str,
        count: int
    ) -> List[PracticeProblem]:
        """Generate short answer questions"""

        prompt = f"""Generate {count} {difficulty} short answer questions about:

Topic: {topic}
Subtopic: {subtopic or "General"}

These questions should:
- Test deep understanding
- Require explanation, not just memorization
- Be answerable in 2-3 sentences

Return as JSON array:
[
  {{
    "question": "Question text",
    "correct_answer": "Key points that should be in answer",
    "explanation": "Full explanation with context",
    "concepts": ["concept1", "concept2"]
  }},
  ...
]
"""

        try:
            response = await asyncio.to_thread(
                self.llm.invoke,
                [HumanMessage(content=prompt)]
            )

            content = response.content
            if "```json" in content:
                content = content.split("```json")[1].split("```")[0].strip()
            elif "```" in content:
                content = content.split("```")[1].split("```")[0].strip()

            data = json.loads(content)

            problems = []
            for problem_data in data:
                problem = PracticeProblem(
                    topic=topic,
                    subtopic=subtopic,
                    difficulty=DifficultyLevel(difficulty),
                    problem_type=ProblemType.SHORT_ANSWER,
                    question=problem_data["question"],
                    correct_answer=problem_data["correct_answer"],
                    explanation=problem_data["explanation"],
                    concepts=problem_data.get("concepts", []),
                )
                problems.append(problem)

            return problems

        except Exception as e:
            print(f"Error generating short answer problems: {e}")
            return []

    async def evaluate_answer(
        self,
        problem: PracticeProblem,
        user_answer: str
    ) -> Dict[str, Any]:
        """
        Evaluate user's answer to a problem using AI

        Args:
            problem: The practice problem
            user_answer: User's answer

        Returns:
            Evaluation result with feedback
        """

        if problem.problem_type == ProblemType.CODING:
            return await self._evaluate_coding_answer(problem, user_answer)
        elif problem.problem_type == ProblemType.MULTIPLE_CHOICE:
            return self._evaluate_mcq_answer(problem, user_answer)
        else:
            return await self._evaluate_open_answer(problem, user_answer)

    async def _evaluate_coding_answer(
        self,
        problem: PracticeProblem,
        code: str
    ) -> Dict[str, Any]:
        """Evaluate coding solution"""

        prompt = f"""You are a code reviewer. Evaluate this solution:

Problem:
{problem.question}

Student's Code:
{code}

Expected Test Cases:
{json.dumps(problem.test_cases, indent=2)}

Provide evaluation in JSON format:
{{
  "is_correct": true/false,
  "passed_tests": [list of passed test indices],
  "failed_tests": [list of failed test indices],
  "feedback": "Constructive feedback",
  "strengths": ["strength 1", "strength 2"],
  "improvements": ["suggestion 1", "suggestion 2"],
  "score": 0-100
}}
"""

        try:
            response = await asyncio.to_thread(
                self.code_llm.invoke,
                [HumanMessage(content=prompt)]
            )

            content = response.content
            if "```json" in content:
                content = content.split("```json")[1].split("```")[0].strip()

            evaluation = json.loads(content)
            return evaluation

        except Exception as e:
            print(f"Error evaluating code: {e}")
            return {
                "is_correct": False,
                "feedback": "Error evaluating code",
                "score": 0
            }

    def _evaluate_mcq_answer(
        self,
        problem: PracticeProblem,
        answer: str
    ) -> Dict[str, Any]:
        """Evaluate multiple choice answer"""

        is_correct = answer.strip().lower() == problem.correct_answer.strip().lower()

        return {
            "is_correct": is_correct,
            "correct_answer": problem.correct_answer,
            "explanation": problem.explanation,
            "score": 100 if is_correct else 0
        }

    async def _evaluate_open_answer(
        self,
        problem: PracticeProblem,
        answer: str
    ) -> Dict[str, Any]:
        """Evaluate open-ended answer using AI"""

        prompt = f"""Evaluate this student's answer:

Question: {problem.question}

Expected Answer: {problem.correct_answer}

Student's Answer: {answer}

Provide evaluation in JSON:
{{
  "is_correct": true/false,
  "score": 0-100,
  "feedback": "Specific feedback",
  "covered_points": ["point 1", "point 2"],
  "missed_points": ["point 1", "point 2"]
}}
"""

        try:
            response = await asyncio.to_thread(
                self.llm.invoke,
                [HumanMessage(content=prompt)]
            )

            content = response.content
            if "```json" in content:
                content = content.split("```json")[1].split("```")[0].strip()

            evaluation = json.loads(content)
            return evaluation

        except Exception as e:
            print(f"Error evaluating answer: {e}")
            return {
                "is_correct": False,
                "feedback": "Error evaluating answer",
                "score": 0
            }

    def _adjust_difficulty(self, base_difficulty: str, skill_level: float) -> str:
        """Adjust difficulty based on user's skill level"""

        if skill_level < 30:
            return "beginner"
        elif skill_level < 60:
            return "intermediate"
        elif skill_level < 85:
            return "advanced"
        else:
            return "expert"

    async def _store_problems(self, problems: List[PracticeProblem]):
        """Store generated problems in MongoDB"""

        for problem in problems:
            problem_dict = problem.model_dump(by_alias=True, exclude_none=True)
            await self.problems_collection.insert_one(problem_dict)

    async def get_adaptive_next_problem(
        self,
        user_id: int,
        topic: str,
        recent_performance: List[bool]
    ) -> Optional[PracticeProblem]:
        """
        Get next problem adapted to user's recent performance

        Args:
            user_id: User ID
            topic: Topic
            recent_performance: List of recent correct/incorrect results

        Returns:
            Adaptive next problem
        """

        # Calculate success rate from recent performance
        if recent_performance:
            success_rate = sum(recent_performance) / len(recent_performance)
        else:
            success_rate = 0.5

        # Adjust difficulty
        if success_rate > 0.8:
            # User is doing well, increase difficulty
            difficulty = "advanced"
        elif success_rate > 0.5:
            # User is doing okay, maintain difficulty
            difficulty = "intermediate"
        else:
            # User is struggling, decrease difficulty
            difficulty = "beginner"

        # Find unsolved problems at appropriate difficulty
        problem = await self.problems_collection.find_one({
            "topic": topic,
            "difficulty": difficulty
        })

        if problem:
            return PracticeProblem(**problem)

        return None
