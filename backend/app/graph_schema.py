from neo4j import GraphDatabase

from backend.app.config import settings

CONSTRAINTS_AND_INDEXES = [
    """
    CREATE CONSTRAINT law_id_unique IF NOT EXISTS
    FOR (l:Law)
    REQUIRE l.id IS UNIQUE
    """,
    """
    CREATE CONSTRAINT article_id_unique IF NOT EXISTS
    FOR (a:Article)
    REQUIRE a.id IS UNIQUE
    """,
    """
    CREATE CONSTRAINT case_id_unique IF NOT EXISTS
    FOR (c:LegalCase)
    REQUIRE c.id IS UNIQUE
    """,
    """
    CREATE CONSTRAINT issue_id_unique IF NOT EXISTS
    FOR (i:Issue)
    REQUIRE i.id IS UNIQUE
    """,
    """
    CREATE CONSTRAINT chunk_id_unique IF NOT EXISTS
    FOR (ch:Chunk)
    REQUIRE ch.id IS UNIQUE
    """,
    """
    CREATE INDEX law_name_index IF NOT EXISTS
    FOR (l:Law)
    ON (l.name)
    """,
    """
    CREATE INDEX article_law_id_index IF NOT EXISTS
    FOR (a:Article)
    ON (a.law_id)
    """,
    """
    CREATE INDEX case_number_index IF NOT EXISTS
    FOR (c:LegalCase)
    ON (c.case_number)
    """,
    """
    CREATE INDEX issue_name_index IF NOT EXISTS
    FOR (i:Issue)
    ON (i.name)
    """,
]

def apply_graph_schema() -> None:
    driver = GraphDatabase.driver(
        settings.neo4j_uri,
        auth=(settings.neo4j_user, settings.neo4j_password),
    )

    try:
        with driver.session() as session:
            for query in CONSTRAINTS_AND_INDEXES:
                session.run(query)

    finally:
        driver.close()