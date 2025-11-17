"""
Progress Tracker Agent: Tracks user progress, updates skill levels, manages spaced repetition
"""
from typing import Dict, List, Any, Optional
from datetime import datetime, timedelta
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_
from influxdb_client import Point
from influxdb_client.client.write_api import ASYNCHRONOUS
import asyncio

from backend.core.config import settings
from backend.db.models import (
    User, UserProgress, LearningSession, LearningStreak,
    SpacedRepetitionCard, SessionStatus
)


class ProgressTrackerAgent:
    """
    Tracks learning progress, updates metrics, and manages spaced repetition
    """

    def __init__(self, db_session: AsyncSession, influxdb_client, redis_client):
        self.db = db_session
        self.influx = influxdb_client
        self.redis = redis_client

        # InfluxDB write API
        self.write_api = influxdb_client.write_api(write_options=ASYNCHRONOUS)

    async def track_session_completion(
        self,
        session_id: int,
        user_id: int,
        topic: str,
        duration_seconds: int,
        problems_attempted: int,
        problems_correct: int,
        user_rating: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        Track completion of a learning session and update all metrics

        Args:
            session_id: Session ID
            user_id: User ID
            topic: Topic studied
            duration_seconds: Time spent
            problems_attempted: Number of problems attempted
            problems_correct: Number solved correctly
            user_rating: User's rating of the session (1-5)

        Returns:
            Updated progress metrics
        """

        # Calculate accuracy
        accuracy = (problems_correct / problems_attempted * 100) if problems_attempted > 0 else 0

        # Update session in database
        session_query = select(LearningSession).where(LearningSession.id == session_id)
        result = await self.db.execute(session_query)
        session = result.scalar_one()

        session.status = SessionStatus.COMPLETED
        session.completed_at = datetime.utcnow()
        session.duration_seconds = duration_seconds
        session.problems_attempted = problems_attempted
        session.problems_correct = problems_correct
        session.accuracy = accuracy
        session.user_rating = user_rating

        await self.db.commit()

        # Update user progress
        await self._update_user_progress(user_id, topic, accuracy, duration_seconds)

        # Update learning streak
        await self._update_learning_streak(user_id, duration_seconds)

        # Write metrics to InfluxDB
        await self._write_time_series_metrics(user_id, topic, accuracy, duration_seconds)

        # Cache updated stats in Redis
        await self._cache_user_stats(user_id)

        # Generate updated spaced repetition schedule
        await self._update_spaced_repetition(user_id, topic, accuracy)

        # Get updated metrics
        metrics = await self.get_user_metrics(user_id, topic)

        return metrics

    async def _update_user_progress(
        self,
        user_id: int,
        topic: str,
        accuracy: float,
        duration_seconds: int
    ):
        """Update user's progress for a topic"""

        # Get existing progress or create new
        progress_query = select(UserProgress).where(
            and_(
                UserProgress.user_id == user_id,
                UserProgress.topic == topic
            )
        )
        result = await self.db.execute(progress_query)
        progress = result.scalar_one_or_none()

        if not progress:
            progress = UserProgress(
                user_id=user_id,
                topic=topic,
                skill_level=0.0,
                mastery_percentage=0.0,
                total_sessions=0,
                total_time_seconds=0,
                problems_solved=0
            )
            self.db.add(progress)

        # Update metrics
        progress.total_sessions += 1
        progress.total_time_seconds += duration_seconds
        progress.last_practiced_at = datetime.utcnow()

        # Update skill level (weighted average with learning curve)
        if progress.average_accuracy is None:
            progress.average_accuracy = accuracy
        else:
            # Exponential moving average
            alpha = 0.3  # Weight for new data
            progress.average_accuracy = (alpha * accuracy) + ((1 - alpha) * progress.average_accuracy)

        # Calculate skill level (0-100) based on accuracy and consistency
        consistency_bonus = min(progress.total_sessions * 2, 20)  # Up to 20 points for consistency
        progress.skill_level = min(progress.average_accuracy + consistency_bonus, 100)

        # Calculate mastery percentage (requires multiple successful sessions)
        if progress.total_sessions >= 5 and progress.average_accuracy >= 80:
            progress.mastery_percentage = min(progress.skill_level, 100)
        else:
            progress.mastery_percentage = progress.skill_level * 0.7

        await self.db.commit()

    async def _update_learning_streak(self, user_id: int, duration_seconds: int):
        """Update user's learning streak"""

        # Get or create streak record
        streak_query = select(LearningStreak).where(LearningStreak.user_id == user_id)
        result = await self.db.execute(streak_query)
        streak = result.scalar_one_or_none()

        if not streak:
            streak = LearningStreak(
                user_id=user_id,
                current_streak=1,
                longest_streak=1,
                last_activity_date=datetime.utcnow(),
                streak_start_date=datetime.utcnow(),
                total_days_active=1,
                total_sessions=1,
                total_minutes=duration_seconds // 60
            )
            self.db.add(streak)
        else:
            # Check if this is a new day
            last_date = streak.last_activity_date.date() if streak.last_activity_date else None
            today = datetime.utcnow().date()

            if last_date != today:
                # Check if streak continues or breaks
                if last_date and (today - last_date).days == 1:
                    # Streak continues
                    streak.current_streak += 1
                    if streak.current_streak > streak.longest_streak:
                        streak.longest_streak = streak.current_streak
                elif last_date and (today - last_date).days > 1:
                    # Streak broken, restart
                    streak.current_streak = 1
                    streak.streak_start_date = datetime.utcnow()

                streak.total_days_active += 1

            streak.last_activity_date = datetime.utcnow()
            streak.total_sessions += 1
            streak.total_minutes += duration_seconds // 60

        await self.db.commit()

    async def _write_time_series_metrics(
        self,
        user_id: int,
        topic: str,
        accuracy: float,
        duration_seconds: int
    ):
        """Write metrics to InfluxDB for time-series analysis"""

        # Learning velocity point
        point = Point("learning_session") \
            .tag("user_id", str(user_id)) \
            .tag("topic", topic) \
            .field("accuracy", accuracy) \
            .field("duration_seconds", duration_seconds) \
            .field("duration_minutes", duration_seconds / 60) \
            .time(datetime.utcnow())

        await asyncio.to_thread(
            self.write_api.write,
            bucket=settings.INFLUXDB_BUCKET,
            org=settings.INFLUXDB_ORG,
            record=point
        )

    async def _cache_user_stats(self, user_id: int):
        """Cache frequently accessed user stats in Redis"""

        # Get aggregated stats
        stats = await self._get_aggregated_stats(user_id)

        # Store in Redis with 1 hour expiry
        cache_key = f"user_stats:{user_id}"
        await self.redis.setex(
            cache_key,
            3600,  # 1 hour
            str(stats)  # Store as JSON string
        )

    async def _get_aggregated_stats(self, user_id: int) -> Dict[str, Any]:
        """Get aggregated statistics for user"""

        # Total sessions
        session_count_query = select(func.count(LearningSession.id)).where(
            LearningSession.user_id == user_id
        )
        result = await self.db.execute(session_count_query)
        total_sessions = result.scalar()

        # Topics studied
        topics_query = select(UserProgress.topic).where(
            UserProgress.user_id == user_id
        )
        result = await self.db.execute(topics_query)
        topics = [row[0] for row in result.all()]

        # Streak info
        streak_query = select(LearningStreak).where(LearningStreak.user_id == user_id)
        result = await self.db.execute(streak_query)
        streak = result.scalar_one_or_none()

        return {
            "total_sessions": total_sessions or 0,
            "topics_count": len(topics),
            "topics": topics,
            "current_streak": streak.current_streak if streak else 0,
            "total_minutes": streak.total_minutes if streak else 0
        }

    async def _update_spaced_repetition(
        self,
        user_id: int,
        topic: str,
        accuracy: float
    ):
        """Update spaced repetition schedule using SM-2 algorithm"""

        # Get cards for this topic
        cards_query = select(SpacedRepetitionCard).where(
            and_(
                SpacedRepetitionCard.user_id == user_id,
                SpacedRepetitionCard.topic == topic,
                SpacedRepetitionCard.next_review_date <= datetime.utcnow()
            )
        ).limit(10)

        result = await self.db.execute(cards_query)
        cards = result.scalars().all()

        # Update each card based on performance
        quality = self._accuracy_to_quality(accuracy)

        for card in cards:
            await self._update_card_sm2(card, quality)

        await self.db.commit()

    def _accuracy_to_quality(self, accuracy: float) -> int:
        """Convert accuracy percentage to SM-2 quality (0-5)"""
        if accuracy >= 90:
            return 5  # Perfect
        elif accuracy >= 80:
            return 4  # Correct with hesitation
        elif accuracy >= 60:
            return 3  # Correct with difficulty
        elif accuracy >= 40:
            return 2  # Incorrect but remembered
        else:
            return 1  # Incorrect, didn't remember

    async def _update_card_sm2(self, card: SpacedRepetitionCard, quality: int):
        """
        Update spaced repetition card using SM-2 algorithm

        quality: 0-5 rating
        """

        card.total_reviews += 1
        card.last_reviewed_at = datetime.utcnow()

        if quality >= 3:
            card.correct_count += 1

            if card.repetition_count == 0:
                card.interval_days = 1
            elif card.repetition_count == 1:
                card.interval_days = 6
            else:
                card.interval_days = round(card.interval_days * card.ease_factor)

            card.repetition_count += 1

            # Update ease factor
            card.ease_factor = max(1.3, card.ease_factor + (0.1 - (5 - quality) * (0.08 + (5 - quality) * 0.02)))

        else:
            # Reset if quality < 3
            card.incorrect_count += 1
            card.repetition_count = 0
            card.interval_days = 1

        # Set next review date
        card.next_review_date = datetime.utcnow() + timedelta(days=card.interval_days)

    async def get_user_metrics(
        self,
        user_id: int,
        topic: Optional[str] = None
    ) -> Dict[str, Any]:
        """Get comprehensive user metrics"""

        # Try cache first
        cache_key = f"user_metrics:{user_id}:{topic or 'all'}"
        cached = await self.redis.get(cache_key)
        if cached:
            return eval(cached)  # Parse cached dict

        # Get progress
        if topic:
            progress_query = select(UserProgress).where(
                and_(
                    UserProgress.user_id == user_id,
                    UserProgress.topic == topic
                )
            )
            result = await self.db.execute(progress_query)
            progress = result.scalar_one_or_none()

            metrics = {
                "topic": topic,
                "skill_level": progress.skill_level if progress else 0,
                "mastery_percentage": progress.mastery_percentage if progress else 0,
                "total_sessions": progress.total_sessions if progress else 0,
                "total_time_hours": (progress.total_time_seconds / 3600) if progress else 0,
                "average_accuracy": progress.average_accuracy if progress else 0,
                "last_practiced": progress.last_practiced_at.isoformat() if progress and progress.last_practiced_at else None
            }
        else:
            # Get overall metrics
            progress_query = select(UserProgress).where(UserProgress.user_id == user_id)
            result = await self.db.execute(progress_query)
            all_progress = result.scalars().all()

            metrics = {
                "topics_studied": len(all_progress),
                "average_skill_level": sum(p.skill_level for p in all_progress) / len(all_progress) if all_progress else 0,
                "total_sessions": sum(p.total_sessions for p in all_progress),
                "total_time_hours": sum(p.total_time_seconds for p in all_progress) / 3600,
                "topics": [
                    {
                        "topic": p.topic,
                        "skill_level": p.skill_level,
                        "mastery": p.mastery_percentage
                    }
                    for p in all_progress
                ]
            }

        # Cache for 15 minutes
        await self.redis.setex(cache_key, 900, str(metrics))

        return metrics

    async def get_due_reviews(self, user_id: int) -> List[SpacedRepetitionCard]:
        """Get spaced repetition cards due for review"""

        cards_query = select(SpacedRepetitionCard).where(
            and_(
                SpacedRepetitionCard.user_id == user_id,
                SpacedRepetitionCard.next_review_date <= datetime.utcnow(),
                SpacedRepetitionCard.is_active == True
            )
        ).order_by(SpacedRepetitionCard.next_review_date.asc())

        result = await self.db.execute(cards_query)
        cards = result.scalars().all()

        return list(cards)

    async def get_learning_analytics(
        self,
        user_id: int,
        days: int = 30
    ) -> Dict[str, Any]:
        """
        Get learning analytics over time using InfluxDB

        Args:
            user_id: User ID
            days: Number of days to analyze

        Returns:
            Analytics data
        """

        query_api = self.influx.query_api()

        # Query for learning velocity
        flux_query = f'''
        from(bucket: "{settings.INFLUXDB_BUCKET}")
          |> range(start: -{days}d)
          |> filter(fn: (r) => r["_measurement"] == "learning_session")
          |> filter(fn: (r) => r["user_id"] == "{user_id}")
          |> group(columns: ["_time"])
          |> aggregateWindow(every: 1d, fn: mean)
        '''

        tables = await asyncio.to_thread(query_api.query, flux_query)

        # Process results
        analytics = {
            "period_days": days,
            "daily_accuracy": [],
            "daily_time_minutes": [],
            "dates": []
        }

        for table in tables:
            for record in table.records:
                analytics["dates"].append(record.get_time().isoformat())
                if record.get_field() == "accuracy":
                    analytics["daily_accuracy"].append(record.get_value())
                elif record.get_field() == "duration_minutes":
                    analytics["daily_time_minutes"].append(record.get_value())

        return analytics
