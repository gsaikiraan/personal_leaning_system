"""
Neo4j Knowledge Graph Schema and Initialization
"""
from typing import List, Dict, Any


# Cypher queries for creating the knowledge graph schema

CREATE_CONSTRAINTS = [
    # Topic nodes
    """
    CREATE CONSTRAINT topic_name IF NOT EXISTS
    FOR (t:Topic) REQUIRE t.name IS UNIQUE
    """,

    # Concept nodes
    """
    CREATE CONSTRAINT concept_id IF NOT EXISTS
    FOR (c:Concept) REQUIRE c.id IS UNIQUE
    """,

    # Skill nodes
    """
    CREATE CONSTRAINT skill_name IF NOT EXISTS
    FOR (s:Skill) REQUIRE s.name IS UNIQUE
    """,
]

CREATE_INDEXES = [
    # Topic difficulty
    """
    CREATE INDEX topic_difficulty IF NOT EXISTS
    FOR (t:Topic) ON (t.difficulty)
    """,

    # Concept category
    """
    CREATE INDEX concept_category IF NOT EXISTS
    FOR (c:Concept) ON (c.category)
    """,

    # Skill level
    """
    CREATE INDEX skill_level IF NOT EXISTS
    FOR (s:Skill) ON (s.level)
    """,
]


async def initialize_knowledge_graph(neo4j_session):
    """Initialize the knowledge graph schema and base data"""

    # Create constraints
    for query in CREATE_CONSTRAINTS:
        await neo4j_session.run(query)

    # Create indexes
    for query in CREATE_INDEXES:
        await neo4j_session.run(query)

    print("✅ Neo4j constraints and indexes created")

    # Create base knowledge structure for common topics
    await create_base_topics(neo4j_session)


async def create_base_topics(neo4j_session):
    """Create base topic structure for common learning domains"""

    # Programming topics
    programming_topics = [
        {
            "name": "Python Basics",
            "category": "Programming",
            "difficulty": "beginner",
            "estimated_hours": 40,
            "description": "Fundamental Python programming concepts",
            "prerequisites": []
        },
        {
            "name": "Data Structures",
            "category": "Programming",
            "difficulty": "intermediate",
            "estimated_hours": 60,
            "description": "Arrays, linked lists, trees, graphs, hash tables",
            "prerequisites": ["Python Basics"]
        },
        {
            "name": "Algorithms",
            "category": "Programming",
            "difficulty": "intermediate",
            "estimated_hours": 80,
            "description": "Sorting, searching, dynamic programming, greedy algorithms",
            "prerequisites": ["Data Structures"]
        },
        {
            "name": "Machine Learning Fundamentals",
            "category": "AI/ML",
            "difficulty": "intermediate",
            "estimated_hours": 100,
            "description": "Supervised/unsupervised learning, regression, classification",
            "prerequisites": ["Python Basics", "Statistics"]
        },
        {
            "name": "Deep Learning",
            "category": "AI/ML",
            "difficulty": "advanced",
            "estimated_hours": 120,
            "description": "Neural networks, CNNs, RNNs, transformers",
            "prerequisites": ["Machine Learning Fundamentals", "Linear Algebra"]
        },
        {
            "name": "System Design",
            "category": "Engineering",
            "difficulty": "advanced",
            "estimated_hours": 80,
            "description": "Scalability, distributed systems, architecture patterns",
            "prerequisites": ["Data Structures", "Algorithms"]
        },
        {
            "name": "Statistics",
            "category": "Mathematics",
            "difficulty": "intermediate",
            "estimated_hours": 50,
            "description": "Probability, distributions, hypothesis testing",
            "prerequisites": []
        },
        {
            "name": "Linear Algebra",
            "category": "Mathematics",
            "difficulty": "intermediate",
            "estimated_hours": 60,
            "description": "Vectors, matrices, eigenvalues, transformations",
            "prerequisites": []
        },
    ]

    # Create topics
    for topic in programming_topics:
        query = """
        MERGE (t:Topic {name: $name})
        SET t.category = $category,
            t.difficulty = $difficulty,
            t.estimated_hours = $estimated_hours,
            t.description = $description,
            t.created_at = datetime()
        RETURN t
        """
        await neo4j_session.run(query, **topic)

    # Create prerequisite relationships
    for topic in programming_topics:
        if topic["prerequisites"]:
            for prereq in topic["prerequisites"]:
                query = """
                MATCH (prereq:Topic {name: $prereq_name})
                MATCH (topic:Topic {name: $topic_name})
                MERGE (prereq)-[:PREREQUISITE_FOR]->(topic)
                """
                await neo4j_session.run(
                    query,
                    prereq_name=prereq,
                    topic_name=topic["name"]
                )

    # Create concept nodes with detailed breakdowns
    await create_topic_concepts(neo4j_session)

    print("✅ Base knowledge graph structure created")


