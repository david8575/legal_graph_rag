from neo4j import GraphDatabase
from qdrant_client import QdrantClient

from backend.app.config import settings

def check_neo4j() -> dict:
    driver = GraphDatabase.driver(
        settings.neo4j_uri,
        auth=(settings.neo4j_user, settings.neo4j_password)
    )

    try:
        with driver.session() as session:
            result = session.run("RETURN 1 AS ok")
            value = result.single()["ok"]

        return {
            "status": "ok",
            "result": value,
        }
    finally:
        driver.close()

def check_qdrant() -> dict:
    client = QdrantClient(url=settings.qdrant_url)

    collections = client.get_collections()

    return {
        "status": "ok",
        "collections_count": len(collections.collections),
    }