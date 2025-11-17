"""
Content Curator Agent: Finds, curates, and ranks learning content from multiple sources
Uses web scraping, API integrations, and vector similarity search
"""
from typing import List, Dict, Any, Optional
from datetime import datetime
import asyncio
import httpx
from bs4 import BeautifulSoup
from langchain_openai import ChatOpenAI, OpenAIEmbeddings
from langchain.schema import HumanMessage, SystemMessage
from sqlalchemy.ext.asyncio import AsyncSession
import pinecone
from youtube_transcript_api import YouTubeTranscriptApi
import re

from backend.core.config import settings
from backend.db.mongodb_schemas import (
    LearningContent, ContentType, ContentSource, DifficultyLevel
)


class ContentCuratorAgent:
    """
    Finds and curates high-quality learning content from various sources
    """

    def __init__(self, db_session: AsyncSession, mongodb_db):
        self.db = db_session
        self.mongodb = mongodb_db
        self.content_collection = mongodb_db.learning_content

        # Initialize LLM for content analysis
        self.llm = ChatOpenAI(
            model="gpt-4-turbo-preview",
            temperature=0.3,
            api_key=settings.OPENAI_API_KEY
        )

        # Initialize embeddings for semantic search
        self.embeddings = OpenAIEmbeddings(
            model="text-embedding-3-large",
            api_key=settings.OPENAI_API_KEY
        )

        # HTTP client for API calls
        self.http_client = httpx.AsyncClient(timeout=30.0)

        # Initialize Pinecone for vector search
        self._init_pinecone()

    def _init_pinecone(self):
        """Initialize Pinecone vector database"""
        pinecone.init(
            api_key=settings.PINECONE_API_KEY,
            environment=settings.PINECONE_ENVIRONMENT
        )

        # Check if index exists, create if not
        if settings.PINECONE_INDEX_NAME not in pinecone.list_indexes():
            pinecone.create_index(
                name=settings.PINECONE_INDEX_NAME,
                dimension=3072,  # text-embedding-3-large dimension
                metric="cosine"
            )

        self.pinecone_index = pinecone.Index(settings.PINECONE_INDEX_NAME)

    async def curate_content(
        self,
        topic: str,
        difficulty: str = "intermediate",
        content_types: Optional[List[str]] = None,
        max_items: int = 10
    ) -> List[LearningContent]:
        """
        Main method: Curate learning content for a topic

        Args:
            topic: The topic to find content for
            difficulty: Difficulty level (beginner/intermediate/advanced)
            content_types: Types of content to search for
            max_items: Maximum number of items to return

        Returns:
            List of curated learning content items
        """

        if content_types is None:
            content_types = ["article", "video", "tutorial", "documentation"]

        # Search from multiple sources in parallel
        search_tasks = []

        if "video" in content_types:
            search_tasks.append(self._search_youtube(topic, difficulty, limit=5))

        if "article" in content_types:
            search_tasks.append(self._search_medium(topic, difficulty, limit=3))
            search_tasks.append(self._search_dev_to(topic, difficulty, limit=3))

        if "documentation" in content_types or "tutorial" in content_types:
            search_tasks.append(self._search_github(topic, limit=3))

        # Execute all searches in parallel
        search_results = await asyncio.gather(*search_tasks, return_exceptions=True)

        # Flatten results
        all_content = []
        for result in search_results:
            if isinstance(result, list):
                all_content.extend(result)

        # Rank and filter content
        ranked_content = await self._rank_content(all_content, topic, difficulty)

        # Select top items
        top_content = ranked_content[:max_items]

        # Store in MongoDB and Pinecone
        await self._store_content(top_content)

        return top_content

    async def _search_youtube(
        self,
        topic: str,
        difficulty: str,
        limit: int = 5
    ) -> List[LearningContent]:
        """Search YouTube for educational videos"""

        if not settings.YOUTUBE_API_KEY:
            return []

        try:
            # YouTube Data API v3
            url = "https://www.googleapis.com/youtube/v3/search"
            params = {
                "part": "snippet",
                "q": f"{topic} tutorial {difficulty}",
                "type": "video",
                "videoDuration": "medium",  # 4-20 minutes
                "maxResults": limit,
                "key": settings.YOUTUBE_API_KEY,
                "relevanceLanguage": "en",
                "order": "relevance"
            }

            response = await self.http_client.get(url, params=params)
            data = response.json()

            content_items = []
            for item in data.get("items", []):
                video_id = item["id"]["videoId"]
                snippet = item["snippet"]

                # Get transcript if available
                transcript = await self._get_youtube_transcript(video_id)

                content = LearningContent(
                    title=snippet["title"],
                    description=snippet["description"],
                    content_type=ContentType.VIDEO,
                    source=ContentSource.YOUTUBE,
                    url=f"https://www.youtube.com/watch?v={video_id}",
                    content_text=transcript,
                    topic=topic,
                    difficulty=DifficultyLevel(difficulty),
                    publish_date=datetime.fromisoformat(snippet["publishedAt"].replace("Z", "+00:00")),
                    author=snippet["channelTitle"]
                )

                content_items.append(content)

            return content_items

        except Exception as e:
            print(f"YouTube search error: {e}")
            return []

    async def _get_youtube_transcript(self, video_id: str) -> Optional[str]:
        """Get transcript for a YouTube video"""
        try:
            transcript_list = YouTubeTranscriptApi.get_transcript(video_id)
            transcript_text = " ".join([entry["text"] for entry in transcript_list])
            return transcript_text
        except:
            return None

    async def _search_medium(
        self,
        topic: str,
        difficulty: str,
        limit: int = 3
    ) -> List[LearningContent]:
        """Search Medium for articles"""

        try:
            # Medium doesn't have official API, use web scraping
            search_url = f"https://medium.com/search?q={topic.replace(' ', '+')}"

            response = await self.http_client.get(search_url)
            soup = BeautifulSoup(response.text, 'html.parser')

            # Find article elements (Medium's structure may change)
            articles = soup.find_all('article', limit=limit)

            content_items = []
            for article in articles:
                try:
                    title_elem = article.find('h2')
                    if not title_elem:
                        continue

                    title = title_elem.get_text(strip=True)

                    # Get link
                    link = article.find('a')
                    url = link['href'] if link else None
                    if url and not url.startswith('http'):
                        url = f"https://medium.com{url}"

                    # Get description
                    desc_elem = article.find('h3') or article.find('p')
                    description = desc_elem.get_text(strip=True) if desc_elem else ""

                    content = LearningContent(
                        title=title,
                        description=description,
                        content_type=ContentType.ARTICLE,
                        source=ContentSource.MEDIUM,
                        url=url,
                        topic=topic,
                        difficulty=DifficultyLevel(difficulty)
                    )

                    content_items.append(content)

                except Exception as e:
                    print(f"Error parsing Medium article: {e}")
                    continue

            return content_items

        except Exception as e:
            print(f"Medium search error: {e}")
            return []

    async def _search_dev_to(
        self,
        topic: str,
        difficulty: str,
        limit: int = 3
    ) -> List[LearningContent]:
        """Search Dev.to for articles"""

        try:
            # Dev.to has a public API
            url = "https://dev.to/api/articles"
            params = {
                "tag": topic.lower().replace(" ", ""),
                "per_page": limit
            }

            response = await self.http_client.get(url, params=params)
            articles = response.json()

            content_items = []
            for article in articles:
                content = LearningContent(
                    title=article["title"],
                    description=article["description"],
                    content_type=ContentType.ARTICLE,
                    source=ContentSource.DEV_TO,
                    url=article["url"],
                    topic=topic,
                    difficulty=DifficultyLevel(difficulty),
                    publish_date=datetime.fromisoformat(article["published_at"].replace("Z", "+00:00")),
                    author=article["user"]["name"],
                    views=article.get("page_views_count"),
                    likes=article.get("positive_reactions_count")
                )

                content_items.append(content)

            return content_items

        except Exception as e:
            print(f"Dev.to search error: {e}")
            return []

    async def _search_github(
        self,
        topic: str,
        limit: int = 3
    ) -> List[LearningContent]:
        """Search GitHub for relevant repositories and code examples"""

        if not settings.GITHUB_TOKEN:
            return []

        try:
            url = "https://api.github.com/search/repositories"
            params = {
                "q": f"{topic} tutorial OR guide OR example",
                "sort": "stars",
                "order": "desc",
                "per_page": limit
            }
            headers = {
                "Authorization": f"token {settings.GITHUB_TOKEN}",
                "Accept": "application/vnd.github.v3+json"
            }

            response = await self.http_client.get(url, params=params, headers=headers)
            data = response.json()

            content_items = []
            for repo in data.get("items", []):
                content = LearningContent(
                    title=repo["full_name"],
                    description=repo.get("description", ""),
                    content_type=ContentType.CODE_EXAMPLE,
                    source=ContentSource.GITHUB,
                    url=repo["html_url"],
                    topic=topic,
                    difficulty=DifficultyLevel.INTERMEDIATE,
                    author=repo["owner"]["login"],
                    likes=repo["stargazers_count"]
                )

                content_items.append(content)

            return content_items

        except Exception as e:
            print(f"GitHub search error: {e}")
            return []

    async def _rank_content(
        self,
        content_items: List[LearningContent],
        topic: str,
        difficulty: str
    ) -> List[LearningContent]:
        """
        Rank content items using AI-powered quality assessment
        """

        if not content_items:
            return []

        # Create a batch prompt for the LLM to rank content
        content_summaries = []
        for i, item in enumerate(content_items):
            summary = f"""
{i+1}. {item.title}
   Source: {item.source}
   Type: {item.content_type}
   Description: {item.description[:200]}
   URL: {item.url}
"""
            content_summaries.append(summary)

        ranking_prompt = f"""
You are an expert at evaluating educational content quality.

Topic: {topic}
Difficulty Level: {difficulty}

Here are {len(content_items)} content items to rank:

{''.join(content_summaries)}

Please rank these items from best to worst based on:
1. Relevance to the topic
2. Quality and clarity
3. Appropriate difficulty level
4. Credibility of source
5. Practical value for learning

Return only the numbers in ranked order (best first), comma-separated.
Example: 3,1,5,2,4
"""

        try:
            response = await asyncio.to_thread(
                self.llm.invoke,
                [HumanMessage(content=ranking_prompt)]
            )

            # Parse ranking
            ranking_str = response.content.strip()
            ranking_indices = [int(x.strip()) - 1 for x in ranking_str.split(",")]

            # Reorder content based on ranking
            ranked_content = [content_items[i] for i in ranking_indices if i < len(content_items)]

            # Calculate quality scores
            for i, item in enumerate(ranked_content):
                item.quality_score = 100 - (i * 10)  # Simple scoring
                item.relevance_score = 100 - (i * 5)

            return ranked_content

        except Exception as e:
            print(f"Content ranking error: {e}")
            # Return original order if ranking fails
            return content_items

    async def _store_content(self, content_items: List[LearningContent]):
        """Store content in MongoDB and create embeddings in Pinecone"""

        for item in content_items:
            # Generate embedding
            text_to_embed = f"{item.title} {item.description}"
            embedding = await asyncio.to_thread(
                self.embeddings.embed_query,
                text_to_embed
            )

            item.embedding = embedding
            item.embedding_model = "text-embedding-3-large"

            # Store in MongoDB
            content_dict = item.model_dump(by_alias=True, exclude_none=True)
            result = await self.content_collection.insert_one(content_dict)

            content_id = str(result.inserted_id)

            # Store embedding in Pinecone
            self.pinecone_index.upsert(
                vectors=[(
                    content_id,
                    embedding,
                    {
                        "title": item.title,
                        "topic": item.topic,
                        "difficulty": item.difficulty.value,
                        "source": item.source.value,
                        "content_type": item.content_type.value
                    }
                )]
            )

    async def semantic_search(
        self,
        query: str,
        topic: Optional[str] = None,
        difficulty: Optional[str] = None,
        limit: int = 5
    ) -> List[Dict[str, Any]]:
        """
        Semantic search for content using vector similarity
        """

        # Generate query embedding
        query_embedding = await asyncio.to_thread(
            self.embeddings.embed_query,
            query
        )

        # Build filter
        filter_dict = {}
        if topic:
            filter_dict["topic"] = topic
        if difficulty:
            filter_dict["difficulty"] = difficulty

        # Search in Pinecone
        results = self.pinecone_index.query(
            vector=query_embedding,
            top_k=limit,
            include_metadata=True,
            filter=filter_dict if filter_dict else None
        )

        # Fetch full content from MongoDB
        content_ids = [match["id"] for match in results["matches"]]
        cursor = self.content_collection.find({"_id": {"$in": content_ids}})

        content_items = []
        async for doc in cursor:
            content_items.append(doc)

        return content_items

    async def close(self):
        """Close HTTP client"""
        await self.http_client.aclose()