async def create_topic_concepts(neo4j_session):
    """Create detailed concept breakdowns for topics"""

    # Python Basics concepts
    python_concepts = [
        {"id": "py_001", "name": "Variables and Data Types", "difficulty": "beginner"},
        {"id": "py_002", "name": "Control Flow (if/else/loops)", "difficulty": "beginner"},
        {"id": "py_003", "name": "Functions", "difficulty": "beginner"},
        {"id": "py_004", "name": "Lists and Tuples", "difficulty": "beginner"},
        {"id": "py_005", "name": "Dictionaries and Sets", "difficulty": "beginner"},
        {"id": "py_006", "name": "Object-Oriented Programming", "difficulty": "intermediate"},
        {"id": "py_007", "name": "File I/O", "difficulty": "beginner"},
        {"id": "py_008", "name": "Exception Handling", "difficulty": "intermediate"},
    ]

    for concept in python_concepts:
        query = """
        MERGE (c:Concept {id: $id})
        SET c.name = $name,
            c.difficulty = $difficulty,
            c.created_at = datetime()
        WITH c
        MATCH (t:Topic {name: 'Python Basics'})
        MERGE (c)-[:BELONGS_TO]->(t)
        """
        await neo4j_session.run(query, **concept)

    # Data Structures concepts
    ds_concepts = [
        {"id": "ds_001", "name": "Arrays", "difficulty": "beginner"},
        {"id": "ds_002", "name": "Linked Lists", "difficulty": "intermediate"},
        {"id": "ds_003", "name": "Stacks and Queues", "difficulty": "intermediate"},
        {"id": "ds_004", "name": "Trees (Binary, BST)", "difficulty": "intermediate"},
        {"id": "ds_005", "name": "Graphs", "difficulty": "advanced"},
        {"id": "ds_006", "name": "Hash Tables", "difficulty": "intermediate"},
        {"id": "ds_007", "name": "Heaps", "difficulty": "advanced"},
        {"id": "ds_008", "name": "Tries", "difficulty": "advanced"},
    ]

    for concept in ds_concepts:
        query = """
        MERGE (c:Concept {id: $id})
        SET c.name = $name,
            c.difficulty = $difficulty,
            c.created_at = datetime()
        WITH c
        MATCH (t:Topic {name: 'Data Structures'})
        MERGE (c)-[:BELONGS_TO]->(t)
        """
        await neo4j_session.run(query, **concept)

    # Machine Learning concepts
    ml_concepts = [
        {"id": "ml_001", "name": "Linear Regression", "difficulty": "beginner"},
        {"id": "ml_002", "name": "Logistic Regression", "difficulty": "beginner"},
        {"id": "ml_003", "name": "Decision Trees", "difficulty": "intermediate"},
        {"id": "ml_004", "name": "Random Forests", "difficulty": "intermediate"},
        {"id": "ml_005", "name": "Support Vector Machines", "difficulty": "advanced"},
        {"id": "ml_006", "name": "K-Means Clustering", "difficulty": "intermediate"},
        {"id": "ml_007", "name": "Neural Networks Basics", "difficulty": "intermediate"},
        {"id": "ml_008", "name": "Model Evaluation", "difficulty": "intermediate"},
    ]

    for concept in ml_concepts:
        query = """
        MERGE (c:Concept {id: $id})
        SET c.name = $name,
            c.difficulty = $difficulty,
            c.created_at = datetime()
        WITH c
        MATCH (t:Topic {name: 'Machine Learning Fundamentals'})
        MERGE (c)-[:BELONGS_TO]->(t)
        """
        await neo4j_session.run(query, **concept)


async def add_user_knowledge_state(neo4j_session, user_id: int, topic: str, mastery_level: float):
    """Track user's knowledge state in the graph"""

    query = """
    MERGE (u:User {id: $user_id})
    WITH u
    MATCH (t:Topic {name: $topic})
    MERGE (u)-[k:KNOWS]->(t)
    SET k.mastery_level = $mastery_level,
        k.last_updated = datetime()
    RETURN k
    """

    result = await neo4j_session.run(
        query,
        user_id=user_id,
        topic=topic,
        mastery_level=mastery_level
    )
    return result


async def get_learning_path(neo4j_session, user_id: int, target_topic: str) -> List[Dict[str, Any]]:
    """
    Get recommended learning path for a user to reach target topic
    Uses graph traversal to find prerequisite chain
    """

    query = """
    MATCH (target:Topic {name: $target_topic})
    MATCH path = (start:Topic)-[:PREREQUISITE_FOR*0..]->(target)
    WHERE NOT (start)<-[:PREREQUISITE_FOR]-(:Topic)

    // Check user's knowledge
    OPTIONAL MATCH (u:User {id: $user_id})-[k:KNOWS]->(start)

    WITH path, start, k
    WHERE k IS NULL OR k.mastery_level < 70

    UNWIND nodes(path) as topic
    RETURN DISTINCT topic.name as name,
                    topic.difficulty as difficulty,
                    topic.estimated_hours as estimated_hours,
                    topic.description as description
    ORDER BY size([n in nodes(path) WHERE n = topic])
    """

    result = await neo4j_session.run(
        query,
        user_id=user_id,
        target_topic=target_topic
    )

    learning_path = []
    async for record in result:
        learning_path.append({
            "name": record["name"],
            "difficulty": record["difficulty"],
            "estimated_hours": record["estimated_hours"],
            "description": record["description"]
        })

    return learning_path


async def get_related_topics(neo4j_session, topic: str, limit: int = 5) -> List[str]:
    """Get topics related to the given topic"""

    query = """
    MATCH (t:Topic {name: $topic})
    MATCH (t)-[:PREREQUISITE_FOR|RELATED_TO]-(related:Topic)
    RETURN DISTINCT related.name as name
    LIMIT $limit
    """

    result = await neo4j_session.run(query, topic=topic, limit=limit)

    related = []
    async for record in result:
        related.append(record["name"])

    return related
